"""V3-only bounded native CPU/RSS sampler on real GitHub-hosted Windows/Linux.

Samples actual process + children with psutil, kills on sampled budget breach,
time limit, capture limit or surviving process descendants. Not a scientific
energy measurement or a hard kernel-enforced instantaneous memory maximum.
"""
from __future__ import annotations
import hashlib
import os
import subprocess
import threading
import time

MAX_WALL_SECONDS = 120
MAX_CAPTURE = 1_000_000
MAX_SAMPLED_RSS_BYTES = 1024 * 1024 * 1024
MAX_SAMPLED_CPU_MS = 120_000
SAMPLE_PERIOD_SECONDS = 0.02


class ResourceDenied(ValueError):
    pass


def bounded_sampled_process(argv, *, cwd, env):
    try:
        import psutil
    except ImportError as exc:
        raise ResourceDenied("F139_V3_PSUTIL_REQUIRED_BOTH_OS") from exc
    if not (type(argv) in (tuple,list) and all(type(x) is str for x in argv)
            and cwd.is_dir() and type(env) is dict):
        raise ResourceDenied("F139_V3_UNTRUSTED_RUNNER")
    if any(x in env for x in (
            "GH_TOKEN","GITHUB_TOKEN","F139_WORKER_HMAC_KEY","OPENAI_API_KEY")):
        raise ResourceDenied("F139_V3_CREDENTIAL_EXPOSURE")
    start=time.monotonic()
    raw=bytearray()
    reader_errors=[]
    over_output=threading.Event()
    proc=subprocess.Popen(
        list(argv),cwd=str(cwd),env=env,stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,stderr=subprocess.STDOUT,bufsize=0,
        creationflags=(subprocess.CREATE_NEW_PROCESS_GROUP
                       if os.name=="nt" else 0),
        start_new_session=(os.name!="nt"),
    )
    root=psutil.Process(proc.pid)
    observed={}
    peak=0
    cpu_peak=0
    samples=0
    live_children={}
    def stop_tree():
        for child in list(live_children.values())[::-1]+[root]:
            try:
                if child.is_running():
                    child.kill()
            except psutil.NoSuchProcess:
                pass
            except psutil.AccessDenied as exc:
                reader_errors.append(str(type(exc).__name__))
        try: proc.kill()
        except ProcessLookupError: pass
    def drain():
        try:
            while True:
                chunk=proc.stdout.read(8192)
                if not chunk:
                    break
                if len(raw)+len(chunk)>MAX_CAPTURE:
                    over_output.set()
                    break
                raw.extend(chunk)
        except (OSError,ValueError) as exc:
            reader_errors.append(type(exc).__name__)
    thread=threading.Thread(target=drain,daemon=True)
    thread.start()
    failed=None
    try:
        while True:
            if time.monotonic()-start > MAX_WALL_SECONDS:
                failed="WALL_BUDGET"; break
            if over_output.is_set() or reader_errors:
                failed="OUTPUT_OR_READER"; break
            try:
                nodes=[root]+root.children(recursive=True)
            except psutil.NoSuchProcess:
                nodes=[]
            except (psutil.AccessDenied,psutil.Error) as exc:
                failed="UNREADABLE_PROCESS_TREE"; break
            rss=0
            for child in nodes:
                try:
                    pid=child.pid
                    create=child.create_time()
                    key=(pid,create)
                    if key not in observed:
                        observed[key]=[0.0,0.0]
                    cpu=child.cpu_times()
                    total=cpu.user+cpu.system
                    observed[key][0]=max(observed[key][0],total)
                    observed[key][1]=max(observed[key][1],child.memory_info().rss)
                    rss+=child.memory_info().rss
                    if pid!=proc.pid:
                        live_children[key]=child
                except psutil.NoSuchProcess:
                    continue
                except (psutil.AccessDenied,psutil.Error):
                    failed="UNREADABLE_RESOURCE_SAMPLE"; break
            if failed: break
            samples+=1
            peak=max(peak,rss)
            cpu_peak=int(sum(item[0] for item in observed.values())*1000)
            if peak>MAX_SAMPLED_RSS_BYTES or cpu_peak>MAX_SAMPLED_CPU_MS:
                failed="RESOURCE_BUDGET"; break
            if proc.poll() is not None:
                break
            time.sleep(SAMPLE_PERIOD_SECONDS)
        if failed:
            stop_tree()
        try: proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            failed="STUCK_DESCENDANT"; stop_tree(); proc.wait(timeout=5)
        thread.join(timeout=4)
        if thread.is_alive():
            failed="CAPTURE_PIPE_DESCENDANT"; stop_tree()
            thread.join(timeout=3)
        if thread.is_alive() or reader_errors or over_output.is_set():
            failed=failed or "OUTPUT_OR_TREE_CAPTURE"
        for child in live_children.values():
            try:
                if child.is_running() and child.status()!=psutil.STATUS_ZOMBIE:
                    failed="ORPHANED_CHILD"; stop_tree()
                    break
            except psutil.NoSuchProcess:
                continue
        if failed:
            raise ResourceDenied("F139_V3_BOUNDED_CHILD_"+failed)
        if samples<1 or peak<=0 or cpu_peak<=0:
            raise ResourceDenied("F139_V3_MISSING_REAL_CPU_OR_RSS_SAMPLES")
        if len(raw)>MAX_CAPTURE:
            raise ResourceDenied("F139_V3_OUTPUT_OVERRUN")
        return {
            "stdout":bytes(raw),
            "returncode":proc.returncode,
            "child_peak_rss_bytes":peak,
            "child_cpu_ms":cpu_peak,
            "resource_samples":samples,
            "resource_accounting":"psutil-sampled-process-tree-v1",
            "resource_budget_verified":True,
        }
    finally:
        try:
            if proc.poll() is None: stop_tree()
        finally:
            if proc.stdout: proc.stdout.close()

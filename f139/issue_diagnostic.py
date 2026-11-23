"""Bounded, issue-specific Go package diagnostic. Not code generation or science."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import threading
import time

from f139.verify_ticket import (
    D2K_DIAGNOSTIC_SCHEMA, D2K_PACKAGES, admit, inputs_from_env, demand,
)

MAX_OUTPUT = 100000
MAX_EXCERPT = 12000
TIMEOUT_SEC = 110

def bounded_run(command, *, env, timeout=TIMEOUT_SEC):
    """Capture a real Go test with bounded RAM and terminate on output overflow.

    A dedicated reader drains PIPE incrementally; subprocess.run(input=PIPE)
    instead buffers arbitrary output before its caller can enforce any limit.
    """
    process = subprocess.Popen(command, stdin=subprocess.DEVNULL,
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                               env=env, bufsize=0)
    chunks = []
    total = [0]
    overflow = threading.Event()
    reader_errors = []

    def collect():
        try:
            while True:
                part = process.stdout.read(8192)
                if not part:
                    break
                allowed = MAX_OUTPUT - total[0]
                if len(part) > allowed:
                    if allowed:
                        chunks.append(part[:allowed])
                        total[0] += allowed
                    overflow.set()
                    # Terminate the noisy child immediately, before it can consume
                    # unbounded memory in a user-space capture buffer.
                    try:
                        process.kill()
                    except OSError:
                        pass
                    break
                chunks.append(part)
                total[0] += len(part)
        except OSError as exc:
            reader_errors.append(exc)
        finally:
            process.stdout.close()

    reader = threading.Thread(target=collect, name="f139-d2k-bounded-output",
                              daemon=True)
    reader.start()
    timed_out = False
    try:
        returncode = process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
        process.kill()
        returncode = process.wait()
    reader.join(timeout=5)
    demand(not reader.is_alive(), "D2K_CAPTURE_READER_STALLED")
    demand(not reader_errors, "D2K_CAPTURE_READER_FAILED")
    raw = b"".join(chunks)
    if overflow.is_set():
        marker = b"[F139_D2K_OUTPUT_LIMIT_EXCEEDED: process terminated]\n"
        raw = marker + raw[:MAX_OUTPUT-len(marker)]
        return subprocess.CompletedProcess(command, 125, raw)
    if timed_out:
        raise subprocess.TimeoutExpired(command, timeout, output=raw)
    return subprocess.CompletedProcess(command, returncode, raw)


def diagnose(inputs: dict, *, command_runner=None, clock=time.monotonic):
    admit(inputs)
    demand(inputs["ticket"].startswith("f139-d2k-")
           and inputs["target_package"] in D2K_PACKAGES,
           "D2K_TARGET_NOT_AUTHORIZED")
    env = os.environ.copy()
    env.pop("F139_WORKER_HMAC_KEY", None)
    env.pop("GH_TOKEN", None)
    env.pop("GITHUB_TOKEN", None)
    cmd = ["go", "test", "-count=1", "-timeout=90s", inputs["target_package"]]
    began=clock()
    try:
        if command_runner is None:
            process = bounded_run(cmd, timeout=TIMEOUT_SEC, env=env)
        else:
            # Injection seam is limited to hosted deterministic test fixtures.
            process = command_runner(cmd, check=False, stdin=subprocess.DEVNULL,
                                     stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                     timeout=TIMEOUT_SEC, env=env)
        raw=process.stdout if isinstance(process.stdout,bytes) else b""
        demand(len(raw) <= MAX_OUTPUT,"D2K_OUTPUT_TOO_LARGE")
        code=int(process.returncode)
        outcome="PASS" if code==0 else "TEST_FAILURE"
        demand(0 <= code <= 255, "D2K_EXIT_CODE_INVALID")
    except subprocess.TimeoutExpired as exc:
        raw=exc.stdout if isinstance(exc.stdout,bytes) else b""
        demand(len(raw) <= MAX_OUTPUT, "D2K_TIMEOUT_OUTPUT_TOO_LARGE")
        code=-1
        outcome="TIMEOUT"
    milliseconds=min(120000,max(0,round((clock()-began)*1000)))
    return {
        "schema":D2K_DIAGNOSTIC_SCHEMA,
        "source_sha":inputs["head_sha"],
        "issue_number":int(inputs["issue_number"]),
        "issue_id":int(inputs["issue_id"]),
        "body_sha256":inputs["body_sha256"],
        "target_package":inputs["target_package"],
        "run_id":int(inputs["run_id"]),
        "os":inputs["os"],
        "outcome":outcome,
        "returncode":code,
        "duration_ms":milliseconds,
        "output_sha256":hashlib.sha256(raw).hexdigest(),
        "output_excerpt":raw[:MAX_EXCERPT].decode("utf-8",errors="replace"),
        "output_bytes":len(raw),
        "scientific_first_use":False,
        "paid_model_calls":0,
    }

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    demand(args.output.parent.is_dir() and not args.output.exists(),
           "D2K_OUTPUT_PATH_EXISTS")
    report=diagnose(inputs_from_env())
    data=(json.dumps(report,sort_keys=True,separators=(",",":"),ensure_ascii=True)+"\n").encode()
    demand(len(data) <= 32768, "D2K_RESULT_OVERSIZE")
    with args.output.open("xb") as fp:
        fp.write(data)
        fp.flush()
        os.fsync(fp.fileno())
    print("F139_D2K_PACKAGE_DIAGNOSTIC_RECORDED="+report["outcome"])
    print("F139_D2K_SCIENCE_ORIGINALS=ZERO")

if __name__=="__main__":
    main()

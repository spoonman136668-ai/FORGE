"""Bounded, issue-specific Go package diagnostic. Not code generation or science."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import signal
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

# D2K Go diagnostics have no entitlement to owner HMAC/ticket data,
# GH credentials, action identity, or inherited arbitrary environment.
# Keep only operating-system and Go runtime settings; disable module
# downloads and ambient user-level Go configuration.
_GO_CHILD_ENV_KEYS = frozenset((
    "PATH", "PATHEXT", "SYSTEMROOT", "WINDIR", "COMSPEC",
    "HOME", "USERPROFILE", "HOMEDRIVE", "HOMEPATH", "LOCALAPPDATA",
    "APPDATA", "TMP", "TEMP", "TMPDIR", "LANG", "LC_ALL",
    "GOROOT", "GOPATH", "GOCACHE", "GOMODCACHE",
    "GOFLAGS", "GOMAXPROCS", "GOMEMLIMIT", "CGO_ENABLED", "CC", "CXX",
))


def _go_child_environment(source):
    env = {key: value for key, value in source.items()
           if key.upper() in _GO_CHILD_ENV_KEYS}
    # No outbound dependency fetching and no unaudited Go user overrides.
    env.update(GOPROXY="off", GOSUMDB="off",
               GOTOOLCHAIN="local", GOENV="off")
    return env


class _WindowsDiagnosticJob:
    """Bound a D2K child and its descendants to one Windows Job Object.

    KILL_ON_JOB_CLOSE retains descendants even when their direct parent exits.
    This is process-tree cleanup, not a claim of general worker isolation.
    """
    def __init__(self):
        import ctypes
        from ctypes import wintypes

        class Basic(ctypes.Structure):
            _fields_ = [
                ("PerProcessUserTimeLimit", ctypes.c_longlong),
                ("PerJobUserTimeLimit", ctypes.c_longlong),
                ("LimitFlags", wintypes.DWORD),
                ("MinimumWorkingSetSize", ctypes.c_size_t),
                ("MaximumWorkingSetSize", ctypes.c_size_t),
                ("ActiveProcessLimit", wintypes.DWORD),
                ("Affinity", ctypes.c_size_t),
                ("PriorityClass", wintypes.DWORD),
                ("SchedulingClass", wintypes.DWORD),
            ]

        class Io(ctypes.Structure):
            _fields_ = [(n, ctypes.c_ulonglong) for n in (
                "ReadOperationCount", "WriteOperationCount", "OtherOperationCount",
                "ReadTransferCount", "WriteTransferCount", "OtherTransferCount")]

        class Extended(ctypes.Structure):
            _fields_ = [
                ("BasicLimitInformation", Basic),
                ("IoInfo", Io),
                ("ProcessMemoryLimit", ctypes.c_size_t),
                ("JobMemoryLimit", ctypes.c_size_t),
                ("PeakProcessMemoryUsed", ctypes.c_size_t),
                ("PeakJobMemoryUsed", ctypes.c_size_t),
            ]

        self._ctypes = ctypes
        self._lock = threading.Lock()
        self._api = ctypes.WinDLL("kernel32", use_last_error=True)
        self._api.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
        self._api.CreateJobObjectW.restype = wintypes.HANDLE
        self._api.SetInformationJobObject.argtypes = [
            wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
        self._api.SetInformationJobObject.restype = wintypes.BOOL
        self._api.AssignProcessToJobObject.argtypes = [
            wintypes.HANDLE, wintypes.HANDLE]
        self._api.AssignProcessToJobObject.restype = wintypes.BOOL
        self._api.CloseHandle.argtypes = [wintypes.HANDLE]
        self._api.CloseHandle.restype = wintypes.BOOL
        self._handle = self._api.CreateJobObjectW(None, None)
        demand(bool(self._handle), "D2K_WINDOWS_JOB_CREATION_FAILED")
        limits = Extended()
        limits.BasicLimitInformation.LimitFlags = 0x2000  # KILL_ON_JOB_CLOSE
        if not self._api.SetInformationJobObject(
                self._handle, 9, ctypes.byref(limits), ctypes.sizeof(limits)):
            self.close()
            demand(False, "D2K_WINDOWS_JOB_LIMIT_FAILED")

    def attach(self, process):
        with self._lock:
            demand(bool(self._handle), "D2K_WINDOWS_JOB_ALREADY_CLOSED")
            demand(bool(self._api.AssignProcessToJobObject(
                self._handle, process._handle)), "D2K_WINDOWS_JOB_ATTACH_FAILED")

    def close(self):
        with self._lock:
            if self._handle:
                handle, self._handle = self._handle, None
                demand(bool(self._api.CloseHandle(handle)),
                       "D2K_WINDOWS_JOB_CLOSE_FAILED")



def _resume_windows_primary_thread(process):
    """Resume exactly one still-suspended primary thread, after Job admission.

    Popen closes the CreateProcess primary-thread handle internally. Enumerate
    the new suspended PID's threads through Toolhelp, refusing ambiguous or
    inaccessible state. Returning zero from ResumeThread means the child was
    already runnable and is therefore a containment failure, not success.
    """
    import ctypes
    from ctypes import wintypes

    class ThreadEntry(ctypes.Structure):
        _fields_ = (
            ("dwSize", wintypes.DWORD),
            ("cntUsage", wintypes.DWORD),
            ("th32ThreadID", wintypes.DWORD),
            ("th32OwnerProcessID", wintypes.DWORD),
            ("tpBasePri", wintypes.LONG),
            ("tpDeltaPri", wintypes.LONG),
            ("dwFlags", wintypes.DWORD),
        )

    api = ctypes.WinDLL("kernel32", use_last_error=True)
    api.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
    api.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    api.Thread32First.argtypes = [wintypes.HANDLE, ctypes.POINTER(ThreadEntry)]
    api.Thread32First.restype = wintypes.BOOL
    api.Thread32Next.argtypes = [wintypes.HANDLE, ctypes.POINTER(ThreadEntry)]
    api.Thread32Next.restype = wintypes.BOOL
    api.OpenThread.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    api.OpenThread.restype = wintypes.HANDLE
    api.ResumeThread.argtypes = [wintypes.HANDLE]
    api.ResumeThread.restype = wintypes.DWORD
    api.CloseHandle.argtypes = [wintypes.HANDLE]
    api.CloseHandle.restype = wintypes.BOOL
    snapshot = api.CreateToolhelp32Snapshot(0x00000004, 0)  # all threads
    demand(snapshot and snapshot != ctypes.c_void_p(-1).value,
           "D2K_WINDOWS_THREAD_SNAPSHOT_FAILED")
    try:
        entry = ThreadEntry()
        entry.dwSize = ctypes.sizeof(entry)
        demand(bool(api.Thread32First(snapshot, ctypes.byref(entry))),
               "D2K_WINDOWS_THREAD_SNAPSHOT_EMPTY")
        threads = []
        while True:
            if entry.th32OwnerProcessID == process.pid:
                threads.append(entry.th32ThreadID)
            if not api.Thread32Next(snapshot, ctypes.byref(entry)):
                demand(ctypes.get_last_error() == 18,
                       "D2K_WINDOWS_THREAD_SNAPSHOT_INCOMPLETE")
                break
        demand(len(threads) == 1, "D2K_WINDOWS_PRIMARY_THREAD_AMBIGUOUS")
    finally:
        api.CloseHandle(snapshot)
    thread = api.OpenThread(0x0002, False, threads[0])  # THREAD_SUSPEND_RESUME
    demand(bool(thread), "D2K_WINDOWS_PRIMARY_THREAD_OPEN_FAILED")
    try:
        # Exactly one CREATE_SUSPENDED level must be present.
        demand(api.ResumeThread(thread) == 1,
               "D2K_WINDOWS_PRIMARY_THREAD_RESUME_FAILED")
    finally:
        api.CloseHandle(thread)


def _posix_wait_unreaped(process, timeout):
    """Observe child exit without releasing its PID/process-group identity.

    Popen.wait()/poll() reap immediately. A successful wait followed by
    os.killpg(PID, SIGKILL) is unsafe if PID/PGID has been recycled in between.
    Retain the direct child as an unreaped zombie until the final group signal.
    Only the finalizer is allowed to call process.wait().
    """
    deadline = time.monotonic() + timeout
    while True:
        status = os.waitid(os.P_PID, process.pid,
                           os.WEXITED | os.WNOWAIT | os.WNOHANG)
        if status is not None:
            if status.si_code == os.CLD_EXITED:
                return status.si_status
            if status.si_code in (os.CLD_KILLED, os.CLD_DUMPED):
                return -status.si_status
            demand(False, "D2K_POSIX_CHILD_EXIT_STATUS_UNTRUSTED")
        left = deadline - time.monotonic()
        if left <= 0:
            raise subprocess.TimeoutExpired(process.args, timeout)
        time.sleep(min(0.02, left))


def bounded_run(command, *, env, timeout=TIMEOUT_SEC):
    """Capture bounded output and clean up inherited-pipe descendants.

    POSIX children enter a new process group; Windows children must join a
    KILL_ON_JOB_CLOSE Job Object. Failed Windows admission is an error, never
    a silent fallback to process.kill() of only the direct child.
    """
    # Defence in depth: even direct bounded_run callers cannot pass through
    # arbitrary signed-ticket or host secrets in the test process environment.
    env = _go_child_environment(env)
    job = _WindowsDiagnosticJob() if os.name == "nt" else None
    process = None
    cleanup_gate = threading.Lock()
    finalized = [False]
    try:
        process = subprocess.Popen(
            command, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, env=env, bufsize=0,
            creationflags=((subprocess.CREATE_NEW_PROCESS_GROUP | 0x00000004)
                           if os.name == "nt" else 0),
            start_new_session=(os.name != "nt"))
        # 0x4 = CREATE_SUSPENDED. No user code or descendant can execute
        # before the Job Object accepts the child and the sole primary thread
        # has been resumed. Failure closes the Job and kills the child.
        if job is not None:
            job.attach(process)
            _resume_windows_primary_thread(process)

        chunks = []
        total = [0]
        overflow = threading.Event()
        reader_errors = []
        cleanup_errors = []

        def stop_tree():
            # The reader may still run after a failing waitid/exception.
            # Once final cleanup starts, it must never send another signal:
            # the leader may be reaped and its PGID recycled shortly after.
            with cleanup_gate:
                if finalized[0]:
                    return
                try:
                    if job is not None:
                        job.close()
                    else:
                        try:
                            os.killpg(process.pid, signal.SIGKILL)
                        except ProcessLookupError:
                            pass
                except (OSError, ValueError) as exc:
                    cleanup_errors.append(type(exc).__name__)
                # Never poll/reap POSIX before final cleanup.
                if job is not None and process.poll() is None:
                    try:
                        process.kill()
                    except ProcessLookupError:
                        pass

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
                        stop_tree()
                        break
                    chunks.append(part)
                    total[0] += len(part)
            except (OSError, ValueError) as exc:
                reader_errors.append(type(exc).__name__)
            finally:
                process.stdout.close()

        reader = threading.Thread(target=collect, name="f139-d2k-bounded-output",
                                  daemon=True)
        reader.start()
        timed_out = False
        try:
            returncode = (process.wait(timeout=timeout)
                          if job is not None else _posix_wait_unreaped(process, timeout))
        except subprocess.TimeoutExpired:
            timed_out = True
            stop_tree()
            returncode = (process.wait(timeout=5)
                          if job is not None else _posix_wait_unreaped(process, 5))
        reader.join(timeout=2)
        # Parent exit does not prove that inherited stdout handles closed.
        orphaned = reader.is_alive() and not timed_out and not overflow.is_set()
        if reader.is_alive():
            stop_tree()
            reader.join(timeout=5)
        demand(not reader.is_alive(), "D2K_CAPTURE_READER_STALLED")
        demand(not cleanup_errors, "D2K_PROCESS_TREE_CLEANUP_FAILED")
        demand(not reader_errors, "D2K_CAPTURE_READER_FAILED")
        # Preserve the original fail-closed outcome after successful cleanup.
        demand(not orphaned, "D2K_CAPTURE_READER_STALLED")
        raw = b"".join(chunks)
        if overflow.is_set():
            marker = b"[F139_D2K_OUTPUT_LIMIT_EXCEEDED: process terminated]\n"
            raw = marker + raw[:MAX_OUTPUT-len(marker)]
            return subprocess.CompletedProcess(command, 125, raw)
        if timed_out:
            raise subprocess.TimeoutExpired(command, timeout, output=raw)
        return subprocess.CompletedProcess(command, returncode, raw)
    finally:
        if process is not None:
            try:
                # Atomically fence late reader stop_tree calls before the last
                # owned-group signal. POSIX child remains unreaped until after
                # this signal; no thread can signal after identity release.
                with cleanup_gate:
                    finalized[0] = True
                    if job is not None:
                        job.close()
                    else:
                        try:
                            os.killpg(process.pid, signal.SIGKILL)
                        except ProcessLookupError:
                            pass
            finally:
                if job is None:
                    # Reap only AFTER all possible process-group signals:
                    # until now the child PID cannot be recycled.
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        try:
                            process.kill()
                        except ProcessLookupError:
                            pass
                        process.wait(timeout=5)
                elif process.poll() is None:
                    try:
                        process.kill()
                    except ProcessLookupError:
                        pass
                    process.wait(timeout=5)
        elif job is not None:
            job.close()


def diagnose(inputs: dict, *, command_runner=None, clock=time.monotonic):
    admit(inputs)
    demand(inputs["ticket"].startswith("f139-d2k-")
           and inputs["target_package"] in D2K_PACKAGES,
           "D2K_TARGET_NOT_AUTHORIZED")
    env = _go_child_environment(os.environ)
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

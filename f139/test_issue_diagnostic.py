"""D2K source-bound Go diagnostic qualification with synthetic process outputs."""
import hashlib
import os
import subprocess
import sys
import unittest
from types import SimpleNamespace
from unittest import mock

from f139.issue_diagnostic import diagnose, bounded_run, MAX_OUTPUT, TIMEOUT_SEC
from f139.verify_ticket import signature, Untrusted, REPO

SOURCE = "e1b16d0a4097e9fd3d61c9ee635486a72395cf4b"
KEY = "f139-test-hmac-secret-never-deploy-00000000000000000000"
BODY = "a" * 64


def authorized():
    ticket="f139-d2k-i1401-"+SOURCE[:12]+"-"+BODY[:8]
    data={
        "key":KEY,"ticket":ticket,"lane":"Qualification","source_sha":SOURCE,
        "epoch":"1","repository":REPO,"ref":"refs/heads/main",
        "event":"workflow_dispatch","head_sha":SOURCE,"run_attempt":"1",
        "run_id":"12345","os":"windows-latest","issue_number":"1401",
        "issue_id":"91401","body_sha256":BODY,"target_package":"./planner",
    }
    data["signature"]=signature(
        KEY,ticket,"Qualification",SOURCE,"1",issue_number="1401",
        issue_id="91401",body_sha256=BODY,target_package="./planner")
    return data


class D2KPackageDiagnosticTests(unittest.TestCase):
    def test_exact_go_command_and_clean_child_environment(self):
        calls=[]
        def runner(command, **kwargs):
            calls.append((command,kwargs))
            return SimpleNamespace(returncode=0,stdout=b"ok\n")
        with mock.patch.dict(os.environ, {
            "GH_TOKEN":"test-secret","GITHUB_TOKEN":"test-secret",
            "F139_WORKER_HMAC_KEY":"test-secret","F139_SIGNATURE":"test-signed-authority",
            "F139_TICKET":"test-ticket","F139_ISSUE_NUMBER":"1401",
            "OPENAI_API_KEY":"test-secret","RUNNER_TEMP":"secret-path",
            "GITHUB_WORKSPACE":"secret-workspace","PYTHONPATH":"secret-path",
            "EXTRA_DIAGNOSTIC_SECRET":"secret","GOPROXY":"https://user:password@example.invalid",
            "GOFLAGS":"-p=2","GOMAXPROCS":"2"}):
            result=diagnose(authorized(),command_runner=runner,clock=lambda:5)
        self.assertEqual(result["outcome"],"PASS")
        self.assertEqual(result["returncode"],0)
        self.assertEqual(result["issue_number"],1401)
        self.assertEqual(result["body_sha256"],BODY)
        self.assertEqual(result["output_sha256"],hashlib.sha256(b"ok\n").hexdigest())
        command,options=calls[0]
        self.assertEqual(command,["go","test","-count=1","-timeout=90s","./planner"])
        self.assertEqual(options["stdin"],subprocess.DEVNULL)
        self.assertEqual(options["timeout"],TIMEOUT_SEC)
        for key in ("GH_TOKEN","GITHUB_TOKEN","F139_WORKER_HMAC_KEY",
                    "F139_SIGNATURE","F139_TICKET","F139_ISSUE_NUMBER",
                    "OPENAI_API_KEY","RUNNER_TEMP","GITHUB_WORKSPACE",
                    "PYTHONPATH","EXTRA_DIAGNOSTIC_SECRET"):
            self.assertNotIn(key,options["env"])
        self.assertEqual(options["env"]["GOFLAGS"], "-p=2")
        self.assertEqual(options["env"]["GOMAXPROCS"], "2")
        for key in ("GOPROXY", "GOSUMDB", "GOTOOLCHAIN", "GOENV"):
            self.assertIn(key, options["env"])
        self.assertEqual(options["env"]["GOPROXY"], "off")
        self.assertEqual(options["env"]["GOSUMDB"], "off")
        self.assertEqual(options["env"]["GOTOOLCHAIN"], "local")
        self.assertEqual(options["env"]["GOENV"], "off")

    def test_test_failure_preserved_not_promoted(self):
        report=diagnose(authorized(),command_runner=lambda *a,**k:
                        SimpleNamespace(returncode=1,stdout=b"failed"))
        self.assertEqual(report["outcome"],"TEST_FAILURE")
        self.assertEqual(report["returncode"],1)
        self.assertFalse(report["scientific_first_use"])
        self.assertEqual(report["paid_model_calls"],0)

    def test_timeout_preserved_not_replayed(self):
        def runner(*args,**kwargs):
            raise subprocess.TimeoutExpired(args[0],TIMEOUT_SEC,output=b"timeout")
        report=diagnose(authorized(),command_runner=runner)
        self.assertEqual(report["outcome"],"TIMEOUT")
        self.assertEqual(report["returncode"],-1)

    def test_real_subprocess_output_limit_kills_and_retains_negative(self):
        outcome = bounded_run(
            [sys.executable, "-c", "import sys; sys.stdout.write('X' * 400000); sys.stdout.flush()"],
            env=os.environ.copy(),timeout=10)
        self.assertEqual(outcome.returncode,125)
        self.assertLessEqual(len(outcome.stdout),MAX_OUTPUT)
        self.assertIn(b"F139_D2K_OUTPUT_LIMIT_EXCEEDED",outcome.stdout[:100])

    def test_real_subprocess_timeout_retains_bounded_prefix(self):
        with self.assertRaises(subprocess.TimeoutExpired) as caught:
            bounded_run(
                [sys.executable,"-c", "import sys,time; print('begin',flush=True);time.sleep(20)"],
                env=os.environ.copy(),timeout=0.5)
        self.assertIn(b"begin",caught.exception.output)
        self.assertLessEqual(len(caught.exception.output),MAX_OUTPUT)

    def test_wrong_signature_invalid_package_and_oversize_fail_closed(self):
        item=authorized();item["target_package"]="../private"
        with self.assertRaises(Untrusted):
            diagnose(item,command_runner=lambda *a,**k:None)
        item=authorized();item["signature"]="0"*64
        with self.assertRaises(Untrusted):
            diagnose(item,command_runner=lambda *a,**k:None)
        with self.assertRaisesRegex(Untrusted,"D2K_OUTPUT_TOO_LARGE"):
            diagnose(authorized(),command_runner=lambda *a,**k:
                     SimpleNamespace(returncode=0,stdout=b"x"*(MAX_OUTPUT+1)))
        with self.assertRaisesRegex(Untrusted,"D2K_EXIT_CODE_INVALID"):
            diagnose(authorized(),command_runner=lambda *a,**k:
                     SimpleNamespace(returncode=-9,stdout=b"unexpected signal"))

    @staticmethod
    def _descendant_alive(pid):
        if sys.platform == "win32":
            import ctypes
            from ctypes import wintypes
            api = ctypes.WinDLL("kernel32", use_last_error=True)
            api.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
            api.OpenProcess.restype = wintypes.HANDLE
            api.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
            api.GetExitCodeProcess.restype = wintypes.BOOL
            api.CloseHandle.argtypes = [wintypes.HANDLE]
            h = api.OpenProcess(0x1000, False, pid)
            if not h:
                return False
            try:
                result = wintypes.DWORD()
                if not api.GetExitCodeProcess(h, ctypes.byref(result)):
                    raise AssertionError("child process state unreadable")
                return result.value == 259  # STILL_ACTIVE
            finally:
                api.CloseHandle(h)
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return False
        # Linux CI can leave an exited orphan as a harmless init-owned zombie.
        from pathlib import Path
        stat = Path("/proc") / str(pid) / "stat"
        if stat.is_file() and stat.read_text().rsplit(")", 1)[1].strip().startswith("Z"):
            return False
        return True

    def test_real_descendant_held_stdout_negative_is_cleaned(self):
        """A legitimate parent exit must never leave a 30-second test child alive."""
        import tempfile
        import time
        from pathlib import Path
        script = (
            "import subprocess,sys;"
            "p=subprocess.Popen([sys.executable,'-c','import time;time.sleep(30)'],"
            "stdout=sys.stdout,stderr=sys.stderr);"
            "open(sys.argv[1],'w').write(str(p.pid));"
            "print('parent done',flush=True)"
        )
        with tempfile.TemporaryDirectory(prefix="forge-rsi-r14-") as d:
            pidfile = Path(d) / "child.pid"
            began = time.monotonic()
            pid = None
            try:
                with self.assertRaisesRegex(Untrusted, "D2K_CAPTURE_READER_STALLED"):
                    bounded_run([sys.executable, "-c", script, str(pidfile)],
                                env=os.environ.copy(), timeout=12)
                self.assertTrue(pidfile.is_file(), "test parent did not spawn child")
                pid = int(pidfile.read_text())
                for _ in range(20):
                    if not self._descendant_alive(pid):
                        break
                    time.sleep(0.1)
                self.assertFalse(self._descendant_alive(pid),
                                 "original bounded diagnostic leaked a live descendant")
                self.assertLess(time.monotonic() - began, 8)
            finally:
                if pid is None and pidfile.exists():
                    pid = int(pidfile.read_text())
                if pid is not None and self._descendant_alive(pid):
                    if sys.platform == "win32":
                        subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"],
                                       stdout=subprocess.DEVNULL,
                                       stderr=subprocess.DEVNULL, timeout=5,
                                       check=False)
                    else:
                        import signal
                        os.kill(pid, signal.SIGKILL)

    def test_normal_parent_exit_does_not_leave_redirected_descendant_running(self):
        """Exit 0 and pipe EOF do not authorize a background child to persist."""
        import tempfile
        import time
        from pathlib import Path
        script = (
            "import subprocess,sys;"
            "p=subprocess.Popen([sys.executable,'-c','import time;time.sleep(30)'],"
            "stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);"
            "open(sys.argv[1],'w').write(str(p.pid));"
            "print('done',flush=True)"
        )
        with tempfile.TemporaryDirectory(prefix="forge-rsi-r14-normal-") as d:
            pidfile = Path(d) / "child.pid"
            pid = None
            try:
                completed = bounded_run([sys.executable, "-c", script, str(pidfile)],
                                        env=os.environ.copy(), timeout=12)
                self.assertEqual(completed.returncode, 0)
                self.assertIn(b"done", completed.stdout)
                self.assertTrue(pidfile.is_file())
                pid = int(pidfile.read_text())
                for _ in range(20):
                    if not self._descendant_alive(pid):
                        break
                    time.sleep(0.1)
                self.assertFalse(self._descendant_alive(pid),
                                 "successful parent exit leaked a live descendant")
            finally:
                if pid is None and pidfile.exists():
                    pid = int(pidfile.read_text())
                if pid is not None and self._descendant_alive(pid):
                    if sys.platform == "win32":
                        subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"],
                                       stdout=subprocess.DEVNULL,
                                       stderr=subprocess.DEVNULL, timeout=5,
                                       check=False)
                    else:
                        import signal
                        os.kill(pid, signal.SIGKILL)

    @unittest.skipIf(sys.platform == "win32", "POSIX unreaped child identity")
    def test_posix_retains_group_leader_until_final_signal(self):
        """The cleanup group signal must precede the Popen leader reap."""
        import signal
        from f139 import issue_diagnostic
        real_killpg = os.killpg
        observed = []
        def inspect_group(pgid, signo):
            self.assertEqual(signo, signal.SIGKILL)
            status = os.waitid(os.P_PID, pgid,
                               os.WEXITED | os.WNOWAIT | os.WNOHANG)
            self.assertIsNotNone(status,
                                 "leader reaped before final group cleanup")
            observed.append(pgid)
            return real_killpg(pgid, signo)
        with mock.patch.object(issue_diagnostic.os, "killpg",
                               side_effect=inspect_group):
            completed = bounded_run(
                [sys.executable, "-c", "print('done', flush=True)"],
                env=os.environ.copy(), timeout=8)
        self.assertEqual(completed.returncode, 0)
        self.assertEqual(completed.stdout, b"done\n")
        self.assertEqual(len(observed), 1)

    def test_direct_bounded_runner_also_sanitizes_credentials(self):
        from f139.issue_diagnostic import _go_child_environment
        raw = {"PATH": os.environ.get("PATH", ""),
               "F139_SIGNATURE": "signed-authority",
               "GH_TOKEN": "private-token",
               "GITHUB_TOKEN": "private-token",
               "GOPROXY": "https://secret@example.invalid"}
        safe = _go_child_environment(raw)
        self.assertEqual(safe["PATH"], raw["PATH"])
        self.assertEqual(safe["GOPROXY"], "off")
        self.assertNotIn("F139_SIGNATURE", safe)
        self.assertNotIn("GH_TOKEN", safe)
        self.assertNotIn("GITHUB_TOKEN", safe)

    @unittest.skipUnless(sys.platform == "win32", "Windows Job failure-path contract")
    def test_windows_job_admission_and_resume_errors_leave_no_child(self):
        """Injected pre-resume failures must kill/reap the suspended child."""
        from f139 import issue_diagnostic
        script = "import time;time.sleep(30)"
        candidates = (
            ("attach", "F139_D2K_WINDOWS_JOB_ATTACH_FAILED"),
            ("resume", "F139_D2K_WINDOWS_THREAD_SNAPSHOT_FAILED"),
            ("resume", "F139_D2K_WINDOWS_PRIMARY_THREAD_RESUME_FAILED"),
        )
        for stage, reason in candidates:
            with self.subTest(stage=stage, reason=reason):
                observed = []
                def failing_attach(job, child):
                    observed.append(child.pid)
                    raise Untrusted(reason)
                def failing_resume(child):
                    observed.append(child.pid)
                    raise Untrusted(reason)
                if stage == "attach":
                    patch = mock.patch.object(issue_diagnostic._WindowsDiagnosticJob,
                                              "attach", failing_attach)
                else:
                    patch = mock.patch.object(issue_diagnostic,
                                              "_resume_windows_primary_thread",
                                              failing_resume)
                with patch:
                    with self.assertRaisesRegex(Untrusted, reason):
                        bounded_run([sys.executable, "-c", script],
                                    env=os.environ.copy(), timeout=8)
                self.assertEqual(len(observed), 1)
                self.assertFalse(self._descendant_alive(observed[0]),
                                 "injected failure leaked a suspended child")

    @unittest.skipUnless(sys.platform == "win32", "Windows Job failure-path contract")
    def test_windows_exception_after_resumption_kills_job(self):
        """An error after a successful resume still closes the owned Job."""
        from f139 import issue_diagnostic
        real_resume = issue_diagnostic._resume_windows_primary_thread
        observed = []
        def throw_after_resume(process):
            observed.append(process.pid)
            real_resume(process)
            raise Untrusted("F139_D2K_WINDOWS_POST_RESUME_FAILURE")
        with mock.patch.object(issue_diagnostic,
                               "_resume_windows_primary_thread", throw_after_resume):
            with self.assertRaisesRegex(Untrusted, "D2K_WINDOWS_POST_RESUME_FAILURE"):
                bounded_run([sys.executable, "-c", "import time;time.sleep(30)"],
                            env=os.environ.copy(), timeout=8)
        self.assertEqual(len(observed), 1)
        self.assertFalse(self._descendant_alive(observed[0]),
                         "exception after resumption leaked a child")

    @unittest.skipUnless(sys.platform == "win32", "Windows suspended-start contract")
    def test_windows_rapid_parent_exit_still_assigned_before_running(self):
        # Old attach-after-Popen fails intermittently for immediate exits.
        # Repeated quick exits must work on the original native Windows CI.
        for attempt in range(8):
            with self.subTest(attempt=attempt):
                completed = bounded_run(
                    [sys.executable, "-c", "import sys;sys.stdout.write('short')"],
                    env=os.environ.copy(), timeout=8)
                self.assertEqual((completed.returncode, completed.stdout),
                                 (0, b"short"))

    def test_regular_small_output_preserved(self):
        result = bounded_run(
            [sys.executable, "-c", "print('ok',flush=True)"],
            env=os.environ.copy(), timeout=8)
        # Python's text print uses CRLF on Windows, LF on POSIX.
        self.assertEqual((result.returncode, result.stdout),
                         (0, b"ok" + os.linesep.encode("ascii")))

    def test_bounded_tree_cleanup_does_not_admit_worker_or_science(self):
        """The signed D2K receipt and exact diagnostic command remain intact."""
        report = diagnose(authorized(), command_runner=lambda *a, **kw:
                          SimpleNamespace(returncode=0, stdout=b"ok"))
        self.assertFalse(report["scientific_first_use"])
        self.assertEqual(report["paid_model_calls"], 0)
        self.assertEqual(report["outcome"], "PASS")
        self.assertEqual(report["target_package"], "./planner")

    def test_output_overflow_also_cleans_descendant(self):
        """Overflow must reject and kill the whole inherited-stdout tree."""
        import tempfile
        import time
        from pathlib import Path
        script = (
            "import subprocess,sys;"
            "p=subprocess.Popen([sys.executable,'-c','import time;time.sleep(30)'],"
            "stdout=sys.stdout,stderr=sys.stderr);"
            "open(sys.argv[1],'w').write(str(p.pid));"
            "sys.stdout.write('Z'*250000);sys.stdout.flush()"
        )
        with tempfile.TemporaryDirectory(prefix="forge-rsi-r14-overflow-") as d:
            pidfile = Path(d) / "child.pid"
            pid = None
            try:
                observed = bounded_run(
                    [sys.executable, "-c", script, str(pidfile)],
                    env=os.environ.copy(), timeout=12)
                self.assertEqual(observed.returncode, 125)
                self.assertLessEqual(len(observed.stdout), MAX_OUTPUT)
                self.assertIn(b"F139_D2K_OUTPUT_LIMIT_EXCEEDED",
                              observed.stdout[:100])
                self.assertTrue(pidfile.exists())
                pid = int(pidfile.read_text())
                for _ in range(20):
                    if not self._descendant_alive(pid):
                        break
                    time.sleep(0.1)
                self.assertFalse(self._descendant_alive(pid),
                                 "output overflow left a live descendant")
            finally:
                if pid is None and pidfile.exists():
                    pid = int(pidfile.read_text())
                if pid is not None and self._descendant_alive(pid):
                    if sys.platform == "win32":
                        subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"],
                                       stdout=subprocess.DEVNULL,
                                       stderr=subprocess.DEVNULL, timeout=5,
                                       check=False)
                    else:
                        import signal
                        os.kill(pid, signal.SIGKILL)

if __name__=="__main__":
    unittest.main()

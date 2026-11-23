"""F139 original-owner self-PID cutover checks, with no scheduled task mutation."""
import os
from pathlib import Path
import tempfile
import types
import unittest
from unittest import mock
import subprocess

from f139.local_controller import native_original_owner_profile, F139Error


class OwnerCutoverSelfPidTests(unittest.TestCase):
    def test_exact_owner_cli_pid_is_passed_to_read_only_process_filter(self):
        with tempfile.TemporaryDirectory() as tmp:
            db=Path(tmp)/"FORGE-F139"/"state.sqlite"
            db.parent.mkdir()
            db.touch()
            fake_os=types.SimpleNamespace(
                name="nt", environ={"LOCALAPPDATA":tmp}, getpid=lambda:76543)
            observed=[]
            def fake_run(argv, **kw):
                observed.append((argv,kw))
                assert kw["env"]["F139_EXPECTED_NATIVE_CLI_PID"]=="76543"
                assert kw["env"]["F139_EXPECTED_TASK_DATABASE"]==str(db.resolve())
                assert "[int]$_.ProcessId -ne $selfId" in argv[-1]
                assert "$t.State -ne 'Disabled'" in argv[-1]
                return subprocess.CompletedProcess(argv,0,b"F139_NATIVE_ORIGINAL_OWNER_PROFILE=PASS\n")
            with mock.patch.dict(native_original_owner_profile.__globals__,{
                "os":fake_os
            }),mock.patch("shutil.which",return_value="powershell.exe"),mock.patch(
                "subprocess.run",side_effect=fake_run):
                self.assertTrue(native_original_owner_profile(db))
            self.assertEqual(len(observed),1)

    def test_readonly_owner_guard_denies_second_competing_process(self):
        with tempfile.TemporaryDirectory() as tmp:
            db=Path(tmp)/"FORGE-F139"/"state.sqlite"
            db.parent.mkdir()
            db.touch()
            fake_os=types.SimpleNamespace(
                name="nt", environ={"LOCALAPPDATA":tmp}, getpid=lambda:76543)
            with mock.patch.dict(native_original_owner_profile.__globals__,{
                "os":fake_os
            }),mock.patch("shutil.which",return_value="powershell.exe"),mock.patch(
                "subprocess.run",return_value=subprocess.CompletedProcess(
                    ["powershell.exe"],50,b"")):
                with self.assertRaisesRegex(F139Error,
                                            "ORIGINAL_OWNER_PROFILE_TASK_ROUTE_OR_DB_DRIFT"):
                    native_original_owner_profile(db)


if __name__=="__main__":
    unittest.main()

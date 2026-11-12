import unittest
from unittest.mock import patch
from f139 import h53_windows_owner as w

class OwnerTests(unittest.TestCase):
    def test_parse_and_negative_controls(self):
        args='-RepositoryRoot "C:/repo" -Database "C:/Users/test/AppData/Local/FORGE-F139/state.sqlite" -PythonExe "C:/python.exe" -File "C:/repo/Run-FORGE-F139.ps1" -PollSeconds 300'
        o=dict(task_name="FORGE-F139-UnifiedController",task_state="Ready",
               task_sid="S-1",runner_sid="S-1",actions=1,triggers=3,
               arguments=args,last_result=0)
        with patch("pathlib.Path.is_file",return_value=True):
            result=w.verify_owner(o,localappdata="C:/Users/test/AppData/Local",
                                  installed_sha=w.guard.SOURCE,installed_dirty=False)
            self.assertEqual(result["source_sha"],w.guard.SOURCE)
            for key,value in [("task_sid","S-2"),("actions",2),("triggers",4),
                              ("task_state","Disabled"),("arguments",args.replace("300","30"))]:
                with self.assertRaises(RuntimeError):
                    w.verify_owner({**o,key:value},localappdata="C:/Users/test/AppData/Local",
                                   installed_sha=w.guard.SOURCE,installed_dirty=False)
            with self.assertRaises(RuntimeError):
                w.verify_owner(o,localappdata="C:/Users/test/AppData/Local",
                               installed_sha="bad",installed_dirty=False)
            with self.assertRaises(RuntimeError):
                w.verify_owner(o,localappdata="C:/Users/test/AppData/Local",
                               installed_sha=w.guard.SOURCE,installed_dirty=True)
        with patch("pathlib.Path.is_file",return_value=False):
            with self.assertRaises(RuntimeError):
                w.verify_owner(o,localappdata="C:/Users/test/AppData/Local",
                               installed_sha=w.guard.SOURCE,installed_dirty=False)
if __name__=="__main__":
    unittest.main()

"""One-shot original-owner negative admission uses only authenticated reads.

Isolated original-history fixture. Proves the new CLI fetches the exact
existing provider run, all four terminal jobs, original ZIP and does not
attempt a new workflow dispatch or replace original F139 scheduler.
"""
import contextlib
import io
import os
import subprocess
from unittest import mock
import unittest

from f139.local_controller import cli
from f139.nci04_negative_owner_store import KIND
from test_nci04_negative_owner_store import OwnerNegativeStoreTests
from test_nci04_owner_issue import HMAC


class ExactNegativeCli(unittest.TestCase):
    def setUp(self):
        OwnerNegativeStoreTests.setUp(self)

    def test_original_provider_read_only_and_single_custody_event(self):
        fields = []
        fixture = self

        class FakeApi:
            def protected_main(self):
                fields.append("protected_main")
                return "a"*40

            def legacy_dispatchers_disabled(self):
                fields.append("legacy_dispatchers_disabled")
                return True

            def get(self, route):
                fields.append(("GET",route))
                if route == "repos/spoonman136668-ai/FORGE/actions/runs/"+str(fixture.rid):
                    return fixture.run
                if route == ("repos/spoonman136668-ai/FORGE/actions/runs/"
                             +str(fixture.rid)+"/jobs?per_page=100"):
                    return {"total_count":4,"jobs":fixture.jobs}
                if route == ("repos/spoonman136668-ai/FORGE/actions/runs/"
                             +str(fixture.rid)+"/artifacts?per_page=100"):
                    return {"total_count":1,"artifacts":[fixture.artifact]}
                raise AssertionError("UNEXPECTED_PROVIDER_ROUTE "+route)

            def artifact(self, artifact_id):
                fields.append(("ARTIFACT",artifact_id))
                assert artifact_id == fixture.artid
                return fixture.archive

            def dispatch(self,*a,**kw):
                raise AssertionError("NO_NATIVE_REDISPATCH")

            def dispatch_native(self,*a,**kw):
                raise AssertionError("NO_NATIVE_REDISPATCH")

        def git(args, **kwargs):
            if args[-2:] == ["rev-parse","HEAD"]:
                return subprocess.CompletedProcess(args,0,("a"*40+"\n").encode())
            if args[-2:] == ["status","--porcelain"] or (
                    "status" in args and "--untracked-files=all" in args):
                return subprocess.CompletedProcess(args,0,b"")
            raise AssertionError("UNEXPECTED_GIT_COMMAND "+str(args))

        with (mock.patch("f139.local_controller.GitHub",return_value=FakeApi()),
              mock.patch("f139.local_controller.native_original_owner_profile",
                         return_value=True) as owner,
              mock.patch("f139.local_controller.legacy_windows_task_disabled",
                         return_value=True),
              mock.patch("f139.local_controller.SingleOwner",
                         return_value=contextlib.nullcontext()),
              mock.patch("f139.local_controller.subprocess.run",side_effect=git),
              mock.patch.dict(os.environ,{"F139_WORKER_HMAC_KEY":HMAC}),
              contextlib.redirect_stdout(io.StringIO()) as out):
            cli(["--db",str(self.path),"custody-original-native-negative"])
            self.assertEqual(owner.call_count,1)
        self.assertIn("original_negative_custody",out.getvalue())
        self.assertEqual(self.db.meta()["head_seq"],48)
        self.assertEqual(self.db.conn.execute(
            "SELECT COUNT(*) FROM events WHERE kind=?",(KIND,)).fetchone()[0],1)
        self.assertTrue(all(not (isinstance(item,tuple) and item[0]=="POST")
                            for item in fields))
        self.assertEqual(sum(isinstance(item,tuple)
                             and item[0]=="ARTIFACT" for item in fields),1)
        self.db.verify()


if __name__=="__main__":
    unittest.main()

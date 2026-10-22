"""A8E2A3 exact read-only original-provider CLI path, isolated synthetic owner.

This uses only fake provider replies and a synthetic 55-event owner database.
The original provider ZIP, owner HMAC and real owner process are never accessed.
"""
import contextlib
import io
import os
import subprocess
import unittest
from unittest import mock

from f139.local_controller import cli
from f139.nci04_split_negative_owner_store import KIND, RUN_ID, ARTIFACT_ID
from test_nci04_split_negative_owner_store import SecondNegativeSyntheticOwnerTests


class OriginalSplitNegativeCli(unittest.TestCase):
    def setUp(self):
        SecondNegativeSyntheticOwnerTests.setUp(self)
        self.routes = []
        fixture = self

        class FakeApi:
            def protected_main(self):
                fixture.routes.append("protected_main")
                return "a" * 40

            def legacy_dispatchers_disabled(self):
                fixture.routes.append("legacy_dispatchers_disabled")
                return True

            def get(self, route):
                fixture.routes.append(("GET", route))
                prefix = ("repos/spoonman136668-ai/FORGE/actions/runs/"
                          + str(RUN_ID))
                if route == prefix:
                    return {"id": RUN_ID}
                if route == prefix + "/jobs?per_page=100":
                    return {"total_count": 4, "jobs": [{}, {}, {}, {}]}
                if route == prefix + "/artifacts?per_page=100":
                    return {"total_count": 1, "artifacts": [{"id": ARTIFACT_ID}]}
                raise AssertionError("UNEXPECTED_PROVIDER_ROUTE " + route)

            def artifact(self, artifact_id):
                fixture.routes.append(("ARTIFACT", artifact_id))
                assert artifact_id == ARTIFACT_ID
                return fixture.archive

            def dispatch(self, *args, **kwargs):
                raise AssertionError("PROVIDER_DISPATCH_FORBIDDEN")

            def dispatch_native(self, *args, **kwargs):
                raise AssertionError("PROVIDER_DISPATCH_FORBIDDEN")

        self.api = FakeApi()

        def git(args, **kwargs):
            if args[-2:] == ["rev-parse", "HEAD"]:
                return subprocess.CompletedProcess(args, 0, ("a" * 40 + "\n").encode())
            if "status" in args and "--untracked-files=all" in args:
                return subprocess.CompletedProcess(args, 0, b"")
            raise AssertionError("UNEXPECTED_GIT_COMMAND " + str(args))

        self.git = git

    def invoke(self, *, git=None):
        with (mock.patch("f139.local_controller.GitHub", return_value=self.api),
              mock.patch("f139.local_controller.native_original_owner_profile",
                         return_value=True),
              mock.patch("f139.local_controller.legacy_windows_task_disabled",
                         return_value=True),
              mock.patch("f139.local_controller.SingleOwner",
                         return_value=contextlib.nullcontext()),
              mock.patch("f139.local_controller.subprocess.run",
                         side_effect=git or self.git),
              mock.patch(
                  "f139.nci04_negative_owner_store.verify_original_negative_custody",
                  return_value=True),
              mock.patch.dict(os.environ, {"F139_WORKER_HMAC_KEY": "synthetic-owner-hmac-key-not-production-00000"}),
              contextlib.redirect_stdout(io.StringIO()) as output):
            cli(["--db", str(self.path), "custody-original-native-split-negative"])
            return output.getvalue()

    def test_original_get_only_once_and_new_custody_event_56(self):
        result = self.invoke()
        self.assertIn('"second_negative_custody": "PASS"', result)
        self.assertEqual(self.db.meta()["head_seq"], 56)
        self.assertEqual(self.db.conn.execute(
            "SELECT COUNT(*) FROM events WHERE kind=?", (KIND,)).fetchone()[0], 1)
        self.assertEqual(
            [value[1] for value in self.routes
             if isinstance(value, tuple) and value[0] == "ARTIFACT"],
            [ARTIFACT_ID])
        self.assertEqual(len([x for x in self.routes
                              if isinstance(x, tuple) and x[0] == "GET"]), 3)
        self.assertTrue(all(x[0] != "POST" for x in self.routes
                            if isinstance(x, tuple)))

    def test_owner_exact_head_prevents_second_admission_or_replay(self):
        self.invoke()
        original = self.db.meta()["head_hash"]
        original_gets = sum(isinstance(x, tuple) and x[0] == "GET"
                            for x in self.routes)
        with self.assertRaises(Exception):
            self.invoke()
        self.assertEqual(self.db.meta()["head_seq"], 56)
        self.assertEqual(self.db.meta()["head_hash"], original)
        self.assertEqual(sum(isinstance(x, tuple) and x[0] == "GET"
                             for x in self.routes), original_gets)

    def test_dirty_checkout_rejected_before_provider_access(self):
        def dirty(args, **kwargs):
            if args[-2:] == ["rev-parse", "HEAD"]:
                return subprocess.CompletedProcess(args, 0, ("a" * 40).encode())
            if "status" in args and "--untracked-files=all" in args:
                return subprocess.CompletedProcess(args, 0, b"dirty")
            raise AssertionError("UNEXPECTED_GIT_COMMAND")
        with self.assertRaises(Exception):
            self.invoke(git=dirty)
        self.assertEqual(self.db.meta()["head_seq"], 55)
        self.assertFalse(any(isinstance(x, tuple) and x[0] == "GET"
                             for x in self.routes))


if __name__ == "__main__":
    unittest.main()

"""V41 original Windows read-only route: fail-closed source and owner checks."""
from contextlib import closing
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from f139.local_controller import Database, GitHub
from f139 import nci04_v41_original_owner_status as route
from f139 import nci04_v41_catalog_recovery_preflight as source


class V41OriginalOwnerStatusTests(unittest.TestCase):
    def test_unapproved_event_never_calls_provider(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "state.sqlite"
            with patch.object(GitHub, "native_repo_get",
                              side_effect=AssertionError("provider read")):
                for environment in ({}, {"GITHUB_REPOSITORY":source.REPO,
                                          "GITHUB_SHA":"9"*40}):
                    with self.subTest(environment=environment):
                        with self.assertRaisesRegex(
                                route.V41StatusDenied,
                                "EXACT_ORIGINAL_OWNER_RUNNER_EVENT"):
                            route.main(["--db",str(path),"--target","9"*40],
                                       environ=environment,event={})

    def test_wrong_target_or_absent_db_fails_before_get(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/"state.sqlite"
            with patch.object(source, "source_preflight",
                              side_effect=AssertionError("should not GET")):
                for target in ("", "bad", source.OWNER_SOURCE, None):
                    with self.subTest(target=target):
                        with self.assertRaises(route.V41StatusDenied):
                            route.inspect_original(path,GitHub(),target=target)
                with self.assertRaises(route.V41StatusDenied):
                    route.inspect_original(path,GitHub(),target="9"*40)

    def test_mock_remote_is_not_authentic_original_sqlite(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "state.sqlite"
            with closing(Database.initialize(path,source.OWNER_SOURCE)) as original:
                meta=original.meta().copy()
            with patch.object(source, "source_preflight",
                              return_value={"issues_per_page":[100,100,0],
                                            "unique_eligible_issues":200}):
                with self.assertRaises(source.V41ReadOnlyDenied):
                    route.inspect_original(path,GitHub(),target="9"*40)
            with closing(Database.open_readonly(path)) as readonly:
                self.assertEqual(readonly.meta(),meta)
                self.assertEqual(readonly.conn.total_changes,0)

    def test_existing_mutation_routes_are_not_exposed(self):
        import inspect
        code=inspect.getsource(route)
        for forbidden in ("db.event(", "db.transition_source(",
                          "workflow_dispatch(", "Start-ScheduledTask",
                          "Stop-ScheduledTask", "Disable-ScheduledTask",
                          ".post(", "create_ref("):
            self.assertNotIn(forbidden,code)
        self.assertFalse(hasattr(route,"commit_transition"))
        self.assertFalse(hasattr(route,"install_release"))
        self.assertFalse(hasattr(route,"reactivate_native"))


if __name__=="__main__":
    unittest.main()

"""Fail-closed tests of read-only unattended operational continuity evidence."""
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import continuity as c

NOW = datetime(2026, 10, 16, 21, 0, tzinfo=timezone.utc)
CURRENT = "a" * 40
PREVIOUS = ("b" * 40, "c" * 40)
BLOB = "d" * 40
WF = 198001

def run(idx, *, event="schedule", conclusion="success", attempt=1):
    return {"id": 41000000000 + idx, "workflow_id": WF,
            "event": event, "head_branch": "main", "head_sha": PREVIOUS[idx],
            "run_attempt": attempt, "status": "completed", "conclusion": conclusion,
            "created_at": f"2026-10-16T{13 if idx == 0 else 19}:19:01Z",
            "updated_at": f"2026-10-16T{13 if idx == 0 else 19}:19:31Z"}

class FakeAPI:
    def __init__(self):
        self.items = {}
        self.items["/actions/workflows/" + c.WORKFLOW] = {
            "id": WF, "path": ".github/workflows/" + c.WORKFLOW,
            "state": "active"}
        self.items["/actions/workflows/198001/runs?event=schedule&per_page=25"] = {
            "workflow_runs": [run(1), run(0)]}
        for sha in (CURRENT,) + PREVIOUS:
            for path in c.SOURCE_PATHS:
                self.items["/contents/" + path + "?ref=" + sha] = {
                    "type": "file", "sha": BLOB}
        for idx in range(2):
            r = run(idx)
            self.items[f"/actions/runs/{r['id']}/artifacts?per_page=100"] = {
                "artifacts": [{"id": 52000 + idx, "name": c.ARTIFACT,
                               "size_in_bytes": 1300, "expired": False,
                               "digest": "sha256:" + "f" * 64,
                               "workflow_run": {"id": r["id"], "head_branch": "main",
                                                "head_sha": r["head_sha"]}}]}
    def get(self, path):
        return deepcopy(self.items[path])

class ContinuityTests(unittest.TestCase):
    def test_two_real_successful_scheduled_observations(self):
        result = c.report(FakeAPI(), NOW, CURRENT)
        self.assertTrue(result["qualified"])
        self.assertEqual(result["status"], "QUALIFIED_TWO_COMPLETED_SCHEDULED_OBSERVATIONS")
        self.assertEqual([x["run_id"] for x in result["observations"]], [41000000000, 41000000001])
        self.assertFalse(result["scientific_first_use_authorized"])
        self.assertEqual(result["science_dispatches"], 0)
        self.assertFalse(result["ckb_plane_accessed"])

    def test_no_or_one_schedule_stays_pending_not_qualified(self):
        for retained in (0, 1):
            a = FakeAPI()
            a.items["/actions/workflows/198001/runs?event=schedule&per_page=25"]["workflow_runs"] = [run(1)][:retained]
            result = c.report(a, NOW, CURRENT)
            self.assertFalse(result["qualified"])
            self.assertEqual(result["status"], "PENDING_TWO_COMPLETED_SCHEDULED_RUNS")

    def test_manual_or_push_successes_do_not_count(self):
        a = FakeAPI()
        runs = a.items["/actions/workflows/198001/runs?event=schedule&per_page=25"]["workflow_runs"]
        runs[:] = [run(1, event="workflow_dispatch"), run(0)]
        with self.assertRaisesRegex(c.EvidenceError, "RECENT_SCHEDULE_IDENTITY_UNVERIFIED"):
            c.report(a, NOW, CURRENT)

    def test_latest_scheduled_failure_is_preserved_not_qualified(self):
        a = FakeAPI()
        rows = a.items["/actions/workflows/198001/runs?event=schedule&per_page=25"]["workflow_runs"]
        rows[0]["conclusion"] = "failure"
        result = c.report(a, NOW, CURRENT)
        self.assertEqual(result["status"],
                         "RECOVERING_PRIOR_SCHEDULE_FAILURE_NO_CONTINUITY")
        self.assertFalse(result["qualified"])
        self.assertEqual(result["recent_unsuccessful_observations"], [{
            "run_id": 41000000001, "head_sha": PREVIOUS[1],
            "conclusion": "failure"}])
        self.assertEqual(result["observations"], [])
        self.assertFalse(result["scientific_first_use_authorized"])
        self.assertEqual(result["science_dispatches"], 0)

    def test_cancelled_timedout_failures_remain_negative_and_nonadmitted(self):
        for conclusion in ("failure", "cancelled", "timed_out"):
            a = FakeAPI()
            row = a.items["/actions/workflows/198001/runs?event=schedule&per_page=25"]["workflow_runs"][0]
            row["conclusion"] = conclusion
            with self.subTest(conclusion=conclusion):
                result = c.report(a, NOW, CURRENT)
                self.assertFalse(result["qualified"])
                self.assertEqual(result["recent_unsuccessful_observations"][0]["conclusion"],
                                 conclusion)
                self.assertEqual(result["status"], "RECOVERING_PRIOR_SCHEDULE_FAILURE_NO_CONTINUITY")
                self.assertFalse(result["scientific_first_use_authorized"])

    def test_new_two_successes_establish_real_continuity_after_old_failure(self):
        a = FakeAPI()
        history = a.items["/actions/workflows/198001/runs?event=schedule&per_page=25"]["workflow_runs"]
        older_failed = run(0)
        older_failed["id"] = 41000000010
        older_failed["conclusion"] = "failure"
        older_failed["created_at"] = "2026-10-16T07:19:01Z"
        older_failed["updated_at"] = "2026-10-16T07:19:31Z"
        history.append(older_failed)
        result = c.report(a, NOW, CURRENT)
        self.assertTrue(result["qualified"])
        self.assertEqual([v["run_id"] for v in result["observations"]],
                         [41000000000, 41000000001])
        self.assertFalse(result["scientific_first_use_authorized"])
        self.assertEqual(result["science_dispatches"], 0)

    def test_failure_still_blocks_when_only_one_new_success_has_completed(self):
        a = FakeAPI()
        history = a.items["/actions/workflows/198001/runs?event=schedule&per_page=25"]["workflow_runs"]
        history[1]["conclusion"] = "failure"
        report = c.report(a, NOW, CURRENT)
        self.assertFalse(report["qualified"])
        self.assertEqual(report["status"],
                         "RECOVERING_PRIOR_SCHEDULE_FAILURE_NO_CONTINUITY")
        self.assertEqual(report["recent_unsuccessful_observations"][0]["run_id"],
                         history[1]["id"])

    def test_noncompleted_other_schedule_is_not_a_recovery_receipt(self):
        a = FakeAPI()
        rows = a.items["/actions/workflows/198001/runs?event=schedule&per_page=25"]["workflow_runs"]
        rows[0]["status"] = "in_progress"
        rows[0]["conclusion"] = None
        with self.assertRaisesRegex(c.EvidenceError, "RECENT_SCHEDULE_UNSUCCESSFUL_OR_UNVERIFIED"):
            c.report(a, NOW, CURRENT)

    def test_unknown_finished_conclusion_cannot_claim_recovery(self):
        a = FakeAPI()
        rows = a.items["/actions/workflows/198001/runs?event=schedule&per_page=25"]["workflow_runs"]
        rows[0]["conclusion"] = "neutral_unknown"
        with self.assertRaisesRegex(c.EvidenceError, "RECENT_SCHEDULE_CONCLUSION_UNVERIFIED"):
            c.report(a, NOW, CURRENT)

    def test_rerun_is_not_proof_of_first_attempt_continuity(self):
        a = FakeAPI()
        a.items["/actions/workflows/198001/runs?event=schedule&per_page=25"]["workflow_runs"][0]["run_attempt"] = 2
        with self.assertRaises(c.EvidenceError):
            c.report(a, NOW, CURRENT)

    def test_expired_or_missing_source_artifact_is_denied(self):
        for change in ("expired", "digest", "head_sha"):
            a = FakeAPI()
            artifact = a.items["/actions/runs/41000000001/artifacts?per_page=100"]["artifacts"][0]
            artifact[change] = True if change == "expired" else "invalid"
            if change == "head_sha":
                artifact["workflow_run"]["head_sha"] = "e" * 40
            with self.assertRaises(c.EvidenceError):
                c.report(a, NOW, CURRENT)

    def test_semantic_source_drift_is_not_reused(self):
        for path in c.SOURCE_PATHS:
            a = FakeAPI()
            a.items["/contents/" + path + "?ref=" + PREVIOUS[1]]["sha"] = "e" * 40
            with self.assertRaisesRegex(c.EvidenceError, "QUALIFICATION_SOURCE_DRIFT"):
                c.report(a, NOW, CURRENT)

    def test_duplicate_schedule_run_id_denied(self):
        a = FakeAPI()
        a.items["/actions/workflows/198001/runs?event=schedule&per_page=25"]["workflow_runs"] = [run(0), run(0)]
        with self.assertRaisesRegex(c.EvidenceError, "REPEATED_SCHEDULE_RUN_ID"):
            c.report(a, NOW, CURRENT)

    def test_future_timestamp_denied(self):
        a = FakeAPI()
        a.items["/actions/workflows/198001/runs?event=schedule&per_page=25"]["workflow_runs"][0]["updated_at"] = "2027-10-16T19:19:31Z"
        with self.assertRaises(c.EvidenceError):
            c.report(a, NOW, CURRENT)

    def test_stale_or_skipped_schedule_denied(self):
        a = FakeAPI()
        a.items["/actions/workflows/198001/runs?event=schedule&per_page=25"]["workflow_runs"][0]["created_at"] = "2026-10-17T05:19:01Z"
        with self.assertRaisesRegex(c.EvidenceError, "SCHEDULE_CLOCK_UNVERIFIED"):
            c.report(a, datetime(2026, 10, 17, 6, 0, tzinfo=timezone.utc), CURRENT)

    def test_foreign_workflow_or_disabled_workflow_never_accepted(self):
        a = FakeAPI()
        a.items["/actions/workflows/" + c.WORKFLOW]["state"] = "disabled_manually"
        with self.assertRaisesRegex(c.EvidenceError, "WORKFLOW_IDENTITY_UNVERIFIED"):
            c.report(a, NOW, CURRENT)
        b = FakeAPI()
        b.items["/actions/workflows/198001/runs?event=schedule&per_page=25"]["workflow_runs"][0]["workflow_id"] = 122
        self.assertFalse(c.report(b, NOW, CURRENT)["qualified"])


    def active_self(self):
        r = run(1)
        r.update({"id": 41000000002, "head_sha": CURRENT,
                  "status": "in_progress", "conclusion": None,
                  "created_at": "2026-10-16T20:59:00Z",
                  "updated_at": "2026-10-16T20:59:20Z"})
        return r

    def test_current_scheduled_run_is_not_its_own_completed_witness(self):
        a = FakeAPI()
        own = self.active_self()
        a.items["/actions/workflows/198001/runs?event=schedule&per_page=25"]["workflow_runs"].insert(0, own)
        result = c.report(a, NOW, CURRENT, current_run_id=own["id"])
        self.assertTrue(result["qualified"])
        self.assertTrue(result["current_scheduled_run_excluded"])
        self.assertEqual([x["run_id"] for x in result["observations"]],
                         [41000000000, 41000000001])
        self.assertFalse(result["scientific_first_use_authorized"])
        self.assertEqual(result["science_dispatches"], 0)

    def test_one_completed_plus_self_remains_pending(self):
        a = FakeAPI()
        own = self.active_self()
        a.items["/actions/workflows/198001/runs?event=schedule&per_page=25"]["workflow_runs"] = [
            own, run(1)]
        result = c.report(a, NOW, CURRENT, current_run_id=own["id"])
        self.assertFalse(result["qualified"])
        self.assertEqual(result["scheduled_runs_found"], 1)
        self.assertTrue(result["current_scheduled_run_excluded"])

    def test_self_alone_never_becomes_a_completed_observation(self):
        a = FakeAPI()
        own = self.active_self()
        a.items["/actions/workflows/198001/runs?event=schedule&per_page=25"]["workflow_runs"] = [own]
        result = c.report(a, NOW, CURRENT, current_run_id=own["id"])
        self.assertFalse(result["qualified"])
        self.assertEqual(result["scheduled_runs_found"], 0)

    def test_self_id_is_not_permission_to_hide_untrusted_origins(self):
        for update in (
            {"head_sha": "f" * 40},
            {"head_branch": "other"},
            {"event": "workflow_dispatch"},
            {"run_attempt": 2},
            {"status": "completed", "conclusion": "success"},
            {"status": "in_progress", "conclusion": "success"},
        ):
            a = FakeAPI()
            own = self.active_self()
            own.update(update)
            a.items["/actions/workflows/198001/runs?event=schedule&per_page=25"]["workflow_runs"].insert(0, own)
            with self.assertRaisesRegex(c.EvidenceError, "CURRENT_RUN_SELF_IDENTITY_UNVERIFIED"):
                c.report(a, NOW, CURRENT, current_run_id=own["id"])

    def test_self_exclusion_never_skips_another_unfinished_schedule(self):
        a = FakeAPI()
        own = self.active_self()
        stranger = self.active_self()
        stranger.update({"id": 41000000003, "created_at": "2026-10-16T20:58:00Z"})
        a.items["/actions/workflows/198001/runs?event=schedule&per_page=25"]["workflow_runs"] = [
            own, stranger, run(1), run(0)]
        with self.assertRaises(c.EvidenceError):
            c.report(a, NOW, CURRENT, current_run_id=own["id"])

    def test_self_exclusion_never_skips_new_failed_schedule(self):
        a = FakeAPI()
        own = self.active_self()
        bad = run(1)
        bad["conclusion"] = "failure"
        a.items["/actions/workflows/198001/runs?event=schedule&per_page=25"]["workflow_runs"] = [
            own, bad, run(0)]
        result = c.report(a, NOW, CURRENT, current_run_id=own["id"])
        self.assertFalse(result["qualified"])
        self.assertTrue(result["current_scheduled_run_excluded"])
        self.assertEqual(result["status"],
                         "RECOVERING_PRIOR_SCHEDULE_FAILURE_NO_CONTINUITY")
        self.assertEqual([x["run_id"] for x in result["recent_unsuccessful_observations"]],
                         [bad["id"]])
        self.assertEqual(result["observations"], [])

    def test_invalid_current_run_id_denied(self):
        for invalid in (True, "41000000002", 0, -1):
            with self.assertRaisesRegex(c.EvidenceError, "CURRENT_RUN_ID_INVALID"):
                c.report(FakeAPI(), NOW, CURRENT, current_run_id=invalid)

if __name__ == "__main__":
    unittest.main()

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

    def test_failed_history_stays_failed_despite_delayed_cadence(self):
        a=FakeAPI()
        rows=a.items["/actions/workflows/198001/runs?event=schedule&per_page=25"]["workflow_runs"]
        # GitHub's schedule may be delayed, so two distinct real schedules
        # can fall under the three-hour minimum gap; an old FAILED run is
        # still a failed run, not a permissible successful observation.
        rows[0]["conclusion"]="failure"
        rows[1]["created_at"]="2026-10-16T17:19:01Z"
        with self.assertRaisesRegex(c.EvidenceError,
                                    "RECENT_SCHEDULE_UNSUCCESSFUL"):
            c.report(a,NOW,CURRENT)
        # Two actual successful runs with the SAME cadence defect remain
        # quarantined and cannot receive a continuity qualification.
        rows[0]["conclusion"]="success"
        with self.assertRaisesRegex(c.EvidenceError,
                                    "SCHEDULE_CADENCE_OR_FRESHNESS"):
            c.report(a,NOW,CURRENT)

    def test_old_forensic_artifact_never_certifies_healthy_observation(self):
        a = FakeAPI()
        artifact = a.items["/actions/runs/41000000001/artifacts?per_page=100"]["artifacts"][0]
        artifact["name"] = "forge-native-autonomy-operational-source-only"
        with self.assertRaisesRegex(c.EvidenceError,"ARTIFACT_NOT_UNIQUE"):
            c.report(a, NOW, CURRENT)

    def test_exact_historical_failure_can_be_acknowledged_without_qualification(self):
        bad={"schema":c.SCHEMA,"qualified":False,
             "status":"QUARANTINED_UNVERIFIED",
             "reason":"RECENT_SCHEDULE_UNSUCCESSFUL_OR_UNVERIFIED",
             "science_dispatches":0,
             "scientific_first_use_authorized":False,
             "ckb_plane_accessed":False}
        self.assertEqual(c.acknowledge_previous_failed_observation(bad),
                         "HISTORICAL_SUPERVISION_FAILURE_ACKNOWLEDGED_NO_CONTINUITY_OR_SCIENCE")
        for key,value in (("qualified",True),("status","QUALIFIED_TWO_COMPLETED_SCHEDULED_OBSERVATIONS"),
                          ("reason","QUALIFICATION_SOURCE_DRIFT"),
                          ("reason","API_ORIGIN_UNAVAILABLE"),
                          ("reason","SCHEDULE_CADENCE_OR_FRESHNESS_UNVERIFIED"),
                          ("reason","SOURCE_BLOB_UNVERIFIED"),
                          ("science_dispatches",1),
                          ("scientific_first_use_authorized",True),
                          ("ckb_plane_accessed",True)):
            injected=dict(bad)
            injected[key]=value
            with self.assertRaises(c.EvidenceError):
                c.acknowledge_previous_failed_observation(injected)
        for invalid in (dict(bad,extra_key=123),{"schema":c.SCHEMA},None,[]):
            with self.assertRaises(c.EvidenceError):
                c.acknowledge_previous_failed_observation(invalid)

    def test_historical_failed_attempt_remains_negative_even_with_new_markers(self):
        a=FakeAPI()
        items=a.items["/actions/workflows/198001/runs?event=schedule&per_page=25"]["workflow_runs"]
        items[0]["conclusion"]="failure"
        with self.assertRaisesRegex(c.EvidenceError,"RECENT_SCHEDULE_UNSUCCESSFUL"):
            c.report(a,NOW,CURRENT)

    def test_scheduled_healthy_observation_marker_is_not_research_authority(self):
        result=c.report(FakeAPI(),NOW,CURRENT)
        self.assertTrue(result["qualified"])
        self.assertTrue(all(a["artifact"]["sha256"].startswith("sha256:")
                            for a in result["observations"]))
        self.assertFalse(result["scientific_evidence_authenticated"])
        self.assertFalse(result["scientific_first_use_authorized"])
        self.assertEqual(result["science_dispatches"],0)
        self.assertEqual(result["optimizer_promotions"],0)

    def test_existing_workflow_retains_negative_custody_and_distinct_marker(self):
        workflow=(Path(__file__).resolve().parents[1]/
                  ".github/workflows/forge-native-autonomy-supervision.yml").read_text()
        self.assertIn("name: forge-native-autonomy-operational-source-only",workflow)
        self.assertIn("name: forge-native-autonomy-operational-verified-only",workflow)
        self.assertIn("if: always()",workflow)
        self.assertIn("if: success()",workflow)
        self.assertIn("acknowledge_previous_failed_observation(report)",workflow)
        self.assertIn("FORGE_NATIVE_CONTINUITY=QUARANTINED_UNVERIFIED",workflow)
        self.assertIn("FORGE_AUTONOMY_FIRSTUSE_OR_SCIENCE_DISPATCH=DENIED",workflow)

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
        with self.assertRaisesRegex(c.EvidenceError, "RECENT_SCHEDULE_UNSUCCESSFUL"):
            c.report(a, NOW, CURRENT)

    def test_latest_scheduled_failure_is_not_skipped(self):
        a = FakeAPI()
        a.items["/actions/workflows/198001/runs?event=schedule&per_page=25"]["workflow_runs"][0]["conclusion"] = "failure"
        with self.assertRaisesRegex(c.EvidenceError, "RECENT_SCHEDULE_UNSUCCESSFUL"):
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
        with self.assertRaisesRegex(c.EvidenceError, "SCHEDULE_CADENCE_OR_FRESHNESS"):
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
        with self.assertRaisesRegex(c.EvidenceError, "RECENT_SCHEDULE_UNSUCCESSFUL"):
            c.report(a, NOW, CURRENT, current_run_id=own["id"])

    def test_invalid_current_run_id_denied(self):
        for invalid in (True, "41000000002", 0, -1):
            with self.assertRaisesRegex(c.EvidenceError, "CURRENT_RUN_ID_INVALID"):
                c.report(FakeAPI(), NOW, CURRENT, current_run_id=invalid)

if __name__ == "__main__":
    unittest.main()

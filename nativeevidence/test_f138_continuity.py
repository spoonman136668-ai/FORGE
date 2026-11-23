"""F138-B adversarial source, parent, OS, replay and chronology qualification."""
from __future__ import annotations
import copy
import datetime as dt
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

import f138_continuity as m
import f138_lineage as source

SHA = "e2fca32e0d4439aed801dac6b697ecea28855017"
OLD = "03bd3673beb16352cbca2b9261e754ccf2cc6865"
EPOCH = "2026-10-18T10:26:38Z"
OBSERVED = "2026-10-18T11:25:00Z"
CHILDREN = (
    (39120007064, "2026-10-18T10:37:47Z", "2026-10-18T10:39:27Z",
     39119993456, "2026-10-18T10:37:33Z"),
    (39121310943, "2026-10-18T10:57:49Z", "2026-10-18T10:59:33Z",
     39121294863, "2026-10-18T10:57:34Z"),
    (39122657120, "2026-10-18T11:17:46Z", "2026-10-18T11:19:31Z",
     39122641881, "2026-10-18T11:17:33Z"),
)

def provider(rid, at, end, *, controller=False, event="workflow_dispatch",
             sha=SHA):
    return {
        "id": rid, "name": m.CNAME if controller else m.INAME,
        "path": m.CONTROLLER if controller else m.INTEGRATED,
        "head_branch": "main", "head_sha": sha, "run_attempt": 1,
        "event": event, "status": "completed", "conclusion": "success",
        "created_at": at, "run_started_at": at, "updated_at": end,
        "repository": {"full_name": m.REPO},
        "head_repository": {"full_name": m.REPO},
        "actor": {"login": "spoonman136668-ai" if controller
                  else "github-actions[bot]"},
        "triggering_actor": {"login": "spoonman136668-ai" if controller
                             else "github-actions[bot]"}
    }

def index(items, field):
    return {"total_count": len(items), field: items}

def artifact(rid, name, *, sha=SHA):
    # API archive bytes/digest are verified independently by the collector.
    return {
        "id": rid * 10 + len(name), "name": name, "expired": False,
        "digest": "sha256:" + "a" * 64, "size_in_bytes": 100,
        "workflow_run": {"id": rid, "head_sha": sha}
    }

def record(folder, name, report):
    folder.mkdir(parents=True)
    raw = (json.dumps(report, sort_keys=True, separators=(",", ":"))
           + "\n").encode()
    (folder / name).write_bytes(raw)
    return raw

def fixture(folder, *, with_schedule=False):
    children = []
    parents = []
    artifacts = {}
    jobs = {}
    for pos, (rid, at, end, pid, before) in enumerate(CHILDREN):
        scheduled = with_schedule and pos == 1
        event = "schedule" if scheduled else "workflow_dispatch"
        child = provider(rid, at, end, event=event)
        children.append(child)
        origin = "schedule" if scheduled else m.WINDOWS
        inputs = dict(repository=m.REPO, ref="refs/heads/main",
                      source_sha=SHA, run_id=str(rid), run_attempt="1",
                      event=event, origin=origin,
                      parent_run_id="" if scheduled else str(pid),
                      parent_source_sha="" if scheduled else SHA)
        report = source.build(**inputs)
        for os in m.OS:
            folder_os = folder / str(rid) / os
            folder_os.mkdir(parents=True)
            raw = source.encode(report)
            (folder_os / "f138-lineage.json").write_bytes(raw)
            (folder_os / "f138-lineage.sha256").write_bytes(
                (hashlib.sha256(raw).hexdigest() + "  f138-lineage.json\n").encode("ascii"))
        artifacts[str(rid)] = index([
            artifact(rid, "forge-f138-lineage-" + os)
            for os in m.OS
        ], "artifacts")
        jobs[str(rid)] = index([
            {"id": rid * 10 + i + 1, "name": job, "status": "completed",
             "conclusion": "success"}
            for i, job in enumerate(sorted(m.REQUIRED_JOBS))
        ], "jobs")
        if not scheduled:
            parent = provider(pid, before, at,
                              controller=True)
            parents.append(parent)
            artifacts[str(pid)] = index([
                artifact(pid, "forge-f137-windows-decision-" + str(pid))
            ], "artifacts")
            nonce = ("%032x" % (pos + 1))
            proof = {
                "schema": "forge.autonomy.f137.windows-development-wake.v1",
                "controller_run_id": pid, "source_sha": SHA,
                "origin": m.WINDOWS, "dispatch": True, "reasons": [],
                "genuine_schedule_claim": False,
                "scientific_first_use_authorized": False,
                "science_originals": 0, "accepted_ref_mutations": 0,
                "paid_api_calls": 0, "codex_calls": 0,
                "wake_nonce": nonce
            }
            record(folder / str(pid), "decision.json", proof)
    prior_child = provider(39118033321,"2026-10-18T10:07:47Z",
                           "2026-10-18T10:09:12Z",sha=OLD)
    prior_parent = provider(39118017343,"2026-10-18T10:07:33Z",
                            "2026-10-18T10:07:52Z",
                            controller=True,sha=OLD)
    children = list(reversed(children)) + [prior_child]
    parents = list(reversed(parents)) + [prior_parent]
    snapshot = {
        "schema": "forge.autonomy.f138.provider-snapshot.v1",
        "source_sha": SHA, "merged_at": EPOCH,
        "observed_at": OBSERVED,
        "integrated_index": index(children, "workflow_runs"),
        "controller_index": index(parents, "workflow_runs"),
        "artifacts": artifacts, "jobs": jobs,
    }
    return snapshot

class ContinuityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.folder = Path(self.temp.name)
        self.snapshot = fixture(self.folder)
        self.addCleanup(self.temp.cleanup)

    def assessment(self, snap=None):
        return m.assess(snap if snap is not None else self.snapshot,self.folder)

    def rejects(self, snap):
        with self.assertRaises(m.Quarantine):
            self.assessment(snap)

    def test_three_authentic_windows_recoveries_are_not_cron(self):
        result = self.assessment()
        self.assertEqual(result["verdict"], "PENDING")
        self.assertTrue(result["windows_recovery_continuity_verified"])
        self.assertEqual(result["verified_unattended_runs"], 3)
        self.assertEqual(result["genuine_scheduled_count"], 0)
        self.assertEqual(result["windows_recovery_count"], 3)
        self.assertEqual(len(result["windows_continuity_run_ids"]), 3)
        self.assertEqual(result["qualifying_three_run_ids"], [])
        self.assertFalse(result["permanent_custody_verified"])
        self.assertFalse(result["scientific_first_use_authorized"])

    def test_proven_genuine_schedule_enables_mixed_continuity(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            snap = fixture(folder,with_schedule=True)
            result = m.assess(snap,folder)
            self.assertEqual(result["verdict"], "PASS")
            self.assertEqual(result["genuine_scheduled_count"], 1)
            self.assertEqual(result["windows_recovery_count"], 2)
            self.assertEqual(result["qualifying_three_run_ids"],
                [x[0] for x in CHILDREN])
            self.assertFalse(result["permanent_custody_verified"])

    def test_a_proxy_dispatch_cannot_masquerade_as_cron(self):
        s=copy.deepcopy(self.snapshot)
        s["integrated_index"]["workflow_runs"][1]["event"]="schedule"
        self.rejects(s)

    def test_missing_receipt_or_modified_bytes(self):
        target=self.folder/str(CHILDREN[0][0])/"ubuntu-latest"/"f138-lineage.json"
        target.write_bytes(target.read_bytes()+b" ")
        self.rejects(self.snapshot)

    def test_source_drift_between_commit_and_child(self):
        s=copy.deepcopy(self.snapshot)
        s["integrated_index"]["workflow_runs"][0]["head_sha"]=OLD
        self.rejects(s)

    def test_parent_run_replay_or_unqualified_decision(self):
        first=CHILDREN[0][3]
        last=CHILDREN[2][3]
        target=self.folder/str(last)/"decision.json"
        d=json.loads(target.read_text())
        d["controller_run_id"]=first
        target.write_text(json.dumps(d))
        self.rejects(self.snapshot)

    def test_duplicate_nonces_are_fail_closed(self):
        first=CHILDREN[0][3]
        last=CHILDREN[2][3]
        p1=json.loads((self.folder/str(first)/"decision.json").read_text())
        target=self.folder/str(last)/"decision.json"
        p3=json.loads(target.read_text())
        p3["wake_nonce"]=p1["wake_nonce"]
        target.write_text(json.dumps(p3))
        self.rejects(self.snapshot)

    def test_overlap_between_completed_runs_rejected(self):
        s=copy.deepcopy(self.snapshot)
        row=s["integrated_index"]["workflow_runs"][1]
        row["created_at"]="2026-10-18T10:38:00Z"
        row["run_started_at"]=row["created_at"]
        # Sorted timestamps remain decreasing; overlapping interval violates.
        self.rejects(s)

    def test_missing_full_history_and_archive_fail_closed(self):
        s=copy.deepcopy(self.snapshot)
        s["integrated_index"]["workflow_runs"].pop()
        s["integrated_index"]["total_count"]-=1
        self.rejects(s)
        s=copy.deepcopy(self.snapshot)
        s["artifacts"][str(CHILDREN[0][0])]["artifacts"].pop()
        s["artifacts"][str(CHILDREN[0][0])]["total_count"]-=1
        self.rejects(s)

    def test_unverified_artifact_expiry_and_job_failure(self):
        s=copy.deepcopy(self.snapshot)
        s["artifacts"][str(CHILDREN[0][0])]["artifacts"][0]["expired"]=True
        self.rejects(s)
        s=copy.deepcopy(self.snapshot)
        s["jobs"][str(CHILDREN[0][0])]["jobs"][0]["conclusion"]="failure"
        self.rejects(s)

    def test_rerun_attempt_and_parent_mismatch(self):
        s=copy.deepcopy(self.snapshot)
        s["integrated_index"]["workflow_runs"][0]["run_attempt"]=2
        self.rejects(s)
        s=copy.deepcopy(self.snapshot)
        s["controller_index"]["workflow_runs"][0]["run_attempt"]=2
        self.rejects(s)

    def test_nonunique_provider_history_and_foreign_repo(self):
        s=copy.deepcopy(self.snapshot)
        s["integrated_index"]["workflow_runs"][1]["id"]=s["integrated_index"]["workflow_runs"][0]["id"]
        self.rejects(s)
        s=copy.deepcopy(self.snapshot)
        s["integrated_index"]["workflow_runs"][0]["repository"]["full_name"]="wrong/FORGE"
        self.rejects(s)

    def test_post_merge_source_lineage_only(self):
        self.assertEqual(self.assessment()["source_sha"],SHA)

    def test_collector_never_mutates_or_dispatches(self):
        script=(Path(__file__).resolve().parents[1]/"scripts"/"f138_readonly_snapshot.py").read_text()
        self.assertNotIn("gh api --method POST", script)
        self.assertNotIn('"--method", "POST"', script)
        self.assertNotIn("gh workflow run", script)
        self.assertIn('["gh","api",route]',script)
        self.assertIn('F138_NEW_DEVELOPMENT_DISPATCHES=ZERO',script)

if __name__=="__main__":
    unittest.main()

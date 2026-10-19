"""Acceptance of F139-D2's frozen original-run repair, never a second dispatch."""
import io
import json
import tempfile
from pathlib import Path
import unittest
from unittest import mock
import zipfile

from local_controller import Database, F139Error, canonical, hash_bytes
import reconcile_original as repair
import transition_original_source as transition

KEYS = ["f139-d2c-qualification-659bb1f4d751",
        "f139-d2c-wingless-659bb1f4d751"]

def zip_receipt(ticket, frozen, label, epoch=1):
    payload = canonical({
        "schema": "forge.f139.development-worker-receipt.v1",
        "ticket": ticket, "lane": frozen["lane"], "epoch": epoch,
        "run_id": frozen["run_id"], "os": label, "source_sha": repair.SOURCE,
        "development_only": True, "scientific_first_use_authorized": False,
        "scientific_originals_dispatched": 0, "accepted_ref_mutations": 0,
        "paid_model_calls": 0, "codex_calls": 0,
    })
    memory = io.BytesIO()
    with zipfile.ZipFile(memory, "w", zipfile.ZIP_DEFLATED) as bundle:
        bundle.writestr("f139-receipt.json", payload)
        bundle.writestr("f139-receipt.sha256",
                        hash_bytes(payload) + "  f139-receipt.json\n")
    return memory.getvalue()

class FrozenProvider:
    def __init__(self, original):
        self.original = original
        self.archive = {}
        for ticket, item in original.items():
            for label in ("ubuntu-latest", "windows-latest"):
                self.archive[item[label][0]] = zip_receipt(ticket, item, label)
        self.dispatch_count = 0
        self.corrupt = False
        self.legacy_disabled = True

    def legacy_dispatchers_disabled(self):
        return self.legacy_disabled

    def candidates(self, ticket, started_at):
        return {"id": self.original[ticket]["run_id"]}

    def run_proof(self, run, ticket, source, started_at):
        frozen = self.original[ticket]
        archives = []
        for label in ("ubuntu-latest", "windows-latest"):
            artifact_id, sha = frozen[label]
            data = self.archive[artifact_id]
            archives.append({
                "id": artifact_id, "name": "forge-f139-dev-receipt-" + label,
                "digest": "sha256:" + sha, "size_in_bytes": len(data),
                "workflow_run": {"id": frozen["run_id"], "head_sha": repair.SOURCE}
            })
        return (run["id"], archives)

    def artifact(self, artifact_id):
        value = self.archive[artifact_id]
        return value + b"changed" if self.corrupt else value

class OriginalQuarantineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="f139-d2e-")
        self.addCleanup(self.tmp.cleanup)
        self.dbpath = Path(self.tmp.name) / "state.sqlite"
        self.db = Database.initialize(self.dbpath, repair.SOURCE)
        self.addCleanup(self.db.close)
        original = {
            KEYS[0]: {"lane": "Qualification", "run_id": 39178196331},
            KEYS[1]: {"lane": "Wingless", "run_id": 39178299792},
        }
        for index, ticket in enumerate(KEYS):
            for label in ("ubuntu-latest", "windows-latest"):
                artifact_id = 1000 + index * 2 + (0 if label == "ubuntu-latest" else 1)
                original[ticket][label] = (artifact_id,
                         hash_bytes(zip_receipt(ticket, original[ticket], label)))
        self.original = original
        self.api = FrozenProvider(original)
        self.original_patch = mock.patch.object(repair, "ORIGINALS", original)
        self.original_patch.start()
        self.addCleanup(self.original_patch.stop)
        self.disable_patch = mock.patch.object(repair, "legacy_windows_task_disabled",
                                               return_value=True)
        self.disable_patch.start()
        self.addCleanup(self.disable_patch.stop)
        self.stopped_patch = mock.patch.object(repair, "require_stopped_controller",
                                               return_value=None)
        self.stopped_patch.start()
        self.addCleanup(self.stopped_patch.stop)
        self.db.enqueue([
            {"ticket": name, "lane": original[name]["lane"],
             "source_sha": repair.SOURCE} for name in KEYS], "f" * 64)
        self.db.enable(legacy_suspended=True)
        for index, name in enumerate(KEYS):
            self.db.claim(name, f"2026-10-18T23:5{index}:00Z")
            self.db.dispatch_observed(name)
            self.db.quarantine(name, "PROVIDER_SOURCE_EVENT_SPOOFED")
        self.assertEqual(self.db.meta()["head_seq"], 9)

    def test_audit_then_original_run_reconciliation_preserves_negative_history(self):
        before = self.db.meta()["head_hash"]
        report = repair.reconcile(self.dbpath, api=self.api)
        self.assertEqual(report["disposition"], "F139D2E_PROVIDER_AND_DB_DRY_RUN_PASS")
        self.assertEqual(report["db_writes"], 0)
        self.assertEqual(self.db.meta()["head_hash"], before)
        accepted = repair.reconcile(self.dbpath, apply=True, api=self.api)
        self.assertEqual(accepted["disposition"], "F139D2E_ORIGINAL_RUNS_RECONCILED_NO_REPLAY")
        self.assertEqual(accepted["event_head_seq"], 11)
        self.assertEqual(accepted["dispatches"], 0)
        self.assertEqual(self.db.meta()["starts"], 2)
        self.assertEqual([r["stage"] for r in self.db.status()["tasks"]],
                         ["VERIFIED", "VERIFIED"])
        for task in self.db.status()["tasks"]:
            self.assertEqual(task["quarantine_reason"], "PROVIDER_SOURCE_EVENT_SPOOFED")
            path = Path(task["evidence_dir"])
            self.assertEqual({p.name for p in path.iterdir()},
                             {"ubuntu-latest.zip", "windows-latest.zip", "manifest.json"})
        kinds = [r["kind"] for r in self.db.conn.execute("SELECT kind FROM events ORDER BY seq")]
        self.assertEqual(tuple(kinds[:9]), repair.ORIGINAL_KINDS)
        self.assertEqual(kinds[9:], ["QUARANTINE_ORIGINAL_RECONCILED"] * 2)
        with self.assertRaisesRegex(F139Error, "FROZEN_STATE_DRIFT"):
            repair.reconcile(self.dbpath, apply=True, api=self.api)
        self.assertEqual(self.api.dispatch_count, 0)

    def test_verified_originals_survive_source_transition_without_rewriting_history(self):
        repair.reconcile(self.dbpath, apply=True, api=self.api)
        original_events = list(self.db.conn.execute("SELECT kind,payload,sha FROM events ORDER BY seq"))
        original_tasks = [(x["ticket"], x["source_sha"], x["run_id"], x["evidence_sha"])
                          for x in self.db.status()["tasks"]]
        self.assertEqual(len(original_events), 11)
        replacement = "2" * 40
        self.db.transition_source(replacement)
        status = self.db.status()
        self.assertEqual(status["meta"]["source_sha"], replacement)
        self.assertEqual(status["meta"]["head_seq"], 12)
        self.assertEqual(status["meta"]["starts"], 2)
        self.assertEqual([(x["ticket"], x["source_sha"], x["run_id"], x["evidence_sha"])
                          for x in status["tasks"]], original_tasks)
        self.assertEqual(original_events, list(
            self.db.conn.execute("SELECT kind,payload,sha FROM events ORDER BY seq LIMIT 11")))
        newevent = self.db.conn.execute("SELECT kind,payload FROM events WHERE seq=12").fetchone()
        self.assertEqual(newevent["kind"], "SOURCE_TRANSITION_ADMITTED")
        self.assertEqual(json.loads(newevent["payload"])["from_source_sha"], repair.SOURCE)
        self.db.close()
        self.db = Database(self.dbpath)
        self.assertEqual(self.db.meta()["source_sha"], replacement)
        with self.assertRaisesRegex(F139Error, "OWNER_OR_IDENTITY"):
            self.db.transition_source(replacement)
        self.db.close()  # Explicitly release SQLite handles before Windows TempDirectory cleanup

    def test_transition_disallowed_for_quarantined_attempts(self):
        with self.assertRaisesRegex(F139Error, "UNVERIFIED_OR_PENDING"):
            self.db.transition_source("2" * 40)
        self.assertEqual(self.db.meta()["head_seq"], 9)
        self.assertEqual(self.db.meta()["source_sha"], repair.SOURCE)

    def test_transition_event_tamper_fails_closed(self):
        repair.reconcile(self.dbpath, apply=True, api=self.api)
        self.db.transition_source("2" * 40)
        self.db.conn.execute("UPDATE meta SET source_sha=? WHERE id=1", ("3" * 40,))
        with self.assertRaisesRegex(F139Error, "SOURCE_TRANSITION_HEAD_INVALID"):
            self.db.verify()

    def test_original_source_promotion_backed_up_once_without_replay(self):
        repair.reconcile(self.dbpath, apply=True, api=self.api)
        nextsha = "2" * 40
        self.api.protected_main = lambda: nextsha
        with mock.patch.object(transition, "ORIGINALS", self.original), \
             mock.patch.object(transition, "verify_inactive_owners", return_value=None):
            old = self.db.meta()
            dry = transition.reconcile_source(self.dbpath, nextsha, api=self.api)
            self.assertEqual(dry["disposition"], "F139_SOURCE_TRANSITION_DRY_RUN_PASS")
            self.assertEqual(dry["db_writes"], 0)
            self.assertEqual(self.db.meta()["head_hash"], old["head_hash"])
            applied = transition.reconcile_source(self.dbpath, nextsha, apply=True, api=self.api)
            self.assertEqual(applied["disposition"],
                             "F139_SOURCE_TRANSITION_COMMITTED_HISTORICAL_SOURCE_PRESERVED")
            self.assertEqual(applied["head_seq"], 12)
            self.assertEqual(applied["dispatches"], 0)
            self.assertEqual(applied["historic_ticket_sources_rewritten"], 0)
            self.assertTrue(Path(applied["backup"]).is_file())
            before = self.db.meta()
            self.assertEqual(before["source_sha"], nextsha)
            self.assertTrue(all(task["source_sha"] == repair.SOURCE for task in
                                self.db.status()["tasks"]))
            self.assertEqual(self.db.meta()["starts"], 2)
            with self.assertRaisesRegex(F139Error, "ORIGINAL_SOURCE_OR_HEAD_DRIFT"):
                transition.reconcile_source(self.dbpath, nextsha, apply=True, api=self.api)
            self.assertEqual(self.api.dispatch_count, 0)

    def test_transition_rejects_wrong_new_protected_main_without_database_writes(self):
        repair.reconcile(self.dbpath, apply=True, api=self.api)
        self.api.protected_main = lambda: "3" * 40
        with mock.patch.object(transition, "ORIGINALS", self.original), \
             mock.patch.object(transition, "verify_inactive_owners", return_value=None):
            with self.assertRaisesRegex(F139Error, "NEW_MAIN_NOT_PROTECTED_EXACT"):
                transition.reconcile_source(self.dbpath, "2" * 40, apply=True, api=self.api)
            self.assertEqual(self.db.meta()["head_seq"], 11)
            self.assertFalse((self.dbpath.parent / "source-transition-custody").exists())

    def test_mismatched_zip_blocks_without_history_change(self):
        self.api.corrupt = True
        before = self.db.meta()["head_hash"]
        with self.assertRaisesRegex(F139Error, "EXTERNAL_ARTIFACT_BYTES"):
            repair.reconcile(self.dbpath, apply=True, api=self.api)
        self.assertEqual(self.db.meta()["head_hash"], before)

    def test_modified_quarantine_reason_blocks_without_history_change(self):
        self.db.conn.execute(
            "UPDATE tasks SET quarantine_reason='UNCLASSIFIED_REJECTION' WHERE ticket=?",
            (KEYS[0],))
        with self.assertRaisesRegex(F139Error, "QUARANTINE_STATE_DRIFT"):
            repair.reconcile(self.dbpath, api=self.api)
        self.assertEqual(self.db.meta()["head_seq"], 9)

    def test_legacy_owner_reenabled_blocks_before_archive_or_write(self):
        self.api.legacy_disabled = False
        with self.assertRaisesRegex(F139Error, "LEGACY_OWNER_NOT_DISABLED"):
            repair.reconcile(self.dbpath, apply=True, api=self.api)
        self.assertEqual(self.db.meta()["head_seq"], 9)
        self.assertFalse((self.dbpath.parent / "evidence").exists())

    def test_partial_archive_refuses_overwrite(self):
        first = KEYS[0]
        folder = self.dbpath.parent / "evidence" / first / str(self.original[first]["run_id"])
        folder.mkdir(parents=True)
        (folder / "ubuntu-latest.zip").write_bytes(b"partial")
        with self.assertRaisesRegex(F139Error, "EVIDENCE_RECOVERY_CONFLICT"):
            repair.reconcile(self.dbpath, apply=True, api=self.api)
        self.assertEqual((folder / "ubuntu-latest.zip").read_bytes(), b"partial")
        self.assertEqual(self.db.meta()["head_seq"], 9)

    def test_exact_source_boundary(self):
        self.db.conn.execute("UPDATE meta SET source_sha=? WHERE id=1", ("0" * 40,))
        with self.assertRaisesRegex(F139Error, "FROZEN_STATE_DRIFT"):
            repair.reconcile(self.dbpath, api=self.api)
        self.assertEqual(self.api.dispatch_count, 0)

if __name__ == "__main__":
    unittest.main()

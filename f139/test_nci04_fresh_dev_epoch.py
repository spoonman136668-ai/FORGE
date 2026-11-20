"""Development-only, synthetic cold-custody tests for inert fresh F139 staging.

The V59 full original-host verifier is stubbed here. These tests do NOT
qualify Windows owner quiescence, task rebind, science or live activation.
"""
from __future__ import annotations

import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from f139.local_controller import Database, SingleOwner
from f139.nci04_native_contract import canonical
from f139.nci04_v59_owner_forward_readiness import SOURCE, HEAD_SEQ, HEAD_SHA256
from f139.nci04_fresh_dev_epoch import (
    FreshDevelopmentDenied, SCHEMA, hash_file, prepare_inert_epoch,
)

TARGET = "0d933a15507f132826b4fc6e5608c3d2d16cbfe3"
RUN = 44584522737
PREFIX = "f139.nci04_fresh_dev_epoch"


class SyntheticFreshDevelopmentTests(unittest.TestCase):
    def setUp(self):
        t = tempfile.TemporaryDirectory(prefix="f139-fresh-dev-fixture-")
        self.addCleanup(t.cleanup)
        self.root = Path(t.name) / "FORGE-F139"
        self.root.mkdir()
        self.old = self.root / "state.sqlite"
        x = Database.initialize(self.old, SOURCE)
        x.close()
        self.orig = Database.open_readonly(self.old)
        self.addCleanup(self.orig.close)
        # open_readonly intentionally resolves the original SQLite path.
        # Windows temporary-directory aliases need its canonical root when
        # constructing the same-owner, sibling archive identity.
        self.root = self.orig.filename.parent
        self.old = self.orig.filename
        self.before_old_hash = hash_file(self.old)
        self.archive = self.root / ("f139-v59-before-" + str(RUN))
        self.archive.mkdir()
        backup = self.archive / "state.sqlite"
        shutil.copyfile(self.old, backup)
        self.cold = {
            "schema": "forge.f139.v59.original-cold-createonly.v1",
            "owner_run_id": RUN, "original_source_sha": SOURCE,
            "target_source_sha": TARGET,
            "original_head_seq": HEAD_SEQ,
            "original_head_sha256": HEAD_SHA256,
            "source_transition_authorized": False,
            "scientific_first_use": False, "owner_mutations": 0,
            "files_sha256": {"state.sqlite": hash_file(backup)},
        }
        self.seal = self.archive / "manifest.sha256.json"
        self.write_seal()
        self.frozen = {
            "source_sha": SOURCE, "head_seq": HEAD_SEQ,
            "head_sha256": HEAD_SHA256,
        }
        self.verified = {
            "from_source_sha": SOURCE, "to_source_sha": TARGET,
            "original_head_seq": HEAD_SEQ,
            "original_head_sha256": HEAD_SHA256,
            "backup_sqlite_sha256": hash_file(backup),
            "original_owner_mutations": 0,
            "source_transition_authorized": False,
            "scientific_first_use": False,
        }
        self.locks = patch.object(SingleOwner, "held", return_value=True)
        self.auditor = patch(
            PREFIX + ".audit_frozen_original_readonly",
            return_value=self.frozen)
        self.verifier = patch(
            PREFIX + ".verify_original_cold_backup",
            return_value=self.verified)
        self.exclusions = {
            "schema": "forge.f139.fresh-development-consumed-exclusions.v1",
            "source_sha": SOURCE, "original_head_seq": HEAD_SEQ,
            "original_head_sha256": HEAD_SHA256,
            "old_issue_numbers": [687], "old_tickets": ["prior-ticket"],
            "release_qualified": False, "fresh_activation_authorized": False,
            "previous_work_replay_authorized": False,
        }
        self.history = patch(
            PREFIX + ".freeze_original_exclusions",
            return_value=self.exclusions)
        from f139.nci04_fresh_yggdrasil_boundary import (
            ACCEPTED, AMALGAM_HEAD, LINEAGE_HEAD,
        )
        from f139.nci04_fresh_yggdrasil_boundary import (
            RECEIPT_SCHEMA as YGG_SCHEMA,
        )
        self.lineage = {
            "schema": YGG_SCHEMA,
            "accepted_main_source_sha": ACCEPTED,
            "amalgam_draft_head_sha": AMALGAM_HEAD,
            "lineage_draft_head_sha": LINEAGE_HEAD,
            "checkpoint_imported": False,
            "model_continuation_authorized": False,
            "release_qualified": False,
        }
        self.ygg = patch(
            PREFIX + ".read_yggdrasil_research_boundary",
            return_value=self.lineage)
        for p in (self.locks, self.auditor, self.verifier, self.history, self.ygg):
            p.start()
            self.addCleanup(p.stop)

    def write_seal(self):
        self.seal.write_bytes(canonical(self.cold))

    def prepare(self, **kw):
        arguments = {
            "target": TARGET, "owner_run_id": RUN,
            "task_quiescence_witness": lambda: True,
            "yggdrasil_readonly_get": lambda route: {},
        }
        arguments.update(kw)
        return prepare_inert_epoch(self.orig, self.archive, **arguments)

    def fresh(self):
        return self.root / ("f139-fresh-dev-" + str(RUN))

    def test_creates_only_separate_disabled_empty_sqlite(self):
        report = self.prepare()
        self.assertEqual(report["schema"], SCHEMA)
        self.assertEqual(report["previous_source_sha"], SOURCE)
        self.assertEqual(report["historical_head_seq"], HEAD_SEQ)
        self.assertEqual(report["target_source_sha"], TARGET)
        self.assertFalse(report["fresh_database_enabled"])
        self.assertFalse(report["scientific_first_use"])
        self.assertFalse(report["old_work_replay_authorized"])
        self.assertFalse(report["owner_task_rebind_authorized"])
        self.assertFalse(report["release_qualified"])
        self.assertEqual(report["original_owner_mutations"], 0)
        self.assertEqual(report["original_task_mutations"], 0)
        self.assertEqual(report["fresh_queue_entries"], 0)
        self.assertEqual(report["paid_model_calls"], 0)
        self.assertTrue(self.old.is_file())
        self.assertEqual(hash_file(self.old), self.before_old_hash)
        newdb = Database(self.fresh() / "state.sqlite")
        try:
            meta = newdb.meta()
            self.assertEqual(meta["enabled"], 0)
            self.assertEqual(meta["legacy_suspended"], 0)
            self.assertEqual(meta["head_seq"], 0)
            self.assertEqual(meta["source_sha"], TARGET)
            self.assertEqual(newdb.conn.execute(
                "SELECT COUNT(*) FROM events").fetchone()[0], 0)
            self.assertEqual(newdb.conn.execute(
                "SELECT COUNT(*) FROM tasks").fetchone()[0], 0)
        finally:
            newdb.close()
        disk = (self.fresh() / "fresh-dev-manifest.sha256.json").read_bytes()
        receipt = json.loads(disk)
        self.assertEqual(disk, canonical(receipt))
        self.assertFalse(receipt["owner_task_rebind_authorized"])
        prior = (self.fresh() / "consumed-development-identities.json")
        self.assertEqual(prior.read_bytes(), canonical(self.exclusions))
        from f139.nci04_native_contract import digest
        self.assertEqual(receipt["historical_consumed_exclusions_sha256"],
                         digest(prior.read_bytes()))
        self.assertFalse(json.loads(prior.read_bytes())["release_qualified"])
        ygg = (self.fresh() / "yggdrasil-research-lineage.json")
        self.assertEqual(ygg.read_bytes(), canonical(self.lineage))
        self.assertEqual(receipt["yggdrasil_research_boundary_sha256"],
                         digest(ygg.read_bytes()))
        self.assertEqual(
            receipt["yggdrasil_accepted_main_sha"],
            self.lineage["accepted_main_source_sha"])
        self.assertFalse(receipt["yggdrasil_checkpoint_imported"])
        self.assertFalse(receipt["yggdrasil_owner_continuation_authorized"])

    def test_missing_yggdrasil_reader_never_stages_state(self):
        with self.assertRaisesRegex(FreshDevelopmentDenied,
                                    "YGGDRASIL_GITHUB_READONLY_READER_REQUIRED"):
            self.prepare(yggdrasil_readonly_get=None)
        self.assertFalse(self.fresh().exists())

    def test_research_draft_reclassified_as_accepted_denies_state(self):
        with patch(PREFIX + ".read_yggdrasil_research_boundary",
                   return_value={
                       **self.lineage, "checkpoint_imported": True}):
            with self.assertRaisesRegex(FreshDevelopmentDenied,
                                        "YGGDRASIL_MODEL_OR_SOURCE_CUSTODY_INVALID"):
                self.prepare()
        self.assertFalse(self.fresh().exists())

    def test_unqualified_history_never_creates_fresh(self):
        with patch(PREFIX + ".freeze_original_exclusions",
                   return_value={**self.exclusions,
                                 "fresh_activation_authorized": True}):
            with self.assertRaisesRegex(FreshDevelopmentDenied,
                                        "CONSUMED_HISTORY_NOT_FROZEN"):
                self.prepare()
        self.assertFalse(self.fresh().exists())

    def test_history_freezer_failure_never_creates_fresh(self):
        with patch(PREFIX + ".freeze_original_exclusions",
                   side_effect=ValueError("F139_OLD_CUSTODY_MISSING")):
            with self.assertRaisesRegex(ValueError, "OLD_CUSTODY_MISSING"):
                self.prepare()
        self.assertFalse(self.fresh().exists())

    def test_second_prepare_denied_without_overwrite(self):
        first = self.prepare()
        with self.assertRaisesRegex(FreshDevelopmentDenied, "FRESH_PATH_INVALID"):
            self.prepare()
        self.assertEqual(hash_file(self.old), self.before_old_hash)
        self.assertEqual(first["fresh_sqlite_sha256"],
                         hash_file(self.fresh() / "state.sqlite"))

    def test_no_quiescence_never_creates_fresh(self):
        with self.assertRaisesRegex(FreshDevelopmentDenied, "NOT_QUIESCED"):
            self.prepare(task_quiescence_witness=lambda: False)
        self.assertFalse(self.fresh().exists())

    def test_no_owner_mutex_never_creates_fresh(self):
        with patch.object(SingleOwner, "held", return_value=False):
            with self.assertRaisesRegex(FreshDevelopmentDenied, "MUTEX_INVALID"):
                self.prepare()
        self.assertFalse(self.fresh().exists())

    def test_wrong_target_or_run_denied(self):
        for kw in ({"target": SOURCE}, {"target": "invalid"},
                   {"owner_run_id": RUN - RUN}, {"owner_run_id": True}):
            with self.subTest(kw=kw):
                with self.assertRaisesRegex(FreshDevelopmentDenied, "TARGET_OR_RUN"):
                    self.prepare(**kw)
        self.assertFalse(self.fresh().exists())

    def test_stale_frozen_owner_denied(self):
        with patch(PREFIX + ".audit_frozen_original_readonly",
                   return_value={"source_sha": SOURCE,
                                 "head_seq": HEAD_SEQ - 1,
                                 "head_sha256": HEAD_SHA256}):
            with self.assertRaisesRegex(FreshDevelopmentDenied, "PREIMAGE_DRIFT"):
                self.prepare()
        self.assertFalse(self.fresh().exists())

    def test_modified_backup_bytes_denied(self):
        with (self.archive / "state.sqlite").open("ab") as f:
            f.write(b"tampered-backup")
        with self.assertRaisesRegex(FreshDevelopmentDenied, "BYTES_DRIFT"):
            self.prepare()
        self.assertFalse(self.fresh().exists())

    def test_missing_archive_manifest_denied(self):
        self.seal.unlink()
        with self.assertRaisesRegex(FreshDevelopmentDenied, "SEALED_ARCHIVE_MISSING"):
            self.prepare()
        self.assertFalse(self.fresh().exists())

    def test_uncertified_archive_denied(self):
        with patch(PREFIX + ".verify_original_cold_backup",
                   return_value={**self.verified, "scientific_first_use": True}):
            with self.assertRaisesRegex(FreshDevelopmentDenied,
                                        "COLD_VERIFIER_REJECTED"):
                self.prepare()
        self.assertFalse(self.fresh().exists())

    def test_archive_mutation_flag_denied(self):
        self.cold["owner_mutations"] = 1
        self.write_seal()
        with self.assertRaisesRegex(FreshDevelopmentDenied, "MANIFEST_PREIMAGE"):
            self.prepare()
        self.assertFalse(self.fresh().exists())

    def test_archive_extra_file_denied(self):
        (self.archive / "unexpected.txt").write_text("unexpected")
        with self.assertRaisesRegex(FreshDevelopmentDenied, "INVENTORY_DRIFT"):
            self.prepare()
        self.assertFalse(self.fresh().exists())


    def test_fresh_disabled_epoch_routes_before_any_original_feed_or_remote(self):
        self.prepare()
        from f139.local_controller import run_once
        from f139.nci04_fresh_native_owner_route import SCHEMA as ROUTE_SCHEMA
        newdb = Database(self.fresh() / "state.sqlite")
        class ForbiddenProvider:
            def __getattribute__(self, name):
                raise AssertionError("FRESH_DISABLED_MUST_NEVER_FETCH_" + name)
        try:
            before = newdb.meta()
            result = run_once(
                newdb, ForbiddenProvider(), self.fresh() / "state.sqlite",
                "synthetic-local-only-" + "x" * 44)
            self.assertEqual(result["schema"], ROUTE_SCHEMA)
            self.assertEqual(
                result["disposition"],
                "FRESH_DEVELOPMENT_STAGED_DISABLED_NO_DISPATCH")
            self.assertEqual(result["staged_owner_run_id"], RUN)
            self.assertEqual(result["source_sha"], TARGET)
            self.assertEqual(result["original_head_seq"], HEAD_SEQ)
            self.assertFalse(result["fresh_native_activation_authorized"])
            self.assertFalse(result["original_task_rebind_authorized"])
            self.assertFalse(result["fresh_work_admitted"])
            self.assertFalse(result["worker_dispatched"])
            self.assertFalse(result["yggdrasil_checkpoint_loaded"])
            self.assertFalse(result["scientific_first_use"])
            self.assertEqual(result["paid_model_calls"], 0)
            self.assertEqual(newdb.meta(), before)
            self.assertEqual(
                newdb.conn.execute("SELECT COUNT(*) FROM events").fetchone()[0], 0)
            self.assertEqual(
                newdb.conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0], 0)
        finally:
            newdb.close()
        self.assertEqual(hash_file(self.old), self.before_old_hash)

    def test_fresh_route_rejects_provenance_byte_tamper_without_dispatch(self):
        self.prepare()
        from f139.nci04_fresh_native_owner_route import (
            FreshNativeRouteDenied, inspect_staged_fresh_native_mode,
        )
        file = self.fresh() / "consumed-development-identities.json"
        parsed = json.loads(file.read_bytes())
        parsed["old_issue_numbers"] = [1000001]
        file.write_bytes(canonical(parsed))
        newdb = Database(self.fresh() / "state.sqlite")
        try:
            with self.assertRaisesRegex(
                    FreshNativeRouteDenied, "PROVENANCE_DIGEST_DRIFT"):
                inspect_staged_fresh_native_mode(
                    newdb, self.fresh() / "state.sqlite")
            self.assertEqual(newdb.meta()["enabled"], 0)
            self.assertEqual(newdb.meta()["head_seq"], 0)
        finally:
            newdb.close()

    def test_fresh_route_fails_closed_on_locally_forged_activation_event(self):
        self.prepare()
        from f139.nci04_fresh_native_owner_route import (
            FreshNativeRouteDenied, inspect_staged_fresh_native_mode,
        )
        newdb = Database(self.fresh() / "state.sqlite")
        try:
            with newdb.transaction():
                newdb.event("FRESH_NATIVE_DEVELOPMENT_ACTIVATED", {
                    "claim": "untrusted synthetic activation",
                    "scientific_first_use": False,
                })
            with self.assertRaisesRegex(
                    FreshNativeRouteDenied, "FRESH_DB_NOT_DISABLED_AND_EMPTY"):
                inspect_staged_fresh_native_mode(
                    newdb, self.fresh() / "state.sqlite")
        finally:
            newdb.close()

    def test_original_database_is_not_classified_as_fresh(self):
        from f139.nci04_fresh_native_owner_route import (
            inspect_staged_fresh_native_mode,
        )
        self.assertIsNone(
            inspect_staged_fresh_native_mode(self.orig, self.old))
        # A legacy imported class alias or thin test stand-in cannot be
        # rejected by a fresh-epoch-only identity check.
        self.assertIsNone(
            inspect_staged_fresh_native_mode(object(), self.old))

    def test_actual_windows_module_entrypoint_alias_is_accepted(self):
        self.prepare()
        from f139.nci04_fresh_native_owner_route import (
            inspect_staged_fresh_native_mode,
        )
        # Python -m f139.local_controller defines Database in __main__,
        # even though the fresh guard imports f139.local_controller.
        # This exercises the real SQLite class shape and known CLI alias.
        alias = type("Database", (Database,), {"__module__": "__main__"})
        db = alias(self.fresh() / "state.sqlite")
        try:
            result = inspect_staged_fresh_native_mode(
                db, self.fresh() / "state.sqlite")
            self.assertEqual(
                result["disposition"],
                "FRESH_DEVELOPMENT_STAGED_DISABLED_NO_DISPATCH")
            self.assertFalse(result["worker_dispatched"])
            self.assertFalse(result["fresh_native_activation_authorized"])
        finally:
            db.close()

    def test_fresh_path_rejects_foreign_database_object(self):
        self.prepare()
        from f139.nci04_fresh_native_owner_route import (
            FreshNativeRouteDenied, inspect_staged_fresh_native_mode,
        )
        with self.assertRaisesRegex(
                FreshNativeRouteDenied, "FRESH_DATABASE_CLASS_INVALID"):
            inspect_staged_fresh_native_mode(
                object(), self.fresh() / "state.sqlite")

    def test_fresh_staging_manifest_tamper_cannot_route(self):
        self.prepare()
        from f139.nci04_fresh_native_owner_route import (
            FreshNativeRouteDenied, inspect_staged_fresh_native_mode,
        )
        path = self.fresh() / "fresh-dev-manifest.sha256.json"
        record = json.loads(path.read_bytes())
        record["source_transition_authorized"] = True
        path.write_bytes(canonical(record))
        newdb = Database(self.fresh() / "state.sqlite")
        try:
            with self.assertRaisesRegex(
                    FreshNativeRouteDenied, "STAGE_MANIFEST_NOT_DISABLED"):
                inspect_staged_fresh_native_mode(
                    newdb, self.fresh() / "state.sqlite")
        finally:
            newdb.close()

    def make_synthetic_activation(self, *,
                                  release_override=None,
                                  floor_override=None):
        """Synthetic SQLite ONLY; no Windows task or GitHub API is invoked."""
        from f139.nci04_native_contract import digest
        from f139.nci04_fresh_native_activation import (
            ACTIVATION_KIND, ACTIVATION_SCHEMA, OWNER_RELEASE_SCHEMA,
        )
        from f139.nci04_fresh_remote_floor import SCHEMA as FLOOR_SCHEMA
        from f139.nci04_fresh_yggdrasil_boundary import ACCEPTED
        self.prepare()
        path = self.fresh() / "state.sqlite"
        stage_raw = (self.fresh() / "fresh-dev-manifest.sha256.json").read_bytes()
        exclusions_raw = (
            self.fresh() / "consumed-development-identities.json").read_bytes()
        lineage_raw = (
            self.fresh() / "yggdrasil-research-lineage.json").read_bytes()
        floor = {
            "schema": FLOOR_SCHEMA,
            "original_source_sha": SOURCE,
            "original_head_seq": HEAD_SEQ,
            "original_head_sha256": HEAD_SHA256,
            "target_forge_source_sha": TARGET,
            "consumed_exclusions_sha256": digest(exclusions_raw),
            "remote_cutover_issue_number_floor": 1835,
            "remote_cutover_issue_provider_verified": True,
            "fresh_activation_authorized": False,
            "owner_task_rebind_authorized": False,
            "release_qualified": False,
            "scientific_first_use": False,
        }
        if floor_override:
            floor.update(floor_override)
        floor_raw = canonical(floor)
        (self.fresh() / "remote-issue-cutover-floor.json").write_bytes(
            floor_raw)
        release = {
            "schema": OWNER_RELEASE_SCHEMA,
            "owner_task_name": "FORGE-F139-UnifiedController",
            "target_forge_source_sha": TARGET,
            "owner_run_id": RUN,
            "original_source_sha": SOURCE,
            "original_head_seq": HEAD_SEQ,
            "original_head_sha256": HEAD_SHA256,
            "remote_cutover_receipt_sha256": digest(floor_raw),
            "original_task_quiesced": True,
            "original_process_absent": True,
            "original_mutex_held": True,
            "original_sid_independently_verified": True,
            "single_task_rebind_authorized": True,
            "new_controller": False,
            "new_scheduler": False,
            "scientific_first_use": False,
        }
        if release_override:
            release.update(release_override)
        release_raw = canonical(release)
        (self.fresh() / "original-task-release.json").write_bytes(
            release_raw)
        db = Database(path)
        db.enable(legacy_suspended=True)
        record = {
            "schema": ACTIVATION_SCHEMA,
            "source_sha": TARGET,
            "prior_event_head_sha256": db.meta()["head_hash"],
            "owner_run_id": RUN,
            "original_source_sha": SOURCE,
            "original_head_seq": HEAD_SEQ,
            "original_head_sha256": HEAD_SHA256,
            "stage_manifest_sha256": digest(stage_raw),
            "consumed_exclusions_sha256": digest(exclusions_raw),
            "yggdrasil_research_boundary_sha256": digest(lineage_raw),
            "remote_cutover_receipt_sha256": digest(floor_raw),
            "original_task_release_receipt_sha256": digest(release_raw),
            "remote_issue_number_floor": floor["remote_cutover_issue_number_floor"],
            "accepted_yggdrasil_main_sha": ACCEPTED,
            "development_only": True,
            "scientific_first_use": False,
            "paid_model_calls": 0,
            "new_controller": False,
            "new_scheduler": False,
            "new_queue": False,
            "worker_dispatch_authorized": False,
            "model_continuation_authorized": False,
        }
        with db.transaction():
            db.event(ACTIVATION_KIND, record)
        return db, record

    def test_versioned_activation_is_audited_but_still_cannot_dispatch(self):
        from f139.local_controller import run_once
        from f139.nci04_fresh_native_activation import (
            audit_fresh_native_activation,
        )
        from f139.nci04_fresh_native_owner_route import (
            inspect_staged_fresh_native_mode,
        )
        db, record = self.make_synthetic_activation()
        try:
            db.verify()
            self.assertEqual(audit_fresh_native_activation(db), record)
            before = db.meta()
            class ForbiddenProvider:
                def __getattribute__(self, name):
                    raise AssertionError("PROVIDER_ACCESS_DURING_FRESH_" + name)
            outcome = run_once(
                db, ForbiddenProvider(), self.fresh() / "state.sqlite",
                "dev-only-hmac-not-used-" + "a" * 32)
            self.assertEqual(
                outcome["disposition"],
                "FRESH_ACTIVATION_RECORDED_DISPATCH_BLOCKED")
            self.assertTrue(outcome["activation_event_recorded"])
            self.assertFalse(outcome["owner_release_independently_verified_runtime"])
            self.assertFalse(outcome["native_issue_admission_authorized"])
            self.assertFalse(outcome["fresh_native_activation_authorized"])
            self.assertFalse(outcome["worker_dispatched"])
            self.assertFalse(outcome["yggdrasil_checkpoint_loaded"])
            self.assertEqual(db.meta(), before)
            self.assertEqual(db.conn.execute(
                "SELECT COUNT(*) FROM tasks").fetchone()[0], 0)
        finally:
            db.close()
        self.assertEqual(hash_file(self.old), self.before_old_hash)

    def test_missing_original_host_release_never_grants_activation_dispatch(self):
        from f139.nci04_fresh_native_owner_route import (
            FreshNativeRouteDenied, inspect_staged_fresh_native_mode,
        )
        db, record = self.make_synthetic_activation()
        try:
            (self.fresh() / "original-task-release.json").unlink()
            db.verify()
            with self.assertRaisesRegex(
                    FreshNativeRouteDenied, "PROVENANCE_FILE_NOT_SEALED"):
                inspect_staged_fresh_native_mode(
                    db, self.fresh() / "state.sqlite")
        finally:
            db.close()

    def test_unqualified_release_and_floor_fail_closed(self):
        from f139.nci04_fresh_native_activation import FreshActivationDenied
        from f139.nci04_fresh_native_owner_route import (
            inspect_staged_fresh_native_mode,
        )
        db, record = self.make_synthetic_activation(
            release_override={"original_sid_independently_verified": False})
        try:
            with self.assertRaisesRegex(
                    FreshActivationDenied, "ORIGINAL_WINDOWS_OWNER_RELEASE"):
                inspect_staged_fresh_native_mode(
                    db, self.fresh() / "state.sqlite")
        finally:
            db.close()

    def test_fresh_cutover_floor_cannot_replay_known_original_issue(self):
        from f139.nci04_fresh_native_activation import FreshActivationDenied
        from f139.nci04_fresh_native_owner_route import (
            inspect_staged_fresh_native_mode,
        )
        db, record = self.make_synthetic_activation(
            floor_override={"remote_cutover_issue_number_floor": 1})
        try:
            with self.assertRaisesRegex(
                    FreshActivationDenied, "ORIGINAL_PROVIDER_FLOOR"):
                inspect_staged_fresh_native_mode(
                    db, self.fresh() / "state.sqlite")
            self.assertEqual(db.conn.execute(
                "SELECT COUNT(*) FROM tasks").fetchone()[0], 0)
        finally:
            db.close()

    def test_duplicate_or_mutated_activation_event_is_rejected_on_cold_verify(self):
        from f139.nci04_fresh_native_activation import (
            ACTIVATION_KIND, FreshActivationDenied,
        )
        db, record = self.make_synthetic_activation()
        try:
            with db.transaction():
                db.event(ACTIVATION_KIND, record)
            with self.assertRaisesRegex(
                    FreshActivationDenied, "LOCAL_ACTIVATION_EVENT_SEQUENCE_INVALID"):
                db.verify()
        finally:
            db.close()

    def test_original_nonfresh_activation_audit_never_requires_fresh_receipts(self):
        from f139.nci04_fresh_native_activation import audit_fresh_native_activation
        self.assertIsNone(audit_fresh_native_activation(self.orig))
        self.assertEqual(hash_file(self.old), self.before_old_hash)

if __name__ == "__main__":
    unittest.main()

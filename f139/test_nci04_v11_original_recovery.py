"""Fail-closed post-G54 original owner recovery source and trigger checks."""
from __future__ import annotations

import inspect
from pathlib import Path
import unittest

from f139.local_controller import Database, SingleOwner, cli, g54_original_canonical
from f139.nci04_v11_owner_release import SOURCE_V10


class OriginalV11RecoveryTests(unittest.TestCase):
    def test_g54_exact_unreplayed_task_survives_new_v11_source(self):
        cold = inspect.getsource(Database.verify)
        self.assertIn("negative_v11", cold)
        self.assertIn("V11_SOURCE_TRANSITION_DUPLICATED", cold)
        self.assertIn("g54_custody = g54_original_canonical(self)", cold)
        self.assertIn("prior_g54_ambiguous", cold)
        self.assertIn("or prior_prepost_negative or prior_g54_ambiguous", cold)
        self.assertIn('row["stage"] == "QUARANTINED"', cold)
        self.assertIn('row["run_id"] is None', cold)
        self.assertIn('row["source_sha"] in historical_sources', cold)

    def test_no_class_name_or_sqlite_copy_substitution(self):
        helper = inspect.getsource(g54_original_canonical)
        self.assertIn("type(db) is CanonicalDatabase", helper)
        self.assertIn("g54_original_canonical", inspect.getsource(Database.verify))
        self.assertIn("Path(main.__file__).resolve(strict=True)", helper)
        self.assertIn("Path(db.filename).resolve(strict=True)", helper)
        self.assertIn("CanonicalDatabase(original)", helper)
        self.assertNotIn("tempfile", helper)

    def test_only_existing_windows_owner_witness_may_cut_over(self):
        workflow = (Path(__file__).resolve().parent.parent /
                    ".github/workflows/f139-g54-v9-owner-cutover.yml").read_text()
        self.assertEqual(workflow.count("  v11-recover-original:\n"), 1)
        self.assertEqual(workflow.count("  v11-recovery-readonly:\n"), 1)
        self.assertEqual(workflow.count("  read-only-status:\n"), 1)
        self.assertIn("F139-V11-OWNER-RECOVER ", workflow)
        self.assertIn("F139-V11-RECOVERY-STATUS ", workflow)
        self.assertIn("F139_V11_RECOVER_ORIGINAL_TASK_NOT_SAFELY_DISABLED", workflow)
        self.assertIn("F139_V11_RECOVER_ESCALATED_ORIGINAL_OWNER_REQUIRED", workflow)
        self.assertIn("F139_V11_RECOVER_SOURCE_APPROVAL_INVALID", workflow)
        self.assertIn("F139_V11_RECOVER_ORIGINAL_SQLITE_NOT_UNCHANGED_249", workflow)
        self.assertIn("F139_V11_RECOVER_G54_NO_REPLAY=PASS", workflow)
        self.assertIn("F139_V11_RECOVER_POSTWRITE_ORIGINAL_TASK_HELD_DISABLED", workflow)
        self.assertIn("F139_V11_RECOVERY_READ_ONLY=PASS", workflow)
        self.assertIn("F139_V11_RECOVER_SCIENTIFIC_FIRST_USE=FALSE", workflow)
        self.assertIn("F139_V11_RECOVER_PAID_MODEL_CALLS=0", workflow)
        self.assertIn("F139_V11_RECOVER_NEW_CONTROLLER=FALSE", workflow)
        self.assertIn("FORGE-CODEX-REMOTE", workflow)
        self.assertIn(SOURCE_V10, workflow)

    def test_original_cli_keeps_native_source_admission_bound_to_owner(self):
        entry = inspect.getsource(cli)
        self.assertIn('"transition-qualified-native-v11"', entry)
        self.assertIn('native_original_owner_profile(args.db)', entry)
        self.assertIn("with SingleOwner(args.db.with_suffix(\".lock\"))", entry)
        self.assertNotIn("owner_model_write(", inspect.getsource(Database.transition_source))


if __name__ == "__main__":
    unittest.main()

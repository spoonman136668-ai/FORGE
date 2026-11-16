"""V40 original native-owner isolation and negative engineering contracts.

No original Windows task, SQLite, owner credentials or workflow run is
accessed by this unit suite; it tests source-only fail-closed boundaries.
"""
import inspect
import unittest
from pathlib import Path

from f139 import nci04_v41_hybrid_event1833_owner as owner
from f139 import nci04_v41_hybrid_event1833_commit as commit
from f139 import nci04_v41_hybrid_event1833_postcommit as post
from f139 import nci04_v41_hybrid_event1833_cold as cold
from f139 import nci04_v41_hybrid_event1833_successor as successor


class V40OwnerReleaseContractTests(unittest.TestCase):
    def test_real_original_event1832_source_and_immutable_owner_custody(self):
        self.assertEqual(successor.SOURCE,
                         "1479f963160001037566e4cef33582c5293fb773")
        self.assertEqual(successor.PREDECESSOR_SEQ, 1832)
        self.assertEqual(successor.PREDECESSOR_OWNER_EVENT_ID, 6902399422)
        self.assertEqual(successor.PREDECESSOR_BACKUP_RUN_ID, 43769577997)
        self.assertEqual(owner.PREDECESSOR_SOURCE_COMMIT_COMMENT_ID,
                         6902472106)
        self.assertEqual(owner.PREDECESSOR_POSTCOMMIT_COMMENT_ID,
                         6902549450)
        self.assertEqual(owner.PR, 1777)
        self.assertEqual(
            owner.BRANCH,
            "engineering/f139-v39-event1832-postwrite-canonical-readback-20261115")
        self.assertEqual(commit.BACKUP_JOB,
                         "hybrid-v40-original-event1832-backup")
        self.assertEqual(
            commit.BACKUP_WORKFLOW,
            "FORGE F139 V39 guarded original-owner successor source-only")

    def test_real_owner_required_for_every_live_source_adapter(self):
        with self.assertRaises(owner.Event1833OwnerDenied):
            owner.original_readiness(None, {}, {}, None)
        with self.assertRaises(owner.Event1833OwnerDenied):
            owner.original_backup(None, {}, {}, None)
        with self.assertRaises(commit.Event1833CommitDenied):
            commit.original_source_commit(None, {}, {}, None)
        with self.assertRaises(post.Event1833PostcommitDenied):
            post.original_postcommit(None, {}, {}, None)
        with self.assertRaises(cold.Event1832ColdDenied):
            cold.stage_complete_cold_bundle(
                None, target="b"*40, run_id=43799999999,
                disabled_owner_witness=lambda: True,
                release_witness=lambda: True)

    def test_no_implicit_owner_scheduling_or_science(self):
        for module in (owner, commit, post, cold, successor):
            source=inspect.getsource(module)
            self.assertNotIn("Register-ScheduledTask",source)
            self.assertNotIn("Start-ScheduledTask",source)
            self.assertNotIn("workflow_dispatch",source)
            self.assertNotIn("OPENAI_API_KEY = ",source)
        self.assertIn("SingleOwner(",inspect.getsource(commit))
        self.assertIn("Database.open_readonly",inspect.getsource(post))
        self.assertIn("independent_detached_restore_verified",
                      inspect.getsource(cold))
        self.assertIn("original_owner_mutations",inspect.getsource(commit))
        self.assertNotIn("scientific_first_use\": True",
                         inspect.getsource(successor))

    def test_four_native_owner_stages_reuse_existing_workflow(self):
        root=Path(__file__).resolve().parents[1]
        workflow=(root/".github/workflows/f139-v39-original-source-successor.yml").read_text("utf-8")
        self.assertIn("group: forge-f139-v39-original-source-v2",workflow)
        self.assertIn("cancel-in-progress: false",workflow)
        self.assertNotIn("workflow_dispatch:",workflow)
        self.assertNotIn("schedule:",workflow)
        self.assertNotIn("Register-ScheduledTask",workflow)
        self.assertEqual(workflow.count(
            "  hybrid-v40-original-event1832-readiness:"),1)
        self.assertEqual(workflow.count(
            "  hybrid-v40-original-event1832-backup:"),1)
        self.assertEqual(workflow.count(
            "  hybrid-v40-original-event1833-source-commit:"),1)
        self.assertEqual(workflow.count(
            "  hybrid-v40-original-event1833-postcommit:"),1)
        for entry in (
            "nci04_v41_hybrid_event1833_owner",
            "nci04_v41_hybrid_event1833_commit",
            "nci04_v41_hybrid_event1833_postcommit",
            "F139-HYBRID-V40-READINESS ",
            "F139-HYBRID-V40-BACKUP ",
            "F139-HYBRID-V40-COMMIT ",
            "F139-HYBRID-V40-POSTCOMMIT ",
        ):
            self.assertIn(entry,workflow)

    def test_original_activation_cannot_resume_without_native_event(self):
        root=Path(__file__).resolve().parents[1]
        script=(root/"f139/v41_hybrid_original_activate.ps1").read_text("utf-8")
        self.assertIn("nci04_v41_hybrid_event1833_postcommit",script)
        self.assertIn("activate-native --approval",script)
        self.assertIn("verify_native_activation(db)",script)
        self.assertIn("F139_HYBRID_V40_ORIGINAL_NATIVE_ACTIVATION=PASS",script)
        self.assertLess(script.index("upgrade-hybrid-lane"),
                        script.index("activate-native --approval"))
        self.assertLess(script.index("activate-native --approval"),
                        script.index("gh api --method PATCH"))
        self.assertLess(script.index("gh api --method PATCH"),
                        script.index("Start-ScheduledTask -TaskName"))
        self.assertEqual(script.count("Start-ScheduledTask -TaskName"),1)
        self.assertEqual(script.count("Set-ScheduledTask -TaskName"),1)
        self.assertNotIn("Register-ScheduledTask",script)


if __name__ == "__main__":
    unittest.main()

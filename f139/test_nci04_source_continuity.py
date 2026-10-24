"""F139 bounded source continuity: prohibit all authority/runtime drift.

Only a provable descendant of the currently installed source whose ENTIRE
file diff consists of isolated research-preview additions/modifications may
avoid needless owner migration. This test uses a fake read-only GitHub source;
it does not activate or dispatch the original task.
"""
from __future__ import annotations

import copy
import unittest

from f139.nci04_source_continuity import (
    SourceContinuityDenied, prove_protected_research_only_advance,
)

REPO = "spoonman136668-ai/FORGE"
DEPLOYED = "2" * 40
LATEST = "3" * 40


def file(path, *, status="added", changes=100, patch="@@ -0,0 +1 @@\n+x"):
    return {
        "filename": path, "status": status, "changes": changes,
        "sha": "a" * 40, "patch": patch,
    }


class ProtectedResearchSource:
    def __init__(self):
        self.counter = 0
        self.branch = {"protected": True, "commit": {"sha": LATEST}}
        commits = [{"sha": f"{i:040x}"} for i in range(1, 4)]
        commits.append({"sha": LATEST})
        self.compare = {
            "status": "ahead", "ahead_by": 4, "behind_by": 0,
            "total_commits": 4,
            "merge_base_commit": {"sha": DEPLOYED},
            "commits": commits,
            "files": [
                file("docs/RSH-03-VERIFIED-REMOTE-FSA-READONLY.md", changes=27),
                file("researchfeed/fsa_remote.go", changes=93),
                file("fsaservice/rsh03_readonly_bridge_test.go", changes=141),
            ],
        }

    def get(self, path):
        self.counter += 1
        if path == f"repos/{REPO}/branches/main":
            return copy.deepcopy(self.branch)
        if path == f"repos/{REPO}/compare/{DEPLOYED}...{LATEST}":
            return copy.deepcopy(self.compare)
        raise AssertionError("unauthorized GitHub route: " + path)


class SourceContinuityTests(unittest.TestCase):
    def prove(self, source):
        return prove_protected_research_only_advance(
            source.get, deployed_source=DEPLOYED, protected_source=LATEST)

    def deny(self, change, reason=None):
        source = ProtectedResearchSource()
        change(source)
        with self.assertRaises(SourceContinuityDenied) as cm:
            self.prove(source)
        if reason:
            self.assertIn(reason, str(cm.exception))

    def test_isolated_three_file_rsh03_is_allowed_without_new_authority(self):
        src = ProtectedResearchSource()
        proof = self.prove(src)
        self.assertEqual(src.counter, 3)
        self.assertEqual(proof["file_count"], 3)
        self.assertEqual(proof["forward_commits"], 4)
        self.assertEqual(proof["changed_lines"], 261)
        self.assertEqual(proof["deployed_source"], DEPLOYED)
        self.assertEqual(proof["protected_source"], LATEST)
        self.assertTrue(proof["runtime_source_unchanged"])
        self.assertFalse(proof["scientific_first_use"])
        self.assertFalse(proof["source_transition_granted"])
        self.assertFalse(proof["new_controller"])

    def test_earlier_rsh01_rsh02_added_research_is_qualified_too(self):
        src = ProtectedResearchSource()
        src.compare["files"] = [
            file("docs/RSH-01-SIX-LANE-RESEARCH-EVIDENCE-PREVIEW.md"),
            file("docs/RSH-02-FSA-READONLY-SIX-LANE-PREFLIGHT.md"),
            file("researchfeed/preview.go"),
            file("researchfeed/fsa_observe.go"),
        ]
        self.assertEqual(self.prove(src)["file_count"], 4)

    def test_append_only_rsh04_original_receipt_is_data_only(self):
        src = ProtectedResearchSource()
        src.compare["files"] = [
            file("docs/RSH-04-ORIGINAL-BYTES-INTEGRITY.md", changes=33),
            file("researchfeed/original_integrity.go", changes=144),
            file("researchfeed/original_integrity_test.go", changes=192),
            file("reference/research-originals/20261024-rsh04-raw-integrity-receipt.json",
                 changes=57),
        ]
        proof = self.prove(src)
        self.assertEqual(proof["file_count"], 4)
        self.assertFalse(proof["scientific_first_use"])
        self.assertFalse(proof["source_transition_granted"])

    def test_original_evidence_cannot_be_rewritten(self):
        self.deny(lambda s: s.compare["files"].append(
            file("reference/research-originals/20261024-rsh04-raw-integrity-receipt.json",
                 status="modified")), "ORIGINAL_EVIDENCE_REWRITTEN")
        self.deny(lambda s: s.compare["files"].append(
            file("reference/research-originals/20261024-rsh04-raw-integrity-receipt.json",
                 status="removed")), "RUNTIME_OR_UNTRUSTED_FILE_CHANGED")

    def test_receipt_pattern_does_not_admit_arbitrary_data(self):
        for path in (
            "reference/research-originals/private-key.json",
            "reference/research-originals/20261024-rsh04-credentials.json",
            "reference/research-originals/20261024-rsh04-raw-integrity-receipt.py",
            "reference/research-originals/20261024-rsh04-raw-integrity-receipt.json/evil",
            "reference/research-originals/../f139/local_controller.py",
            "reference/research-originals/20261024-RSH04-raw-integrity-receipt.json",
        ):
            with self.subTest(path=path):
                self.deny(lambda s, p=path: s.compare["files"].append(file(p)),
                          "RUNTIME_OR_UNTRUSTED_FILE_CHANGED")

    def test_all_operational_paths_fail_closed(self):
        disallowed = (
            "f139/local_controller.py",
            "f139/nci04_owner_ledger.py",
            "f139/nci04_candidate_publisher.py",
            "scripts/Run-FORGE-F139.ps1",
            ".github/workflows/forge-f139-development-worker.yml",
            "docs/rebuild/RB1_SINGLE_TRACK_CONTRACT.md",
            "go.mod", "go.sum", "AGENTS.md",
            "fsaservice/rsh03_readonly_bridge.go",
            "fsaservice/tls.go",
            ".github/CODEOWNERS",
            "f139/../researchfeed/preview.go",
            "researchfeed/../../f139/owner.go",
        )
        for path in disallowed:
            with self.subTest(path=path):
                self.deny(lambda s, p=path: s.compare["files"].append(
                    file(p)), "RUNTIME_OR_UNTRUSTED_FILE_CHANGED")

    def test_unknown_or_deleted_source_and_renames_denied(self):
        for status in ("removed", "renamed", "copied", "changed"):
            with self.subTest(status=status):
                self.deny(lambda s, v=status: s.compare["files"][0].update(
                    status=v), "RUNTIME_OR_UNTRUSTED_FILE_CHANGED")

    def test_transient_protected_head_change_denied(self):
        src = ProtectedResearchSource()
        fn = src.get
        calls = [0]
        def moving(route):
            value = fn(route)
            if route == f"repos/{REPO}/branches/main":
                calls[0] += 1
                if calls[0] > 1:
                    value["commit"]["sha"] = "f" * 40
            return value
        with self.assertRaisesRegex(SourceContinuityDenied,
                                    "PROTECTED_HEAD_MOVED"):
            prove_protected_research_only_advance(
                moving, deployed_source=DEPLOYED, protected_source=LATEST)

    def test_wrong_source_pin_is_denied(self):
        self.deny(lambda s: s.compare["merge_base_commit"].update(
            sha="4" * 40), "NOT_BOUNDED_FORWARD_ANCESTRY")
        self.deny(lambda s: s.compare.update(
            behind_by=1), "NOT_BOUNDED_FORWARD_ANCESTRY")
        self.deny(lambda s: s.compare.update(
            status="diverged"), "NOT_BOUNDED_FORWARD_ANCESTRY")
        self.deny(lambda s: s.branch.update(
            protected=False), "PROTECTED_MAIN_MOVED_OR_UNPROTECTED")
        self.deny(lambda s: s.branch["commit"].update(
            sha="f" * 40), "PROTECTED_MAIN_MOVED_OR_UNPROTECTED")

    def test_fake_or_incomplete_commit_history_denied(self):
        self.deny(lambda s: s.compare.update(
            commits=s.compare["commits"][:-1]),
            "COMMIT_HISTORY_TRUNCATED_OR_MOVED")
        self.deny(lambda s: s.compare.update(
            ahead_by=81, total_commits=81),
            "NOT_BOUNDED_FORWARD_ANCESTRY")
        self.deny(lambda s: s.compare["commits"].append(
            s.compare["commits"][-1]),
            "COMMIT_HISTORY_TRUNCATED_OR_MOVED")

    def test_missing_diff_or_patch_denied(self):
        self.deny(lambda s: s.compare.update(
            files=[]), "DIFF_TRUNCATED_OR_EMPTY")
        self.deny(lambda s: s.compare["files"][0].pop("patch"),
                  "RUNTIME_OR_UNTRUSTED_FILE_CHANGED")
        self.deny(lambda s: s.compare["files"].append(
            copy.deepcopy(s.compare["files"][0])),
            "DUPLICATE_CHANGED_FILE")
        self.deny(lambda s: s.compare["files"][0].update(
            changes=2001), "RUNTIME_OR_UNTRUSTED_FILE_CHANGED")

    def test_no_implicit_authority_for_unqualified_inputs(self):
        for old,new in (("invalid", LATEST), (DEPLOYED, "invalid"),
                        (DEPLOYED, DEPLOYED)):
            with self.subTest(old=old,new=new):
                with self.assertRaisesRegex(SourceContinuityDenied,
                                            "SOURCE_SHA_INVALID"):
                    prove_protected_research_only_advance(
                        ProtectedResearchSource().get,
                        deployed_source=old, protected_source=new)


if __name__ == "__main__":
    unittest.main()

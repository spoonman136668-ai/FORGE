"""Negative and positive V41 unadmitted-proposal source-custody controls.

All tests use disposable SQLite and synthetic authenticated GET-only API
snapshots; never touch the original Windows owner or issue #1715 itself.
"""
from contextlib import closing
import base64
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from f139.local_controller import Database, GitHub, F139Error, SingleOwner
from f139.nci04_native_contract import canonical
from f139.nci04_owner_issue import inspect_owner_issue
from f139 import nci04_v41_pending_custody as v41
from f139.test_nci04_native_successor_catalog import source_issue, TARGET, TREE

NEXT = "9" * 40
OLD_ID = 6333201763


def original(number=1715, source=v41.FROM_V40, issue_id=OLD_ID):
    return source_issue(source, number, issue_id, lane="Yggdrasil")


def authenticate(raw, source):
    return inspect_owner_issue(raw, protected_main=source,
        authenticated_target_commit=TARGET,
        authenticated_target_tree=TREE)


class PendingCustodyTests(unittest.TestCase):
    def setUp(self):
        self.docs = [original()]
        self.calls = []
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.path = Path(self.folder.name) / "state.sqlite"
        with closing(Database.initialize(self.path, v41.FROM_V40)) as db:
            db.conn.execute("UPDATE meta SET enabled=1,legacy_suspended=1 WHERE id=1")

    def api(self):
        def runner(args):
            self.calls.append(tuple(args))
            self.assertEqual(len(args), 1)
            route = args[0]
            prefix = ("repos/spoonman136668-ai/FORGE/issues?state=open&labels="
                      "f139-native-development-eligible&per_page=100&page=")
            if route.startswith(prefix) and route[len(prefix):].isdigit():
                n = int(route[len(prefix):])
                self.assertGreater(n, 0)
                return canonical(self.docs[(n-1)*100:n*100])
            if route == "repos/spoonman136668-ai/Yggdrasil/git/commits/" + TARGET:
                return canonical({"sha": TARGET, "tree": {"sha": TREE}})
            raise AssertionError("UNEXPECTED_NON_GET_ROUTE " + route)
        return GitHub(runner=runner)

    def frozen(self, *, patch_history=None):
        with SingleOwner(self.path.with_suffix(".lock")):
            with closing(Database.open_readonly(self.path)) as db:
                previous = db.meta().copy()
                changes = db.conn.total_changes
                # Disposable fixture has no spent original history. The live
                # source path uses the UNMOCKED event and task floors.
                with patch.multiple(v41, MIN_ORIGINAL_HEAD=0,
                                    MIN_VERIFIED=0, MIN_QUARANTINED=0):
                    if patch_history is None:
                        result = v41.inspect_never_admitted(db, self.api())
                    else:
                        with patch.object(v41, "native_events", return_value=patch_history):
                            result = v41.inspect_never_admitted(db, self.api())
                self.assertEqual(db.meta(), previous)
                self.assertEqual(db.conn.total_changes, changes)
                self.assertEqual(db.conn.execute("PRAGMA query_only").fetchone()[0], 1)
        return result

    def test_newly_initialized_source_spoof_is_not_genuine_original(self):
        # Even a matching source string and SQLite quick_check are insufficient
        # without the independently observed original history high-water.
        with SingleOwner(self.path.with_suffix(".lock")):
            with closing(Database.open_readonly(self.path)) as db:
                with self.assertRaisesRegex(v41.V41PendingDenied,
                                            "ORIGINAL_SOURCE_OR_IDLE_DRIFT"):
                    v41.inspect_never_admitted(db, self.api())

    def test_original_pending_identity_freezes_without_dispatch_or_mutation(self):
        receipt = self.frozen()
        self.assertEqual(receipt["issue_number"], 1715)
        self.assertEqual(receipt["issue_id"], OLD_ID)
        self.assertEqual(receipt["source_sha"], v41.FROM_V40)
        self.assertEqual(receipt["disposition"], "UNADMITTED_RETAINED_NO_DISPATCH")
        self.assertFalse(receipt["reissue_authorized"])
        self.assertFalse(receipt["source_transition_authorized"])
        self.assertFalse(receipt["scientific_first_use"])
        self.assertEqual(receipt["owner_mutations"], 0)
        self.assertEqual(receipt["new_dispatches"], 0)
        self.assertEqual(len([x for x in self.calls if "/git/commits/" in x[0]]), 1)
        self.assertTrue(all(len(c) == 1 and "POST" not in c[0] for c in self.calls))

    def test_current_source_proposal_cannot_be_silently_changed_or_dropped(self):
        self.docs = []
        with self.assertRaisesRegex(v41.V41PendingDenied,
                                    "PENDING_NOT_EXACTLY_ONE_UNADMITTED_YGGDRASIL"):
            self.frozen()
        self.docs = [original(), original(1716, issue_id=OLD_ID+1)]
        with self.assertRaisesRegex(v41.V41PendingDenied,
                                    "PENDING_NOT_EXACTLY_ONE_UNADMITTED_YGGDRASIL"):
            self.frozen()
        self.docs = [original(source="8"*40)]
        with self.assertRaisesRegex(F139Error, "NATIVE_ISSUE_OR_SOURCE_REJECTED"):
            self.frozen()

    def test_original_mutex_readonly_and_identity_are_mandatory(self):
        with closing(Database.open_readonly(self.path)) as db:
            with self.assertRaisesRegex(v41.V41PendingDenied,
                                        "QUERY_ONLY_ORIGINAL_MUTEX_REQUIRED"):
                v41.inspect_never_admitted(db, self.api())
        with SingleOwner(self.path.with_suffix(".lock")):
            with closing(Database(self.path)) as db:
                with self.assertRaisesRegex(v41.V41PendingDenied,
                                            "QUERY_ONLY_ORIGINAL_MUTEX_REQUIRED"):
                    v41.inspect_never_admitted(db, self.api())
        with SingleOwner(self.path.with_suffix(".lock")):
            with closing(Database.open_readonly(self.path)) as db:
                with self.assertRaisesRegex(v41.V41PendingDenied,
                                            "UNEXPECTED_PENDING_NUMBER"):
                    v41.inspect_never_admitted(db, self.api(), expected_number=1716)

    def test_already_admitted_candidate_must_not_be_reissued(self):
        old = authenticate(self.docs[0], v41.FROM_V40)
        history = [{"issue_number": old.number, "issue_id": old.issue_id,
                    "source_sha": old.source_sha,
                    "issue_body_sha256": old.issue_body_sha256,
                    "ticket": old.ticket}]
        with self.assertRaisesRegex(v41.V41PendingDenied,
                                    "ALREADY_ADMITTED_NO_REISSUE"):
            self.frozen(patch_history=history)

    def test_tampered_original_identity_or_missing_provider_cannot_freeze(self):
        self.docs[0]["id"] = OLD_ID + 1
        # A *valid* provider issue with a different identity is not our frozen
        # proposal; the cold freeze must fail if a different number appears.
        self.docs[0]["number"] = 1720
        with self.assertRaisesRegex(v41.V41PendingDenied,
                                    "PENDING_NOT_EXACTLY_ONE_UNADMITTED_YGGDRASIL"):
            self.frozen()
        self.docs = [original()]
        self.docs[0]["user"]["login"] = "attacker"
        with self.assertRaisesRegex(F139Error, "NATIVE_ISSUE_OR_SOURCE_REJECTED"):
            self.frozen()
        self.docs = [original()]
        with patch.object(GitHub, "native_eligible_issues",
                          side_effect=F139Error("F139_GITHUB_API_FAILED")):
            with self.assertRaisesRegex(F139Error,"GITHUB_API_FAILED"):
                self.frozen()

    def test_exact_200_catalog_with_199_admitted_old_issues_one_pending(self):
        docs = [original(1000+i, issue_id=6550000000+i) for i in range(199)]
        admission = []
        for raw in docs:
            a = authenticate(raw, v41.FROM_V40)
            admission.append({"issue_number": a.number, "issue_id": a.issue_id,
                              "source_sha": a.source_sha,
                              "issue_body_sha256": a.issue_body_sha256,
                              "ticket": a.ticket})
        self.docs = docs + [original()]
        frozen = self.frozen(patch_history=admission)
        self.assertEqual(frozen["issue_number"], 1715)
        pages = [c[0] for c in self.calls if "/issues?" in c[0]]
        self.assertEqual(len(pages), 3)
        self.assertTrue(pages[-1].endswith("page=3"))
        self.assertEqual(sum("/git/commits/" in c[0] for c in self.calls), 1)
        self.docs[100]["id"] = self.docs[0]["id"]
        with self.assertRaisesRegex(F139Error, "NATIVE_DUPLICATE_OR_INVALID_ISSUE_IDENTITY"):
            self.frozen(patch_history=admission)

    def test_201st_issue_safely_blocks_freeze_instead_of_being_ignored(self):
        self.docs = [original(1000+i, issue_id=6551000000+i) for i in range(200)]
        self.docs.append(original())
        with self.assertRaisesRegex(v41.V41PendingDenied,
                                    "PENDING_NOT_EXACTLY_ONE_UNADMITTED_YGGDRASIL"):
            self.frozen()

    def test_source_bound_reissue_preserves_all_non_source_intent_fields(self):
        frozen = self.frozen()
        old = authenticate(original(), v41.FROM_V40)
        new = authenticate(original(1720, NEXT, OLD_ID+1), NEXT)
        proof = v41.compare_source_bound_reissue(frozen, old, new,
                                                 target_source=NEXT)
        self.assertEqual(proof["old_issue_number"], 1715)
        self.assertEqual(proof["new_issue_number"], 1720)
        self.assertEqual(proof["semantic_identity_sha256"],
                         frozen["semantic_identity_sha256"])
        self.assertNotEqual(proof["old_ticket"], proof["new_ticket"])
        self.assertFalse(proof["source_transition_authorized"])
        self.assertFalse(proof["reissue_authorized"])
        self.assertEqual(proof["new_dispatches"], 0)
        self.assertEqual(proof["owner_mutations"], 0)

    def test_reissue_rejects_semantic_changes_duplicate_id_and_source(self):
        frozen = self.frozen()
        old = authenticate(original(), v41.FROM_V40)
        unchanged = authenticate(original(1720, NEXT, OLD_ID+1), NEXT)
        for proposed, src in (
            (unchanged, "8"*40),
            (authenticate(original(1720, NEXT, OLD_ID), NEXT), NEXT),
            (authenticate(original(1715, NEXT, OLD_ID+1), NEXT), NEXT),
            (authenticate(original(1720, v41.FROM_V40, OLD_ID+1),
                          v41.FROM_V40), NEXT),
        ):
            with self.subTest(issue=proposed.number, source=src):
                with self.assertRaisesRegex(v41.V41PendingDenied,
                                            "REISSUE_IDENTITY_OR_CANDIDATE_DRIFT"):
                    v41.compare_source_bound_reissue(frozen, old, proposed,
                                                     target_source=src)
        altered = original(1720, NEXT, OLD_ID+1)
        body = json.loads(altered["body"])
        intent = json.loads(base64.b64decode(body["intent_base64"], validate=True))
        intent["training_config_sha256"] = "a"*64
        body["intent_base64"] = base64.b64encode(canonical(intent)).decode("ascii")
        altered["body"] = json.dumps(body, sort_keys=True)
        changed = authenticate(altered, NEXT)
        with self.assertRaisesRegex(v41.V41PendingDenied,
                                    "REISSUE_IDENTITY_OR_CANDIDATE_DRIFT"):
            v41.compare_source_bound_reissue(frozen, old, changed,
                                             target_source=NEXT)

    def test_frozen_receipt_cannot_grant_authority_or_relabel_issue(self):
        frozen = self.frozen()
        old = authenticate(original(), v41.FROM_V40)
        proposed = authenticate(original(1720, NEXT, OLD_ID+1), NEXT)
        for key, val in (
            ("source_transition_authorized", True),
            ("reissue_authorized", True),
            ("new_dispatches", 1),
            ("owner_mutations", 1),
            ("scientific_first_use", True),
            ("issue_body_sha256", "0"*64),
            ("semantic_identity_sha256", "0"*64),
            ("original_head_seq", "0"),
            ("original_head_sha256", "x"*64),
            ("extra_key", True),
        ):
            modified = {**frozen, key:val}
            with self.subTest(key=key):
                with self.assertRaises(v41.V41PendingDenied):
                    v41.compare_source_bound_reissue(modified, old, proposed,
                                                     target_source=NEXT)


if __name__ == "__main__":
    unittest.main()

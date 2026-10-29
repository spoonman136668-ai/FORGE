"""Offline boundary tests for opt-in MP-AI05 operational query entrypoint."""
import json
import hashlib
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "tools"))
from mpai05_recall_cli import retrieve, _write_private

SHA = "a" * 40
TEMPLATE = ("Can you find the saved memory related to "
            "causal memory evidence and explain the original evidence?")


class FakeSnapshot:
    def __init__(self, empty_clean=False):
        self.calls = []
        self.empty_clean = empty_clean

    def recall(self, sha, query, projects, profile):
        self.calls.append((sha, query, projects[:], profile))
        records = [] if self.empty_clean and query == "causal memory evidence" else [
            {"id": "pinned/id", "source_refs": [{"type": "source", "ref": "reviewed"}]}]
        return {"source_sha": sha, "matches": records,
                "scope": projects, "query_used": query}


class OperationalConsumerTests(unittest.TestCase):
    def test_default_off_preserves_query(self):
        s = FakeSnapshot()
        data, receipt = retrieve(s, SHA, TEMPLATE, projects=["Mind-Palace"])
        self.assertEqual(receipt["mode"], "off")
        self.assertEqual(receipt["routing"], "disabled")
        self.assertEqual(data["query_used"], TEMPLATE)
        self.assertEqual(len(s.calls), 1)

    def test_eligible_normalizes_recognized_only(self):
        s = FakeSnapshot()
        data, receipt = retrieve(s, SHA, TEMPLATE, projects=["Mind-Palace"],
                                 mode="eligible")
        self.assertEqual(receipt["routing"], "normalized")
        self.assertEqual(data["query_used"], "causal memory evidence")
        self.assertNotIn(TEMPLATE, repr(receipt))

    def test_eligible_unknown_passes_through(self):
        s = FakeSnapshot()
        query = "How was memory evidence validated?"
        data, receipt = retrieve(s, SHA, query, projects=["Mind-Palace"],
                                 mode="eligible")
        self.assertEqual(receipt["routing"], "unmodified")
        self.assertEqual(data["query_used"], query)

    def test_zero_hit_falls_back(self):
        s = FakeSnapshot(empty_clean=True)
        data, receipt = retrieve(s, SHA, TEMPLATE, projects=["Mind-Palace"],
                                 mode="eligible")
        self.assertEqual(receipt["routing"], "original_fallback")
        self.assertEqual(data["query_used"], TEMPLATE)
        self.assertEqual(len(s.calls), 2)

    def test_shadow_serves_original_and_records_comparison(self):
        s = FakeSnapshot(empty_clean=True)
        data, receipt = retrieve(s, SHA, TEMPLATE, projects=["Mind-Palace"],
                                 mode="shadow")
        self.assertEqual(data["query_used"], TEMPLATE)
        self.assertEqual(receipt["routing"], "disabled")
        self.assertEqual(receipt["shadow_record_count"], 1)
        self.assertFalse(receipt["shadow_changed_top4"])
        self.assertEqual(len(s.calls), 3)  # original + cleaned + fallback original

    def test_source_and_scope_and_profile_enforced(self):
        s = FakeSnapshot()
        for source, scope, profile in [
            ("x", ["Mind-Palace"], "continuation"),
            (SHA, ["Wingless"], "continuation"),
            (SHA, ["Mind-Palace", "Wingless"], "continuation"),
            (SHA, ["Mind-Palace"], "bad"),
        ]:
            with self.subTest(source=source, scope=scope, profile=profile):
                with self.assertRaises(ValueError):
                    retrieve(s, source, TEMPLATE, projects=scope, profile=profile)
        self.assertFalse(s.calls)

    def test_input_limits(self):
        s = FakeSnapshot()
        for q in (" ", "x" * 4097):
            with self.assertRaises(ValueError):
                retrieve(s, SHA, q, projects=["Mind-Palace"])
        self.assertFalse(s.calls)

    def test_malformed_provenance_denied(self):
        class Invalid(FakeSnapshot):
            def recall(self, sha, query, projects, profile):
                return {"source_sha": sha, "matches": [{"id": "bad"}]}
        with self.assertRaises(RuntimeError):
            retrieve(Invalid(), SHA, TEMPLATE, projects=["Mind-Palace"])

    def test_private_result_exclusive_write_and_no_workspace(self):
        with tempfile.TemporaryDirectory() as source, tempfile.TemporaryDirectory() as output:
            root = pathlib.Path(source)
            target = pathlib.Path(output) / "receipt.json"
            s = FakeSnapshot()
            result, receipt = retrieve(s, SHA, TEMPLATE, projects=["Mind-Palace"])
            _write_private(str(target), root, result, receipt)
            saved = json.loads(target.read_text(encoding="utf-8"))
            self.assertEqual(saved["result"], result)
            with self.assertRaises(FileExistsError):
                _write_private(str(target), root, result, receipt)
            with self.assertRaises(ValueError):
                _write_private(str(root / "private.json"), root, result, receipt)
            with self.assertRaises(ValueError):
                _write_private("receipt.json", root, result, receipt)



class ReferenceResolutionTests(unittest.TestCase):
    """Source-only contract: never accept a stub as factual evidence."""

    class RefSnapshot:
        def __init__(self, defect=None, copies=1):
            self.defect = defect
            self.copies = copies
            self.get_calls = []
            self.statement = ("The original experiment was development only; "
                              "accuracy is unproven. Do not promote as a win.")
            self.refs = [{"type": "acceptance",
                          "ref": "https://github.com/example/verified-source"}]

        def recall(self, sha, query, projects, profile):
            pointers = []
            for i in range(self.copies):
                pointer = {
                    "id": "lesson/record-" + str(i),
                    "project": "Mind-Palace",
                    "kind": "lesson",
                    "status": "observed",
                    "source_refs": self.refs,
                    "statement": "Reference only. Fetch full record.",
                    "retrieval_preview_kind": "reference_only",
                    "full_record_required": True,
                    "source_statement_sha256":
                        hashlib.sha256(self.statement.encode("utf-8")).hexdigest(),
                }
                if self.defect == "missing_flag":
                    pointer["full_record_required"] = False
                if self.defect == "wrong_hash":
                    pointer["source_statement_sha256"] = "0" * 64
                if self.defect == "scope":
                    pointer["project"] = "Wingless"
                pointers.append(pointer)
            return {"source_sha": sha, "scope": projects,
                    "records_sha256": "f" * 64, "matches": pointers}

        def get_record(self, sha, record_id, projects):
            self.get_calls.append((sha, record_id, projects[:]))
            full = {"id": record_id, "project": "Mind-Palace",
                    "kind": "lesson", "status": "observed",
                    "source_refs": self.refs,
                    "statement": self.statement}
            source = sha
            digest = "f" * 64
            if self.defect == "missing_record":
                return {"source_sha": source, "found": False}
            if self.defect == "wrong_source":
                source = "b" * 40
            if self.defect == "wrong_snapshot":
                digest = "0" * 64
            if self.defect == "wrong_provenance":
                full["source_refs"] = [{"type": "source", "ref": "untrusted"}]
            if self.defect == "wrong_record_project":
                full["project"] = "Wingless"
            return {"source_sha": source, "records_sha256": digest,
                    "found": True, "record": full}

    def test_opt_in_follows_exact_pointer_to_full_record(self):
        snapshot = self.RefSnapshot()
        out, receipt = retrieve(snapshot, SHA, TEMPLATE, projects=["Mind-Palace"],
                                resolve_reference_only=True)
        self.assertEqual(receipt["resolved_reference_count"], 1)
        self.assertEqual(receipt["reference_followup"], "enabled")
        self.assertEqual(snapshot.get_calls,
                         [(SHA, "lesson/record-0", ["Mind-Palace"])])
        self.assertEqual(out["reference_resolution"], "verified_full_records")
        self.assertEqual(out["resolved_reference_records"][0]["statement"],
                         snapshot.statement)
        self.assertTrue(out["matches"][0]["full_record_required"])
        self.assertEqual(out["matches"][0]["retrieval_preview_kind"], "reference_only")

    def test_default_behavior_is_unchanged_and_no_full_fetch(self):
        snapshot = self.RefSnapshot()
        out, receipt = retrieve(snapshot, SHA, TEMPLATE, projects=["Mind-Palace"])
        self.assertEqual(receipt["reference_followup"], "disabled")
        self.assertEqual(receipt["resolved_reference_count"], 0)
        self.assertNotIn("resolved_reference_records", out)
        self.assertFalse(snapshot.get_calls)

    def test_reference_drift_and_missing_evidence_fail_closed(self):
        for defect in ("missing_flag", "wrong_hash", "missing_record",
                       "wrong_source", "wrong_snapshot", "wrong_provenance",
                       "wrong_record_project"):
            with self.subTest(defect=defect):
                snapshot = self.RefSnapshot(defect=defect)
                with self.assertRaises(RuntimeError):
                    retrieve(snapshot, SHA, TEMPLATE, projects=["Mind-Palace"],
                             resolve_reference_only=True)

    def test_more_than_five_reference_followups_rejected(self):
        snapshot = self.RefSnapshot(copies=6)
        with self.assertRaises(RuntimeError):
            retrieve(snapshot, SHA, TEMPLATE, projects=["Mind-Palace"],
                     resolve_reference_only=True)
        self.assertEqual(len(snapshot.get_calls), 5)


if __name__ == "__main__":
    unittest.main()

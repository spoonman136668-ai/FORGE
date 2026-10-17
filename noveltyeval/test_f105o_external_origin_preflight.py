"""Synthetic F105-O invariants: no unsealing, no compatible-score fabrication."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import f105o_external_origin_preflight as f


def valid_objects():
    return {k: {"original_git_blob": b, "original_blob_size": n}
            for k, (b, n) in f.FILES.items()}


class SourceCandidateGate(unittest.TestCase):
    def test_original_external_candidate_exact_identity(self):
        out = f.make_report(valid_objects())
        self.assertEqual(out["status"], f.VERDICT)
        self.assertEqual(out["candidate_repo"], "kelvin-jiang/FreebaseQA")
        self.assertEqual(out["author_declared_population"]["eval"], 3996)
        self.assertFalse(out["new_scientific_firstuse"])
        self.assertFalse(out["generalization_qualified"])
        self.assertFalse(out["qa_file_contents_read_by_application"])
        self.assertIsNone(out["reported_accuracy"])
        self.assertEqual(out["candidate_questions_scored"], 0)

    def test_one_changed_external_source_blob_or_byte_size_is_denied(self):
        for path in f.FILES:
            v = valid_objects()
            v[path]["original_git_blob"] = "0" * 40
            with self.assertRaises(f.Denied):
                f.make_report(v)
            v = valid_objects()
            v[path]["original_blob_size"] += 1
            with self.assertRaises(f.Denied):
                f.make_report(v)
        for path in f.FILES:
            v = valid_objects()
            del v[path]
            with self.assertRaises(f.Denied):
                f.make_report(v)

    def test_metadata_only_git_commands_and_prevent_content_read(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with mock.patch.object(f.subprocess, "run") as run:
                run.return_value.returncode = 0
                run.return_value.stdout = b"dummy\n"
                run.return_value.stderr = b""
                for operation in (
                    ["show", "HEAD:FreebaseQA-eval.json"],
                    ["cat-file", "-p", "HEAD:FreebaseQA-eval.json"],
                    ["cat-file", "--batch", "HEAD:FreebaseQA-eval.json"],
                    ["checkout", "FreebaseQA-eval.json"],
                    ["log", "-p", "HEAD"],
                    ["rev-parse", "HEAD:unapproved.json"],
                ):
                    with self.assertRaises(f.Denied):
                        f.git_output(root, ["git", "-C", str(root), *operation])
                self.assertEqual(run.call_count, 0)
                for operation in (
                    ["rev-parse", "HEAD"],
                    ["rev-parse", "HEAD:FreebaseQA-eval.json"],
                    ["cat-file", "-s", "HEAD:FreebaseQA-eval.json"],
                ):
                    self.assertEqual(f.git_output(root, ["git", "-C", str(root), *operation]), "dummy")
                self.assertEqual(run.call_count, 3)

    def test_sparse_tree_requires_unopened_candidate_question_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "README.md").write_text(
                "FreebaseQA CC-BY-4.0 3,996 20,358 3,994 "
                "RawQuestion ProcessedQuestion Parses TopicEntityMid "
                "InferentialChain AnswersMid",
                encoding="utf-8")
            (root / "LICENSE").write_text("Creative Commons Attribution", encoding="utf-8")
            expected = iter([
                f.HEAD,
                *[value for k in f.FILES for value in (f.FILES[k][0], str(f.FILES[k][1]))],
            ])
            with mock.patch.object(f, "git_output", side_effect=lambda *_: next(expected)):
                a = f.identify(root)
            self.assertEqual(a, valid_objects())
            (root / "FreebaseQA-eval.json").write_text("DO NOT OPEN", encoding="utf-8")
            expected = iter([
                f.HEAD,
                *[value for k in f.FILES for value in (f.FILES[k][0], str(f.FILES[k][1]))],
            ])
            with mock.patch.object(f, "git_output", side_effect=lambda *_: next(expected)):
                with self.assertRaises(f.Denied):
                    f.identify(root)

    def test_no_user_visible_per_question_or_scientific_authority(self):
        txt = json.dumps(f.make_report(valid_objects()), sort_keys=True)
        for key in (
            "independently_sealed_content_proven",
            "new_scientific_firstuse", "accepted_science",
            "accepted_ref_mutation", "dream_pareto_promotion",
            "thetaevolve_accepted_training", "science_dispatch",
            "per_question_data_published",
        ):
            if key == "per_question_data_published":
                self.assertNotIn('"' + key + '"', txt)
            else:
                self.assertIn('"' + key + '": false', txt)
        self.assertIn('"requires_separate_freebase_graph_admission": true', txt)
        self.assertIn('"evaluation_answers_seen": 0', txt)


if __name__ == "__main__":
    unittest.main()

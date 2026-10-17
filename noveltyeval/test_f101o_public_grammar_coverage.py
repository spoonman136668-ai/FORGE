"""Synthetic adverse source-interface tests for frozen F101-O public-only audit."""
import hashlib
import unittest

import f101o_public_grammar_coverage as a

Q1 = b"which person directed the movies starred by [Actor Name]?"
Q2 = b"who wrote movies that share directors with the movie [Film Name]?"


class SourceSafetyTests(unittest.TestCase):
    def test_changed_answer_bytes_produce_identical_question_only_input(self):
        a1 = a.question_only_bytes(Q1+b"\tCorrect\n"+Q1+b"\tAnother Answer\n", expected=2)
        a2 = a.question_only_bytes(Q1+b"\tWrong|Other\n"+Q1+b"\tCompletely Different\n", expected=2)
        self.assertEqual(a1, a2)
        self.assertEqual(a1, Q1+b"\n"+Q1+b"\n")
        self.assertNotIn(b"Correct", a1)
        self.assertNotIn(b"Wrong", a2)

    def test_all_source_rows_are_retained_in_denominator(self):
        payload = a.question_only_bytes(Q1+b"\tA\n"+Q1+b"\tB\n", expected=2)
        self.assertEqual(payload.count(Q1), 2)
        with self.assertRaises(a.Denied):
            a.question_only_bytes(Q1+b"\tA\n"+Q1+b"\tB\n", expected=1)

    def test_bad_rows_fail_closed(self):
        for raw in [b"", Q1, Q1+b"\t", Q1+b"\tA\tB", b"\tAnswer"]:
            with self.assertRaises(a.Denied):
                a.question_only_bytes(raw, expected=1)

    def test_blob_digest_is_immutable_source_bytes(self):
        raw=b"question\tanswer\n"
        expect=hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\x00"+raw).hexdigest()
        self.assertEqual(a.git_blob_hash(raw),expect)
        self.assertNotEqual(a.git_blob_hash(raw+b"x"),expect)

    def test_real_question_strings_only_reach_go_parser(self):
        p=a.question_only_bytes(Q1+b"\tProtected Label\n"+Q2+b"\tAnother Label\n",expected=2)
        result2=a.count_questions(p,2,2)
        result3=a.count_questions(p,3,2)
        self.assertEqual(result2["questions"],2)
        self.assertEqual(result2["matched"],1)
        self.assertEqual(result2["abstained"],1)
        self.assertEqual(result3["matched"],1)
        self.assertEqual(result3["abstained"],1)
        self.assertEqual(result2["answers_read"],0)
        self.assertEqual(result3["model_calls"],0)

if __name__ == "__main__":
    unittest.main()

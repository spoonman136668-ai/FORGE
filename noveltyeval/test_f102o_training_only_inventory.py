"""Synthetic invariant tests for F102-O train-only source inventory."""
import hashlib
import unittest

import f102o_training_only_inventory as m

class InventoryTests(unittest.TestCase):
    def test_answer_mutation_never_changes_question_grammar(self):
        q=b"Who Directed the Movies [Film Name]?"
        before=m.count_public_train(q+b"\tTRUE\n"+q+b"\tABC\n")
        after=m.count_public_train(q+b"\tFALSE\n"+q+b"\tXYZ\n")
        self.assertEqual(before,after)
        self.assertEqual(before["rows"],2)
        self.assertEqual(before["top_40_question_only_families"][0],
                         {"masked_grammar":"who directed the movies []","frequency":2})
        self.assertNotIn("Film Name",str(before))
        self.assertNotIn("TRUE",str(before))

    def test_case_preserving_source_erasure_and_masking(self):
        self.assertEqual(m.mask_family(b"WHO DIRECTED [AbCd]?"),
                         m.mask_family(b"who directed [zzzz]?"))
        self.assertEqual(m.mask_family(b"who directed [zzzz]?"),"who directed []")
        for invalid in [b"",b"hello",b"[A][B]",b"[[A]]",b"[]",b"[A\nB]",
                        b"\xff[A]\xff", b"[A]"+bytes([0])]:
            self.assertIsNone(m.mask_family(invalid))

    def test_all_rows_preserved_even_invalid(self):
        r=m.count_public_train(b"[A]?\tY\ninvalid\tN\n[B][C]?\tZ\n")
        self.assertEqual(r["rows"],3)
        self.assertEqual(r["valid_bracket_question_rows"],1)
        self.assertEqual(r["malformed_or_unsupported_topic_structure"],2)
        self.assertEqual(r["unique_masked_families"],1)

    def test_row_and_byte_caps_fail_closed(self):
        with self.assertRaises(m.Denied):
            m.count_public_train(b"")
        with self.assertRaises(m.Denied):
            m.count_public_train(b"x"*(m.MAX_BYTES+1))
        with self.assertRaises(m.Denied):
            m.count_public_train(b"[a]?\ty\n"*(m.MAX_ROWS+1))

    def test_git_blob_is_original_binary_not_crlf_worktree(self):
        raw=b"x\tanswer\n"
        sha=hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\x00"+raw).hexdigest()
        self.assertEqual(m.blob_id(raw),sha)
        self.assertNotEqual(m.blob_id(raw.replace(b"\n",b"\r\n")),sha)

if __name__=="__main__":
    unittest.main()

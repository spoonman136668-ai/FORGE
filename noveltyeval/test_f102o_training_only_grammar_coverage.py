"""Synthetic adversarial F102-O TRAIN-only counting tests."""
import hashlib
import unittest
import f102o_training_only_grammar_coverage as m

Q2=b"the actor of [Movie: One] also starred in which films?"
Q3=b"who directed movies that share actors with the movie [Film Two]?"

class SourceOnlyCoverage(unittest.TestCase):
    def test_answer_mutation_equivalence_under_actual_go_parser(self):
        left=m.question_only(Q2+b"\tAnswer 1\n"+Q2+b"\tAnswer 2\n",2)
        right=m.question_only(Q2+b"\tWrong\n"+Q2+b"\tInjected\n",2)
        self.assertEqual(left,right)
        a=m.count_only_questions(left,2,2)
        b=m.count_only_questions(right,2,2)
        self.assertEqual(a,b)
        self.assertEqual(a["matched"],2)
        self.assertEqual(a["answers_read"],0)

    def test_three_hop_exact_and_unknown_are_accounted(self):
        inputs=m.question_only(Q3+b"\tOne\n"+b"invalid question\tTwo\n",2)
        r=m.count_only_questions(inputs,3,2)
        self.assertEqual(r["matched"],1)
        self.assertEqual(r["abstained"],1)
        self.assertEqual(r["questions"],2)
        self.assertEqual(sum(r["reasons"].values()),1)

    def test_missing_and_extra_rows_fail_closed(self):
        for bad,den in [(b"",1),(Q2,1),(Q2+b"\tA\n",2),(b"\tlabel\n",1)]:
            with self.assertRaises(m.Denied):
                m.question_only(bad,den)

    def test_source_hash_controls_binary_original_bytes(self):
        b=b"question\tlabel\n"
        want=hashlib.sha1(b"blob "+str(len(b)).encode()+b"\x00"+b).hexdigest()
        self.assertEqual(m.git_blob(b),want)
        self.assertNotEqual(m.git_blob(b.replace(b"\n",b"\r\n")),want)

if __name__=="__main__":
    unittest.main()

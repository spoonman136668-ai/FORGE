import unittest
from audit import original_effects, candidate_alternatives

class OriginalPublicEffectTests(unittest.TestCase):
    def test_sparse_competing_action_eligibility(self):
        row=[[0]*7 for _ in range(7)]
        row[0][0]=3
        row[2][0]=3
        row[2][1]=3
        self.assertEqual(candidate_alternatives(row)[0],2)
        row[2][0]=2
        self.assertNotIn(0,candidate_alternatives(row))

import unittest
from fractions import Fraction

from audit import audit, control_propose, exact_bayesian_predictive
from pinned_native_taskcell import TaskCell

class ConventionalParityTests(unittest.TestCase):
    def test_beta_exact_predictive_is_source_only(self):
        self.assertEqual(exact_bayesian_predictive(0,0),Fraction(1,2))
        self.assertEqual(exact_bayesian_predictive(2,3),Fraction(3,5))
        self.assertEqual(exact_bayesian_predictive(4096,4096),Fraction(4097,4098))
    def test_native_selected_context_policy_equals_beta_control(self):
        native=TaskCell()
        for _ in range(3):
            native.record(0,False)
            native.record(5,True)
        self.assertEqual(native.propose(0),(5,True))
        self.assertEqual(native.propose(0),
            control_propose(0,native.count,native.effect))
        self.assertEqual(native.propose(5),
            control_propose(5,native.count,native.effect))
    def test_no_evidence_preserves_parent(self):
        native=TaskCell()
        self.assertEqual(native.propose(2),(2,False))
        self.assertEqual(control_propose(2,native.count,native.effect),(2,False))
    def test_reject_impossible_counts(self):
        for k,n in ((-1,1),(2,1),(1,-1),(4097,4097),(1,1.0)):
            with self.assertRaises(ValueError):
                exact_bayesian_predictive(k,n)
    def test_full_bounded_decision_exhaustion(self):
        suites=list(audit())
        self.assertEqual(len(suites),3)
        self.assertEqual(suites[-1]["disagreements"],0)
        self.assertEqual(suites[-1]["posterior_score_disagreements"],0)
        self.assertGreater(suites[-1]["cases"],100000)
        self.assertGreater(suites[-1]["overrides"],0)

if __name__=="__main__":
    unittest.main()

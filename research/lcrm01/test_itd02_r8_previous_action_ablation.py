"""Verify previous-action ablation preserves evidence but merges contexts."""
import unittest
from itd02_r8_conditional_beta import ConditionalBeta
from itd02_r8_previous_action_ablation import PreviousActionAblatedBeta

class AblationTest(unittest.TestCase):
    def test_collapses_previous_action_contexts(self):
        native=ConditionalBeta()
        ablated=PreviousActionAblatedBeta()
        for model in (native,ablated):
            model.observe(False,2,False)
            model.observe(True,0,True)
            model.begin_episode()
            model.observe(True,0,False)
        self.assertEqual(native.samples,ablated.samples)
        self.assertEqual(native.bins[7][0],[0,1])
        self.assertEqual(native.bins[4][0],[1,0])
        self.assertEqual(ablated.bins[4][0],[1,1])
        self.assertEqual(ablated.bins[7][0],[0,0])
    def test_turn_selection_still_requires_evidence(self):
        model=PreviousActionAblatedBeta()
        self.assertIsNone(model.turn_choice(True))
        for _ in range(4):
            model.observe(True,0,True)
            model.observe(True,1,False)
        self.assertEqual(model.turn_choice(True),1)

if __name__=="__main__":unittest.main()

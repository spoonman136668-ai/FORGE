"""Source-only regression for independent R8 conditional Beta reference."""
import unittest
from itd02_r8_conditional_beta import ConditionalBeta

class ConditionalBetaTest(unittest.TestCase):
    def test_prior_and_threshold(self):
        b=ConditionalBeta()
        self.assertEqual(b.risks(True),((0.5,0.5),False))
        self.assertIsNone(b.turn_choice(True))
        for _ in range(4):
            b.begin_episode()
            b.observe(True,0,True)
            b.begin_episode()
            b.observe(True,1,False)
        b.begin_episode()
        risk,eligible=b.risks(True)
        self.assertTrue(eligible)
        self.assertEqual(risk,(5/6,1/6))
        self.assertEqual(b.turn_choice(True),1)
    def test_previous_action_is_context(self):
        b=ConditionalBeta()
        b.observe(False,2,False)
        b.observe(True,0,True)
        self.assertEqual(b.bins[7][0],[0,1])
        b.begin_episode()
        self.assertEqual(b.risks(True),((0.5,0.5),False))
    def test_forward_is_not_turn_sample(self):
        b=ConditionalBeta()
        b.observe(True,2,True)
        self.assertEqual(b.samples,0)
    def test_illegal_action_rejected(self):
        with self.assertRaises(ValueError):
            ConditionalBeta().observe(False,True,True)

if __name__=="__main__": unittest.main()

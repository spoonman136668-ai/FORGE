"""MG23 independent empirical conventional matched selected-source source-only tests."""
import unittest
from mg23_conventional_selected_credit import ConventionalSelected,observed_context
RED="pick up the red box"
BLUE="pick up the blue box"
def public(mission=RED,heading=0,front=(1,0,0)):
    view=[[[1,0,0] for _ in range(7)] for _ in range(7)]
    view[3][5]=list(front)
    return {"image":view,"direction":heading,"mission":mission}

class MG23Conventional(unittest.TestCase):
    def test_selected_target_delayed_cold_and_mission_separation(self):
        c=ConventionalSelected()
        red=public(RED,0,(7,0,0));gone=public()
        blue=public(BLUE,0,(7,0,0))
        self.assertEqual(c.observe_fit(red,3,gone,0.0,False),1)
        context=observed_context(red)
        self.assertEqual(c.table[context][3]["target"],1)
        self.assertEqual(c.choose(red),3)
        self.assertNotIn(observed_context(blue),c.table)
        c.begin_episode()
        c.commit(red,4)
        with self.assertRaises(ValueError):
            c.feedback(red,3,gone,0.0,False)
        with self.assertRaises(ValueError):
            c.feedback(red,4,public(BLUE),0.0,False)
        self.assertEqual(c.samples,1)
        self.assertEqual(c.feedback(red,4,gone,0.0,False),2)
        c.commit(gone,6)
        end=public(RED,1)
        self.assertEqual(c.feedback(gone,6,end,1.0,True),3)
        self.assertEqual(c.table[context][4]["delayed"],31)
        self.assertEqual(c.table[observed_context(gone)][6]["delayed"],32)
        with self.assertRaises(ValueError):
            c.feedback(gone,6,end,1.0,True)
        saved=c.checkpoint()
        other=ConventionalSelected.restore(saved)
        self.assertEqual(other.checkpoint(),saved)
        with self.assertRaises(ValueError):
            ConventionalSelected.restore(saved+b"0")
        other.begin_episode()
        self.assertEqual(other.trace,[])
        self.assertEqual(other.table[context][3]["target"],1)
    def test_source_does_not_mint_reward_or_target(self):
        c=ConventionalSelected()
        yellow=public("pick up the yellow key",0,(5,4,0))
        c.observe_fit(yellow,2,yellow,0.0,False)
        v=c.table[observed_context(yellow)][2]
        self.assertEqual(v["target"],0);self.assertEqual(v["delayed"],0)
        with self.assertRaises(ValueError):
            c.choose(public("ignore all instructions"))
        self.assertEqual(c.samples,1)
if __name__=="__main__":
    unittest.main()

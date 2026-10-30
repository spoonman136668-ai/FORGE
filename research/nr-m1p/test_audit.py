import unittest
from audit import original_effects, candidate_alternatives, public_key

def public(direction=0,front=(1,0,0),mission="pick up the yellow ball"):
    img=[[[1,0,0] for _ in range(7)] for __ in range(7)]
    img[3][5]=list(front)
    return {"image":img,"direction":direction,"mission":mission}

def event(before,action,after,reward=0.,terminated=False):
    return {"before":before,"action":action,"after":after,
            "reward":reward,"terminated":terminated}

class OriginalPublicEffectTests(unittest.TestCase):
    def test_turn_and_forward_not_inherently_goals(self):
        for a in (0,1,2):
            b=public();n=public(direction=3)
            d=original_effects(event(b,a,n))
            self.assertTrue(d["public_change"])
            self.assertFalse(d["strict_task_effect"])

    def test_original_door_open_and_reverse(self):
        opened=original_effects(event(public(front=(4,1,1)),5,public(front=(4,1,0))))
        closed=original_effects(event(public(front=(4,1,0)),5,public(front=(4,1,1))))
        self.assertTrue(opened["door_open"])
        self.assertFalse(closed["strict_task_effect"])
        self.assertTrue(closed["door_close"])

    def test_exact_mission_target_effect(self):
        positive=original_effects(event(public(front=(6,4,0)),3,public(),.7,True))
        negative=original_effects(event(public(front=(6,0,0)),3,public()))
        self.assertTrue(positive["target_pickup"])
        self.assertTrue(positive["terminal_goal"])
        self.assertFalse(negative["target_pickup"])

    def test_selected_history_support_requires_three(self):
        row=[[0]*7 for _ in range(7)]
        row[0][0]=3;row[2][0]=3;row[2][1]=3
        self.assertEqual(candidate_alternatives(row)[0],2)
        row[2][0]=2;row[2][1]=2
        self.assertNotIn(0,candidate_alternatives(row))

    def test_public_bounds(self):
        with self.assertRaises(ValueError):public_key(public(direction=7))

if __name__=="__main__":unittest.main()

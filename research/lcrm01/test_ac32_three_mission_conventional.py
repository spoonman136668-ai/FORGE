"""Five AC32 source-free three-mission conventional blocker/recovery checks."""
import copy,json,unittest
from ac32_three_mission_conventional import (
    ThreeMissionControl,canonical,original_public,LEGACY,MISSIONS)
def frame(mission,front=1):
    p={"image":[[[1,0,0] for _ in range(7)] for _ in range(7)],
       "direction":0,"mission":mission}
    p["image"][3][5][0]=front
    return p
class MockVisualParent:
    def __init__(self):
        self.samples=0
        self.observed=[]
        self.episode=0
    def begin_episode(self):self.episode+=1
    def learn(self,b,a,c):
        if b["mission"]!=LEGACY or c["mission"]!=LEGACY:
            raise ValueError("MOCK_CONVENTIONAL_PARENT_NOT_BLIND")
        self.samples+=1
        self.observed.append({"before":b,"action":a,"after":c})
    def choose(self,p):
        if p["mission"]!=LEGACY:raise ValueError("MOCK_CONVENTIONAL_BAD_PARENT")
        return 1
    def checkpoint(self):
        return canonical({"samples":self.samples,"observed":self.observed,"episode":self.episode})
    @classmethod
    def restore(cls,data):
        state=json.loads(data)
        if set(state)!={"samples","observed","episode"}:
            raise ValueError("BAD_MOCK_PARENT")
        a=cls();a.samples=state["samples"];a.observed=state["observed"];a.episode=state["episode"]
        if a.checkpoint()!=data:raise ValueError("BAD_MOCK_CANONICAL")
        return a

class AC32ThreeMissionControlTests(unittest.TestCase):
    def test_exact_three_genuine_original_source_missions_verbatim(self):
        self.assertEqual(MISSIONS,{LEGACY,"get to the green goal square","open the door"})
        c=ThreeMissionControl(MockVisualParent())
        for mission in (LEGACY,"get to the green goal square","open the door"):
            old=frame(mission);new=frame(mission,4)
            self.assertEqual(original_public(old)["mission"],mission)
            c.learn(old,2,new,0.0)
            self.assertIn(mission,c.missions)
            self.assertEqual(c.parent.observed[-1]["before"]["mission"],LEGACY)
        self.assertEqual(c.samples,3)
        self.assertEqual(sum(x["count"] for row in c.missions.values() for x in row),3)

    def test_original_mg15_reward_choice_formula_unchanged_for_prior_two(self):
        c=ThreeMissionControl(MockVisualParent())
        for mission in (LEGACY,"get to the green goal square"):
            c.begin_episode()
            for action,reward in ((2,0),(2,1),(3,1),(3,0),(3,0)):
                c.learn(frame(mission),action,frame(mission,4),reward)
            # score 4096*(1)/(2+64) versus 4096*(1)/(3+64)
            self.assertEqual(c.choose(frame(mission)),2)
            self.assertEqual(c.missions[mission][2],{"count":2,"success":1})
            self.assertEqual(c.missions[mission][3],{"count":3,"success":1})
        self.assertEqual(c.samples,10)

    def test_new_unlock_mission_own_selected_source_and_cold_restore(self):
        c=ThreeMissionControl(MockVisualParent())
        a=frame("open the door")
        c.begin_episode()
        self.assertEqual(c.choose(a),1)
        c.learn(a,4,frame("open the door",4),1.0)
        self.assertEqual(c.choose(a),4)
        raw=c.checkpoint()
        restored=ThreeMissionControl.restore(raw,MockVisualParent.restore)
        self.assertEqual(restored.checkpoint(),raw)
        self.assertEqual(restored.choose(a),4)
        self.assertEqual(restored.missions["open the door"][4]["success"],1)

    def test_private_fields_forged_mission_and_invalid_return_rejected(self):
        c=ThreeMissionControl(MockVisualParent())
        p=frame("open the door")
        for modified in (dict(p,agent_pos=[2,2]),dict(p,mission="use key"),
                         dict(p,direction=True),dict(p,mission="")):
            with self.assertRaises(ValueError):c.choose(modified)
        for act,reward,q in ((True,0,p),(7,0,p),(2,float("nan"),p),
                             (2,-0.1,p),(2,0,frame(LEGACY))):
            with self.assertRaises(ValueError):c.learn(p,act,q,reward)
        self.assertEqual(c.samples,0)
        self.assertFalse(c.missions)

    def test_wrong_checkpoint_history_and_unrecognized_mission_fail_closed(self):
        c=ThreeMissionControl(MockVisualParent())
        c.learn(frame(LEGACY),0,frame(LEGACY,4),0.0)
        raw=c.checkpoint()
        with self.assertRaises(ValueError):
            ThreeMissionControl.restore(raw+b"X",MockVisualParent.restore)
        state=json.loads(raw)
        state["state"]["missions"]["open the door"]=[{"count":0,"success":0}]*7
        state["state"]["missions"]["open the door"][0]={"count":1,"success":1}
        with self.assertRaises(ValueError):
            ThreeMissionControl.restore(canonical(state),MockVisualParent.restore)
        with self.assertRaises(ValueError):
            ThreeMissionControl.restore(b"{}",MockVisualParent.restore)

if __name__=="__main__":unittest.main()

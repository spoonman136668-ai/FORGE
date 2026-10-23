"""O17 source-free tests: causal gating, frozen state, capacity, control identity."""
import sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from research.optimizer_o17.model import PhaseGate
from research.optimizer_o16.model import FIFO,Stride,LearnedEviction

class O17SourceFree(unittest.TestCase):
    def test_bounded_phase_policy_and_legal_public_suits(self):
        for lag in (3,7):
            m=PhaseGate(lag,seed=29)
            for t in range(51):
                self.assertIn(m.read(t,t%4),range(4))
                m.write(t,t%4,train=True)
                m.feedback(t,1 if t%4==0 else -1)
                self.assertLessEqual(len(m.mem.items),4)
                self.assertLessEqual(m.mem.peak,4)
            self.assertGreater(m.fit_updates,0)
            self.assertGreater(m.fit_write_events,0)
    def test_only_prior_decisions_are_reward_credited(self):
        m=PhaseGate(3,seed=7)
        for t in range(7):
            m.write(t,t%4,train=True)
        self.assertGreater(len(m.pending),0)
        self.assertEqual(m.fit_updates,0)
        m.feedback(7,1)
        self.assertEqual(m.fit_updates,1)
        self.assertGreater(m.fit_reward_events,0)
    def test_eval_freeze_and_phase_rotation_control(self):
        a=PhaseGate(7,seed=1);b=PhaseGate(7,seed=1,phase_shift=1)
        a.logits=[4.,-4.,4.,-4.]
        b.logits=list(a.logits)
        x=a.state().copy()
        choices=[]
        for t in range(40):
            a.write(t,t%4,train=False)
            b.write(t,t%4,train=False)
            a.feedback(t,0);b.feedback(t,0)
            choices.append((a.mem.writes,b.mem.writes))
        self.assertEqual(a.state(),x)
        self.assertNotEqual(a.mem.items,b.mem.items)
    def test_legacy_and_strong_conventional_preserved(self):
        for ctor in (lambda: FIFO(7),lambda:Stride(7,2),
                     lambda:LearnedEviction(7,seed=7)):
            m=ctor()
            for t in range(40):
                m.write(t,t%4,train=False)
                m.feedback(t,0)
            self.assertLessEqual(m.mem.peak,4)
if __name__=="__main__":unittest.main()

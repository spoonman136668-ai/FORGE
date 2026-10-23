"""O16 source-free deterministic capacity/learning/custody preflight."""
import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from model import Memory,FIFO,Reservoir,Stride,LearnedEviction

class TestO16(unittest.TestCase):
    def test_capacity_timestamp_only_read(self):
        m=Memory(4)
        for t in range(12):
            m.put(t,t%4,None if t<4 else 0)
            self.assertLessEqual(m.peak,4)
        self.assertEqual(m.read(12,1,99),3)
        self.assertEqual(m.read(12,4,99),99)
    def test_all_arms_bounded_and_legal(self):
        for arm in [FIFO(7),Reservoir(7,seed=23),Stride(7,2),LearnedEviction(7,seed=23)]:
            for t in range(75):
                self.assertIn(arm.read(t,t%4),range(4))
                arm.write(t,t%4,train=True)
                arm.feedback(t,1 if t%3 else -1)
                self.assertLessEqual(len(arm.mem.items),4)
    def test_reward_applies_after_delayed_source_step(self):
        p=LearnedEviction(3,seed=2)
        for t in range(5):p.write(t,t%4,train=True)
        self.assertEqual(p.fit_updates,0)
        p.feedback(6,1)
        self.assertEqual(p.fit_updates,0)
        p.feedback(7,1)
        self.assertEqual(p.fit_updates,1)
        self.assertTrue(any(abs(v)>1e-8 for v in p.w))
    def test_dev_checkpoint_cannot_change(self):
        p=LearnedEviction(7,seed=3)
        p.w=[.3,-.2,.1,-.05,.2,-.2]
        saved=p.state().copy()
        for t in range(60):
            p.write(t,t%4,train=False);p.feedback(t,1)
        p.reset_episode()
        self.assertEqual(p.state(),saved)
        self.assertEqual(p.mem.items,[])
    def test_stride_control_differs_from_fifo(self):
        a,b=FIFO(7),Stride(7,2)
        for t in range(20):a.write(t,t%4);b.write(t,t%4)
        self.assertNotEqual(a.mem.items,b.mem.items)
if __name__=='__main__':unittest.main()

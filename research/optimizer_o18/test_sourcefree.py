"""O18 source-free pre-original-source qualification."""
import sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from research.optimizer_o18.model import RecordCredit
from research.optimizer_o17.model import PhaseGate
from research.optimizer_o16.model import FIFO,Stride,LearnedEviction

class O18SourceFree(unittest.TestCase):
    def test_all_memories_bounded_and_legal(self):
        for lag in (3,7):
            for obj in (RecordCredit(lag,seed=13),FIFO(lag),
                        Stride(lag,2),PhaseGate(lag,seed=13),LearnedEviction(lag,seed=13)):
                for t in range(60):
                    self.assertIn(obj.read(t,t%4),range(4))
                    obj.feedback(t,1 if t%3 else -1)
                    obj.write(t,t%4,train=True)
                    self.assertLessEqual(len(obj.mem.items),4)
                    self.assertLessEqual(obj.mem.peak,4)
                    if isinstance(obj,RecordCredit):
                        self.assertLessEqual(len(obj.pending),lag+1)
                        self.assertLessEqual(len(obj.use_counts),4)
    def test_reward_updates_eligible_prior_only(self):
        obj=RecordCredit(3,seed=17)
        for t in range(6):
            obj.write(t,t%4,train=True)
        before=list(obj.w)
        obj.feedback(6,1)
        self.assertEqual(obj.reward_events,1)
        self.assertEqual(obj.fit_updates,1)
        self.assertNotEqual(obj.w,before)
        self.assertNotIn(2,obj.pending)
    def test_dev_frozen_and_ablation_changes_feature_values(self):
        learned=RecordCredit(7)
        ablated=RecordCredit(7,feature_ablation=True)
        for p in (learned,ablated):
            p.w=[.1,.2,1.,-.4,.5,.9,.3,.1]
            for t in range(4):p.write(t,t%4,train=False)
        self.assertNotEqual(learned.options(5,2),ablated.options(5,2))
        original=learned.state().copy()
        for t in range(4,65):
            learned.read(t,t%4)
            learned.feedback(t,0.)
            learned.write(t,t%4,train=False)
        self.assertEqual(learned.state(),original)
        self.assertEqual(len(learned.pending),0)
        self.assertEqual(learned.fit_updates,0)
    def test_public_source_roles_not_colliding(self):
        from research.optimizer_o15.runner import source_seed
        role_ids=[]
        for d in range(2):
            for rep in range(3):
                role_ids += [source_seed("FIT",d,rep,i) for i in range(48)]
                role_ids += [13100000+400000*d+10000*rep+i for i in range(48)]
                role_ids += [14300000+400000*d+10000*rep+i for i in range(24)]
        self.assertEqual(len(role_ids),len(set(role_ids)))
        self.assertEqual(len(role_ids),720)
        # Neither O16 DEV nor O17 corrected DEV uses these sources.
        dev={14300000+400000*d+10000*rep+i
             for d in range(2) for rep in range(3) for i in range(24)}
        old={base+400000*d+10000*rep+i for base in (9900000,12300000)
             for d in range(2) for rep in range(3) for i in range(24)}
        self.assertFalse(dev & old)

if __name__=="__main__":unittest.main()

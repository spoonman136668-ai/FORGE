"""NR-M2B: cross-episode learned action-factor cells versus trained R7.

All transitions originate solely from authored public 8-bit before/action/after
fixtures. No original MiniGrid/Pycolab environment, goal or heldout is run.
"""
from hashlib import sha1,sha256
import json
from pathlib import Path
import random
import subprocess
import sys
import tempfile
import time
import unittest

from nr_m1z_pinned_r7 import NonlinearLocalLearner
from nr_m2b_factor_cells import PersistentFactorCells, CAP

ORIGINAL_R7_GIT_BLOB="204ecd993b954b23e66d6d1e8b3568e7c93183c5"
ACTIONS=(0,1,2,0,1)

def public_effect(seed,action,before):
    """Previously authored, source-only R7 deterministic effect law."""
    after=0
    for bit in range(8):
        p=(bit+action)%8
        q=(bit+action+2)%8
        r=(bit+action+5)%8
        val=(((before>>p)&1)&((before>>q)&1))^((before>>r)&1)^((seed+bit+action)&1)
        after |= val<<bit
    return after

def source_samples(seed):
    order=random.Random(seed).sample(range(256),192)
    return [order[i:i+64] for i in range(0,len(order),64)]

def trained_original_r7(seed):
    control=NonlinearLocalLearner()
    for state in [state for episode in source_samples(seed) for state in episode]:
        for action in range(3):
            control.observe("one-source-public-world",action,state,public_effect(seed,action,state))
    control.fit()
    return control

def source_selected_training(model,seed):
    for episode in source_samples(seed):
        model.begin_episode()
        for before in episode:
            for action in range(3):
                model.commit(before,action)
                model.feedback(before,action,public_effect(seed,action,before))

def held_states(seed):
    fitted={s for episode in source_samples(seed) for s in episode}
    return sorted(set(range(256))-fitted)

def true_chain(seed,before,actions):
    for action in actions:
        before=public_effect(seed,action,before)
    return before

class FactorCellTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        source=Path(__file__).with_name("nr_m1z_pinned_r7.py")
        actual=source.read_bytes()
        git=subprocess.run(["git","show","HEAD:research/nr-m1x/nr_m1z_pinned_r7.py"],
                           capture_output=True,check=True).stdout
        digest=sha1(b"blob "+str(len(git)).encode()+b"\0"+git).hexdigest()
        if digest!=ORIGINAL_R7_GIT_BLOB or actual.replace(b"\r\n",b"\n")!=git:
            raise AssertionError("NRM2B_ORIGINAL_R7_SOURCE_DRIFT")
        cls.base=trained_original_r7(11)
        cls.base_bytes=cls.base.checkpoint()
        cls.base_sha=sha256(cls.base_bytes).hexdigest()

    def setUp(self):
        self.native=PersistentFactorCells(self.base)

    def test_strict_selected_custody_and_abstention(self):
        self.assertEqual(self.native.step(3,0),(None,False))
        with self.assertRaises(ValueError):
            self.native.commit(3,0)
        self.native.begin_episode()
        with self.assertRaises(ValueError):
            self.native.feedback(3,0,9)
        with self.assertRaises(ValueError):
            self.native.commit(300,0)
        self.native.commit(3,0)
        with self.assertRaises(ValueError):
            self.native.commit(3,1)
        with self.assertRaises(ValueError):
            self.native.checkpoint()
        with self.assertRaises(ValueError):
            self.native.feedback(3,1,9)
        self.native.feedback(3,0,9)
        with self.assertRaises(ValueError):
            self.native.feedback(3,0,9)
        self.assertEqual(self.native.step(3,0),(None,False))
        self.assertEqual(self.native.events,1)
        self.assertEqual(self.base.checkpoint(),self.base_bytes)

    def test_three_episodes_learn_five_step_unseen_public_effects_matching_strong_r7(self):
        start=time.perf_counter()
        source_selected_training(self.native,11)
        self.assertEqual(self.native.episodes,3)
        self.assertEqual(self.native.events,576)
        self.assertEqual(self.native.evictions,0)
        self.assertEqual([len(self.native.rows[a]) for a in range(3)],[CAP]*3)
        best=trained_original_r7(11)
        matched=0
        for before in held_states(11):
            for action in range(3):
                got,known=self.native.step(before,action)
                self.assertTrue(known,("insufficient learned support",before,action))
                self.assertEqual(got,public_effect(11,action,before))
                self.assertEqual(got,best.step("one-source-public-world",action,before))
                matched+=1
            actual,known=self.native.forecast(before,ACTIONS)
            self.assertTrue(known,("five-step lack of learned support",before))
            expected=true_chain(11,before,ACTIONS)
            self.assertEqual(actual,expected)
            self.assertEqual(actual,best.predict("one-source-public-world",before,ACTIONS))
            matched+=1
        self.assertEqual(matched,256)
        self.assertEqual(self.base.checkpoint(),self.base_bytes)
        self.assertLess(len(self.native.checkpoint()),25000)
        print("NRM2B_SOURCE_ONLY_TRUE_FACTOR_FIT_PASS heldout_single_and_five_step=256 strong_R7_disagreements=0 elapsed_s=%.5f"%(time.perf_counter()-start))

    def test_episode_boundary_retains_selected_causal_evidence_not_oracle(self):
        source_selected_training(self.native,11)
        trained=self.native.checkpoint()
        predicted=self.native.forecast(201,ACTIONS)
        self.assertTrue(predicted[1])
        self.native.begin_episode()
        self.assertEqual(self.native.forecast(201,ACTIONS),predicted)
        self.assertEqual(self.native.events,576)
        untrained=PersistentFactorCells(self.base)
        untrained.begin_episode()
        self.assertEqual(untrained.forecast(201,ACTIONS),(None,False))
        self.assertNotEqual(self.native.checkpoint(),trained)

    def test_changed_source_dynamics_abstain_then_relearn_without_world_name(self):
        source_selected_training(self.native,11)
        before=201
        first,known=self.native.step(before,0)
        self.assertTrue(known)
        self.native.begin_episode()
        self.native.commit(before,0)
        self.native.feedback(before,0,public_effect(12,0,before))
        # The old exact native factor no longer fits its actually observed
        # new outcome; it must abstain rather than hallucinate certainty.
        self.assertEqual(self.native.step(before,0),(None,False))
        # Run a new public trajectory roster; each own-selected action is
        # still observed, and the 192 most recent pairs per action replace A.
        source_selected_training(self.native,12)
        self.assertEqual(self.native.events,1153)
        self.assertEqual(self.native.evictions,577)
        control=trained_original_r7(12)
        matched=0
        for x in held_states(12):
            for action in range(3):
                y,known=self.native.step(x,action)
                self.assertTrue(known,(x,action))
                self.assertEqual(y,public_effect(12,action,x))
                self.assertEqual(y,control.step("one-source-public-world",action,x))
                matched+=1
            actual,ok=self.native.forecast(x,ACTIONS)
            self.assertTrue(ok)
            self.assertEqual(actual,true_chain(12,x,ACTIONS))
            self.assertEqual(actual,control.predict("one-source-public-world",x,ACTIONS))
            matched+=1
        self.assertEqual(matched,256)
        self.assertNotEqual(self.native.step(before,0)[0],first)
        self.assertEqual(self.base.checkpoint(),self.base_bytes)
        print("NRM2B_SHIFT_AFTER_REAL_SELECTED_FEEDBACK_PASS new_regime_dev_holdout=256 strong_R7_disagreements=0")

    def test_cold_cross_process_and_external_digest_rejection(self):
        source_selected_training(self.native,11)
        raw=self.native.checkpoint()
        digest=sha256(raw).hexdigest()
        fresh=PersistentFactorCells.restore(raw,self.base_sha,digest)
        self.assertEqual(fresh.checkpoint(),raw)
        self.assertEqual(fresh.episodes,3)
        self.assertEqual(fresh.forecast(201,ACTIONS),self.native.forecast(201,ACTIONS))
        with self.assertRaises(ValueError):
            PersistentFactorCells.restore(raw,"0"*64,digest)
        with self.assertRaises(ValueError):
            PersistentFactorCells.restore(raw,self.base_sha,"0"*64)
        with self.assertRaises(ValueError):
            PersistentFactorCells.restore(raw+b" ",self.base_sha,sha256(raw+b" ").hexdigest())
        damaged=json.loads(raw)
        damaged["body"]["rows"][0][1][0][1]=300
        changed=json.dumps(damaged,sort_keys=True,separators=(",",":")).encode()
        with self.assertRaises(ValueError):
            PersistentFactorCells.restore(changed,self.base_sha,sha256(changed).hexdigest())
        with tempfile.TemporaryDirectory(prefix="nr-m2b-") as tmp:
            file=Path(tmp)/"source-selected-factor-checkpoint.json"
            file.write_bytes(raw)
            child_script="""
import pathlib,sys
from hashlib import sha256
from nr_m2b_factor_cells import PersistentFactorCells
data=pathlib.Path(sys.argv[1]).read_bytes()
model=PersistentFactorCells.restore(data,sys.argv[2],sys.argv[3])
assert model.episodes==3 and model.events==576
assert model.forecast(201,[0,1,2,0,1])[1]
assert model.checkpoint()==data
print("NRM2B_FRESH_PROCESS_CROSS_EPISODE_FACTOR_RESTORE_PASS")
"""
            p=subprocess.run([sys.executable,"-B","-c",child_script,str(file),self.base_sha,digest],
                             cwd=str(Path(__file__).parent),text=True,capture_output=True,timeout=35)
            self.assertEqual(p.returncode,0,p.stdout+p.stderr)
            self.assertIn("NRM2B_FRESH_PROCESS_CROSS_EPISODE_FACTOR_RESTORE_PASS",p.stdout)
            self.assertEqual(file.read_bytes(),raw)

if __name__=="__main__":
    unittest.main()

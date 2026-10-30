"""NR-M2A source-free online adaptation and conventional parity qualification.

No original environment or privileged simulator source loaded.
"""
from collections import Counter, defaultdict, deque
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from nr_m1z_pinned_r7 import NonlinearLocalLearner
from nr_m2a_online_seam import SelectedOnlineSeam, canonical

ORIGINAL_R7_BLOB = "204ecd993b954b23e66d6d1e8b3568e7c93183c5"

def base_model():
    model = NonlinearLocalLearner()
    for action in (0, 1, 2):
        for before in range(192):
            model.observe("historical-source-A", action, before, before ^ (3, 5, 6)[action])
    model.fit()
    return model

class EqualDataCategoricalControl:
    """Independent standard categorical Beta(1,1) predictive with same evidence."""
    def __init__(self):
        self.rows = defaultdict(lambda:deque(maxlen=8))
    def observe(self, before, action, after):
        self.rows[(before, action)].append(after)
    def step(self, before, action):
        events = self.rows[(before,action)]
        if len(events) < 3:
            return None, False
        counts = Counter(events)
        top = sorted(counts.items(), key=lambda kv:(-kv[1], kv[0]))
        if len(top)>1 and top[0][1]==top[1][1]:
            return None, False
        value, count=top[0]
        if Fraction(count+1, len(events)+2) < Fraction(3,4):
            return None, False
        return value, True
    def forecast(self, before, actions):
        state=before
        for action in actions:
            value, known=self.step(state, action)
            if not known:
                return None, False
            state=value
        return state, True

class OnlineSeamTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path=Path(__file__).with_name("nr_m1z_pinned_r7.py")
        raw=path.read_bytes()
        git=subprocess.run(["git","show","HEAD:research/nr-m1x/nr_m1z_pinned_r7.py"],
                           capture_output=True,check=True).stdout
        digest=hashlib.sha1(b"blob "+str(len(git)).encode()+b"\0"+git).hexdigest()
        if digest!=ORIGINAL_R7_BLOB or raw.replace(b"\r\n",b"\n")!=git:
            raise AssertionError("NRM2A_R7_SOURCE_IDENTITY_DRIFT")
        cls.base=base_model()
        cls.original=cls.base.checkpoint()
        cls.original_sha=hashlib.sha256(cls.original).hexdigest()

    def setUp(self):
        self.native=SelectedOnlineSeam(self.base)
        self.native.begin_episode()
        self.control=EqualDataCategoricalControl()

    def record(self, before, action, after):
        self.native.commit(before, action)
        self.native.feedback(before, action, after)
        self.control.observe(before, action, after)

    def test_fresh_selected_effect_supports_multistep_prediction_without_world_label(self):
        self.assertEqual(self.native.forecast(9,[0,1]),(None,False))
        self.assertEqual(self.native._base_sha,self.original_sha)
        # New consequences disagree with frozen historical R7. No future
        # teacher state is used: every target below is returned source feedback.
        for i in range(3):
            self.record(9,0,14)
            self.record(14,1,8)
            self.assertEqual(self.native.forecast(9,[0,1]),
                             self.control.forecast(9,[0,1]))
            if i<2:
                self.assertEqual(self.native.forecast(9,[0,1]),(None,False))
        self.assertEqual(self.native.forecast(9,[0,1]),(8,True))
        self.assertEqual(self.native.forecast(9,[0,2]),(None,False))
        self.assertEqual(self.base.checkpoint(),self.original)
        self.assertEqual(self.base.predict("historical-source-A",9,[0,1]),15)
        self.assertEqual(self.native.events,6)

    def test_contradiction_abstains_and_no_session_label_leak(self):
        for after in [14]*3+[13]*3:
            self.record(9,0,after)
            self.assertEqual(self.native.step(9,0),self.control.step(9,0))
        self.assertEqual(self.native.step(9,0),(None,False))
        self.assertEqual(self.native.forecast(9,[0]),(None,False))
        self.assertEqual(self.base.checkpoint(),self.original)
        # Public episode reset does not retain stale-effect certainty
        # from a different dynamic regime. Historical R7 remains immutable.
        self.native.begin_episode()
        self.control=EqualDataCategoricalControl()
        self.assertEqual(self.native.step(9,0),(None,False))
        for _ in range(3):
            self.record(9,0,13)
        self.assertEqual(self.native.step(9,0),(13,True))

    def test_source_selection_replay_pending_and_invalid_feedback_fail_closed(self):
        with self.assertRaises(ValueError):
            self.native.feedback(9,0,14)
        with self.assertRaises(ValueError):
            self.native.commit(9,7)
        self.native.commit(9,0)
        before=self.native.events
        with self.assertRaises(ValueError):
            self.native.feedback(9,1,14)
        with self.assertRaises(ValueError):
            self.native.checkpoint()
        self.assertEqual(self.native.events,before)
        self.native.feedback(9,0,14)
        with self.assertRaises(ValueError):
            self.native.feedback(9,0,14)
        with self.assertRaises(ValueError):
            self.native.commit(300,0)
        self.assertEqual(self.native.events,1)

    def test_source_bound_checkpoint_and_independent_fresh_process(self):
        for i in range(3):
            self.record(9,0,14)
            self.record(14,1,8)
        snapshot=self.native.checkpoint()
        checkpoint_sha=hashlib.sha256(snapshot).hexdigest()
        cold=SelectedOnlineSeam.restore(snapshot,self.original_sha,checkpoint_sha)
        self.assertEqual(cold.checkpoint(),snapshot)
        self.assertEqual(cold.forecast(9,[0,1]),(8,True))
        with self.assertRaises(ValueError):
            SelectedOnlineSeam.restore(snapshot,"0"*64,checkpoint_sha)
        with self.assertRaises(ValueError):
            SelectedOnlineSeam.restore(snapshot+b"x",self.original_sha,checkpoint_sha)
        bad=json.loads(snapshot)
        bad["body"]["rows"][0][2]=[99]
        bad["sha256"]=hashlib.sha256(canonical(bad["body"])).hexdigest()
        with self.assertRaises(ValueError):
            SelectedOnlineSeam.restore(canonical(bad),self.original_sha,checkpoint_sha)
        with tempfile.TemporaryDirectory(prefix="nr-m2a-") as tmp:
            target=Path(tmp)/"selected-public-checkpoint.json"
            target.write_bytes(snapshot)
            child_script="""
import hashlib,pathlib,sys
from nr_m2a_online_seam import SelectedOnlineSeam
source=pathlib.Path(sys.argv[1]).read_bytes()
model=SelectedOnlineSeam.restore(source,sys.argv[2],sys.argv[3])
assert model.forecast(9,[0,1])==(8,True)
assert model.checkpoint()==source
print("NRM2A_FRESH_OS_COLD_SOURCE_BOUND_RESTORE_PASS")
"""
            p=subprocess.run([sys.executable,"-B","-c",child_script,str(target),self.original_sha,checkpoint_sha],
                             cwd=str(Path(__file__).parent),capture_output=True,text=True,timeout=30)
            self.assertEqual(p.returncode,0,p.stdout+" "+p.stderr)
            self.assertIn("NRM2A_FRESH_OS_COLD_SOURCE_BOUND_RESTORE_PASS",p.stdout)
            self.assertEqual(target.read_bytes(),snapshot)

    def test_conventional_control_full_small_source_free_sequence_parity(self):
        # Vary conditions but do not train on an unselected action.
        scenarios=[
            [(9,0,14)]*3,
            [(9,0,14),(9,0,13)]*4,
            [(9,0,14)]*8+[(9,0,13)]*5,
            [(9,0,14)]*3+[(14,1,8)]*3,
            [(3,2,2)]*4+[(3,1,7)]*4,
        ]
        cases=0
        for stream in scenarios:
            native=SelectedOnlineSeam(self.base)
            native.begin_episode()
            control=EqualDataCategoricalControl()
            for before,action,after in stream:
                native.commit(before,action)
                native.feedback(before,action,after)
                control.observe(before,action,after)
                for probe in ((9,0),(9,1),(3,2),(3,1),(14,1)):
                    self.assertEqual(native.step(*probe),control.step(*probe))
                    cases+=1
                for chain in ((0,1),(2,),(1,2)):
                    self.assertEqual(native.forecast(9,chain),control.forecast(9,chain))
                    cases+=1
        self.assertGreater(cases,200)
        self.assertEqual(self.base.checkpoint(),self.original)
        print(f"NRM2A_MATCHED_CONVENTIONAL_CATEGORICAL_SOURCE_ONLY_PASS comparisons={cases}")

if __name__=="__main__":
    unittest.main()

"""NR-M1Z source-only existing R7 interface acceptance probe.

Exact original Yggdrasil R7 source is in nr_m1z_pinned_r7.py. This file
does NOT change its learner or use original-world episodes.
"""
import hashlib
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest
from nr_m1z_pinned_r7 import NonlinearLocalLearner

SOURCE_GIT_BLOB="204ecd993b954b23e66d6d1e8b3568e7c93183c5"
MASKS=(3,5,6)
ACTIONS=(0,1,2,0,1)

def source_effect(action, public):
    if type(action) is not int or action not in range(3) or type(public) is not int or public not in range(256):
        raise ValueError("NRM1Z_INVALID_AUTHOR_SOURCE_INPUT")
    return public ^ MASKS[action]

def build():
    model=NonlinearLocalLearner()
    for a in range(3):
        for before in range(192):
            model.observe("public-world-A",a,before,source_effect(a,before))
    model.fit()
    return model

def predicted_true(start,actions):
    current=start
    for action in actions:
        current=source_effect(action,current)
    return current

class NativeR7Interface(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        raw=pathlib.Path(__file__).with_name("nr_m1z_pinned_r7.py").read_bytes()
        digest=hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()
        if digest!=SOURCE_GIT_BLOB:
            raise AssertionError("NRM1Z_ORIGINAL_R7_GIT_BLOB_CHANGED "+digest)
        cls.native=build()
        cls.checkpoint=cls.native.checkpoint()
        cls.cold=NonlinearLocalLearner.restore(cls.checkpoint)

    def test_same_world_composition_and_checkpoint(self):
        for state in (0,7,9,19,31,47):
            original=self.native.predict("public-world-A",state,ACTIONS)
            self.assertEqual(original,predicted_true(state,ACTIONS))
            self.assertEqual(original,self.cold.predict("public-world-A",state,ACTIONS))
        self.assertEqual(self.checkpoint,self.cold.checkpoint())
        self.assertEqual(self.native.events,576)
        print("NRM1Z_SAME_WORLD_SOURCE_AUTHORED_FIVE_STEP_COMPOSITION_PASS")

    def test_new_world_online_update_is_not_in_original_contract(self):
        with self.assertRaises(KeyError):
            self.cold.predict("public-world-B",9,ACTIONS)
        with self.assertRaisesRegex(ValueError,"R7_CANNOT_LEARN_AFTER_MODEL_FREEZE"):
            self.cold.observe("public-world-B",0,9,source_effect(0,9))
        self.assertEqual(self.checkpoint,self.cold.checkpoint())
        print("NRM1Z_ONLINE_UNFAMILIAR_WORLD_UPDATE_NOT_SUPPORTED_EXPECTED_BLOCKER")

    def test_actual_fresh_interpreter_cold_readback(self):
        with tempfile.TemporaryDirectory() as directory:
            file=pathlib.Path(directory)/"source-only-native-r7.json"
            file.write_bytes(self.checkpoint)
            child="""
import pathlib,sys
from nr_m1z_pinned_r7 import NonlinearLocalLearner
state=NonlinearLocalLearner.restore(pathlib.Path(sys.argv[1]).read_bytes())
assert state.events==576
assert state.predict("public-world-A",9,[0,1,2,0,1])==9^(3^5^6^3^5)
try:
    state.predict("public-world-B",9,[0,1])
except KeyError:
    pass
else:
    raise AssertionError("unseen world falsely qualified")
print("NRM1Z_NEW_PROCESS_CHECKPOINT_AND_SOURCE_WORLD_BOUNDARY_PASS")
"""
            p=subprocess.run([sys.executable,"-B","-c",child,str(file)],
                             cwd=str(pathlib.Path(__file__).parent),
                             capture_output=True,text=True,timeout=30,check=False)
            self.assertEqual(p.returncode,0,p.stdout+" "+p.stderr)
            self.assertIn("NRM1Z_NEW_PROCESS_CHECKPOINT_AND_SOURCE_WORLD_BOUNDARY_PASS",p.stdout)
            self.assertEqual(file.read_bytes(),self.checkpoint)

if __name__=="__main__":
    unittest.main()

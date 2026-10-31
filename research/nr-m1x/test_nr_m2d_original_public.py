"""NR-M2D original-public native source-admissibility negative/transport tests.

There is NO instantiated Farama/MiniGrid world; frames are authored,
not source-returned. The original native R10 source validates transport.
"""
from hashlib import sha1, sha256
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from nr_m1z_pinned_r7 import NonlinearLocalLearner
from nr_m2d_pinned_original_public import (
    ACTION_NAMES, MISSION, public_observation, canonical, digest
)
from nr_m2d_original_public_bridge import ExactPublicSevenActionBridge

ORIGINAL_R10_BLOB="3917d36ce9f86a2c1b998a0a2f93fb27674a9205"
ORIGINAL_R7_BLOB="204ecd993b954b23e66d6d1e8b3568e7c93183c5"

def source_free_frame(mission=MISSION,direction=0):
    return {
        "image":[[[1,0,0] for _ in range(7)] for _ in range(7)],
        "direction":direction,
        "mission":mission
    }

class PublicNativeSevenActionGate(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        for filename, expected in (
            ("nr_m2d_pinned_original_public.py",ORIGINAL_R10_BLOB),
            ("nr_m1z_pinned_r7.py",ORIGINAL_R7_BLOB)
        ):
            name="research/nr-m1x/"+filename
            original=subprocess.run(["git","show","HEAD:"+name],
                                    check=True,capture_output=True).stdout
            actual=Path(__file__).with_name(filename).read_bytes()
            blob=sha1(b"blob "+str(len(original)).encode()+b"\0"+original).hexdigest()
            if blob!=expected or actual.replace(b"\r\n",b"\n")!=original:
                raise AssertionError("NRM2D_PINNED_NATIVE_SOURCE_DRIFT "+filename)
        cls.initial=source_free_frame()

    def test_full_original_native_action_roster_and_selected_source_feedback(self):
        self.assertEqual(ACTION_NAMES,("left","right","forward","pickup",
                                       "drop","toggle","done"))
        self.assertEqual(len(ACTION_NAMES),7)
        for action in range(7):
            adapter=ExactPublicSevenActionBridge()
            before=source_free_frame()
            after=source_free_frame()
            after["image"][0][0]=[1,action%6,0]
            adapter.begin_episode(before)
            adapter.commit(before,action)
            event=adapter.feedback(before,action,after)
            self.assertEqual(event["selected_action"],action)
            self.assertEqual(event["selected_action_name"],ACTION_NAMES[action])
            self.assertEqual(json.loads(event["public_before"]),public_observation(before))
            self.assertEqual(json.loads(event["public_after"]),public_observation(after))
            self.assertEqual(event["public_before_sha256"],digest(before))
            self.assertEqual(event["public_after_sha256"],digest(after))
            self.assertEqual(event["original_event"]["action"],action)
            self.assertEqual(adapter._native.events,1)

    def test_full_public_identity_cannot_fit_unmodified_eight_bit_r7_input(self):
        source_state=source_free_frame()
        source_state["image"][0][0]=[1,0,1]
        other=source_free_frame()
        other["image"][0][0]=[1,0,2]
        self.assertEqual(source_state["image"][3][5],other["image"][3][5])
        self.assertEqual(source_state["direction"],other["direction"])
        self.assertEqual(source_state["mission"],other["mission"])
        self.assertNotEqual(digest(source_state),digest(other))
        self.assertNotEqual(canonical(source_state),canonical(other))
        # 257 distinct admissible public frames with identical mission,
        # direction, and front pixel; 8-bit representation has only 256
        # values. No lossless injection exists even within this subset.
        hashes=set()
        for index in range(257):
            frame=source_free_frame()
            frame["image"][0][0]=[1,index//256,index%256]
            hashes.add(digest(public_observation(frame)))
        self.assertEqual(len(hashes),257)
        old=NonlinearLocalLearner()
        for action in (3,4,5,6):
            with self.assertRaisesRegex(ValueError,"R7_INVALID_PUBLIC_COMPOSITION"):
                old.step("old-source",action,0)
        with self.assertRaisesRegex(ValueError,"R7_INVALID_PUBLIC_COMPOSITION"):
            old.step("old-source",0,source_state)
        print("NRM2D_DIRECT_R7_SEVEN_ACTION_FULL_PUBLIC_ADMISSION_BLOCKED")

    def test_untrusted_privileged_extra_field_mission_and_action_refused(self):
        adapter=ExactPublicSevenActionBridge()
        frame=source_free_frame()
        leaked=source_free_frame()
        leaked["agent_pos"]=[3,2]
        with self.assertRaises(ValueError):
            adapter.begin_episode(leaked)
        adapter.begin_episode(frame)
        with self.assertRaises(ValueError):
            adapter.commit(leaked,0)
        for bad in (-1,7,True,None,1.0):
            with self.assertRaises(ValueError):
                adapter.commit(frame,bad)
        with self.assertRaises(ValueError):
            adapter.begin_episode(source_free_frame("pick up the red box"))
        # MG19 mission expansion is a DIFFERENT original adapter and needs
        # its own native-source integration; R10 must not relabel a mission.
        self.assertEqual(adapter._native.events,0)

    def test_commit_feedback_atomicity_and_replay(self):
        bridge=ExactPublicSevenActionBridge()
        before=source_free_frame()
        after=source_free_frame(direction=1)
        bridge.begin_episode(before)
        with self.assertRaises(ValueError):
            bridge.feedback(before,0,after)
        bridge.commit(before,0)
        with self.assertRaises(ValueError):
            bridge.commit(before,1)
        with self.assertRaises(ValueError):
            bridge.checkpoint()
        with self.assertRaises(ValueError):
            bridge.feedback(before,1,after)
        self.assertEqual(bridge._native.events,0)
        event=bridge.feedback(before,0,after)
        self.assertEqual(event["original_event"]["heading_after"],1)
        with self.assertRaises(ValueError):
            bridge.feedback(before,0,after)
        with self.assertRaises(ValueError):
            bridge.commit(before,0)
        bridge.commit(after,2)
        with self.assertRaises(ValueError):
            bridge.begin_episode(before)
        bridge.feedback(after,2,after)
        self.assertEqual(bridge._native.events,2)

    def test_fresh_interpreter_original_source_checkpoint_and_trusted_sha(self):
        bridge=ExactPublicSevenActionBridge()
        frame=source_free_frame()
        bridge.begin_episode(frame)
        bridge.commit(frame,6)
        bridge.feedback(frame,6,frame)
        checkpoint=bridge.checkpoint()
        sha=sha256(checkpoint).hexdigest()
        cold=ExactPublicSevenActionBridge.restore(checkpoint,sha)
        self.assertEqual(cold.checkpoint(),checkpoint)
        self.assertEqual(cold._native.events,1)
        with self.assertRaises(ValueError):
            ExactPublicSevenActionBridge.restore(checkpoint,"0"*64)
        with self.assertRaises(ValueError):
            ExactPublicSevenActionBridge.restore(checkpoint+b" ",sha256(checkpoint+b" ").hexdigest())
        with tempfile.TemporaryDirectory(prefix="nr-m2d-") as directory:
            target=Path(directory)/"original-public-source-only.json"
            target.write_bytes(checkpoint)
            test_script="""
import pathlib,sys
from hashlib import sha256
from nr_m2d_original_public_bridge import ExactPublicSevenActionBridge
data=pathlib.Path(sys.argv[1]).read_bytes()
restored=ExactPublicSevenActionBridge.restore(data,sys.argv[2])
assert restored._native.events==1
assert restored._native.ledger[0]["action"]==6
assert restored.checkpoint()==data
print("NRM2D_SEVEN_ACTION_NEW_PROCESS_SOURCE_COLD_PASS")
"""
            p=subprocess.run([sys.executable,"-B","-c",test_script,str(target),sha],
                             cwd=str(Path(__file__).parent),
                             capture_output=True,text=True,timeout=25)
            self.assertEqual(p.returncode,0,p.stdout+p.stderr)
            self.assertIn("NRM2D_SEVEN_ACTION_NEW_PROCESS_SOURCE_COLD_PASS",p.stdout)

if __name__=="__main__":
    unittest.main()

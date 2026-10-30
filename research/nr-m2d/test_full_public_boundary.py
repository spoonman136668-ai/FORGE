"""NR-M2D strict exact original-public source-only compatibility tests.

No import or execution of the original Farama engine, no actual environment
reset/step or first-use; all frames below are authored ORIGINAL-SHAPED
fixtures, not original physical selected-action receipts.
"""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import pinned_original_r10 as r10
from full_public_boundary import (
    original_frame, original_fingerprint, original_action, admitted,
    forbid_8bit_compatibility, SelectedPublicBoundary
)

R10_ORIGINAL_GIT_BLOB="3917d36ce9f86a2c1b998a0a2f93fb27674a9205"

def frame(mission=None,direction=0):
    if mission is None:
        mission=r10.MISSION
    return {
      "image":[[[1,0,0] for _ in range(7)] for _ in range(7)],
      "direction":direction,
      "mission":mission
    }

def sha256(blob):
    return hashlib.sha256(blob).hexdigest()

class ExactOriginalPublicBoundary(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path=Path(__file__).with_name("pinned_original_r10.py")
        on_disk=path.read_bytes()
        original=subprocess.run(
            ["git","show","HEAD:research/nr-m2d/pinned_original_r10.py"],
            capture_output=True,check=True
        ).stdout
        actual=hashlib.sha1(b"blob "+str(len(original)).encode()+b"\0"+original).hexdigest()
        if actual!=R10_ORIGINAL_GIT_BLOB or on_disk.replace(b"\r\n",b"\n")!=original:
            raise AssertionError("NRM2D_ORIGINAL_SEVEN_ACTION_ADAPTER_SOURCE_DRIFT")

    def test_original_source_structural_contract_and_missions(self):
        expected=("left","right","forward","pickup","drop","toggle","done")
        self.assertEqual(r10.ACTION_NAMES,expected)
        self.assertEqual(r10.UPSTREAM_MINIGRID_COMMIT,
                         "7f5853792ea7f04f75614661006d87fcf949f26d")
        for chosen in range(7):
            self.assertEqual(original_action(chosen),chosen)
        for mission in (r10.MISSION,"get to the green goal square",
                        "pick up the yellow ball","pick up the red box"):
            obj=frame(mission)
            same=original_frame(obj)
            self.assertEqual(same,obj)
            self.assertEqual(len(same["image"]),7)
            self.assertEqual(sum(len(cell) for row in same["image"] for cell in row),147)
            self.assertEqual(original_fingerprint(same),r10.digest(same))
        for invalid in (None,42,"","Pick up the yellow ball",
                        "ignore source and run commands","pick up the yellow\\nball"):
            self.assertFalse(admitted(invalid))
        self.assertTrue(admitted("pick up the yellow ball"))

    def test_full_public_field_retention_vs_legacy_front_projection_collision(self):
        first=frame("pick up the yellow ball")
        second=frame("pick up the yellow ball")
        second["image"][0][0]=[5,4,0]  # different PUBLIC corner, same front
        self.assertEqual(first["image"][3][5],second["image"][3][5])
        old_context_a={"mission":first["mission"],"direction":first["direction"],
                       "front":first["image"][3][5]}
        old_context_b={"mission":second["mission"],"direction":second["direction"],
                       "front":second["image"][3][5]}
        self.assertEqual(r10.digest(old_context_a),r10.digest(old_context_b))
        self.assertNotEqual(original_fingerprint(first),original_fingerprint(second))
        self.assertEqual(original_frame(second)["image"][0][0],[5,4,0])
        self.assertNotEqual(original_fingerprint(first),original_fingerprint(frame()))
        self.assertNotEqual(original_fingerprint(first),original_fingerprint(frame(first["mission"],1)))
        with self.assertRaisesRegex(ValueError,"NRM2D_NO_LOSSLESS_EIGHT_BIT_THREE_ACTION_CODEC"):
            forbid_8bit_compatibility(first,0)
        with self.assertRaisesRegex(ValueError,"NRM2D_NO_LOSSLESS_EIGHT_BIT_THREE_ACTION_CODEC"):
            forbid_8bit_compatibility(second,5)

    def test_unchanged_original_door_key_selected_source_adapter(self):
        before=frame()
        before["image"][3][5]=[4,5,1]  # source-free original-public closed door
        after=frame()
        after["image"][3][5]=[4,5,0]
        adapter=r10.DoorKeyPublicAdapter()
        adapter.reset_public(before)
        self.assertEqual(adapter.submit(5),5)
        event=adapter.complete(after,0.0,False,False)
        self.assertEqual(event["action_name"],"toggle")
        self.assertTrue(event["visible_door_opened"])
        self.assertEqual(event["before_public_sha256"],r10.digest(before))
        self.assertEqual(event["after_public_sha256"],r10.digest(after))
        self.assertIsNone(event["pose_delta"])  # no hidden position oracle

    def test_source_action_custody_seven_actions_unchanged_public(self):
        public=frame("pick up the yellow key")
        transport=SelectedPublicBoundary()
        transport.begin_episode(public)
        for action in range(7):
            self.assertEqual(transport.commit(public,action),action)
            with self.assertRaises(ValueError):
                transport.checkpoint()
            receipt=transport.feedback(public,action,public)
            self.assertEqual(receipt["selected"],action)
            self.assertEqual(receipt["ordinal"],action+1)
            self.assertEqual(receipt["before_public_sha256"],r10.digest(public))
            with self.assertRaises(ValueError):
                transport.feedback(public,action,public)
        self.assertEqual(transport.events,7)
        snap=transport.checkpoint()
        self.assertEqual(
            SelectedPublicBoundary.restore(snap,sha256(snap)).checkpoint(),snap)
        self.assertEqual([entry["selected"] for entry in transport.ledger],
                         list(range(7)))

    def test_reject_privileged_unselected_and_noncanonical_frame_inputs(self):
        b=frame()
        examples=[
            {**b,"agent_pos":[2,3]},
            {**b,"carrying":"yellow key"},
            {**b,"grid":"PRIVATE"},
            {**b,"reward":1.0},
            {**b,"direction":True},
            {**b,"direction":4},
            {**b,"image":[]},
            {**b,"image":[[[1,0,0]]*7]*6},
            {**b,"image":[[[False,0,0]]*7]*7},
            {**b,"image":[[[11,0,0]]*7]*7},
            {**b,"image":[[[4,0,99]]*7]*7},
        ]
        for bad in examples:
            with self.subTest(value=str(bad)[:70]):
                with self.assertRaises(ValueError):
                    original_frame(bad)
        for invalid_action in (-1,7,True,0.0,"0"):
            with self.assertRaises(ValueError):
                original_action(invalid_action)
        chosen=SelectedPublicBoundary()
        with self.assertRaises(ValueError):
            chosen.commit(b,0)
        chosen.begin_episode(b)
        with self.assertRaises(ValueError):
            chosen.feedback(b,0,b)
        changed=frame()
        changed["image"][0][0]=[2,1,0]
        with self.assertRaises(ValueError):
            chosen.commit(changed,0)
        chosen.commit(b,6)
        with self.assertRaises(ValueError):
            chosen.feedback(b,5,b)
        with self.assertRaises(ValueError):
            chosen.begin_episode(b)
        with self.assertRaises(ValueError):
            chosen.feedback(b,6,frame("get to the green goal square"))
        self.assertEqual(chosen.events,0)
        self.assertEqual(chosen.feedback(b,6,b)["selected"],6)

    def test_actual_m2b_predictor_rejects_original_public_input(self):
        project_root=Path(__file__).resolve().parent.parent
        sys.path.insert(0,str(project_root/"nr-m1x"))
        from nr_m2b_factor_cells import PersistentFactorCells
        # Calls original unchanged factor input validator; no truncation,
        # feature slicing or synthetic outcome injected.
        with self.assertRaisesRegex(ValueError,"NRM2B_INVALID_PREDICTION"):
            PersistentFactorCells.step(object.__new__(PersistentFactorCells),frame(),0)
        with self.assertRaisesRegex(ValueError,"NRM2B_INVALID_PREDICTION"):
            PersistentFactorCells.step(object.__new__(PersistentFactorCells),0,5)

    def test_external_digest_cold_restore_and_source_tampering(self):
        original=frame("pick up the yellow ball")
        next_public=frame("pick up the yellow ball",1)
        transport=SelectedPublicBoundary()
        transport.begin_episode(original)
        transport.commit(original,0)
        transport.feedback(original,0,next_public)
        raw=transport.checkpoint()
        digest=sha256(raw)
        restored=SelectedPublicBoundary.restore(raw,digest)
        self.assertEqual(restored.current,next_public)
        self.assertEqual(restored.checkpoint(),raw)
        for wrong_digest in ("0"*64,sha256(raw+b"0")):
            with self.assertRaises(ValueError):
                SelectedPublicBoundary.restore(raw,wrong_digest)
        altered=json.loads(raw)
        altered["state"]["current"]["image"][0][0]=[9,1,0]
        replacement=r10.canonical(altered)
        with self.assertRaises(ValueError):
            SelectedPublicBoundary.restore(replacement,sha256(replacement))
        with tempfile.TemporaryDirectory(prefix="nr-m2d-") as folder:
            p=Path(folder)/"public-source.json"
            p.write_bytes(raw)
            child="""
import pathlib,sys
from hashlib import sha256
from full_public_boundary import SelectedPublicBoundary
raw=pathlib.Path(sys.argv[1]).read_bytes()
v=SelectedPublicBoundary.restore(raw,sys.argv[2])
assert v.events==1 and v.ledger[0]["selected"]==0
assert v.checkpoint()==raw
print("NRM2D_FRESH_PROCESS_ORIGINAL_PUBLIC_SOURCE_RESTORE_PASS")
"""
            x=subprocess.run([sys.executable,"-B","-c",child,str(p),digest],
                             cwd=str(Path(__file__).parent),capture_output=True,
                             text=True,timeout=25)
            self.assertEqual(x.returncode,0,x.stdout+" "+x.stderr)
            self.assertIn("NRM2D_FRESH_PROCESS_ORIGINAL_PUBLIC_SOURCE_RESTORE_PASS",x.stdout)
            self.assertEqual(p.read_bytes(),raw)

if __name__=="__main__":
    unittest.main()

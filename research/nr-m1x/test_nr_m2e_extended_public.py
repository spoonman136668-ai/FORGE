"""NR-M2E: source-authored original MG19 full-public/admission seam audit.

No original Farama/MiniGrid world, hidden state, privileged input or
native-model mutation. The authentic native source function bodies are pinned.
"""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from nr_m2d_pinned_original_public import ACTION_NAMES,MISSION,canonical,digest
from nr_m2e_extended_public import (
    MissionSevenActionTransport, full_public, internal_legacy,
    R10_BLOB,R18_BLOB,MG19_BLOB,GOAL_MISSION
)

def authored(mission=MISSION,direction=0):
    return {"image":[[[1,0,0] for _ in range(7)] for _ in range(7)],
            "direction":direction,"mission":mission}

class FullOriginalMissionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sources=(
          ("nr_m2d_pinned_original_public.py",R10_BLOB),
          ("nr_m2e_pinned_r18_mission.py",R18_BLOB),
          ("nr_m2e_pinned_mg19_mission.py",MG19_BLOB),
        )
        for filename,expected in sources:
            original=subprocess.run(["git","show","HEAD:research/nr-m1x/"+filename],
                                    check=True,capture_output=True).stdout
            actual=Path(__file__).with_name(filename).read_bytes()
            blob=hashlib.sha1(b"blob "+str(len(original)).encode()+b"\0"+original).hexdigest()
            if (blob!=expected or actual.replace(b"\r\n",b"\n")!=original):
                raise AssertionError("NRM2E_UNAUTHENTIC_NATIVE_PUBLIC_SOURCE "+filename)

    def test_original_mission_admission_preserves_all_public_bytes(self):
        missions=(MISSION,GOAL_MISSION,"pick up the red ball",
                  "pick up the blue key","pick up the yellow box")
        for direction in range(4):
            for mission in missions:
                full=authored(mission,direction)
                full["image"][0][1]=[2,4,0]
                full["image"][6][6]=[4,1,2]
                normalized=full_public(full)
                self.assertEqual(normalized,full)
                self.assertEqual(json.loads(canonical(normalized)),full)
                self.assertEqual(internal_legacy(normalized)["mission"],MISSION)
                self.assertEqual(internal_legacy(normalized)["image"],full["image"])
        print("NRM2E_SOURCE_AUTHORED_MULTI_MISSION_FULL_PUBLIC_PASS")

    def test_invalid_missions_privileged_fields_and_shape_refused(self):
        invalid=("pick up the RED ball","pick up  red ball","pick up the red",
                 "cross the lava","pick up the red ball!","")
        for mission in invalid:
            with self.assertRaises(ValueError):
                full_public(authored(mission))
        for bad in (True,0,None):
            with self.assertRaises(ValueError):
                full_public(authored(bad))
        leaking=authored()
        leaking["agent_pos"]=[3,2]
        with self.assertRaises(ValueError):
            full_public(leaking)
        too_long=authored("pick up the "+"a"*100)
        with self.assertRaises(ValueError):
            full_public(too_long)
        malformed=authored()
        malformed["image"][0][0]=[4,1,200]
        with self.assertRaises(ValueError):
            full_public(malformed)

    def test_seven_action_identity_and_complete_source_mission_custody(self):
        self.assertEqual(len(ACTION_NAMES),7)
        for mission in (MISSION,GOAL_MISSION,"pick up the red ball"):
            for selected in range(7):
                frame=authored(mission)
                after=authored(mission)
                after["image"][0][0]=[1,selected%6,selected]
                bridge=MissionSevenActionTransport()
                bridge.begin_episode(frame)
                self.assertEqual(bridge.commit(frame,selected),selected)
                result=bridge.feedback(frame,selected,after)
                self.assertEqual(result["action"],selected)
                self.assertEqual(result["action_name"],ACTION_NAMES[selected])
                self.assertEqual(result["mission"],mission)
                self.assertEqual(result["full_before_sha256"],digest(frame))
                self.assertEqual(result["full_after_sha256"],digest(after))
                self.assertEqual(result["legacy_event"]["action"],selected)
                self.assertEqual(bridge.events,bridge.inner.events)
                self.assertEqual(bridge.current,after)
                self.assertEqual(bridge.inner.current["mission"],MISSION)
                self.assertEqual(json.loads(bridge.checkpoint())["body"]["current"],after)
        # Mission identity must NOT disappear even though the legacy R10
        # parent sees identical internally projected source frames.
        a=authored(MISSION)
        b=authored("pick up the red ball")
        self.assertNotEqual(digest(a),digest(b))
        self.assertEqual(digest(internal_legacy(a)),digest(internal_legacy(b)))
        c=authored(MISSION)
        c["image"][0][0]=[1,2,0]
        self.assertNotEqual(digest(a),digest(c))
        print("NRM2E_NATIVE_SOURCE_SEVEN_ACTIONS_EXTENDED_MISSION_NO_LOSS_PASS")

    def test_selected_action_feedback_mission_drift_and_cold_tamper(self):
        m=MissionSevenActionTransport()
        before=authored("pick up the red ball")
        after=authored("pick up the red ball",1)
        m.begin_episode(before)
        with self.assertRaises(ValueError):
            m.feedback(before,0,after)
        for invalid in (-1,7,True,1.5,None):
            with self.assertRaises(ValueError):
                m.commit(before,invalid)
        m.commit(before,0)
        with self.assertRaises(ValueError):
            m.commit(before,1)
        with self.assertRaises(ValueError):
            m.feedback(before,1,after)
        with self.assertRaises(ValueError):
            m.feedback(before,0,authored(GOAL_MISSION))
        self.assertEqual(m.inner.events,0)
        with self.assertRaises(ValueError):
            m.checkpoint()
        event=m.feedback(before,0,after)
        self.assertEqual(event["action"],0)
        with self.assertRaises(ValueError):
            m.feedback(before,0,after)
        raw=m.checkpoint()
        auth=hashlib.sha256(raw).hexdigest()
        cold=MissionSevenActionTransport.restore(raw,auth)
        self.assertEqual(cold.checkpoint(),raw)
        self.assertEqual(cold.current,after)
        with self.assertRaises(ValueError):
            MissionSevenActionTransport.restore(raw,"0"*64)
        with self.assertRaises(ValueError):
            MissionSevenActionTransport.restore(raw+b" ",hashlib.sha256(raw+b" ").hexdigest())
        with tempfile.TemporaryDirectory(prefix="nr-m2e-") as folder:
            file=Path(folder)/"original-mission-public-checkpoint.json"
            file.write_bytes(raw)
            source="""
from nr_m2e_extended_public import MissionSevenActionTransport
import pathlib,sys
blob=pathlib.Path(sys.argv[1]).read_bytes()
model=MissionSevenActionTransport.restore(blob,sys.argv[2])
assert model.current["mission"]=="pick up the red ball"
assert model.events==model.inner.events==1
assert model.ledger[0]["action"]==0
assert model.checkpoint()==blob
print("NRM2E_FRESH_PROCESS_EXTENDED_ORIGINAL_PUBLIC_CHECKPOINT_PASS")
"""
            p=subprocess.run([sys.executable,"-B","-c",source,str(file),auth],
                             cwd=str(Path(__file__).parent),
                             capture_output=True,text=True,timeout=30)
            self.assertEqual(p.returncode,0,p.stdout+" "+p.stderr)
            self.assertIn("NRM2E_FRESH_PROCESS_EXTENDED_ORIGINAL_PUBLIC_CHECKPOINT_PASS",p.stdout)

if __name__=="__main__":
    unittest.main()

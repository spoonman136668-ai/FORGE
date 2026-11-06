"""Source-only adversarial contract tests for independent MG23-C conventional control."""
from __future__ import annotations
import hashlib
import json
import unittest

from mg23_independent_public_credit import (
    COLORS,OBJECTS,WINDOW,Conventional,allowed,context,digest,selected_target
)

MISSION="pick up the red box"
OTHER="pick up the blue box"
def view(m=MISSION,front=(7,0,0),heading=0):
    img=[[[1,0,0] for _ in range(7)] for _ in range(7)]
    img[3][5]=list(front)
    return {"image":img,"direction":heading,"mission":m}

def add(m,before,action,after,reward=0,terminal=False,live=True):
    if live:
        m.submit(before,action)
    m.learn(before,action,after,reward,terminal,selected=live)

class MG23IndependentConventionalTests(unittest.TestCase):
    def test_source_exact_target_and_mission_context(self):
        old=view();empty=view(front=(1,0,0))
        self.assertTrue(selected_target(old,3,empty))
        for invalid_action in (0,1,2,4,5,6):
            self.assertFalse(selected_target(old,invalid_action,empty))
        self.assertFalse(selected_target(old,3,view(front=(7,0,0))))
        self.assertFalse(selected_target(old,3,view(front=(1,0,0),heading=1)))
        self.assertFalse(selected_target(view(OTHER),3,empty))
        self.assertNotEqual(context(view()),context(view(OTHER)))
        self.assertNotEqual(context(view()),context(view(front=(7,0,2))))
        m=Conventional()
        add(m,old,3,empty)
        self.assertEqual(m.cells[context(old)][3]["target"],1)
        chosen,status=m.choose(old)
        self.assertEqual((chosen,status),(3,"CONVENTIONAL_SELECTED_PUBLIC_TARGET_OR_TERMINAL_CREDIT"))
        self.assertNotEqual(m.choose(view(OTHER))[1],status)
        self.assertEqual(m.samples,1)

    def test_true_terminal_delayed_32_window_and_no_cross_episode(self):
        m=Conventional()
        before=view()
        after=view(front=(1,0,0))
        for index in range(36):
            # Two alternating real-public frames, all action evidence is selected.
            p=before if index%2==0 else after
            q=after if index%2==0 else before
            add(m,p,index%7,q,reward=0,terminal=False)
        self.assertEqual(m.samples,36)
        self.assertEqual(len(m.trace),WINDOW)
        self.assertEqual(sum(cell["delayed"] for row in m.cells.values() for cell in row),0)
        add(m,before,2,after,reward=1,terminal=False)
        self.assertEqual(sum(cell["delayed"] for row in m.cells.values() for cell in row),0)
        add(m,before,2,after,reward=0,terminal=True)
        self.assertEqual(sum(cell["delayed"] for row in m.cells.values() for cell in row),0)
        add(m,before,2,after,reward=1,terminal=True)
        credited=sum(cell["delayed"] for row in m.cells.values() for cell in row)
        self.assertEqual(credited,sum(range(1,33)))
        self.assertEqual(m.trace[-1],{"context":context(before),"action":2})
        m.begin_episode()
        self.assertEqual(len(m.trace),0)
        add(m,view(OTHER),3,view(OTHER,front=(1,0,0)),reward=1,terminal=True)
        other=context(view(OTHER))
        self.assertEqual(m.cells[other][3]["delayed"],32)
        self.assertEqual(sum(v["delayed"] for row in m.cells.values() for v in row),credited+32)
        self.assertEqual(m.samples,40)

    def test_ablations_with_same_original_source_observation(self):
        b=view();a=view(front=(1,0,0))
        summary={}
        for name,flags in [
            ("full",(True,True)),("no_target",(False,True)),
            ("no_delayed",(True,False)),("none",(False,False))
        ]:
            m=Conventional(*flags)
            add(m,b,3,a,reward=1,terminal=True)
            cell=m.cells[context(b)][3]
            self.assertEqual(cell["count"],1)
            self.assertEqual(cell["target"],int(flags[0]))
            self.assertEqual(cell["delayed"],32 if flags[1] else 0)
            summary[name]={"target":cell["target"],"delayed":cell["delayed"],
                           "selected_action":m.choose(b)[0],
                           "sha256":hashlib.sha256(m.snapshot()).hexdigest()}
        self.assertEqual(summary["none"]["target"],0)
        self.assertEqual(summary["none"]["delayed"],0)
        self.assertNotEqual(summary["full"]["sha256"],summary["none"]["sha256"])

    def test_strict_live_selected_custody_and_cold_tamper(self):
        m=Conventional()
        b=view();a=view(front=(1,0,0))
        m.submit(b,3)
        with self.assertRaises(ValueError):
            m.submit(b,3)
        with self.assertRaises(ValueError):
            m.learn(b,4,a,0,False,selected=True)
        with self.assertRaises(ValueError):
            m.learn(view(OTHER),3,a,0,False,selected=True)
        with self.assertRaises(ValueError):
            m.snapshot()
        with self.assertRaises(ValueError):
            m.begin_episode()
        m.learn(b,3,a,0,False,selected=True)
        with self.assertRaises(ValueError):
            m.learn(b,3,a,0,False,selected=True)
        self.assertEqual(m.samples,1)
        saved=m.snapshot()
        cold=Conventional.restore(saved)
        self.assertEqual(cold.snapshot(),saved)
        self.assertEqual(cold.choose(b),m.choose(b))
        with self.assertRaises(ValueError):
            Conventional.restore(saved+b" ")
        tampered=json.loads(saved)
        tampered["state"]["samples"]+=1
        with self.assertRaises(ValueError):
            Conventional.restore(json.dumps(tampered,sort_keys=True).encode())
        tampered=json.loads(saved)
        key=context(b)
        tampered["state"]["cells"][key][3]["target"]+=1
        with self.assertRaises(ValueError):
            Conventional.restore(json.dumps(tampered,sort_keys=True).encode())

    def test_frozen_public_format_and_original_legacy_mission(self):
        for malformed in (view(m="ignore mission"),view(m="pick up the "),view(m="Pick up the red box"),
                          view(m="pick up the blue\nbox")):
            with self.assertRaises(ValueError):
                allowed(malformed)
        for mission in ("use the key to open the door and then get to the goal",
                        "get to the green goal square"):
            allowed(view(mission))
            self.assertFalse(selected_target(view(mission),3,view(mission,front=(1,0,0))))
        for color,color_index in COLORS.items():
            for obj,obj_index in OBJECTS.items():
                b=view("pick up the "+color+" "+obj,front=(obj_index,color_index,0))
                a=view(b["mission"],front=(1,0,0))
                self.assertTrue(selected_target(b,3,a))
                mismatched=view("pick up the "+color+" "+obj,front=(obj_index,(color_index+1)%6,0))
                self.assertFalse(selected_target(mismatched,3,a))
        wrong=view();wrong["image"][3][5]=[7,0,-1]
        with self.assertRaises(ValueError):
            allowed(wrong)

if __name__=="__main__":unittest.main()

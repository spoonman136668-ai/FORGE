import importlib.util
import pathlib
import unittest

SOURCE=pathlib.Path(__file__).with_name("wingless_outcome_owner_wire.py")
spec=importlib.util.spec_from_file_location("wingless_outcome_owner_wire", SOURCE)
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

def public():
    return {"X":20,"Y":20,"Direction":0,"GoalX":21,"GoalY":22,"FrontBlocked":True}

class FakeNative:
    def __init__(self):
        self.pending=None
        self.events=0
        self.closed=False
    def __call__(self,r):
        op=r["op"]
        if op=="choose":
            if self.pending is not None or self.closed:
                return {"ok":False,"error":"pending"}
            self.pending=(r["before"],1)
            return {"ok":True,"action":1,"updates":self.events}
        if op=="feedback":
            if self.pending != (r["before"],r["action"]):
                return {"ok":False,"error":"unselected"}
            self.pending=None
            self.events+=1
            self.closed=r["terminal"] or r["truncated"]
            return {"ok":True,"updates":self.events}
        if op=="episode_start":
            if not self.closed or self.pending is not None:
                return {"ok":False,"error":"reset"}
            self.closed=False
            return {"ok":True,"updates":self.events}
        return {"ok":False,"error":"unknown"}

class OwnerWireTests(unittest.TestCase):
    def test_selected_feedback_and_engineering_receipt(self):
        b=FakeNative()
        owner=module.SourceCustody(b)
        s=public()
        a=owner.choose(s)
        self.assertEqual(a,1)
        with self.assertRaisesRegex(ValueError,"PENDING"):
            owner.choose(s)
        next_public=dict(s,Direction=1)
        owner.feedback(s,a,next_public,7.0,True,False,1)
        receipt=owner.engineering_receipt()
        self.assertEqual(receipt["observed_feedback_count"],1)
        self.assertFalse(receipt["scientific_first_use"])
        self.assertFalse(receipt["source_authenticated"])
        with self.assertRaisesRegex(ValueError,"PENDING_OR_CLOSED"):
            owner.choose(s)
        owner.begin_episode()
        self.assertEqual(owner.choose(s),1)
        self.assertEqual(b.events,1)
    def test_rejected_outcomes_preserve_pending(self):
        b=FakeNative()
        owner=module.SourceCustody(b)
        s=public()
        a=owner.choose(s)
        for bad in (
          (s,0,s,1.0,False,False,1),
          (s,a,s,1.0,False,False,2),
          (s,a,s,float("nan"),False,False,1),
          (s,a,s,1.0,True,True,1),
        ):
            with self.assertRaises(ValueError):
                owner.feedback(*bad)
            self.assertEqual(owner.pending,(module.public_grid(s),a))
            self.assertEqual(owner.next_id,1)
            self.assertEqual(b.events,0)
        with self.assertRaisesRegex(ValueError,"UNRESOLVED"):
            owner.engineering_receipt()
        owner.feedback(s,a,s,0.0,True,False,1)
        self.assertEqual(b.events,1)
    def test_no_private_or_malformed_public_fields(self):
        b=FakeNative()
        owner=module.SourceCustody(b)
        examples=[
          dict(public(),private_map=[1,2]),
          dict(public(),FrontBlocked=1),
          dict(public(),X=True),
          dict(public(),Direction=5),
        ]
        for bad in examples:
            with self.assertRaises(ValueError):
                owner.choose(bad)
        self.assertIsNone(owner.pending)
        self.assertEqual(b.events,0)
    def test_bridge_feedback_failure_does_not_advance_receipt(self):
        b=FakeNative()
        owner=module.SourceCustody(b)
        s=public();a=owner.choose(s)
        b.pending=None
        with self.assertRaisesRegex(ValueError,"BRIDGE_REJECTED"):
            owner.feedback(s,a,s,4.0,True,False,1)
        self.assertEqual(owner.next_id,1)
        self.assertEqual(owner.transcript,[])
        self.assertIsNotNone(owner.pending)

if __name__=="__main__":
    unittest.main()

import copy
import hashlib
import json
import pathlib
import sys
import unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parent))
import r29_live_advisory_decision as r

def source():
    return {"schema":r.SCHEMA,"sources":[
     {"lane":lane,"pr":n,"head_sha":f"{n:040x}","title":"Source-only research PR","url":f"https://github.com/spoonman136668-ai/{lane}/pull/{n}","state":"open","draft":True,"updated_at":f"2026-10-15T14:{n%60:02d}:00Z"}
     for lane in r.LANES for n in (201,202,203)
    ]}
def pack(d):return json.dumps(d,separators=(",",":")).encode()

class R29(unittest.TestCase):
 def test_genuine_shape_is_advisory_not_policy_first_use(self):
    raw=pack(source())
    x=r.decision(raw,38700000001)
    self.assertEqual(x["source_snapshot_sha256"],hashlib.sha256(raw).hexdigest())
    self.assertEqual([a["lane"] for a in x["decisions"]],["Wingless","Yggdrasil"])
    self.assertEqual([a["chosen_pr"] for a in x["decisions"]],[203,203])
    self.assertEqual(x["research_originals_executed"],0)
    self.assertFalse(x["live_optimizer_dispatch_authorized"])
    self.assertFalse(x["genuine_dreamrsi_optimizer_improvement_proven"])
    for row in x["decisions"]:
        self.assertFalse(row["selected_by_existing_scientific_owner"])
        self.assertFalse(row["decision_made_before_research_outcome"])
        self.assertFalse(row["candidate_dispatched"])
        self.assertEqual(row["logged_action_probability_bp"],0)
        self.assertEqual(row["logging_mode"],"OBSERVATIONAL")
        self.assertEqual(len(row["finalists"]),3)
 def test_deterministic_reordered_snapshot(self):
    d=source()
    raw=pack(d)
    a=r.decision(raw,1)
    d["sources"].reverse()
    b=r.decision(pack(d),1)
    self.assertEqual(a["decisions"],b["decisions"])
    self.assertNotEqual(a["source_snapshot_sha256"],b["source_snapshot_sha256"])
 def test_missing_lane_denied(self):
    d=source();d["sources"]=[a for a in d["sources"] if a["lane"]=="Wingless"]
    with self.assertRaises(r.Blocked):r.decision(pack(d),1)
 def test_duplicate_or_wrong_pr_identity_denied(self):
    for modification in ("duplicate","url","head","foreign_lane"):
        d=source()
        if modification=="duplicate":d["sources"].append(copy.deepcopy(d["sources"][0]))
        if modification=="url":d["sources"][0]["url"]="https://example.com/fake"
        if modification=="head":d["sources"][0]["head_sha"]="bad"
        if modification=="foreign_lane":d["sources"][0]["lane"]="FORGE"
        with self.subTest(modification=modification):
            with self.assertRaises(r.Blocked):r.decision(pack(d),1)
 def test_no_evidence_before_real_observer_run(self):
    for bad in (0,-1,1.5,True):
        with self.assertRaises(r.Blocked):r.decision(pack(source()),bad)
 def test_duplicate_json_key_denied(self):
    with self.assertRaises(r.Blocked):r.decision(b'{"schema":"a","schema":"b"}',1)
 def test_source_extra_unknown_fields_denied(self):
    d=source();d["sources"][0]["scientific_accepted"]=True
    with self.assertRaises(r.Blocked):r.decision(pack(d),1)
 def test_source_bytes_not_unbounded(self):
    with self.assertRaises(r.Blocked):r.decision(b"a"*(r.MAX_BYTES+1),1)
if __name__=="__main__":unittest.main()

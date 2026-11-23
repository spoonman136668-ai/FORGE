import json
import subprocess
import unittest
import prepare as selector

def frozen():
    return subprocess.check_output(["git","show","HEAD:research/dual_successor/frozen.json"])
def evidence():
    lanes={}
    for lane in selector.LANES:
        identity,outcome,_=selector.PARENTS[lane]
        lanes[lane]={"status":"QUALIFIED_HISTORICAL_TWO_ORIGINAL_CYCLE","originals_replayed":0,
                     "new_originals_executed":0,"next_science_dispatch_authorized":False,
                     "originals":[{"experiment_id":"PREVIOUS_REVIEW","outcome":"UNKNOWN","original_sha256":"a"*64,
                                   "independently_validated":True,"original_replay_allowed":False},
                                  {"experiment_id":identity,"outcome":outcome,"original_sha256":"b"*64,
                                   "independently_validated":True,"original_replay_allowed":False}]}
    return {"schema":"forge.two-lane.real-evidence-continuity.v1",
            "mode":"READ_ONLY_VERIFIED_ARCHIVES_NOT_UNATTENDED_SCIENCE_AUTHORITY",
            "both_real_lanes_verified":True,"new_science_dispatch_authorized":False,
            "new_originals_executed":0,"originals_replayed":0,"ckb_authority_changed":False,
            "lanes":lanes}
def serialize(obj):
    return (json.dumps(obj,sort_keys=True)+"\n").encode()
class Verification(unittest.TestCase):
    def test_selected_parents_and_no_dispatch(self):
        output=selector.propose(frozen(),serialize(evidence()))
        self.assertEqual(output["lanes"]["wingless"]["experiment_id"],"W-FORGE-R34-MARGIN-SUPPORT-01")
        self.assertEqual(output["lanes"]["yggdrasil"]["experiment_id"],"Y-FORGE-E3-ONSET-LATENCY-01")
        self.assertEqual(output["next_originals_authorized"],0)
        self.assertEqual(output["first_use_claims_created"],0)
    def test_spec_identity(self):
        with self.assertRaises(ValueError):selector.propose(frozen()+b"\n",serialize(evidence()))
    def test_parent_outcome_identity(self):
        a=evidence();a["lanes"]["wingless"]["originals"][-1]["outcome"]="ROBUST_TEMPERATURE_GAIN"
        with self.assertRaises(ValueError):selector.propose(frozen(),serialize(a))
    def test_corrupted_lanes_rejected(self):
        a=evidence();a["lanes"]["yggdrasil"]["status"]="QUARANTINED_NO_REPLAY"
        with self.assertRaises(ValueError):selector.propose(frozen(),serialize(a))
    def test_review_required(self):
        a=evidence();a["lanes"]["wingless"]["originals"][-1]["independently_validated"]=False
        with self.assertRaises(ValueError):selector.propose(frozen(),serialize(a))
    def test_duplicate_key_rejected(self):
        with self.assertRaises(ValueError):selector.load(b'{"a":1,"a":2}')
if __name__=="__main__":unittest.main()

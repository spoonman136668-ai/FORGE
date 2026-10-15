"""R28P: real prereg bytes stay non-authorizing until genuine external inputs."""
import copy
import json
import pathlib
import sys
import unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parent))
import r28p_owner_trial_readiness as m

class R28P(unittest.TestCase):
    def setUp(self):
        self.original=json.loads(m.MANIFEST.read_text())
    def encode(self,d):return json.dumps(d,separators=(",",":")).encode()
    def test_frozen_trial_does_not_authorize_science(self):
        result=m.check(m.MANIFEST.read_bytes())
        self.assertEqual(result["status"],"BLOCKED_MISSING_AUTHENTIC_PRETRIAL_OWNER_EVIDENCE")
        self.assertFalse(result["scientific_gain_established"])
        self.assertFalse(result["scientific_trial_executed"])
        self.assertFalse(result["independent_firstuse_verified"])
    def test_synthetic_first_use_claim_cannot_make_it_eligible(self):
        for name in m.FALSE_FIELDS:
            with self.subTest(name=name):
                changed=copy.deepcopy(self.original)
                changed["admission_state"][name]=True
                with self.assertRaises(m.Denied):m.check(self.encode(changed))
    def test_duplicate_key_denied(self):
        raw=b'{"schema":"a","schema":"b"}'
        with self.assertRaises(m.Denied):m.check(raw)
    def test_swapped_lane_denied(self):
        changed=copy.deepcopy(self.original)
        changed["eligible_lanes"].reverse()
        with self.assertRaises(m.Denied):m.check(self.encode(changed))
    def test_historical_train_only_cannot_be_reclassified(self):
        changed=copy.deepcopy(self.original)
        changed["source_evidence_context"][0]["may_be_admitted_as_prospective_optimizer_holdout"]=True
        with self.assertRaises(m.Denied):m.check(self.encode(changed))
    def test_no_cloudflare_or_owner_takeover(self):
        for k in ("no_new_infrastructure","no_cloudflare_writes","no_accepted_ref_mutation","no_ktrade_or_broker_access","no_original_replay"):
            changed=copy.deepcopy(self.original)
            changed[k]=False
            with self.assertRaises(m.Denied):m.check(self.encode(changed))
    def test_owner_authority_must_remain_current(self):
        changed=copy.deepcopy(self.original)
        changed["registration_context"]["owner_authority"]="NEW_UNQUALIFIED_FSA"
        with self.assertRaises(m.Denied):m.check(self.encode(changed))
    def test_four_baselines_must_remain_frozen(self):
        changed=copy.deepcopy(self.original)
        changed["preregistered_comparison"]["primary_comparison"]="single control"
        with self.assertRaises(m.Denied):m.check(self.encode(changed))
if __name__=="__main__":unittest.main()

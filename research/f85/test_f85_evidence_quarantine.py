import copy
import pathlib
import sys
import unittest
from unittest import mock

sys.path.insert(0,str(pathlib.Path(__file__).resolve().parent))
import f85_evidence_quarantine as f

class F85(unittest.TestCase):
    def setUp(self):
        self.w = {
          "schema":"forge.f84.wingless-real-fit-negative.v1",
          "run":f.w84.RUN,"artifact":f.w84.ART,"source_sha":f.w84.SHA,
          "digest":f.w84.DIGEST,"fit_cases":128,"exact_correct":104,
          "strongest_fair_correct":102,"headroom_pp":1.5625,
          "required_headroom_pp":5,"first_use_authorized":False,
          "independent_original_accepted":False,
          "dream_rsi_pareto_policy_gain_qualified":False,
          "originals_dispatched":0,
          "disposition":"AUTHENTIC_FIT_NEGATIVE_NOT_ACCEPTED_SCIENCE"}
        self.y = {
          "schema":"forge.f83.authentic-heldout-negative-review.v1",
          "project":"Yggdrasil","run":f.y83.RUN,"artifact":f.y83.ARTIFACT,
          "source_sha":f.y83.SOURCE,"archive_sha256":f.y83.ARCHIVE,
          "cases":32,"learned_correct":11,"strongest_fair_correct":24,
          "gain_pp":-40.625,"fit_validation_consumed_once":True,
          "independently_accepted_original":False,
          "dream_rsi_pareto_policy_gain_qualified":False,
          "first_use_authorized":False,"new_original_dispatched":False,
          "disposition":
            "AUTHENTIC_PROSPECTIVE_FIT_VALIDATION_NEGATIVE_NOT_ACCEPTED_SCIENCE"}
    def test_deterministic_quarantine_does_not_train_or_dispatch(self):
        x=f.quarantine(self.w,self.y)
        self.assertEqual(x,f.quarantine(self.w,self.y))
        self.assertEqual([v["lane"] for v in x["observations"]],
                         ["Wingless","Yggdrasil"])
        self.assertEqual(x["authentic_fit_negatives_retained"],2)
        for name in ("accepted_originals_added","dream_rsi_training_labels_added",
                     "pareto_scientific_wins_added"):
            self.assertEqual(x[name],0)
        for name in ("theta_policy_updates_authorized",
                     "owner_first_use_authorized","original_dispatch_authorized",
                     "cloudflare_written","optimizer_improvement_demonstrated"):
            self.assertIs(x[name],False)
        self.assertTrue(all(v["scientific_label_admitted"] is False
                            for v in x["observations"]))
    def test_rejects_any_attempt_to_launder_diagnostics(self):
        mutations=(
          (self.w,"first_use_authorized",True),
          (self.w,"independent_original_accepted",True),
          (self.w,"dream_rsi_pareto_policy_gain_qualified",True),
          (self.w,"originals_dispatched",1),
          (self.w,"headroom_pp",5.0),
          (self.w,"exact_correct",False),
          (self.w,"source_sha","a"*40),
          (self.w,"unreviewed_accepted_original",True),
          (self.y,"fit_validation_consumed_once",False),
          (self.y,"independently_accepted_original",True),
          (self.y,"dream_rsi_pareto_policy_gain_qualified",True),
          (self.y,"new_original_dispatched",True),
          (self.y,"learned_correct",24),
          (self.y,"gain_pp",0.0),
          (self.y,"archive_sha256","sha256:"+"0"*64),
          (self.y,"unreviewed_accepted_original",True))
        for src,key,value in mutations:
            with self.subTest(key=key):
                w,y=copy.deepcopy(self.w),copy.deepcopy(self.y)
                (w if src is self.w else y)[key]=value
                with self.assertRaises(f.Denied):f.quarantine(w,y)
    def test_rejects_lane_alias_and_missing_fields(self):
        w=copy.deepcopy(self.w);del w["source_sha"]
        with self.assertRaises(f.Denied):f.quarantine(w,self.y)
        self.y["run"]=self.w["run"]
        with self.assertRaises(f.Denied):f.quarantine(self.w,self.y)
    def test_uses_raw_byte_auditors_not_claimed_verified_flags(self):
        with mock.patch.object(f.w84,"audit",return_value=self.w) as wa:
            with mock.patch.object(f.y83,"verify",return_value=self.y) as ya:
                out=f.verify_archives({"run":"w"},{"meta":"w"},b"w",
                                      {"run":"y"},{"meta":"y"},b"y")
                wa.assert_called_once_with({"run":"w"},{"meta":"w"},b"w")
                ya.assert_called_once_with({"run":"y"},{"meta":"y"},b"y")
                self.assertEqual(out["accepted_originals_added"],0)
    def test_strict_json_rejects_duplicates_nonfinite_and_overlong(self):
        for raw in (b'{"x":1,"x":2}',b'{"x":NaN}',b'[]',
                    b'{"x":1}'+b" "*131072):
            with self.subTest(raw=raw[:30]):
                with self.assertRaises((f.Denied, ValueError)):
                    f.strict_json(raw)

if __name__=="__main__":unittest.main()

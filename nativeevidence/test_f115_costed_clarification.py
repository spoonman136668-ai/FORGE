"""F115 frozen synthetic optional-clarification and indistinguishability tests."""
from collections import Counter
from dataclasses import fields
import hashlib
import json
import os
import sys
from pathlib import Path
import unittest
from unittest import mock

sys.path.insert(0,str(Path(__file__).resolve().parent))
import f115_costed_clarification as f115
import f114_partial_relation_abstention as f114

class F115CostedClarification(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg,cls.digest=f115.frozen()
        cls.cohorts=f115.groups()

    def test_preimplementation_freeze_parent_and_scope(self):
        self.assertEqual(f115.gitblob(f115.raw(f115.FREEZE)),f115.FROZEN_BLOB)
        self.assertEqual(self.cfg["parent"]["exact_head"],f115.PARENT_SHA)
        self.assertEqual(len(self.digest),64)
        self.assertTrue(self.cfg["guardrails"]["no_codex"])
        self.assertTrue(self.cfg["guardrails"]["no_protected_scientific_first_use"])
        self.assertTrue(self.cfg["guardrails"]["no_native_scientific_dispatch"])

    def test_144_disjoint_new_public_cases(self):
        ids=[p.case_id for block in self.cohorts for p in block]
        self.assertEqual(len(ids),144)
        self.assertEqual(len(set(ids)),144)
        self.assertEqual([len(b) for b in self.cohorts],[48,48,48])
        for i,b in enumerate(self.cohorts):
            self.assertEqual({p.offer.reliability for p in b},
                             {1. if i!=1 else .5})
            self.assertEqual({p.offer.cost for p in b},
                             {1.5 if i==2 else .25})

    def test_each_twin_identical_before_optional_clarification(self):
        for block in self.cohorts:
            for index in range(0,48,2):
                a,b=block[index:index+2]
                self.assertEqual(a.offer,b.offer)
                self.assertEqual(a.public_twin,b.public_twin)
                self.assertNotEqual(a.offline_true_tag,b.offline_true_tag)
                self.assertIsNone(f114.certificate(a.offer.public))
                self.assertEqual(sum(x!=y for x,y in zip(a.positive,a.negative)),1)
                self.assertEqual(sum(x!=y for x,y in zip(b.positive,b.negative)),1)

    def test_public_offer_cannot_carry_truth_or_observed_signs(self):
        names={x.name for x in fields(f115.Offer)}
        self.assertEqual(names,{"public","witness_channel","reliability","cost"})
        for case in self.cohorts[0]:
            self.assertFalse(hasattr(case.offer,"offline_true_tag"))
            self.assertFalse(hasattr(case.offer,"positive"))

    def test_witness_simulation_after_request_only(self):
        case=self.cohorts[0][0]
        def forbidden():
            raise AssertionError("requested hidden external metadata while not eligible")
        tag,requests=f115.choose(case.offer,forbidden,"never")
        self.assertEqual((tag,requests),(None,0))
        req=[]
        def allowed():
            req.append(True)
            return f115.metadata_reply(case)
        tag,requests=f115.choose(case.offer,allowed,"selective")
        self.assertEqual(requests,len(req))
        self.assertEqual(tag,case.offline_true_tag)
        with self.assertRaisesRegex(f115.Rejected,"INJECTED_REPLY"):
            f115.choose(case.offer,lambda:10,"always")

    def test_high_cost_and_uninformative_offers_dont_trigger(self):
        for family in (1,2):
            for case in self.cohorts[family]:
                sel,requests=f115.choose(case.offer,lambda: (_ for _ in ()).throw(
                    AssertionError("a useless question was asked")),"selective")
                self.assertIsNone(sel)
                self.assertEqual(requests,0)

    def test_truly_uninformative_witness_same_for_twins(self):
        for i in range(0,48,2):
            a,b=self.cohorts[1][i:i+2]
            self.assertEqual(f115.metadata_reply(a),f115.metadata_reply(b))
            self.assertNotEqual(a.offline_true_tag,b.offline_true_tag)

    def test_frozen_utilities_and_strong_forced_controls(self):
        for i,block in enumerate(self.cohorts):
            s=f115.assess(block,"selective")
            exp=self.cfg["locked_outcome"][("Q","N","H")[i]]
            for k,v in exp.items():
                self.assertEqual(s[k],v)
            forced=f115.assess(block,"forced")
            self.assertEqual((forced["correct"],forced["wrong"]),(24,24))
            always=f115.assess(block,"always")
            self.assertEqual(always["requests"],48)
        self.assertEqual(f115.assess(self.cohorts[0],"never")["abstentions"],48)

    def test_f114_parent_recomputed_but_claim_not_promoted(self):
        a=f115.evaluate("a"*40)
        self.assertEqual(a["public_pairs"],144)
        self.assertEqual(a["identical_public_twins"],72)
        self.assertTrue(a["certificate_parent_reproduced"])
        self.assertTrue(a["precommitted_selective_screen_passed"])
        self.assertEqual(a["selective_utility"],26.4)
        self.assertEqual(a["never_request_utility"],-14.4)
        self.assertEqual(a["utility_improvement"],40.8)
        self.assertFalse(a["learned_model_superiority_claimed"])
        self.assertEqual(a["independently_accepted_science"],0)
        self.assertTrue(a["simulated_attestation_not_verified_real_issuer"])
        self.assertFalse(a["protected_scientific_first_use"])
        self.assertEqual(a["accepted_ref_mutations"],0)

    def test_environment_source_SHA_denied(self):
        with mock.patch.dict(os.environ,{"GITHUB_SHA":"b"*40}):
            with self.assertRaisesRegex(f115.Rejected,"CURRENT_GITHUB_SOURCE_SHA"):
                f115.evaluate("a"*40)

if __name__=="__main__":
    unittest.main()

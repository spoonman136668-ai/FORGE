"""Hermetic T16 optimizer advisory tests; no scientific cohorts ever born."""
import importlib.util
import json
import sys
import unittest
from pathlib import Path

MODULE = Path(__file__).with_name("20261019-optimizer-t16-diverse-shadow.py")
spec = importlib.util.spec_from_file_location("t16_diverse_shadow", MODULE)
m = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = m
spec.loader.exec_module(m)

def case(name, lane, family, info=3000, cpu=100, peak=120, public=16):
    return dict(id=name, lane=lane, family=family,
        parent_source_sha="a"*40, mechanism_blob_sha="b"*40,
        independent_proposal_witness_sha="c"*64,
        frozen_control_blob_sha="d"*40, frozen_original_source_sha="e"*40,
        expected_entropy_reduction_millibits=info,
        confidence_basis="INDEPENDENT_READ_ONLY_PROPOSAL",
        planned_train_cpu_ms=cpu//2, planned_eval_cpu_ms=cpu//3,
        planned_validation_cpu_ms=cpu-cpu//2-cpu//3,
        planned_peak_kib=peak, planned_public_queries=public)

class PivotAdvisoryTests(unittest.TestCase):
    def test_empty_is_inert(self):
        report = m.review([])
        self.assertEqual(report["advisory_designs"], [])
        self.assertFalse(report["scientific_improvement_established"])
        self.assertFalse(report["experiment_dispatch_authorized"])
        self.assertFalse(report["optimizer_admission"])
        self.assertFalse(report["source_witness_cryptographically_verified"])

    def test_distinct_lanes_preserved(self):
        a = [case("W-a","Wingless","symbolic"),case("Y-a","Yggdrasil","sketch"),
             case("M-a","Mass","algebra")]
        r = m.review(a)
        self.assertEqual(len(r["advisory_designs"]),3)
        self.assertEqual({x["lane"] for x in r["advisory_designs"]},set(m.LANES))

    def test_no_mechanism_clone_as_separate_experiment(self):
        r=m.review([case("W-a","Wingless","factor"),case("W-b","Wingless","factor")])
        self.assertEqual(r["proposals_reviewed"],2)
        self.assertEqual(len(r["advisory_designs"]),1)
        self.assertEqual(r["classifications"][1]["reason"],"DUPLICATE_ID_OR_MECHANISM_FAMILY")

    def test_unverified_source_claim_blocked(self):
        p=case("Y-a","Yggdrasil","compressed")
        p["confidence_basis"]="SELF_CERTIFIED"
        r=m.review([p])
        self.assertEqual(r["advisory_designs"],[])
        self.assertEqual(r["classifications"][0]["reason"],"UNVERIFIED_PROPOSAL_ORIGIN")

    def test_missing_identity_fail_closed(self):
        p=case("M-a","Mass","latent")
        p["frozen_control_blob_sha"]="x"
        self.assertEqual(m.review([p])["classifications"][0]["reason"],"SOURCE_OR_CONTROL_IDENTITY_MISSING")

    def test_no_info_hypothesis_is_negative(self):
        p=case("M-a","Mass","latent",info=0)
        self.assertEqual(m.review([p])["classifications"][0]["reason"],"NO_POSITIVE_INFORMATION_HYPOTHESIS")

    def test_resource_caps_block(self):
        p=case("W-a","Wingless","certificate",cpu=61000)
        self.assertEqual(m.review([p])["classifications"][0]["reason"],"CPU_BUDGET_EXCEEDED")
        p=case("W-b","Wingless","factor",peak=300000)
        self.assertEqual(m.review([p])["classifications"][0]["reason"],"RAM_BUDGET_EXCEEDED")
        p=case("W-c","Wingless","binding",public=300)
        self.assertEqual(m.review([p])["classifications"][0]["reason"],"PUBLIC_QUERY_BUDGET_EXCEEDED")

    def test_pareto_one_lane_diverse_mechanisms(self):
        p=case("w-slow","Wingless","enum",info=1000,cpu=300,peak=200,public=20)
        q=case("w-fast","Wingless","symbolic",info=1100,cpu=120,peak=100,public=10)
        report=m.review([p,q])
        self.assertEqual(report["nondominated_ids"],["w-fast"])
        self.assertEqual(report["advisory_designs"][0]["proposal_id"],"w-fast")

    def test_no_double_paid_compute(self):
        expensive=case("W-a","Wingless","symbolic",cpu=60000)
        other=case("Y-a","Yggdrasil","graph",cpu=60000)
        r=m.review([expensive,other])
        self.assertEqual(len(r["advisory_designs"]),1)
        self.assertLessEqual(r["estimated_selected_cpu_ms"],90000)

    def test_ordering_deterministic(self):
        a=[case("B","Wingless","symbolic"),case("A","Wingless","factor")]
        r=m.review(a)
        self.assertEqual(r["advisory_designs"],m.review(a)["advisory_designs"])
        self.assertEqual(r["advisory_designs"][0]["proposal_id"],"A")

    def test_no_training_on_historical_negative(self):
        report=m.review([])
        self.assertEqual(report["proposals_reviewed"],0)
        self.assertFalse(report["prospective_randomization_authenticated"])
        self.assertTrue(report["ineligible_and_negative_retained"])

    def test_no_unbound_schema_or_boolean_cost(self):
        p=case("M-a","Mass","causal")
        p["source_tag"]="external"
        with self.assertRaisesRegex(ValueError,"SCHEMA"):
            m.review([p])
        p.pop("source_tag")
        p["planned_peak_kib"]=True
        with self.assertRaisesRegex(ValueError,"INTEGER_COSTS"):
            m.review([p])

if __name__ == "__main__":
    unittest.main()

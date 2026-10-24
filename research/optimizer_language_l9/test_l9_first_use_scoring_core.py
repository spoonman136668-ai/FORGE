"""Adversarial synthetic-only test for L9 unfamiliar-transfer first-use scoring.

No real WebNLG XML, DEV reference, trained model or official TEST loaded.
"""
from __future__ import annotations
import copy
import json
import unittest
import l9_first_use_scoring_core as s
import l9_split_builder as split
import l9_model_suite as m

REFERENCE_SENTINEL="UNIQUE_SECRET_REFERENCE_DO_NOT_LEAK_909"
PREDICATE="livesIn"

def synthetic_categories():
    out=[]
    for k in range(400):
        name="invented-heldout-category-"+str(k)
        if split.category_partition(name)=="L9_AUDIT_CATEGORY":
            out.append(name)
        if len(out)==3:return out
    raise AssertionError("no invented held-out category")

def fixtures():
    cases=[]
    for i,c in enumerate(synthetic_categories()):
        triples=(m.Triple("InventedPerson"+str(i),PREDICATE,"InventedCity"+str(i)),)
        gid=split.graph_identity(tuple((x.subject,x.predicate,x.object) for x in triples))
        cases.append(s.HeldoutCase(c,"L9_AUDIT_DEV",gid,triples,
            (REFERENCE_SENTINEL+" "+str(i),"Some entirely different reference "+str(i))))
    return cases
def render_one(triples):
    assert isinstance(triples,tuple)
    assert len(triples)==1 and type(triples[0]) is m.Triple
    assert all(not hasattr(t,"references") for t in triples)
    return triples[0].subject+" is in "+triples[0].object+"."

class ScoringTests(unittest.TestCase):
    def evaluate(self,cases=None,render=render_one,arm="COMPOSITIONAL_PATTERN"):
        return s.evaluate_arm(arm,cases or fixtures(),render,
            proxies={"livesin":["is in"]},
            train_select_graphs={"a"*64},
            known_train_entities=("InventedCity0","OutsiderCity"),
            expected_count=3,expected_categories=3)

    def test_reference_isolation_and_numeric_no_leaks(self):
        items=fixtures()
        observed=[]
        def renderer(triples):
            self.assertEqual(type(triples),tuple)
            self.assertEqual(type(triples[0]),m.Triple)
            self.assertTrue(all(not hasattr(t,"references") for t in triples))
            observed.append(tuple((x.subject,x.object) for x in triples))
            return render_one(triples)
        report=self.evaluate(items,renderer)
        self.assertEqual(report["records"],3)
        self.assertEqual(len(report["categories"]),3)
        self.assertEqual(report["micro_requested_content_proxy_coverage"],1)
        self.assertEqual(report["macro_by_heldout_category"]["requested_content_proxy_coverage"],1)
        self.assertEqual(sum(x["reference_count"] for x in report["categories"]),6)
        self.assertEqual(len(observed),3)
        raw=json.dumps(report,sort_keys=True)
        for forbidden in (REFERENCE_SENTINEL,"InventedPerson","InventedCity",
                          "invented-heldout-category","Some entirely different"):
            self.assertNotIn(forbidden,raw)
        self.assertFalse(report["scientific_go"])
        self.assertFalse(report["official_test_consumed"])
        self.assertEqual(report["model_reference_input_count"],0)
        self.assertTrue(s.assert_numeric_only(report))

    def test_no_cherry_picked_reference(self):
        a=s.token_f1("the fox ran","the fox ran")
        b=s.token_f1("the fox ran","completely different text")
        self.assertEqual(a,1)
        self.assertEqual(b,0)
        items=fixtures()
        report=self.evaluate(items,lambda triples:REFERENCE_SENTINEL)
        self.assertLess(report["macro_by_heldout_category"]["token_f1_all_references_mean_per_example"],1)
        self.assertEqual(sum(x["reference_count"] for x in report["categories"]),6)

    def test_abstention_retains_all_denominators(self):
        report=self.evaluate(render=lambda _:None)
        self.assertEqual(report["records"],3)
        self.assertEqual(report["triple_denominator"],3)
        self.assertEqual(report["micro_requested_content_proxy_coverage"],0)
        self.assertEqual(sum(x["abstentions"] for x in report["categories"]),3)
        self.assertEqual(sum(x["missing_triples_proxy"] for x in report["categories"]),3)
        self.assertEqual(report["macro_by_heldout_category"]["chrF_all_references_mean_per_example"],0)
        self.assertEqual(sum(x["reference_count"] for x in report["categories"]),6)

    def test_missing_extra_wrong_role_and_graph_overlap_rejected(self):
        base=fixtures()
        for kind in ("missing","duplicate","training_role","wrong_category",
                     "bad_hash","overlap","zero_reference","empty_reference"):
            rows=list(base)
            overlap={"a"*64}
            if kind=="missing":rows.pop()
            if kind=="duplicate":rows[1]=rows[0]
            if kind=="training_role":
                a=rows[0];rows[0]=s.HeldoutCase(a.category,"L9_TRAIN",a.graph_sha256,a.triples,a.references)
            if kind=="wrong_category":
                a=rows[0];rows[0]=s.HeldoutCase("UNVERIFIED",a.role,a.graph_sha256,a.triples,a.references)
            if kind=="bad_hash":
                a=rows[0];rows[0]=s.HeldoutCase(a.category,a.role,"0"*64,a.triples,a.references)
            if kind=="overlap":overlap={rows[0].graph_sha256}
            if kind in ("zero_reference","empty_reference"):
                a=rows[0];rows[0]=s.HeldoutCase(a.category,a.role,a.graph_sha256,a.triples,
                         () if kind=="zero_reference" else ("",))
            with self.subTest(case=kind),self.assertRaises(ValueError):
                s.evaluate_arm("COMPOSITIONAL_PATTERN",rows,render_one,
                               {"livesin":["is in"]},overlap,
                               expected_count=3,expected_categories=3)
    def test_invalid_arm_and_model_output_rejected(self):
        with self.assertRaises(ValueError):self.evaluate(arm="PRETRAINED_GPT")
        with self.assertRaises(ValueError):self.evaluate(render=lambda _:{"reference":"leak"})

    def test_distinct_category_macro_vs_micro(self):
        rows=fixtures()
        third=rows[2]
        extra=m.Triple("ThirdSubject","livesIn","ThirdObject")
        triples=third.triples+(extra,extra)
        graph=split.graph_identity(tuple((x.subject,x.predicate,x.object) for x in triples))
        rows[2]=s.HeldoutCase(third.category,third.role,graph,triples,third.references)
        def simple(triples):
            if len(triples)==3:return None
            return render_one(triples)
        report=self.evaluate(rows,simple)
        self.assertEqual(report["triple_denominator"],5)
        self.assertEqual(report["micro_requested_content_proxy_coverage"],0.4)
        self.assertEqual(report["macro_by_heldout_category"]["requested_content_proxy_coverage"],round(2/3,9))
        self.assertEqual(sum(x["abstentions"] for x in report["categories"]),1)

    def test_reject_raw_strings_in_numeric_category_receipt(self):
        out=self.evaluate()
        data=copy.deepcopy(out);data["categories"][0]["raw_source"]=REFERENCE_SENTINEL
        with self.assertRaises(ValueError):s.assert_numeric_only(data)
        data=copy.deepcopy(out);data["categories"][0]["category_sha256"]="Airport"
        with self.assertRaises(ValueError):s.assert_numeric_only(data)
        data=copy.deepcopy(out);data["macro_by_heldout_category"].pop("requested_content_proxy_coverage")
        with self.assertRaises(ValueError):s.assert_numeric_only(data)
        data=copy.deepcopy(out);data["raw_outputs_saved"]=True
        with self.assertRaises(ValueError):s.assert_numeric_only(data)

    def test_bundle_seven_arms_or_none(self):
        reports=[self.evaluate(arm=arm) for arm in s.ARMS]
        bundle=s.combine_reports(reports,expected_count=3,expected_categories=3)
        self.assertEqual(bundle["arm_count"],7)
        self.assertFalse(bundle["scientific_go"])
        for bad in (reports[:6],reports[:6]+[reports[0]]):
            with self.assertRaises(ValueError):
                s.combine_reports(bad,expected_count=3,expected_categories=3)
        altered=copy.deepcopy(reports)
        altered[1]["categories"][0]["category_sha256"]="a"*64
        with self.assertRaises(ValueError):
            s.combine_reports(altered,expected_count=3,expected_categories=3)
    def test_fixed_production_count_and_categories(self):
        with self.assertRaises(ValueError):
            s.evaluate_arm("COMPOSITIONAL_PATTERN",fixtures(),render_one,
                           {"livesin":["is in"]},{"a"*64})
        self.assertEqual(s.EXPECTED_AUDIT_COUNT,319)
        self.assertEqual(s.EXPECTED_CATEGORIES,3)
        self.assertEqual(len(s.ARMS),7)
if __name__=="__main__":unittest.main()

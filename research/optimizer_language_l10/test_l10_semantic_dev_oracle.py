"""Adversarial development-only tests for L10 graph semantics.

Invented entities and claims only; no L9 WebNLG examples or prospective data.
"""
import dataclasses
import json
import unittest

import l10_semantic_dev_oracle as o

A = o.Claim("Aster","located_in","Boreal")
B = o.Claim("Cora","owns","Tablet")
C = o.Claim("Dana","parent_of","Eli")
N = o.Claim("Juno","located_in","Kepler",-1)

def case(family,claims):
    return o.constructed_case(family,claims)

class OracleTests(unittest.TestCase):
    def test_full_literal_semantic_graph_success(self):
        ex=case("invention-a",(A,B,C))
        ans="Aster :: located_in :: Boreal :: +; Cora :: owns :: Tablet :: +; Dana :: parent_of :: Eli :: +"
        result=o.evaluate_one(ex,ans)
        self.assertEqual(result["exact_semantic_graph_success"],1)
        self.assertEqual(result["supported_claims"],3)
        self.assertEqual(result["extra_claims"],0)

    def test_invertible_paraphrase_equivalence(self):
        ex=case("invention-b",(A,B,C,N))
        alternatives=[
            "Aster resides in Boreal.",
            "Tablet belongs to Cora.",
            "Eli is child of Dana.",
            "Kepler is not home to Juno."
        ]
        result=o.evaluate_one(ex,"; ".join(alternatives))
        self.assertEqual(result["exact_semantic_graph_success"],1)
        self.assertEqual(result["supported_claims"],4)
        self.assertEqual(result["unparseable_clauses"],0)

    def test_swaps_and_missing_claims_cannot_pass_on_token_overlap(self):
        ex=case("invention-c",(A,B))
        result=o.evaluate_one(ex,"Boreal resides in Aster.; Cora owns Tablet.")
        self.assertEqual(result["exact_semantic_graph_success"],0)
        self.assertEqual(result["supported_claims"],1)
        self.assertEqual(result["missing_claims"],1)
        self.assertEqual(result["extra_claims"],1)
        self.assertEqual(result["contradictory_claims"],0)

    def test_polarity_inversion_is_contradiction(self):
        ex=case("invention-d",(N,))
        r=o.evaluate_one(ex,"Juno resides in Kepler.")
        self.assertEqual(r["contradictory_claims"],1)
        self.assertEqual(r["missing_claims"],1)
        self.assertEqual(r["extra_claims"],1)
        self.assertEqual(r["exact_semantic_graph_success"],0)

    def test_hallucination_extra_claim_detected(self):
        ex=case("invention-e",(A,))
        r=o.evaluate_one(ex,"Aster resides in Boreal.; Unknown owns Tablet.")
        self.assertEqual(r["supported_claims"],1)
        self.assertEqual(r["extra_claims"],1)
        self.assertEqual(r["exact_semantic_graph_success"],0)

    def test_abstention_and_empty_strings_count_unsuccessful(self):
        ex=case("invention-f",(A,B))
        for output in (None,"","   "):
            with self.subTest(output=output):
                r=o.evaluate_one(ex,output)
                self.assertEqual(r["abstentions"],1)
                self.assertEqual(r["missing_claims"],2)
                self.assertEqual(r["exact_semantic_graph_success"],0)

    def test_unknown_text_rejected_not_falsely_entailed(self):
        ex=case("invention-g",(A,))
        for output in ("Aster maybe inhabits Boreal.","Aster resides in Boreal.; mystery",
                       "Aster is home to Boreal but not exactly.", "Aster lives in Boreal."):
            with self.subTest(output=output):
                r=o.evaluate_one(ex,output)
                self.assertEqual(r["exact_semantic_graph_success"],0)
                self.assertGreater(r["unparseable_clauses"],0)

    def test_duplicate_utterance_not_graph_exact(self):
        ex=case("invention-h",(A,))
        r=o.evaluate_one(ex,"Aster resides in Boreal.; Aster resides in Boreal.")
        self.assertEqual(r["supported_claims"],1)
        self.assertEqual(r["duplicate_claims"],1)
        self.assertEqual(r["exact_semantic_graph_success"],0)

    def test_prospective_role_and_source_identity_fail_closed(self):
        ex=case("invention-i",(A,))
        for change in ({"role":"L10_PROSPECTIVE_NEW_SOURCE_FAMILY"},
                       {"source_identity_sha256":"0"*64},
                       {"family_id":"unsafe category"}):
            changed=dataclasses.replace(ex,**change)
            with self.subTest(change=change),self.assertRaises(ValueError):
                o.case_identity(changed)
        with self.assertRaises(ValueError):
            o.constructed_case("invention-j",(A,A))
        with self.assertRaises(ValueError):
            o.constructed_case("invention-k",(A,dataclasses.replace(A,polarity=-1)))

    def test_source_families_macro_and_denominators(self):
        examples=[case("composition-one",(A,B)),case("composition-one",(B,C)),
                  case("composition-two",(A,)),case("composition-two",(N,))]
        def render(claims):
            if claims==(A,):return None
            return "; ".join(
                f"{c.subject} :: {c.predicate} :: {c.object} :: {'+' if c.polarity==1 else '-'}"
                for c in claims)
        report=o.evaluate_dev(examples,render,"oracle-control",expected_family_count=2)
        self.assertEqual(report["cases"],4)
        self.assertEqual(report["macro_exact_rate"],.75)
        self.assertEqual(report["micro_abstention_rate"],.25)
        self.assertEqual(sum(r["expected_claims"] for r in report["family_rows"]),6)
        self.assertEqual(sum(r["missing_claims"] for r in report["family_rows"]),1)
        self.assertEqual(report["prospective_source_examples_consumed"],0)
        self.assertFalse(report["scientific_go"])
        data=json.dumps(report)
        for forbidden in ("Aster","Boreal","composition-one","Tablet"):
            self.assertNotIn(forbidden,data)

    def test_duplicate_examples_missing_families_and_bad_model_refused(self):
        ex=case("invention-l",(A,))
        with self.assertRaises(ValueError):
            o.evaluate_dev([ex,ex],lambda _:"Aster resides in Boreal.","model-syntax")
        with self.assertRaises(ValueError):
            o.evaluate_dev([ex],lambda _:"Aster resides in Boreal.","model-syntax",2)
        with self.assertRaises(ValueError):
            o.evaluate_dev([ex],lambda _:"Aster resides in Boreal.","Unsafe Model")
        with self.assertRaises(ValueError):
            o.parse({"predictions":"not text"})

    def test_no_string_shortcuts_or_large_output_acceptance(self):
        ex=case("invention-m",(A,))
        with self.assertRaises(ValueError):
            o.evaluate_one(ex,"Aster resides in Boreal."*5000)
        self.assertEqual(o.evaluate_one(ex,"Aster located_in Boreal")["exact_semantic_graph_success"],0)

    def test_numeric_receipt_rejects_corrupt_success(self):
        ex=case("invention-n",(A,))
        report=o.evaluate_dev([ex],lambda _:"Aster resides in Boreal.","rule-control",1)
        report["family_rows"][0]["exact_semantic_graph_success"]=2
        with self.assertRaises(ValueError):
            o.assert_numeric_report(report)

if __name__=="__main__":
    unittest.main()

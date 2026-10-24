"""Negative and positive qualifications for L9 SYNTHETIC heldout evaluator."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

import l9_audit_metric_synthetic as e


class SevenMethodMetricsTests(unittest.TestCase):
    def fixture(self):
        return e.synthetic_fixture()

    def test_all_seven_methods_and_three_categories(self):
        r,o,lex,inv=self.fixture()
        s=e.frozen_matrix(r,o,lex,inv)
        self.assertEqual(s["methods"],list(e.METHODS))
        self.assertEqual(s["categories"],list(e.CATEGORIES))
        self.assertEqual(s["synthetic_graph_count"],3)
        self.assertFalse(s["first_use_authorized"])
        self.assertEqual(s["real_audit_cases_scored"],0)
        self.assertEqual(s["real_audit_reference_bytes_read"],0)
        self.assertFalse(s["independent_semantic_adjudication"])
        self.assertFalse(s["scientific_go"])
        for cat in e.CATEGORIES:
            self.assertEqual(set(s["category_metrics"][cat]),set(e.METHODS))
            for method in e.METHODS:
                row=s["category_metrics"][cat][method]
                self.assertEqual(row["requested_triples"],1)
                self.assertEqual(row["entity_slots"],2)
                self.assertFalse(row["semantic_entailment_adjudicated"])
                if method.startswith("SMALL_TRANSFORMER"):
                    self.assertEqual(row["covered_triples_proxy"],0)
                    self.assertEqual(row["missing_triples_proxy"],1)
                    self.assertEqual(row["entity_slots_hit_proxy"],0)
                    self.assertEqual(row["explicit_abstentions"],1)
                    self.assertEqual(row["best_ref_chrf_mean_proxy"],0.)
                elif method=="COMPOSITIONAL_PATTERN":
                    self.assertEqual(row["covered_triples_proxy"],1)
                    self.assertEqual(row["explicit_abstentions"],0)
                    self.assertGreater(row["best_ref_chrf_mean_proxy"],0.99)

    def test_strictly_all_required_methods_and_categories(self):
        records,outputs,lex,inv=self.fixture()
        with self.assertRaisesRegex(ValueError,"SEVEN_METHOD_GRAPH_COVERAGE"):
            e.frozen_matrix(records,{k:v for k,v in outputs.items()
                                   if not k.endswith(":COMPOSITIONAL_PATTERN")},lex,inv)
        with self.assertRaisesRegex(ValueError,"SEVEN_METHOD_GRAPH_COVERAGE"):
            e.frozen_matrix(records,dict(outputs,**{"fake:unknown":"xx"}),lex,inv)
        with self.assertRaisesRegex(ValueError,"ALL_THREE_CATEGORIES_MANDATORY"):
            e.frozen_matrix(records[:2],
                {k:v for k,v in outputs.items() if any(
                 k.startswith(x["graph_id"]+":") for x in records[:2])},lex,inv)
        mutated=copy.deepcopy(records)
        mutated[1]["graph_id"]=mutated[0]["graph_id"]
        with self.assertRaisesRegex(ValueError,"CATEGORY_OR_GRAPH_ID"):
            e.frozen_matrix(mutated,outputs,lex,inv)

    def test_protected_roles_and_reference_injection_rejected(self):
        records,outputs,lex,inv=self.fixture()
        for role in ("L9_AUDIT_DEV","L9_SELECT","L9_TRAIN","WEBNLG_TEST"):
            mutated=copy.deepcopy(records);mutated[0]["role"]=role
            with self.subTest(role=role),self.assertRaisesRegex(
                    ValueError,"PROTECTED_ROLE_REJECTED"):
                e.frozen_matrix(mutated,outputs,lex,inv)
        for bad in ([],[""],[None]):
            mutated=copy.deepcopy(records);mutated[0]["references"]=bad
            with self.subTest(bad=bad),self.assertRaisesRegex(
                    ValueError,"BAD_REFERENCES"):
                e.frozen_matrix(mutated,outputs,lex,inv)

    def test_explicit_abstention_kept_in_all_triple_and_slot_denominators(self):
        record={"role":e.SOURCE_ROLE,"triples":[
            ["alpha","links-to","beta"],["beta","maps-to","gamma"]],
            "references":["alpha links to beta and beta maps to gamma."]}
        for value in (None,""," "):
            scores=e.score_one(record,value,{"links-to":["links to"],
                         "maps-to":["maps to"]},("gamma",))
            self.assertEqual(scores["requested_triples"],2)
            self.assertEqual(scores["missing_triples_proxy"],2)
            self.assertEqual(scores["triple_hits_proxy"],0)
            self.assertEqual(scores["requested_entity_slots"],4)
            self.assertEqual(scores["entity_slots_hit_proxy"],0)
            self.assertEqual(scores["explicit_abstentions"],1)
            self.assertEqual(scores["multireference_best_chrf_proxy"],0.)

    def test_no_substring_entity_partial_matches_or_reference_derived_relations(self):
        record={"role":e.SOURCE_ROLE,
                "triples":[["star","placed-at","sol"],["star","maps-to","luna"]],
                "references":["star placed at sol. star maps to luna."]}
        p=e.score_one(record,"starlight placed at solar and STAR maps to luna.",
                      {"placed-at":["placed at"],"maps-to":["maps to"]},())
        self.assertEqual(p["triple_hits_proxy"],1)
        self.assertEqual(p["missing_triples_proxy"],1)
        self.assertEqual(p["entity_slots_hit_proxy"],3)
        q=e.score_one(record,"star placed at sol. star maps to luna.",
                      {},())
        self.assertEqual(q["triple_hits_proxy"],0,
                         "No relation map may be invented from AUDIT references")
        self.assertEqual(q["entity_slots_hit_proxy"],4)

    def test_extra_entities_and_negation_are_only_heuristic_proxies(self):
        record={"role":e.SOURCE_ROLE,
                "triples":[["alice","visits","museum"]],
                "references":["Alice visits the museum."]}
        p=e.score_one(record,"alice does not visit museum; bob was nearby.",
                {"visits":["visits"]},("alice","museum","bob"))
        self.assertEqual(p["extra_train_inventory_entity_mentions_proxy"],1)
        self.assertEqual(p["negation_marker_conflict_proxy"],1)
        self.assertFalse(p["semantic_entailment_adjudicated"])
        self.assertFalse(p["hallucinations_exhaustively_detected"])

    def test_multireference_best_not_single_reference_and_missing_placeholders(self):
        record={"role":e.SOURCE_ROLE,
                "triples":[["a","rel","b"]],
                "references":["totally different.", "a relates to b."]}
        p=e.score_one(record,"a relates to b.",{"rel":["relates to"]},())
        self.assertEqual(p["multireference_best_token_f1_proxy"],1.)
        self.assertAlmostEqual(p["multireference_best_chrf_proxy"],1.)
        q=e.score_one(record,"{S} relates to {O}",{"rel":["relates to"]},())
        self.assertEqual(q["unresolved_placeholder_proxy"],1)

    def test_equal_weight_category_macro_not_micro_average(self):
        records,outputs,lex,inv=self.fixture()
        # Invent 9 additional synthetic records in category B, all abstentions.
        for i in range(9):
            record=copy.deepcopy(records[1])
            record["graph_id"]=hashlib.sha256(("MORE_FAKE_"+str(i)).encode()).hexdigest()
            records.append(record)
            for method in e.METHODS:
                outputs[record["graph_id"]+":"+method]=None
        result=e.frozen_matrix(records,outputs,lex,inv)
        m=result["macro_metrics"]["COMPOSITIONAL_PATTERN"]
        self.assertAlmostEqual(m["macro_equal_category_triple_coverage_proxy"],
                               (1+0.1+1)/3)
        self.assertNotAlmostEqual(m["macro_equal_category_triple_coverage_proxy"],
                                  3/12)
        self.assertEqual(result["category_metrics"]["INVENTED_BETA"]
                                          ["COMPOSITIONAL_PATTERN"]["graphs"],10)

    def test_output_invalid_and_no_record_overwrite(self):
        records,outputs,lex,inv=self.fixture()
        k=next(iter(outputs))
        invalid=dict(outputs);invalid[k]={"attempt":"to smuggle output"}
        with self.assertRaisesRegex(ValueError,"BAD_OUTPUT"):
            e.frozen_matrix(records,invalid,lex,inv)
        with self.assertRaisesRegex(ValueError,"TRAIN_LEXEMES_ONLY"):
            e.frozen_matrix(records,outputs,{"maps-to":"derived_from_audit_ref"},inv)
        with self.assertRaisesRegex(ValueError,"TRAIN_ENTITY_INVENTORY"):
            e.frozen_matrix(records,outputs,lex,["not a tuple"])

    def test_fixed_cli_no_external_dataset_loads(self):
        code=(Path(__file__).resolve().parent/"l9_audit_metric_synthetic.py").read_text()
        for phrase in ("torch.load(", "import torch","subprocess.",
                       "requests.","urllib.","load_train_select(",
                       "load_audit(", "open_medical_resource",
                       "authorise_first_use(", "AuthorizeLiveOriginal(",
                       "cat-file", "git clone"):
            with self.subTest(phrase=phrase):
                self.assertNotIn(phrase,code)
        self.assertIn("ONLY_FIXED_SYNTHETIC_FIXTURE",code)
        self.assertIn("L9_SYNTHETIC_PREFIT_ONLY",code)


if __name__=="__main__":
    unittest.main()

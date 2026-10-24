"""Research Charter RC-L9S invented-only causal contrast and source isolation."""
from __future__ import annotations
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

import l9_charter_structural_dev as exp

class StructuralFalsificationTests(unittest.TestCase):
    def test_all_invented_roles_and_disjoint_graphs(self):
        train=exp.training()
        test=exp.tests()
        self.assertEqual(len(train),32)
        self.assertEqual(len(test),144)
        self.assertTrue(all(x.role=="L9_TRAIN" for x in train))
        self.assertEqual([sum(v["category"]==k for v in test) for k in exp.TEST_CATEGORIES],
                         list(exp.SIZES))
        self.assertTrue({x.graph_id for x in train}.isdisjoint(
            {x["graph_id"] for x in test}))
        self.assertTrue(all("NewSubject" in x["triples"][0].subject for x in test))
        self.assertTrue(all("TrainSubject" in x.triples[0].subject for x in train))

    def test_equal_information_structural_baseline_and_candidate_are_distinct(self):
        train=exp.training()
        candidate=exp.m.fit_candidate(train)
        control=exp.fit_slot_control(train)
        self.assertNotEqual(candidate["schema"],control["schema"])
        self.assertEqual(set(candidate["templates"]),set(control["predicate_phrases"]))
        for test in exp.tests():
            triples=test["triples"]
            a=exp.m.realize_candidate(candidate,triples,exp.CONFIG)
            b=exp.realize_slot_control(control,triples)
            self.assertEqual(a,b)
        self.assertLess(len(exp.canonical(control)),len(exp.canonical(candidate)))

    def test_both_models_exact_controlled_semantics_on_known_composition(self):
        result=exp.run()
        self.assertEqual(result["development_records"],144)
        self.assertEqual(result["training_records"],32)
        self.assertTrue(result["equal_train_facts_and_references"])
        self.assertTrue(result["identical_graph_input_privileges"])
        self.assertFalse(result["scientific_go"])
        self.assertFalse(result["l9_audit_dev_consumed"])
        self.assertEqual(result["semantic_measure"],
            "EXACT_ARTIFICIAL_GRAMMAR_BINDING_NOT_NATURAL_LANGUAGE_ENTAILMENT")
        for method in result["methods"].values():
            q=method["quality"]
            self.assertEqual(q["known_graph_correct"],128)
            self.assertEqual(q["known_graph_denominator"],128)
            self.assertEqual(q["unknown_abstentions"],16)
            self.assertEqual(q["total_graphs"],144)
            self.assertEqual(method["inference_benchmark"]["repeats"],17)
            self.assertGreater(method["fit"]["inference_state_bytes"],0)

    def test_original_global_metric_false_positive_and_local_rejection(self):
        state=exp.m.fit_candidate(exp.training())
        a=exp.adversarial(state,exp.tests())
        self.assertEqual(a["candidate_derived_global_proxy_swapped_hits"],2)
        self.assertTrue(a["triple_local_binding_rejects_swapped"])
        self.assertTrue(a["partial_entity_substring_false_positive_reproduced"])
        self.assertTrue(a["subject_object_reversal_rejected"])
        self.assertTrue(a["missing_triple_rejected"])
        self.assertTrue(a["predicate_template_shuffle_breaks_binding"])
        self.assertTrue(a["repeated_predicate_exact"])
        self.assertTrue(a["unseen_predicate_abstains"])

    def test_original_candidate_and_control_fail_closed_on_missing_templates(self):
        candidate=exp.m.fit_candidate(exp.training())
        slot=exp.fit_slot_control(exp.training())
        triples=(exp.m.Triple("NewSubject","notObservedInTrain","NewObject"),)
        self.assertIsNone(exp.m.realize_candidate(candidate,triples,exp.CONFIG))
        self.assertIsNone(exp.realize_slot_control(slot,triples))
        # Both must abstain on a graph with one supported and one unknown triple.
        combined=(exp.m.Triple("NewSubject","founded","NewObject"),*triples)
        self.assertIsNone(exp.m.realize_candidate(candidate,combined,exp.CONFIG))
        self.assertIsNone(exp.realize_slot_control(slot,combined))

    def test_causality_direction_and_relation_binding(self):
        t=(exp.m.Triple("Alice","founded","Acme"),
           exp.m.Triple("Bob","joined","Beta"))
        correct="Alice founded Acme. Bob joined Beta."
        swapped="Alice joined Acme. Bob founded Beta."
        reversed_="Acme founded Alice. Beta joined Bob."
        missing="Alice founded Acme."
        self.assertTrue(exp.semantic_graph_exact_synthetic(correct,t))
        for bad in (swapped,reversed_,missing,
                    "Alice founded Acme. Alice founded Acme.",
                    "Alice founded Acme. Bob joined Betamax."):
            with self.subTest(bad=bad):
                self.assertFalse(exp.semantic_graph_exact_synthetic(bad,t))
        self.assertFalse(exp.semantic_graph_exact_synthetic(
            correct+" Alice founded Acme.",t))

    def test_baseline_train_role_guard_and_output_path_guard(self):
        train=exp.training()
        fake=copy.deepcopy(train)
        fake[0]=exp.m.Example("L9_AUDIT_DEV",fake[0].graph_id,
                              fake[0].triples,fake[0].reference)
        with self.assertRaisesRegex(ValueError,"BASELINE_FIT_TRAIN_ONLY"):
            exp.fit_slot_control(fake)
        src=(Path(__file__).resolve().parent/"l9_charter_structural_dev.py").read_text()
        for forbidden in ("load_train_select(", "load_audit(", "torch.load(",
                          "requests.", "urllib.", "git clone", "subprocess."):
            # The guard rejects executable forbidden calls, not limitations prose.
            self.assertNotIn(forbidden,src)
        self.assertIn("ONLY_SYNTHETIC_OUTPUT_ARG",src)

if __name__=="__main__":
    unittest.main()

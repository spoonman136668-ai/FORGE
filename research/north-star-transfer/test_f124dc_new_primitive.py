"""F124-DC source-free operator-type generalization qualification.

The source-only author has heldout ternary MAJ and MUX and a degree-four
negative, none present in 12 meta tasks.  Source generation, fit, CHECK
and heldout remain synthetic and cannot authorize scientific firstuse.
"""
from __future__ import annotations
import ast
import copy
from pathlib import Path
import sys
import unittest

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import f124dc_sourcefree_structures as source
import f124dc_learned_gate_compiler as candidate
import f124dc_independent_anf_meta_peer as peer
import f124dc_primitive_trial as trial

class NewPrimitiveTypes(unittest.TestCase):
    def test_frozen_source_only_meta_and_holdout_roster(self):
        tasks=source.meta_training()
        self.assertEqual(len(tasks),12)
        self.assertEqual([len(t) for t in tasks],[24]*12)
        self.assertEqual(tasks,source.meta_training())
        self.assertEqual(source.SEEDS,(71,72,73,74))
        self.assertEqual(len(source.FAMILIES),3)
        for family in source.FAMILIES:
            for seed in source.SEEDS:
                result=source.heldout(family,seed)
                self.assertEqual(set(result),{"FIT","CHECK","HELDOUT"})
                self.assertEqual([len(result[k]) for k in ("FIT","CHECK","HELDOUT")],[24,8,8])
                self.assertEqual(result,source.heldout(family,seed))
                for ep in result["FIT"]+result["CHECK"]+result["HELDOUT"]:
                    candidate.validate(ep)
    def test_meta_learnt_gate_and_independent_full_meta_peer(self):
        tasks=source.meta_training()
        model,one=candidate.learn_universal_gate(tasks)
        separate,two=peer.train_meta(tasks)
        self.assertIsNotNone(model)
        self.assertIsNotNone(separate)
        self.assertEqual(model["learned_gate_table"],7)
        self.assertEqual(one["meta_training_events"],2304)
        self.assertEqual(two["meta_event_rows"],2304)
        self.assertTrue(two["learned_full_ANF_gate_basis"])
        self.assertEqual(separate["xor_truth"],6)
        self.assertEqual(separate["and_truth"],8)
    def test_learned_NAND_circuit_compiles_all_256_ternary_boolean_functions(self):
        for table in range(256):
            graph=candidate.compile_ternary(table)
            for n in range(8):
                inp=(n&1,n>>1&1,n>>2&1)
                got=candidate.evaluate_circuit(graph,inp,7)
                self.assertEqual(got,table>>n&1,(table,n))
    def test_unseen_primitive_types_not_provided_and_peers_equal_fit(self):
        meta=source.meta_training()
        m,_=candidate.learn_universal_gate(meta)
        q,_=peer.train_meta(meta)
        for fam in source.FAMILIES[:2]:
            for seed in source.SEEDS:
                e=source.heldout(fam,seed)
                a,ar=candidate.learn_new_primitive(m,e["FIT"])
                b,br=peer.train_novel(q,e["FIT"])
                self.assertIsNotNone(a,(fam,seed,ar))
                self.assertIsNotNone(b,(fam,seed,br))
                self.assertEqual(ar["FIT_bit_errors"],0)
                self.assertEqual(br["FIT_bit_errors"],0)
                self.assertTrue(all(candidate.score(a,x)["exact"] for x in e["CHECK"]))
                self.assertTrue(all(peer.score(b,x)["exact"] for x in e["CHECK"]))
                self.assertTrue(all(candidate.score(a,x)["exact"] for x in e["HELDOUT"]))
                self.assertTrue(all(peer.score(b,x)["exact"] for x in e["HELDOUT"]))
                self.assertTrue(all(not candidate.score(a,source.hard_negative(x))["exact"]
                                    for x in e["HELDOUT"]))
    def test_four_input_structural_family_rejected_by_three_input_learners(self):
        meta=source.meta_training()
        a,_=candidate.learn_universal_gate(meta)
        b,_=peer.train_meta(meta)
        for seed in source.SEEDS:
            d=source.heldout(source.FAMILIES[2],seed)
            am,ar=candidate.learn_new_primitive(a,d["FIT"])
            bm,br=peer.train_novel(b,d["FIT"])
            self.assertIsNone(am,(seed,ar))
            self.assertIsNone(bm,(seed,br))
            self.assertFalse(ar["natural_FIT"])
            self.assertFalse(br["natural_FIT"])
    def test_meta_gate_ablation_changes_constructed_computational_program(self):
        d=source.heldout(source.FAMILIES[0],71)
        m,_=candidate.learn_universal_gate(source.meta_training())
        complete,_=candidate.learn_new_primitive(m,d["FIT"])
        self.assertIsNotNone(complete)
        blank=dict(m);blank["learned_gate_table"]=None
        aborted,detail=candidate.learn_new_primitive(blank,d["FIT"])
        self.assertIsNone(aborted)
        self.assertTrue(detail["learned_gate_unavailable"])
        # Mutating learned gate parameters actually changes assembled
        # circuit results; this is a parameter ablation, not a victory
        # over equally trained competitor.
        ex=d["HELDOUT"][0]
        altered=dict(complete);altered["learned_gate_table"]=1
        self.assertNotEqual(candidate.rollout(complete,ex),
                            candidate.rollout(altered,ex))
    def test_heldout_labels_do_not_enter_autoregressive_computation(self):
        d=source.heldout(source.FAMILIES[1],72)
        cm,_=candidate.learn_universal_gate(source.meta_training())
        pm,_=peer.train_meta(source.meta_training())
        a,_=candidate.learn_new_primitive(cm,d["FIT"])
        b,_=peer.train_novel(pm,d["FIT"])
        episode=d["HELDOUT"][0]
        corrupted=copy.deepcopy(episode)
        for e in corrupted["events"]:e["observed"]^=15
        self.assertEqual(candidate.rollout(a,episode),candidate.rollout(a,corrupted))
        self.assertEqual(peer.rollout(b,episode),peer.rollout(b,corrupted))
    def test_equal_public_data_and_no_original_scientific_source(self):
        fam=source.FAMILIES[0]
        first=trial.run(fam,71,"meta_NAND_constructor")
        second=trial.run(fam,71,"equally_meta_trained_ANF_peer")
        for field in ("same_public_meta_SHA256","same_public_FIT_SHA256",
                      "same_public_CHECK_SHA256","same_public_unseen_SHA256"):
            self.assertEqual(first[field],second[field])
        self.assertFalse(first["scientific_acceptance"])
        self.assertFalse(second["scientific_acceptance"])
        self.assertEqual(first["scientific_firstuse_consumed"],0)
        self.assertEqual(second["scientific_firstuse_consumed"],0)
        self.assertTrue(first["CHECK_naturally_admitted"])
        self.assertTrue(second["CHECK_naturally_admitted"])
    def test_learner_independent_from_new_source_originator(self):
        for path in ("f124dc_learned_gate_compiler.py",
                     "f124dc_independent_anf_meta_peer.py"):
            tree=ast.parse((HERE/path).read_text())
            imports=[]
            for node in ast.walk(tree):
                if isinstance(node,ast.Import):imports.extend(a.name for a in node.names)
                elif isinstance(node,ast.ImportFrom):imports.append(node.module or "")
            self.assertNotIn("f124dc_sourcefree_structures",imports)
            self.assertFalse(any(x.startswith(("f124cr_","f124cu_","f124co_"))
                                 for x in imports))

if __name__=="__main__":unittest.main()

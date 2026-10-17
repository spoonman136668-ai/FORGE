"""F124-E frozen TRAIN-only diagnostic replay and causal eviction qualification."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parent))
import f124e_frozen_eviction_audit as a
import f124e_key_value_environment as graph
import f124e_learned_associative_memory as net

class F124EFrozenEvictionTests(unittest.TestCase):
    def pair(self):
        return graph.build(140000,[1,1,2],"Wingless","TRAIN")

    def test_exact_original_model_source_ids_and_protected_split(self):
        a.source_identity()
        self.assertEqual(a.TRAIN_SHA,"f54ff4be9b3b567a2faf913e3348da114e2701ee4eab4bcc1f52c8be07aa8585")
        self.assertEqual(a.BASE_HEAD,"878ba8e558a6f5fc122ff7468af0d02362750143")
        self.assertFalse(set(graph.TRAIN["Wingless"]) & set(graph.RESERVED_CONFIRM["Wingless"]))

    def test_matched_exact_frozen_three_slot_replay_for_both_arms_and_labels(self):
        pos,neg=self.pair()
        for arm in ("A","B"):
            weights=net.initial(arm)
            for obs in (pos,neg):
                original=net.forward(obs,weights,arm)[0]
                w=a.witness(obs,weights,arm,3)
                self.assertAlmostEqual(original,w["score"],places=12)
                self.assertGreater(w["public_edge_scans"],0)
                self.assertGreater(w["messages_propagated"],0)
                self.assertEqual(len(w["per_hop"]),len(obs["roles"]))

    def test_scorer_only_causal_provenance_does_not_influence_predictions(self):
        pos,neg=self.pair()
        for arm in ("A","B"):
            weights=net.initial(arm)
            p=a.witness(pos,weights,arm,3)
            n=a.witness(neg,weights,arm,3)
            self.assertEqual(n["causal_target_records"],0)
            self.assertLessEqual(p["causal_target_records"],1)
            flip=copy.deepcopy(pos)
            flip["edges"].reverse()
            q=a.witness(flip,weights,arm,3)
            self.assertAlmostEqual(p["score"],q["score"],places=12)

    def test_posthoc_relaxed_capacity_is_not_a_scientific_selector(self):
        pos,neg=self.pair()
        for arm in ("A","B"):
            weights=net.initial(arm)
            strict=a.witness(pos,weights,arm,3)
            expanded=a.witness(pos,weights,arm,32)
            self.assertGreaterEqual(strict["all_record_evictions"],
                                    expanded["all_record_evictions"])
            self.assertGreaterEqual(expanded["peak_live_records"],
                                    strict["peak_live_records"])
            with self.assertRaises(graph.Invalid):
                a.witness(pos,weights,arm,9)
            with self.assertRaises(graph.Invalid):
                a.witness(pos,weights[:-1],arm,3)

    def test_bad_original_receipt_identity_fails_before_scoring(self):
        with tempfile.TemporaryDirectory() as d:
            f=Path(d)/"fake.json"
            f.write_text("{}")
            with self.assertRaisesRegex(graph.Invalid,"ORIGINAL_TRAIN_DIGEST_MISMATCH"):
                a.source_receipt(f)

    def test_never_open_reservation_or_oracle_model_inputs(self):
        with self.assertRaises(graph.Invalid):
            graph.build(140100,[1,1,2],"Wingless","CONFIRM")
        p,_=self.pair()
        bad=copy.deepcopy(p)
        bad["causal_target"]=True
        with self.assertRaises(graph.Invalid):
            a.witness(bad,net.initial("A"),"A")
        self.assertEqual(a.CAPS,(3,32))

if __name__=="__main__":
    unittest.main()

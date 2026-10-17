"""F124-C fixed-weight TRAIN failure diagnostics, no confirmation inputs."""
import copy
import json
import math
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import f124c_training_failure_audit as audit
import f124c_node_state_models as model
import f124c_reconvergent_graph as source

VECTORS=[[1,1,2],[3,2,0]]

class AuditQualification(unittest.TestCase):
    def sample(self):
        return source.build(100000,VECTORS[0],"Wingless","TRAIN")

    def test_frozen_original_training_reference_pins(self):
        self.assertEqual(len(source.frozen()),64)
        self.assertEqual(audit.F124_SOURCE_HEAD,"ba24e1a7f16023d472d29124caf6524ca9499538")
        self.assertEqual(audit.F124_TRAIN_SHA,
                         "7de031ddfa5dd96df0d55581deca3b98c88a6f3090012ad037d1b8be7b9d1fd3")
        self.assertEqual(source.git_blob(Path(model.__file__).read_bytes().replace(
            b"\r\n",b"\n")), audit.F124_MODEL_BLOB)

    def test_rank_threshold_never_modifies_models(self):
        rows=[{"positive_score":.73,"negative_score":.71},
              {"positive_score":.25,"negative_score":.22}]
        result=audit.rank_and_threshold(rows)
        self.assertEqual(result["oracle_train_paired_correct"],1)
        self.assertEqual(result["operational_threshold_unchanged"],.5)
        self.assertTrue(result["threshold_label_informed_posthoc"])
        self.assertEqual(rows[0]["positive_score"],.73)

    def test_pair_visible_fixed_control_and_matched_parity(self):
        p,n=self.sample()
        yes,counts=audit.fixed_12_of_16(p)
        no,_=audit.fixed_12_of_16(n)
        self.assertTrue(yes)
        self.assertFalse(no)
        self.assertGreater(counts["raw_bit_comparisons"],0)
        self.assertGreater(counts["public_edge_scans"],0)
        self.assertTrue(source.pair_parity(p,n))

    def test_causal_removal_assessed_only_after_inference(self):
        p,_=self.sample()
        edges=audit.select_reconvergence_edges(p)
        self.assertGreaterEqual(len(edges),3)
        w=model.initial("A")
        p_before,_,stats=model.forward(p,w,"A")
        ablation=audit.deletion_ablation(p,w,"A",p_before)
        self.assertEqual(ablation["number_irrelevant_branches"],len(edges)-1)
        self.assertTrue(math.isfinite(ablation["causal_probability_drop"]))
        self.assertGreater(stats["gate_sigmoids"],0)
        self.assertEqual(p,audit.copy_reversed(audit.copy_reversed(p)))

    def test_report_one_arm_uses_graph_only_and_counts_each_stratum(self):
        rows=[]
        for seed in range(100000,100006):
            p,n=source.build(seed,VECTORS[0],"Wingless","TRAIN")
            rows.append((seed,0,p,n))
        # Full-cohort function is deliberately strict about sample count.
        with self.assertRaisesRegex(source.Quarantined,"TRAIN_PAIR_COUNT_DRIFT"):
            audit.diagnose_arm(rows,model.initial("B"),"B")
        rows=[]
        for vectoridx,v in enumerate(VECTORS):
            for seed in source.TRAIN["Wingless"]:
                p,n=source.build(seed,v,"Wingless","TRAIN")
                rows.append((seed,vectoridx,p,n))
        score=audit.diagnose_arm(rows,model.initial("B"),"B")
        self.assertEqual(score["pairs"],48)
        self.assertEqual(sum(score["strata"][k]["pairs"] for k in
                             ("hops:3","hops:4")),48)
        self.assertEqual(score["positive_ranks_above_negative"] <= 48,True)
        self.assertIsNotNone(score["mean_minor_slot_ratio"])
        self.assertEqual(score["posthoc_threshold_upper_bound"]
                         ["operational_threshold_unchanged"],.5)

    def test_source_interface_rejects_confirm_no_privilege(self):
        with self.assertRaises(source.Quarantined):
            source.build(100100,VECTORS[0],"Wingless","CONFIRM")
        p,_=self.sample()
        forged=copy.deepcopy(p)
        forged["truth"]=1
        with self.assertRaises(source.Quarantined):
            audit.fixed_12_of_16(forged)
        with self.assertRaises(source.Quarantined):
            audit.select_reconvergence_edges({"edges":[]})

    def test_exact_bytes_receipt_and_custody(self):
        with tempfile.TemporaryDirectory() as root:
            p=Path(root)/"train.json"
            p.write_bytes(b"{}")
            with self.assertRaisesRegex(source.Quarantined,"IMMUTABLE_TRAIN_RECEIPT_SHA_DRIFT"):
                audit.read_immutable(p,audit.F124_TRAIN_SHA)

if __name__=="__main__":
    unittest.main()

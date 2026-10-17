"""F124-P focused frozen identity, structural ablation and source separation."""
import inspect
import tempfile
from pathlib import Path
import unittest

import f124n_novel_structure_source as n
import f124k_extended_source as k
import f124o_native_learners as prior
import f124p_frozen_variants as variants
import f124p_structural_diagnostics as p


class F124PTests(unittest.TestCase):
    def test_frozen_identity_and_no_science(self):
        x,_ = p.frozen()
        self.assertEqual(x["source_parent"]["qualified_f124o_actions_run"],39078269441)
        self.assertEqual(x["study"]["additional_training_steps"],0)
        self.assertEqual(p.blob(prior.__file__),p.O_SOURCE_BLOB)
        self.assertEqual(p.blob(k.__file__),p.K_SOURCE_BLOB)
        self.assertTrue(all(v is False for v in x["authority"].values()))

    def test_immutable_original_and_bounded_candidates(self):
        for lane in ("Wingless","Yggdrasil"):
            weights = prior.WINGLESS_INIT if lane=="Wingless" else prior.YGGDRASIL_INIT
            for source_name in p.SOURCES:
                seed,vec,positive,negative=next(p.graphs(lane,source_name))
                original_logit,original_work=prior.forward(lane,positive,list(weights))
                replay_logit,replay_work=variants.variant_forward(
                    lane,"original",positive,list(weights))
                self.assertAlmostEqual(original_logit,replay_logit,places=12)
                self.assertEqual(original_work,replay_work)
                for arm in p.ARMS:
                    value,work=variants.variant_forward(
                        lane,arm,positive,list(weights))
                    self.assertTrue(-200<value<200)
                    self.assertGreater(work["public_edge_scans"],0)
                    self.assertLessEqual(work["max_active"],7 if lane=="Yggdrasil" else 192)
                    self.assertLessEqual(work.get("max_retained",0),9)
                for graph in (positive,negative):
                    self.assertEqual(set(graph),{"start","target","roles","edges"})

    def test_no_label_or_oracle_in_new_mechanisms(self):
        for f in (variants.wingless_diverse,variants.yggdrasil_cell_variant):
            src=inspect.getsource(f)
            for forbidden in ("public_routes(", "symbolic_routes(", "build_protected(",
                              "correct_answer", "ground_truth", "RESERVED["):
                self.assertNotIn(forbidden,src)
        with self.assertRaises(n.Quarantined):
            variants.variant_forward("Wingless","unknown",{},list(prior.WINGLESS_INIT))
        with self.assertRaises((k.Invalid,n.Quarantined)):
            k.build_fixture(180100,[1,1,2],"Wingless")
        with self.assertRaises(k.Invalid):
            k.build_protected()

    def test_forged_original_receipt_and_reserved_sources_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            bogus=Path(directory)/"forged.json"
            bogus.write_text('{"lanes":[]}',encoding="utf-8")
            with self.assertRaises(n.Quarantined):
                p.authenticated_weights(bogus)
        self.assertEqual(len(list(p.graphs("Wingless",p.SOURCES[0]))),48)
        self.assertEqual(len(list(p.graphs("Yggdrasil",p.SOURCES[1]))),48)


if __name__=="__main__":
    unittest.main()

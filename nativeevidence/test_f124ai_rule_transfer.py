"""F124-AI new TRAIN source, compositional parser, original hard budgets."""
import inspect,unittest
from collections import Counter
import f124ai_frozen_source as source
import f124ai_compositional_model as model

class F124AIFrozen(unittest.TestCase):
    def test_original_birth_freeze_and_train_separation(self):
        p=source.frozen()
        self.assertEqual(source.witness.blob(source.FREEZE),source.FREEZE_BLOB)
        self.assertEqual(p["lineage"]["qualified_parent_run"],39110523568)
        self.assertTrue(set(source.OPERATORS["TRAIN"]).isdisjoint(
                        source.OPERATORS["HOLDOUT"]))
        self.assertTrue(all(v is False for v in p["authority"].values()))
        for lane in ("Yggdrasil","Wingless"):
            self.assertTrue(set(source.COHORTS[lane]["TRAIN"]).isdisjoint(
                            source.COHORTS[lane]["HOLDOUT"]))
            cases=source.pairs(lane,"TRAIN")
            self.assertEqual(len(cases),48)
            self.assertEqual(Counter(c[2] for c in cases),
                             Counter({family:12 for family in source.FAMILIES}))
            self.assertEqual(Counter(c[3] for c in cases),
                             Counter({op:12 for op in source.OPERATORS["TRAIN"]}))
            for seed,vector,family,op,pos,neg in cases:
                self.assertEqual(source.oracle(pos,op,family),1)
                self.assertEqual(source.oracle(neg,op,family),0)
                self.assertEqual(source.ah.parent.prior.parent.routes15(
                    pos,relaxed=True),0)

    def test_public_rule_composition_without_example_labels(self):
        bits=[1 if i in (0,4,7,11) else 0 for i in range(16)]
        for op in ("xor_FFFF","xor_A55A","xor_55AA","rotl_4","rotl_12","rotl_3"):
            marker=source.prefix(op)
            parsed=model.public_operator(marker+"role")
            self.assertEqual(parsed[2],"role")
            encoded=source.rule_transform(bits,op)
            fake={"start":"s","target":"t","roles":[marker+"r"]*7,
                  "edges":[{"from":"s","to":"t","role":marker+"r",
                            "src_bits":encoded,"dst_bits":[0]*16}]*12}
            restored,counts=model.normalize_public_graph(fake)
            self.assertEqual(restored["edges"][0]["src_bits"],bits)
            self.assertEqual(counts["normalized_edges"],12)

    def test_ygg_original_7_plus_9_train_only(self):
        base=[.4,.9,.65,.75,.8,.2,-.5]
        delta=[1.3,.2]
        for seed,vector,fam,op,pos,neg in source.pairs("Yggdrasil","TRAIN")[:8]:
            for graph in (pos,neg):
                for eta in model.ETAS:
                    score,raw,ratio,work,pre=model.ygg(graph,base,delta,eta)
                    self.assertLessEqual(work["max_active"],7)
                    self.assertLessEqual(work["max_retained"],9)
                    self.assertEqual(pre["extra_retained_cells"],0)
                    self.assertTrue(pre["operator_was_explicit_in_roles"])
        chosen,grid=model.train_eta(source.pairs("Yggdrasil","TRAIN"),base,delta)
        self.assertEqual(len(grid),6)
        self.assertEqual(chosen["paired"],max(v["paired"] for v in grid))

    def test_wing_one_original_12bit_state(self):
        base=[.6,.7,.9,.5,.85,.15,-.55]
        delta=[.05,-.03,.02,-.04]
        for seed,vector,fam,op,pos,neg in source.pairs("Wingless","TRAIN")[:8]:
            for graph in (pos,neg):
                score,work,pre=model.wing(graph,base,delta)
                self.assertEqual(work["max_states_per_node"],1)
                self.assertEqual(work["max_packed_bits_per_state"],12)
                self.assertLessEqual(work["max_active"],64)
                self.assertEqual(pre["extra_retained_cells"],0)

    def test_model_does_not_consult_original_oracle_or_labels(self):
        for fn in (model.normalize_public_graph,model.ygg,model.wing):
            body=inspect.getsource(fn)
            for forbidden in ("oracle(","routes15(","paired_admit(",
                              "positive_route(","public_reference(", '"HOLDOUT"',
                              "restore_public("):
                self.assertNotIn(forbidden,body)

if __name__=="__main__":
    unittest.main()

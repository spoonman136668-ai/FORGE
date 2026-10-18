"""F124-AU focused source isolation and candidate model capacity tests.

No prospective F124-AU scientific TRAIN selection, no new DEV creation.
Model smoke uses synthetic PUBLIC demos and previously-consumed AT TRAIN.
"""
import inspect
import math
import unittest
from collections import Counter

import f124au_train_source as src
import f124au_public_relation_model as yy
import f124au_packed_witness as ww
import f124at_train_source as oldsrc
import f124am_terminal_competition as control

BASE=[.6,.7,.9,.5,.85,.15,-.55]
YD=[.05,-.03]
WD=[.05,-.03,.02,-.04]

def sample_public(shift):
    demos=[]
    for j in range(24):
        x=[(j*3+k*7+shift+k*j)%(k%3+2)%2 for k in range(16)]
        y=[x[(k+shift)%16] for k in range(16)]
        demos.append({"output_bits":x,"input_bits":y})
    return demos

class AUFocused(unittest.TestCase):
    def test_preimplementation_freeze_and_absolute_dev_denial(self):
        spec=src.frozen()
        self.assertEqual(src.witness.blob(src.FREEZE),src.FREEZE_BLOB)
        self.assertEqual(src.witness.blob(src.prior.__file__),src.PARENT_BLOB)
        self.assertEqual(spec["lineage"]["qualified_AT_parent"],
                         src.PARENT_QUALIFIED)
        self.assertEqual(spec["Yggdrasil"]["grid_size"],8)
        self.assertEqual(spec["Wingless"]["grid_size"],7)
        self.assertTrue(set(src.OPERATORS["TRAIN"]).isdisjoint(
            src.OPERATORS["DEV"]))
        for lane in src.COHORTS:
            with self.assertRaises(Exception):
                src.pairs(lane,"DEV")
            with self.assertRaises(Exception):
                src.build(lane,src.COHORTS[lane]["DEV"].start,
                          src.VECTORS[0],"DEV")
            with self.assertRaises(Exception):
                src.build(lane,src.COHORTS[lane]["DEV"].start,
                          src.VECTORS[0],"TRAIN")
        self.assertTrue(all(not value for value
                            in spec["qualification"]["authority"].values()))

    def test_source_birth_fresh_train_not_reused_old(self):
        for lane in ("Yggdrasil","Wingless"):
            old=set(oldsrc.COHORTS[lane]["TRAIN"])
            new=set(src.COHORTS[lane]["TRAIN"])
            self.assertTrue(old.isdisjoint(new))
            seed=src.COHORTS[lane]["TRAIN"].start
            fam,op,nonce,p,n,_=src.build(
                lane,seed,src.VECTORS[0],"TRAIN")
            self.assertEqual(p["demos"],n["demos"])
            self.assertEqual(len(p["demos"]),24)
            self.assertEqual(sum(src.relation(x["input_bits"],op)!=x["output_bits"]
                                 for x in p["demos"]),3)

    def test_operator_agnostic_learned_representation_census(self):
        txt=inspect.getsource(yy)
        for blocked in ("import f124au_train_source",
                        "import f124at_train_source",
                        "inverse_output(",
                        "source.plain("):
            self.assertNotIn(blocked,txt)
        tasks=[sample_public(i%4) for i in range(48)]
        for mode in yy.MODES:
            for width in yy.WIDTHS:
                model=yy.train_shared(tasks,mode,width)
                self.assertFalse(model["source_truth_used"])
                self.assertFalse(model["operator_grammar_used"])
                self.assertEqual(model["shared_parameters"],32*width)
                self.assertEqual(model["shared_float_bytes_lower"],256*width)
                self.assertGreater(model["supervised_update_ops"],0)
                result=yy.estimate(model,tasks[0][0]["output_bits"],tasks[0][:20])
                self.assertEqual(len(result),16)
                self.assertTrue(all(math.isfinite(x) for x in result))
                # Synthetic support should be well-formed even on abstention.
                with self.assertRaises(Exception):
                    yy.normalize({"foo":"bad"},model,47)
        with self.assertRaises(Exception):
            yy.train_shared(tasks,yy.MODES[0],32)
        with self.assertRaises(Exception):
            yy.train_shared(tasks[:47],yy.MODES[0],8)

    def test_wingless_original_exact_and_one_state(self):
        code=inspect.getsource(ww)
        self.assertNotIn("import f124au_train_source",code)
        self.assertNotIn("source.plain(",code)
        oldsrc.frozen()
        seed=oldsrc.COHORTS["Wingless"]["TRAIN"].start
        _,op,nonce,p,n,_=oldsrc.build(
            "Wingless",seed,oldsrc.VECTORS[0],"TRAIN")
        for graph in (oldsrc.plain(p,op,nonce),
                      oldsrc.plain(n,op,nonce)):
            baseline,originalwork=control.terminal_competitive(
                graph,BASE,WD,0.)
            score,work=ww.score(graph,BASE,WD,"original_gamma0",0.)
            self.assertEqual(score,baseline)
            self.assertEqual(work["edge_inspections"],
                             originalwork["edge_inspections"])
            for mode in ww.MODES[1:]:
                for alpha in ww.ALPHAS[1:]:
                    score,details=ww.score(graph,BASE,WD,mode,alpha)
                    self.assertTrue(math.isfinite(score))
                    self.assertEqual(details["max_states_per_node"],1)
                    self.assertEqual(details["max_packed_bits_per_state"],12)
                    self.assertEqual(details["extra_retained_states"],0)
                    self.assertLessEqual(details["max_active"],64)
                    self.assertFalse(details["oracle_used"])
        with self.assertRaises(Exception):
            ww.score(graph,BASE,WD,"original_gamma0",.12)
        with self.assertRaises(Exception):
            ww.score(graph,BASE,WD,"not_registered",.02)

if __name__=="__main__":
    unittest.main()

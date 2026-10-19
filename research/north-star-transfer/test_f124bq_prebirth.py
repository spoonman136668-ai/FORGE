"""F124-BQ nonconsuming source-agnostic proof of learned operation modes.

Synthetic examples are independent deterministic fixtures, NOT the new
prospective FIT/holdout sets or consumed BM/BN/BO/BP source generators.
"""
from __future__ import annotations

import importlib.util
import random
from pathlib import Path
import unittest

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location(
    "bq_frozen_program",HERE/"f124bq_program_learner.py")
model=importlib.util.module_from_spec(spec)
spec.loader.exec_module(model)


def bits(value):
    return [(value>>j)&1 for j in range(16)]


def independent_public(params,seed,flip=(0,4,9,16,21,32)):
    rng=random.Random(seed)
    xs=rng.sample(range(65536),48)
    return [(x,model.forward(x,params)^(1 if i in flip else 0))
            for i,x in enumerate(xs)]


class PublicLearnedAlgebraicComposition(unittest.TestCase):
    def test_32bit_bounded_and_newly_learned_cross_mode(self):
        self.assertEqual(model.STATE_BITS,32)
        self.assertEqual(model.MAX_PROGRAMS,16)
        self.assertEqual(model.FIT_RESIDUAL_EVAL_CAP,10240)
        for source_program in (
            (53,37,41,19,0,1), # unlike BP, second operation XOR
            (87,109,9,173,1,0),# unlike BP, first operation XOR
            (7,13,29,211,1,1),
            (97,217,17,3,0,0),
        ):
            public=independent_public(source_program,
                                       803212+source_program[0])
            fitted,stats,candidates=model.learn(public[:40],public[40:])
            self.assertIsNotNone(fitted,stats)
            self.assertTrue(stats["confidence"])
            self.assertEqual(stats["state_bits"],32)
            self.assertEqual(stats["sourceblind_operator_mode_bits"],2)
            self.assertEqual(stats["operator1_mode_from_public_fit"],
                             source_program[4])
            self.assertEqual(stats["operator2_mode_from_public_fit"],
                             source_program[5])
            self.assertEqual(stats["stage_public_residual_evaluations"],10240)
            self.assertLessEqual(stats["whole_program_FIT_evaluations"],640)
            self.assertEqual(stats["FIT_error_bits"],6)
            self.assertEqual(stats["CHECK_error_bits"],0)
            self.assertIn(fitted,candidates)
            for x in range(0,65536,409):
                self.assertEqual(model.forward(x,fitted),
                                 model.forward(x,source_program))
                self.assertEqual(model.inverse(model.forward(x,source_program),
                                               fitted),x)

    def test_same_graph_causal_validity_and_token_swap_negative(self):
        truth=(53,37,41,19,0,1)
        public=independent_public(truth,145818)
        learned,_,plausible=model.learn(public[:40],public[40:])
        self.assertIsNotNone(learned)
        rng=random.Random(720042)
        roles=["rel_task_synthetic_only_"+str(i) for i in range(8)]
        carry=rng.sample(range(65536),9)
        edges=[{"from":f"n{i}","to":f"n{i+1}","role":roles[i],
                "src_bits":bits(model.forward(carry[i],truth)),
                "dst_bits":bits(carry[i+1])} for i in range(8)]
        decoy={"from":"detached","to":"dead","role":roles[3],
               "src_bits":bits(model.forward(53001,truth)),
               "dst_bits":bits(63001)}
        good={"start":"n0","target":"n8","roles":roles,
              "edges":edges+[decoy],"demos":[]}
        yes,receipt=model.causal_consensus(good,learned,plausible)
        self.assertTrue(yes,receipt)
        self.assertEqual(receipt["hops"],8)
        import copy
        bad=copy.deepcopy(good)
        bad["edges"][3]["src_bits"],bad["edges"][8]["src_bits"]=(
            bad["edges"][8]["src_bits"],bad["edges"][3]["src_bits"])
        accepted,reason=model.causal_consensus(bad,learned,plausible)
        self.assertFalse(accepted)
        self.assertEqual(reason["decision"],"REJECT_WRONG_CAUSAL_PREDECESSOR")

    def test_check_is_veto_not_target_selection(self):
        truth=(53,37,41,19,0,1)
        public=independent_public(truth,988214)
        poisoned=[(x,y^65535) for x,y in public[40:]]
        selection,receipt,plausible=model.learn(public[:40],poisoned)
        self.assertIsNone(selection)
        self.assertFalse(receipt["confidence"])
        self.assertFalse(plausible)
        self.assertTrue(receipt["CHECK_can_only_veto"])

    def test_old_and_private_source_id_cannot_be_used_to_train(self):
        with self.assertRaises(ValueError):
            model.learn([(1,1)]*39,[(1,1)]*8)
        with self.assertRaises(ValueError):
            model.forward(999,(0,0,1,1,0,0))
        with self.assertRaises(ValueError):
            model.causal_consensus({"start":"a"},None,())


if __name__=="__main__":
    unittest.main()

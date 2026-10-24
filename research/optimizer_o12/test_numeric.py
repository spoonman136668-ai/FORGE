"""O12 prospective source-only numeric and fail-closed acceptance tests."""
import copy
from decimal import Decimal as D, localcontext
import math
import unittest

from public_source import (
    FAMILIES,ROLES,COUNTS,UnauthorizedSource,
    role_batch,public_episode,query_info,digest,seed,
)
from o10_frozen_phase import PublicPhaseComposer
from decimal_phase import (DecimalPhase,CTX,PI,fixed_sin_cos,nll)
from train_only import guard,model_for,snapshot,ARMS,TRACE
from compare import compare,STEPS


class O12NumericForensics(unittest.TestCase):
    def test_protocol_and_all_exact_training_roles(self):
        p=guard()
        self.assertEqual(tuple(p["roles"]),ROLES)
        self.assertEqual(tuple(p["models"]),ARMS)
        self.assertEqual(tuple(p["frozen_training"]["trace_after_updates"]),TRACE)
        self.assertEqual(p["frozen_training"]["updates_per_run"],1920)

    def test_new_fresh_train_and_probes_public_source_identity(self):
        for family in FAMILIES:
            hashes=[]
            for role in ROLES:
                batch=role_batch(role,family)
                self.assertEqual(len(batch),COUNTS[role])
                self.assertTrue(all(len(ep)==24 for ep in batch))
                for ep in batch:
                    self.assertTrue(all(ep[i][2]==ep[i+1][0] for i in range(23)))
                    self.assertIn(query_info(ep)["query_t"],(10,18))
                hashes.append(digest(batch))
            self.assertEqual(len(set(hashes)),2)

    def test_old_dev_scientific_and_invalid_ids_fail_closed(self):
        for role in ("O10_TRAIN","O10_SELECT","O10_DEV",
                     "O11_DIAG_TRAIN","HELD","Q21N01_PUBLIC","DEV"):
            with self.assertRaises(UnauthorizedSource):
                public_episode(role,FAMILIES[0],0)
        for i in (-1,48,True,1.0,"1"):
            with self.assertRaises(UnauthorizedSource):
                seed("O12_TRAIN",FAMILIES[0],i)

    def test_pi_trig_deterministic_without_system_libm(self):
        with localcontext(CTX):
            sine,cosine=fixed_sin_cos(D(0))
            self.assertEqual(sine,D(0))
            self.assertEqual(cosine,D(1))
            s,c=fixed_sin_cos(PI)
            self.assertLess(abs(s),D("1e-29"))
            self.assertLess(abs(c+D(1)),D("1e-29"))
            self.assertEqual(fixed_sin_cos(D("0.7")),
                             fixed_sin_cos(D("0.7")))

    def test_original_frozen_phase_code_is_fitted_on_new_train_only(self):
        ep=public_episode(ROLES[0],FAMILIES[0],0)
        m=PublicPhaseComposer("TRAINED_PHASE_MEMORY",17)
        cp=m.checkpoint()
        m.step(ep)
        self.assertNotEqual(cp,m.checkpoint())
        self.assertEqual(m.updates,1)

    def test_decimal_actual_gradient_matches_training_only_finite_difference(self):
        ep=public_episode(ROLES[0],FAMILIES[1],0)
        m=DecimalPhase("DECIMAL_PHASE_34",17)
        original=m.checkpoint()
        with localcontext(CTX):
            loss,g=m.loss_gradient(ep)
            self.assertTrue(loss.is_finite())
            for j in range(8):
                before=m.w[j]
                h=D("1e-11")
                m.w[j]=before+h
                plus=nll(query_info(ep)["target"],m.predict(ep))
                m.w[j]=before-h
                minus=nll(query_info(ep)["target"],m.predict(ep))
                m.w[j]=before
                approx=(plus-minus)/(2*h)
                self.assertLess(abs(g[j]-approx),D("5e-7"),
                                msg=f"o12_decimal_gradient[{j}]")
        self.assertEqual(original,m.checkpoint())

    def test_conditioned_and_plain_decimal_differ_only_after_gradients(self):
        ep=public_episode(ROLES[0],FAMILIES[2],0)
        raw=DecimalPhase("DECIMAL_PHASE_34",17)
        conditioned=DecimalPhase("DECIMAL_PHASE_34_CONDITIONED",17)
        self.assertEqual(raw.w,conditioned.w)
        self.assertEqual(raw.loss_gradient(ep),conditioned.loss_gradient(ep))
        for _ in range(8):
            raw.step(ep)
            conditioned.step(ep)
        self.assertEqual(raw.updates,8)
        self.assertEqual(conditioned.updates,8)
        self.assertTrue(all(z.is_finite() for z in conditioned.w))
        self.assertNotEqual(raw.checkpoint(),conditioned.checkpoint())

    def test_train_diagnostic_snapshot_never_mutates_model(self):
        train=role_batch("O12_TRAIN",FAMILIES[0])
        probe=role_batch("O12_TRAIN_DIAGNOSTIC",FAMILIES[0])
        for arm in ARMS:
            m=model_for(arm,17)
            cp=m.checkpoint()
            snap=snapshot(m,arm,probe,train[0])
            self.assertEqual(cp,m.checkpoint())
            self.assertEqual(snap["step"],0)
            self.assertEqual(len(snap["w"]),8)
            self.assertEqual(len(snap["adam_m"]),8)

    def _receipt(self):
        value="0"
        zero="0x0.0p+0"
        def traces(arm):
            num=zero if arm=="NATIVE_O10_FLOAT" else value
            return [{"step":step,
                     "w":[num]*8,"adam_m":[num]*8,"adam_v":[num]*8,
                     "train_gradient":[num]*8,
                     "train_diagnostic_query_loss":num,
                     "phase":num,"phase_sin":num,"phase_cos":num}
                    for step in STEPS]
        return {
            "schema":"forge.optimizer.o12.new-train-only-numeric-receipt.v1",
            "no_old_o10_o11_dev_or_select_role_consumption":True,
            "protected_scientific_first_use":False,
            "scientific_candidate_admitted":False,
            "original_o10_model_code_blob":
                "56203c6aa60b29c4a5e8fb4bcd250bc212582209",
            "sources_sha256":{f"{f}:{r}":"a"*64
                              for f in FAMILIES for r in ROLES},
            "models":[{"family":f,"seed":s,"arm":a,
                       "checkpoint_sha256":"b"*64,
                       "trace":traces(a)}
                      for f in FAMILIES for s in (17,31) for a in ARMS],
            "whole_process_cpu_s":1.2,
        }

    def test_same_decimal_source_and_traces_pass_without_science_go(self):
        x=self._receipt()
        r=compare(x,copy.deepcopy(x))
        self.assertEqual(r["source_role_digests_match"],"8_OF_8")
        self.assertEqual(r["decimal_cross_os_comparison"],"TEXT_EXACT_PASS")
        self.assertFalse(r["accepted_scientific_candidate"])

    def test_decimal_one_character_drift_fails_without_tolerance(self):
        a=self._receipt()
        b=copy.deepcopy(a)
        b["models"][1]["trace"][3]["w"][3]="0.00000000000000000000001"
        with self.assertRaisesRegex(ValueError,"DECIMAL_EXACT"):
            compare(a,b)

    def test_native_float_difference_reported_not_hidden(self):
        a=self._receipt()
        b=copy.deepcopy(a)
        b["models"][0]["trace"][3]["w"][0]=(1e-4).hex()
        r=compare(a,b)
        self.assertEqual(
            r["native_original_model_drift"][0]["first_weight_gt_1e-6"],3)

    def test_missing_role_rejected(self):
        a=self._receipt()
        b=copy.deepcopy(a)
        b["sources_sha256"].pop(next(iter(b["sources_sha256"])))
        with self.assertRaisesRegex(ValueError,"SOURCE_SHA"):
            compare(a,b)


if __name__=="__main__":
    unittest.main()

"""O8 source-only delayed-learning, memory-erasure and parity-control checks."""
import math
import unittest

from public_source import (
    FAMILIES,ROLES,COUNTS,STEPS,QUERY_TIMES,ProtectedRoleRefused,
    public_episode,all_public,query_info,role_digest,seed,
)
from recurrent_memory import (
    PublicRecurrentMemory,KINDS,SEEDS,EPOCHS,nll,
)
from public_controls import PublicQueryCounts,PublicMemoryLogistic
from runner import ARMS,protocol_guard,eval_query,fit_select


class O8PublicDelayedMemory(unittest.TestCase):
    def test_frozen_roles_and_eight_diagnostic_arms(self):
        p=protocol_guard()
        self.assertEqual(tuple(p["roles"]),ROLES)
        self.assertEqual(p["episodes_by_role"],COUNTS)
        self.assertEqual(len(ARMS),8)
        self.assertEqual(p["evaluation"]["primary"].startswith("Query-only"),True)

    def test_episode_source_role_identity_and_public_chain(self):
        for family in FAMILIES:
            hashes=[]
            for role in ROLES:
                eps=all_public(role,family)
                self.assertEqual(len(eps),COUNTS[role])
                self.assertTrue(all(len(ep)==STEPS for ep in eps))
                for ep in eps:
                    self.assertTrue(all(len(row)==3 and type(row[0]) is int
                                        and row[0] in (0,1) and
                                        type(row[1]) is int and row[1] in (0,1,2)
                                        and type(row[2]) is int and row[2] in (0,1)
                                        for row in ep))
                    self.assertTrue(all(ep[i][2]==ep[i+1][0]
                                        for i in range(STEPS-1)))
                    q=query_info(ep)
                    self.assertIn(q["query_t"],QUERY_TIMES)
                    self.assertEqual(ep[q["query_t"]][1],2)
                hashes.append(role_digest(eps))
            self.assertEqual(len(set(hashes)),3)

    def test_protected_scientific_and_old_roles_fail_closed(self):
        for role in ("HELD","ORIGINAL","FIT_TRAIN","DEV",
                     "O7_TRAIN","O6_PUBLIC_DEV","Q21N01_FIT_VALID"):
            with self.assertRaises(ProtectedRoleRefused):
                public_episode(role,FAMILIES[0],0)
        for bad in (True,-1,96,"1",1.0):
            with self.assertRaises(ProtectedRoleRefused):
                seed("O8_PUBLIC_TRAIN",FAMILIES[0],bad)
        with self.assertRaises(ProtectedRoleRefused):
            public_episode(ROLES[0],"SECRET_LAW",0)

    def test_query_cue_and_parity_derived_from_public_history(self):
        eps=all_public(ROLES[0],FAMILIES[1])[:5]
        for ep in eps:
            q=query_info(ep)
            self.assertEqual(q["cue"],ep[0][0])
            self.assertEqual(
                q["parity"],
                sum(1 for row in ep[:q["query_t"]] if row[1]==1)%2
            )
        self.assertEqual(
            seed(ROLES[0],FAMILIES[0],0),seed(ROLES[0],FAMILIES[0],0)
        )

    def test_gated_and_vanilla_states_train_on_same_public_targets(self):
        eps=all_public(ROLES[0],FAMILIES[0])[:3]
        counts={}
        for kind in KINDS:
            m=PublicRecurrentMemory(kind,17)
            before=m.checkpoint()
            m.fit(eps)
            self.assertNotEqual(before,m.checkpoint())
            self.assertEqual(m.updates,EPOCHS*len(eps))
            probabilities=[m.predict(ep) for ep in eps]
            self.assertTrue(all(0<p<1 and math.isfinite(p)
                                for p in probabilities))
            counts[kind]=m.parameter_count()
        self.assertLess(counts["GATED_2"],counts["VANILLA_4"])
        self.assertLess(counts["VANILLA_4"],counts["GATED_4"])

    def test_selected_model_only_uses_train_select_and_not_dev(self):
        train=all_public(ROLES[0],FAMILIES[1])[:3]
        select=all_public(ROLES[1],FAMILIES[1])[:2]
        dev=all_public(ROLES[2],FAMILIES[1])[:2]
        for kind in KINDS:
            m,meta=fit_select(kind,train,select)
            self.assertTrue(math.isfinite(meta["public_select_nll"]))
            self.assertIn(meta["selected_seed"],SEEDS)
            before=m.checkpoint()
            normal=eval_query(m,dev)
            erased=eval_query(m,dev,erased=True)
            self.assertTrue(math.isfinite(normal) and math.isfinite(erased))
            self.assertEqual(m.checkpoint(),before)

    def test_ablation_resets_retained_history_without_retraining(self):
        sample=all_public(ROLES[0],FAMILIES[0])[:3]
        model=PublicRecurrentMemory("GATED_2",17)
        model.fit(sample)
        before=model.checkpoint()
        differences=[abs(model.predict(ep)-model.predict(ep,erased_query=True))
                     for ep in sample]
        self.assertTrue(any(d>1e-12 for d in differences))
        self.assertEqual(model.checkpoint(),before)

    def test_explicit_public_episodic_and_logistic_controls_fitted(self):
        train=all_public(ROLES[0],FAMILIES[1])[:5]
        dev=all_public(ROLES[2],FAMILIES[1])[:2]
        for model in (
            PublicQueryCounts("CURRENT_QUERY"),
            PublicQueryCounts("FULL_PUBLIC_EPISODIC"),
            PublicMemoryLogistic(),
        ):
            start=model.checkpoint()
            model.fit(train)
            self.assertNotEqual(start,model.checkpoint())
            self.assertGreater(model.updates,0)
            frozen=model.checkpoint()
            self.assertTrue(math.isfinite(eval_query(model,dev)))
            self.assertEqual(frozen,model.checkpoint())

    def test_inference_refuses_invalid_or_privileged_observation_fields(self):
        ep=all_public(ROLES[0],FAMILIES[0])[0]
        model=PublicRecurrentMemory("GATED_2",17)
        original=model.checkpoint()
        tampered=list(ep)
        tampered[0]=(*tampered[0],"hidden_state")
        with self.assertRaises(ValueError):
            model.fit((tuple(tampered),))
        tampered=list(ep)
        tampered[1]=(tampered[1][0],3,tampered[1][2])
        with self.assertRaises(ValueError):
            model.predict(tuple(tampered))
        self.assertEqual(model.checkpoint(),original)

    def test_memory_aware_predictor_has_more_information_than_current_only(self):
        # Delayed query means initial cue and history parity are externally
        # observable and identical to every learner; none receives latent labels.
        eps=all_public(ROLES[0],FAMILIES[1])[:12]
        current=PublicQueryCounts("CURRENT_QUERY")
        history=PublicQueryCounts("FULL_PUBLIC_EPISODIC")
        current.fit(eps)
        history.fit(eps)
        self.assertEqual(current.updates,history.updates)
        self.assertNotEqual(current.checkpoint(),history.checkpoint())

    def test_uniform_null_baseline_and_query_noise_checks(self):
        self.assertAlmostEqual(nll(0,0.5),math.log(2),places=12)
        self.assertAlmostEqual(nll(1,0.5),math.log(2),places=12)
        a=public_episode(ROLES[0],FAMILIES[0],0)
        self.assertEqual(a,public_episode(ROLES[0],FAMILIES[0],0))


if __name__=="__main__":
    unittest.main()

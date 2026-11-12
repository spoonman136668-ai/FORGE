"""O9 adversarial source custody, learned routing and analytic gradient tests."""
import math
import unittest

from public_source import (
    FAMILIES,ROLES,COUNTS,QUERIES,STEPS,RefusedRole,
    public_roles,episode,query_info,seed,digest,
)
from routing import LearnedEpisodicRouting,PARAMS,VARIANTS,nll
from controls import PublicCounts
from runner import ARMS,frozen_protocol,selected,score
from o8_frozen_recurrent import PublicRecurrentMemory


class O9LearningTests(unittest.TestCase):
    def test_frozen_protocol_and_models(self):
        p=frozen_protocol()
        self.assertEqual(tuple(p["roles"]),ROLES)
        self.assertEqual(tuple(p["models"]),ARMS)
        self.assertEqual(p["episodes_by_role"],COUNTS)
        self.assertEqual(p["frozen_hyperparams"]["learned_epochs"],40)

    def test_public_all_source_roles_and_chain(self):
        for family in FAMILIES:
            hashes=[]
            for role in ROLES:
                episodes=public_roles(role,family)
                self.assertEqual(len(episodes),COUNTS[role])
                for ep in episodes:
                    self.assertEqual(len(ep),STEPS)
                    info=query_info(ep)
                    self.assertIn(info["query_t"],QUERIES)
                    self.assertEqual(ep[info["query_t"]][1],2)
                    self.assertTrue(all(ep[t][2]==ep[t+1][0]
                                        for t in range(STEPS-1)))
                    self.assertTrue(all(len(row)==3 and
                                        all(type(x) is int for x in row)
                                        for row in ep))
                hashes.append(digest(episodes))
            self.assertEqual(len(set(hashes)),3)

    def test_forbidden_protected_and_old_public_role_names(self):
        for role in ("Q21_HELD","HELD","ORIGINAL","DEV","FIT_TRAIN",
                     "O8_PUBLIC_DEV","O7_TRAIN","O6_PUBLIC_TRAIN"):
            with self.assertRaises(RefusedRole):
                episode(role,FAMILIES[0],0)
        for idx in (-1,96,1.0,True,"2"):
            with self.assertRaises(RefusedRole):
                seed("O9_PUBLIC_TRAIN",FAMILIES[0],idx)

    def test_derived_cue2_selector_and_parity_are_public(self):
        for ep in public_roles("O9_PUBLIC_TRAIN",FAMILIES[1])[:8]:
            d=query_info(ep)
            self.assertEqual(d["cue"],ep[0][0])
            self.assertEqual(d["cue4"],ep[4][0])
            self.assertEqual(d["selector"],ep[d["query_t"]-1][1])
            self.assertEqual(d["parity"],sum(row[1]==1
                             for row in ep[:d["query_t"]])%2)

    def test_learned_write_read_has_actual_public_loss_gradient(self):
        ep=episode("O9_PUBLIC_TRAIN",FAMILIES[0],0)
        m=LearnedEpisodicRouting("LEARNED_WRITE_READ",17)
        original=m.checkpoint()
        loss,g=m.loss_gradient(ep)
        self.assertTrue(math.isfinite(loss))
        self.assertEqual(len(g),PARAMS)
        for j in (1,4,7,11,14,18,21,22,23):
            value=m.params[j]
            epsilon=1e-5
            m.params[j]=value+epsilon
            plus=nll(query_info(ep)["target"],m.predict(ep))
            m.params[j]=value-epsilon
            minus=nll(query_info(ep)["target"],m.predict(ep))
            m.params[j]=value
            approximate=(plus-minus)/(2*epsilon)
            self.assertAlmostEqual(g[j],approximate,delta=2e-6,
                                   msg=f"feature gradient {j}")
        self.assertEqual(original,m.checkpoint())

    def test_only_output_head_learns_when_route_frozen(self):
        ep=episode("O9_PUBLIC_TRAIN",FAMILIES[0],0)
        m=LearnedEpisodicRouting("FROZEN_RANDOM_ROUTE",17)
        before=m.params[:]
        for _ in range(3):
            m.step(ep)
        self.assertEqual(before[:21],m.params[:21])
        self.assertNotEqual(before[21:],m.params[21:])

    def test_learned_read_fixed_write_freezes_write_weights(self):
        ep=episode("O9_PUBLIC_TRAIN",FAMILIES[1],0)
        m=LearnedEpisodicRouting("LEARNED_READ_FIXED_WRITE",17)
        before=m.params[:]
        for _ in range(4):
            m.step(ep)
        self.assertEqual(before[:7],m.params[:7])
        self.assertNotEqual(before[7:],m.params[7:])

    def test_history_erasure_does_not_mutate_fitted_model(self):
        ep=episode("O9_PUBLIC_TRAIN",FAMILIES[0],0)
        m=LearnedEpisodicRouting("LEARNED_WRITE_READ",17)
        m.fit((ep,))
        frozen=m.checkpoint()
        a=m.predict(ep)
        b=m.predict(ep,erased=True)
        self.assertTrue(math.isfinite(a) and math.isfinite(b))
        self.assertEqual(frozen,m.checkpoint())

    def test_same_public_train_for_controls_and_o8_baseline(self):
        train=public_roles("O9_PUBLIC_TRAIN",FAMILIES[1])[:3]
        dev=public_roles("O9_PUBLIC_DEV",FAMILIES[1])[:2]
        for name in ("PUBLIC_EPISODIC_TABLE","CURRENT_QUERY_COUNTS"):
            m=PublicCounts(name,FAMILIES[1])
            m.fit(train)
            self.assertEqual(m.updates,len(train))
            frozen=m.checkpoint()
            self.assertTrue(math.isfinite(score(m,dev)))
            self.assertEqual(m.checkpoint(),frozen)
        m=PublicRecurrentMemory("GATED_4",17)
        m.fit(train)
        cp=m.checkpoint()
        self.assertTrue(math.isfinite(score(m,dev)))
        self.assertEqual(m.checkpoint(),cp)

    def test_select_only_uses_public_select_restarts(self):
        train=public_roles("O9_PUBLIC_TRAIN",FAMILIES[0])[:3]
        select=public_roles("O9_PUBLIC_SELECT",FAMILIES[0])[:2]
        dev=public_roles("O9_PUBLIC_DEV",FAMILIES[0])[:2]
        for name in VARIANTS:
            model,selection=selected(name,train,select)
            self.assertIn(selection["selected_start"],(17,31))
            self.assertTrue(math.isfinite(selection["public_select_nll"]))
            before=model.checkpoint()
            self.assertTrue(math.isfinite(score(model,dev)))
            self.assertEqual(model.checkpoint(),before)

    def test_null_query_has_no_privileged_features_or_protected_target(self):
        a=episode("O9_PUBLIC_DEV",FAMILIES[3],0)
        self.assertEqual(a,episode("O9_PUBLIC_DEV",FAMILIES[3],0))
        ep=list(a)
        ep[0]=(*ep[0],"hidden_generator_state")
        m=LearnedEpisodicRouting("LEARNED_WRITE_READ",17)
        with self.assertRaises(ValueError):
            m.predict(tuple(ep))


if __name__=="__main__":
    unittest.main()

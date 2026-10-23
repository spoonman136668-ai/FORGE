"""O10 tests of exact public custody, learned composition gradient and controls."""
import math
import unittest

from public_source import (
    FAMILIES,ROLES,ROLE_COUNTS,QUERY_TIMES,UnauthorizedPublicSource,
    episode,public_episodes,seed,query_info,digest,
)
from phase import PublicPhaseComposer,VARIANTS,nll
from controls import PublicCountControl
from o9_frozen_routing import LearnedEpisodicRouting
from runner import ARMS,guard,score,select


class O10CompositionTests(unittest.TestCase):
    def test_frozen_protocol_and_inventory(self):
        p=guard()
        self.assertEqual(tuple(p["roles"]),ROLES)
        self.assertEqual(p["count_per_role"],ROLE_COUNTS)
        self.assertEqual(tuple(p["arms"]),ARMS)
        self.assertEqual(p["frozen_training"]["train_epochs"],40)

    def test_public_sources_exact_sequence_and_digests(self):
        for family in FAMILIES:
            shas=[]
            for role in ROLES:
                episodes=public_episodes(role,family)
                self.assertEqual(len(episodes),ROLE_COUNTS[role])
                for ep in episodes:
                    q=query_info(ep)
                    self.assertIn(q["query_t"],QUERY_TIMES)
                    self.assertEqual(ep[q["query_t"]][1],2)
                    self.assertTrue(all(ep[t][2]==ep[t+1][0]
                                        for t in range(23)))
                shas.append(digest(episodes))
            self.assertEqual(len(set(shas)),3)

    def test_protected_previous_source_roles_refused(self):
        for role in ("Q21_HELD","HELD","ORIGINAL","O9_PUBLIC_DEV",
                     "O8_PUBLIC_DEV","FIT_TRAIN","DEV"):
            with self.assertRaises(UnauthorizedPublicSource):
                episode(role,FAMILIES[0],0)
        for i in (-1,96,True,"1",1.0):
            with self.assertRaises(UnauthorizedPublicSource):
                seed("O10_TRAIN",FAMILIES[0],i)

    def test_query_public_cue4_parity_and_action_counts(self):
        for ep in public_episodes("O10_TRAIN",FAMILIES[2])[:10]:
            q=query_info(ep)
            self.assertEqual(q["cue"],ep[0][0])
            self.assertEqual(q["cue4"],ep[4][0])
            self.assertEqual(q["selector"],ep[q["query_t"]-1][1])
            self.assertEqual(q["parity"],q["n1"]%2)
            self.assertEqual(q["n0"]+q["n1"],q["query_t"])

    def test_learned_phase_analytic_gradient_matches_finite_difference(self):
        ep=episode("O10_TRAIN",FAMILIES[0],0)
        m=PublicPhaseComposer("TRAINED_PHASE_MEMORY",17)
        loss,g=m.loss_gradient(ep)
        self.assertTrue(math.isfinite(loss))
        self.assertEqual(len(g),8)
        for j in range(8):
            old=m.w[j]
            h=1e-5
            m.w[j]=old+h
            plus=nll(query_info(ep)["target"],m.predict(ep))
            m.w[j]=old-h
            minus=nll(query_info(ep)["target"],m.predict(ep))
            m.w[j]=old
            self.assertAlmostEqual(g[j],(plus-minus)/(2*h),delta=2e-6,
                                   msg=f"O10_PARAM_GRAD_{j}")

    def test_frozen_phase_parameters_do_not_change(self):
        ep=episode("O10_TRAIN",FAMILIES[1],0)
        m=PublicPhaseComposer("FROZEN_PHASE_TRAINED_HEAD",17)
        old=m.w[:]
        for _ in range(10):
            m.step(ep)
        self.assertEqual(m.w[:2],old[:2])
        self.assertNotEqual(m.w[2:],old[2:])

    def test_fresh_trained_phase_and_linear_controls(self):
        train=public_episodes("O10_TRAIN",FAMILIES[0])[:3]
        dev=public_episodes("O10_DEV",FAMILIES[0])[:2]
        for variant in VARIANTS:
            m=PublicPhaseComposer(variant,17)
            before=m.checkpoint()
            m.fit(train)
            self.assertNotEqual(before,m.checkpoint())
            self.assertEqual(m.updates,40*len(train))
            cp=m.checkpoint()
            self.assertTrue(math.isfinite(score(m,dev)))
            self.assertEqual(cp,m.checkpoint())

    def test_memory_ablation_erases_phase_without_fitting(self):
        ep=public_episodes("O10_TRAIN",FAMILIES[2])[0]
        m=PublicPhaseComposer("TRAINED_PHASE_MEMORY",31)
        m.fit((ep,))
        cp=m.checkpoint()
        self.assertTrue(0<m.predict(ep,erased=True)<1)
        self.assertTrue(0<m.predict(ep)<1)
        self.assertEqual(cp,m.checkpoint())

    def test_strong_trained_controls_see_same_public_episodes(self):
        train=public_episodes("O10_TRAIN",FAMILIES[1])[:4]
        dev=public_episodes("O10_DEV",FAMILIES[1])[:2]
        for name in ("PUBLIC_ENGINEERED_EPISODIC","CURRENT_ONLY_COUNTS"):
            m=PublicCountControl(name)
            m.fit(train)
            self.assertEqual(m.updates,len(train))
            frozen=m.checkpoint()
            self.assertTrue(math.isfinite(score(m,dev)))
            self.assertEqual(frozen,m.checkpoint())
        o9=LearnedEpisodicRouting("LEARNED_WRITE_READ",17)
        o9.fit(train)
        frozen=o9.checkpoint()
        self.assertTrue(math.isfinite(score(o9,dev)))
        self.assertEqual(frozen,o9.checkpoint())

    def test_selection_does_not_modify_dev_models(self):
        train=public_episodes("O10_TRAIN",FAMILIES[2])[:3]
        select_ep=public_episodes("O10_SELECT",FAMILIES[2])[:2]
        dev=public_episodes("O10_DEV",FAMILIES[2])[:2]
        for arm in VARIANTS:
            m,meta=select(arm,train,select_ep)
            self.assertIn(meta["selected_start"],(17,31))
            cp=m.checkpoint()
            self.assertTrue(math.isfinite(score(m,dev)))
            self.assertEqual(cp,m.checkpoint())

    def test_null_and_public_input_fail_closed(self):
        ep=list(episode("O10_TRAIN",FAMILIES[3],0))
        m=PublicPhaseComposer("TRAINED_PHASE_MEMORY",17)
        ep[0]=(*ep[0],"hidden_state")
        with self.assertRaises(ValueError):
            m.predict(tuple(ep))
        self.assertAlmostEqual(nll(0,0.5),math.log(2),places=12)


if __name__=="__main__":
    unittest.main()

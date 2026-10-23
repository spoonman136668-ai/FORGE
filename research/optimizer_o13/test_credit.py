"""O13 prospective public source, actual temporal gradient and ablation tests."""
import math
import unittest

from public_source import (
    FAMILIES,ROLES,COUNTS,STEPS,ReservedRole,
    episode,public_episodes,seed,digest,
)
from learned_belief import LearnedPublicBelief,ARMS as NEW,SEEDS,FD_EPS
from o4_frozen_controls import PublicActionHMM,PublicHistoryCounts,score
from runner import ARMS,verify_protocol,choose,eval_loss


class O13PredictiveCredit(unittest.TestCase):
    def test_protocol_immutable_model_inventory(self):
        p=verify_protocol()
        self.assertEqual(tuple(p["learners"]),ARMS)
        self.assertEqual(p["roles_per_family"],COUNTS)
        self.assertEqual(p["frozen_training"]["minibatch_episodes"],8)

    def test_unique_new_public_roles_binary_episode_chain(self):
        for f in FAMILIES:
            hashes=[]
            for role in ROLES:
                batch=public_episodes(role,f)
                self.assertEqual(len(batch),COUNTS[role])
                for ep in batch:
                    self.assertEqual(len(ep),STEPS)
                    self.assertTrue(all(len(x)==3 and
                        all(type(t) is int and t in (0,1) for t in x)
                        for x in ep))
                    self.assertTrue(all(ep[i][2]==ep[i+1][0]
                                        for i in range(STEPS-1)))
                hashes.append(digest(batch))
            self.assertEqual(len(set(hashes)),3)

    def test_scientific_prior_roles_prohibited(self):
        for ro in ("HELD","Q21N01","O12_TRAIN_DIAGNOSTIC",
                   "O10_DEV","O13_DEV","O4_PUBLIC_DEV","ORIGINAL"):
            with self.assertRaises(ReservedRole):
                episode(ro,FAMILIES[0],0)
        for index in (-1,48,True,1.0,"5"):
            with self.assertRaises(ReservedRole):
                seed("O13_PUBLIC_TRAIN",FAMILIES[0],index)

    def test_full_and_stopped_gradient_are_different_with_same_forward(self):
        eps=public_episodes(ROLES[0],FAMILIES[0])[:8]
        full=LearnedPublicBelief("FULL_CREDIT_BELIEF",17)
        stop=LearnedPublicBelief("STOP_CREDIT_BELIEF",17)
        self.assertEqual(full.w,stop.w)
        self.assertEqual(full.predict(eps[0]),stop.predict(eps[0]))
        g1,g2=full.minibatch_gradient(eps),stop.minibatch_gradient(eps)
        self.assertEqual(len(g1),5)
        self.assertTrue(all(math.isfinite(g) for g in g1+g2))
        self.assertTrue(any(abs(x-y)>1e-8 for x,y in zip(g1,g2)))
        self.assertEqual(full.w,stop.w)

    def test_full_gradient_estimate_stable_across_small_eps(self):
        eps=public_episodes(ROLES[0],FAMILIES[1])[:8]
        m=LearnedPublicBelief("FULL_CREDIT_BELIEF",31)
        a=m.minibatch_gradient(eps)
        self.assertTrue(all(abs(g)<10. for g in a))
        for j in range(5):
            saved=m.w[j]
            h=FD_EPS/2.
            m.w[j]=saved+h
            up=sum(m.mean_episode_loss(ep,m.w) for ep in eps)/len(eps)
            m.w[j]=saved-h
            dn=sum(m.mean_episode_loss(ep,m.w) for ep in eps)/len(eps)
            m.w[j]=saved
            self.assertAlmostEqual(a[j],(up-dn)/(2*h),delta=1e-6)

    def test_freeze_transitions_preserves_original_parameters(self):
        episodes=public_episodes(ROLES[0],FAMILIES[0])[:8]
        m=LearnedPublicBelief("FROZEN_TRANSITION_BELIEF",17)
        initial=m.w[2:4]
        m.fit(episodes)
        self.assertEqual(initial,m.w[2:4])
        self.assertEqual(m.updates,24)
        self.assertNotEqual(m.w[:2],LearnedPublicBelief(
            "FROZEN_TRANSITION_BELIEF",17).w[:2])

    def test_selected_full_checkpoint_is_inference_immutable(self):
        train=public_episodes(ROLES[0],FAMILIES[0])[:8]
        val=public_episodes(ROLES[1],FAMILIES[0])[:2]
        dev=public_episodes(ROLES[2],FAMILIES[0])[:2]
        model,meta=choose("FULL_CREDIT_BELIEF",train,val)
        self.assertIn(meta["selected_seed"],SEEDS)
        original=model.checkpoint()
        a=eval_loss(model,dev)
        b=eval_loss(model,dev,erased=True)
        self.assertTrue(math.isfinite(a) and math.isfinite(b))
        self.assertEqual(original,model.checkpoint())

    def test_original_em_hmm_and_public_counts_are_fitted(self):
        tr=public_episodes(ROLES[0],FAMILIES[1])[:8]
        dv=public_episodes(ROLES[2],FAMILIES[1])[:2]
        for factory in (lambda:PublicActionHMM(17),
                        lambda:PublicHistoryCounts(True),
                        lambda:PublicHistoryCounts(False)):
            m=factory()
            m.fit(tr)
            self.assertGreater(m.updates,0)
            original=m.checkpoint()
            self.assertTrue(math.isfinite(score(m,dv)))
            self.assertEqual(original,m.checkpoint())

    def test_latent_labels_and_invalid_binary_are_rejected(self):
        ep=list(public_episodes(ROLES[0],FAMILIES[0])[0])
        ep[0]=(*ep[0],"private_state")
        m=LearnedPublicBelief("FULL_CREDIT_BELIEF",17)
        with self.assertRaises((ValueError,TypeError)):
            m.predict(tuple(ep))
        self.assertEqual(m.updates,0)

    def test_new_episode_generation_reproducible(self):
        for f in FAMILIES:
            a=episode(ROLES[0],f,0)
            self.assertEqual(a,episode(ROLES[0],f,0))


if __name__=="__main__":
    unittest.main()

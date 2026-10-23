"""O10 adversarial public paired-intervention and learning qualification."""
import math
import unittest
from public_source import (
    FAMILIES,ROLES,COUNTS,STEPS,QUERY_TIMES,ACTION_INTERVENTION,
    RoleRefused,seed,episode,paired,pairs_for_role,query_info,role_digest,
)
from trainable_memory import TrainedMemory
from recurrent_memory import PublicRecurrentMemory
from public_controls import PublicQueryCounts,PublicMemoryLogistic
from runner import ARMS,protocol_guard,fit_selected,score_pair,Uniform


class O10CounterfactualMemoryTests(unittest.TestCase):
    def test_exact_protocol_and_model_inventory(self):
        p=protocol_guard()
        self.assertEqual(tuple(p["arms"]),ARMS)
        self.assertEqual(p["source"]["episode_counts"],COUNTS)
        self.assertEqual(p["source"]["intervention_action_time"],4)
        self.assertEqual(p["evaluation"]["cross_os"].startswith("9 exact"),True)

    def test_source_roles_protected_and_disjoint(self):
        for f in FAMILIES:
            hashes=[]
            for role in ROLES:
                data=pairs_for_role(role,f)
                self.assertEqual(len(data),COUNTS[role])
                self.assertTrue(all(len(pair)==2 and all(len(ep)==STEPS
                                       for ep in pair) for pair in data))
                hashes.append(role_digest(data))
            self.assertEqual(len(set(hashes)),3)
        for role in ("Q21N01_HELD","HELD","ORIGINAL","FIT_TRAIN",
                     "O9_PUBLIC_DEV","O8_PUBLIC_TRAIN","DEV"):
            with self.assertRaises(RoleRefused):
                episode(role,FAMILIES[0],0)
        for bad in (-1,96,True,"1",1.0):
            with self.assertRaises(RoleRefused):
                seed("O10_TRAIN",FAMILIES[0],bad)

    def test_controlled_initial_cue_causal_effect_excludes_distractor_shift(self):
        base,twin=paired("O10_DEV","CUE_RECALL",0)
        q=query_info(base)["query_t"]
        self.assertIn(q,QUERY_TIMES)
        self.assertEqual(base[0][0]^twin[0][0],1)
        self.assertEqual(base[q][2]^twin[q][2],1)
        self.assertEqual(base[q][1],twin[q][1])
        for t in range(1,q):
            self.assertEqual(base[t],twin[t])
        self.assertEqual(query_info(twin)["query_t"],q)

    def test_early_action_parity_intervention_one_bit_and_shared_noise(self):
        for i in range(5):
            b,t=paired("O10_DEV","ACTION_PARITY",i)
            q=query_info(b)["query_t"]
            self.assertGreater(q,ACTION_INTERVENTION)
            self.assertEqual(
                b[ACTION_INTERVENTION][1]^t[ACTION_INTERVENTION][1],1)
            self.assertEqual(query_info(b)["cue"],query_info(t)["cue"])
            self.assertEqual(query_info(b)["parity"]^query_info(t)["parity"],1)
            self.assertEqual(b[q][2]^t[q][2],1)
            for x in range(q):
                if x==ACTION_INTERVENTION:
                    self.assertEqual(b[x][0],t[x][0])
                    self.assertEqual(b[x][2],t[x][2])
                else:
                    self.assertEqual(b[x],t[x])

    def test_null_intervention_does_not_change_query_truth(self):
        for i in range(5):
            b,t=paired("O10_DEV","NULL_NO_EFFECT",i)
            self.assertEqual(query_info(b)["target"],query_info(t)["target"])
            self.assertEqual(query_info(b)["cue"]^query_info(t)["cue"],1)

    def test_model_receives_public_events_only_and_bptt_is_trainable(self):
        tr=[p[0] for p in pairs_for_role("O10_TRAIN","CUE_RECALL")[:3]]
        for kind in ("LEARNED_EXTERNAL_WRITE_READ_2","GRU_2","GRU_4"):
            m=TrainedMemory(kind,17)
            old=m.checkpoint()
            m.fit(tr)
            self.assertNotEqual(m.checkpoint(),old)
            self.assertGreater(m.updates,0)
            self.assertTrue(all(0<m.predict(ep)<1 for ep in tr))
        m=TrainedMemory("GRU_2",17)
        forged=list(tr[0])
        forged[0]=(*forged[0],"private_hidden_cue")
        with self.assertRaises(ValueError):
            m.predict(tuple(forged))

    def test_no_future_target_or_intervention_flag_leakage(self):
        b,_=paired("O10_DEV","CUE_RECALL",0)
        q=query_info(b)["query_t"]
        target_flipped=list(b)
        o,a,y=target_flipped[q]
        target_flipped[q]=(o,a,1-y)
        after_o,after_a,after_y=target_flipped[q+1]
        target_flipped[q+1]=(1-y,after_a,after_y)
        for m in (TrainedMemory("GRU_2",17),
                  TrainedMemory("LEARNED_EXTERNAL_WRITE_READ_2",17),
                  PublicRecurrentMemory("GATED_4",17)):
            self.assertAlmostEqual(m.predict(b),m.predict(tuple(target_flipped)),
                                   places=12)

    def test_paired_alignment_sign_for_strong_public_episodic_control(self):
        family="CUE_RECALL"
        train=[p[0] for p in pairs_for_role("O10_TRAIN",family)]
        dev=pairs_for_role("O10_DEV",family)[:4]
        m=PublicQueryCounts("FULL_PUBLIC_EPISODIC")
        m.fit(train)
        before=m.checkpoint()
        score=score_pair(m,dev)
        self.assertGreater(score["signed_causal_alignment"],0)
        self.assertTrue(math.isfinite(score["paired_dev_query_nll"]))
        self.assertEqual(m.checkpoint(),before)

    def test_trained_models_are_frozen_on_dev_and_erasure_is_weight_preserving(self):
        train=tuple(p[0] for p in pairs_for_role("O10_TRAIN","ACTION_PARITY")[:3])
        select=tuple(p[0] for p in pairs_for_role("O10_SELECT","ACTION_PARITY")[:2])
        dev=pairs_for_role("O10_DEV","ACTION_PARITY")[:2]
        for name in ("LEARNED_WRITE_READ_2","GRU_2","O8_GATED_4"):
            m,selection=fit_selected(name,train,select)
            self.assertIn(selection["selected_seed"],(17,31))
            cp=m.checkpoint()
            normal=score_pair(m,dev)
            self.assertTrue(math.isfinite(normal["paired_dev_query_nll"]))
            if name=="LEARNED_WRITE_READ_2":
                erased=score_pair(m,dev,erased=True)
                self.assertEqual(cp,m.checkpoint())
                self.assertTrue(math.isfinite(erased["paired_dev_query_nll"]))
            self.assertEqual(cp,m.checkpoint())

    def test_iid_null_has_zero_signed_true_causal_alignment(self):
        dev=pairs_for_role("O10_DEV","NULL_NO_EFFECT")
        for m in (Uniform(),TrainedMemory("LEARNED_EXTERNAL_WRITE_READ_2",17)):
            result=score_pair(m,dev)
            self.assertEqual(result["signed_causal_alignment"],0)
            self.assertTrue(math.isfinite(result["paired_dev_query_nll"]))


if __name__=="__main__":
    unittest.main()

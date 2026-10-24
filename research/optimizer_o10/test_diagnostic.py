"""O10 identity, no answer leakage, trained diagnostic probes and capacity tests."""
import math
import unittest

from public_source import (
    ROLES,FAMILIES,COUNTS,STEPS,QUERY_TIMES,SourceIdentityRejected,
    episode,public_episodes,source_digest,seed,query_info,
)
from o9_exact_trainable_memory import TrainedMemory
from probes import (
    PublicProbe,PublicEpisodicCounts,probe_examples,evaluate_probe,features,
)
from runner import verify_protocol,select_model,query_nll,MODELS,PROBES


class O10EncodeReadoutTests(unittest.TestCase):
    def test_protocol_frozen_and_original_o9_model_bytes_pinned(self):
        p=verify_protocol()
        self.assertEqual(p["predecessor_custody"]["O9_original_memory_blob"],
                         "007f22006211439e625c1c317d32254acf902d74")
        self.assertEqual(set(p["frozen_fit"]["models"]),set(MODELS))
        self.assertEqual(p["frozen_fit"]["epochs"],12)

    def test_all_new_public_sources_role_disjoint_replayable(self):
        for family in FAMILIES:
            identities=[]
            for role in ROLES:
                batch=public_episodes(role,family)
                self.assertEqual(len(batch),COUNTS[role])
                self.assertEqual(len(batch[0]),STEPS)
                for ep in batch:
                    q=query_info(ep)
                    self.assertIn(q["query_t"],QUERY_TIMES)
                    self.assertEqual(ep[q["query_t"]][1],2)
                    self.assertTrue(all(ep[i][2]==ep[i+1][0]
                                        for i in range(STEPS-1)))
                identities.append(source_digest(batch))
            self.assertEqual(len(set(identities)),3)
        self.assertEqual(episode(ROLES[0],FAMILIES[0],0),
                         episode(ROLES[0],FAMILIES[0],0))

    def test_old_and_protected_role_names_fail_closed(self):
        for role in ("O9_PUBLIC_DEV","O8_PUBLIC_TRAIN","Q21_HELD",
                     "Q21N01_FIT_TRAIN","HELD","ORIGINAL","FIT_TRAIN","DEV"):
            with self.assertRaises(SourceIdentityRejected):
                episode(role,FAMILIES[0],0)
        for bad in (-1,96,True,1.0,"0"):
            with self.assertRaises(SourceIdentityRejected):
                seed(ROLES[0],FAMILIES[0],bad)

    def test_same_public_inputs_and_identical_57_parameter_budget(self):
        models={name:TrainedMemory(kind,17) for name,kind in MODELS.items()}
        self.assertEqual(len(models),2)
        for m in models.values():
            self.assertEqual(m.dim,2)
            self.assertEqual(m.parameter_count(),57)
            self.assertEqual(len(m._params()),57)

    def test_query_answer_not_used_in_recurrent_state_or_features(self):
        ep=public_episodes(ROLES[0],FAMILIES[1])[0]
        q=query_info(ep)["query_t"]
        changed=list(ep)
        obs,action,target=changed[q]
        changed[q]=(obs,action,1-target)
        next_obs,next_act,next_target=changed[q+1]
        changed[q+1]=(1-target,next_act,next_target)
        for name,kind in MODELS.items():
            m=TrainedMemory(kind,17)
            self.assertAlmostEqual(m.predict(ep),m.predict(tuple(changed)),places=12)
            before=features(ep,m)
            after=features(tuple(changed),m)
            self.assertEqual(before,after)

    def test_probe_only_uses_train_and_cannot_change_model_state(self):
        train=public_episodes(ROLES[0],FAMILIES[0])[:4]
        dev=public_episodes(ROLES[2],FAMILIES[0])[:3]
        for kind in MODELS.values():
            m=TrainedMemory(kind,17)
            m.fit(train)
            cp=m.checkpoint()
            for feature,label in PROBES:
                p=PublicProbe(feature+"_TO_"+label)
                examples=probe_examples(train,m,feature,label)
                p.fit(examples)
                frozen=p.checkpoint()
                val=evaluate_probe(p,probe_examples(dev,m,feature,label))
                self.assertTrue(math.isfinite(val))
                self.assertEqual(frozen,p.checkpoint())
                self.assertEqual(cp,m.checkpoint())

    def test_fitted_probe_detects_known_public_separable_signal(self):
        data=tuple(((float(i%2),float((i//2)%2)),i%2)
                   for i in range(256))
        m=PublicProbe("SYNTHETIC_DIAGNOSTIC")
        m.fit(data)
        self.assertLess(evaluate_probe(m,data),0.15)
        self.assertEqual(m.updates,25600)

    def test_actual_recurrent_train_and_select_no_dev_update(self):
        train=public_episodes(ROLES[0],FAMILIES[1])[:3]
        select=public_episodes(ROLES[1],FAMILIES[1])[:2]
        dev=public_episodes(ROLES[2],FAMILIES[1])[:2]
        for name in MODELS:
            m,meta=select_model(name,train,select)
            self.assertIn(meta["selected_start"],(17,31))
            self.assertTrue(math.isfinite(meta["public_select_nll"]))
            self.assertEqual(m.updates,3*12)
            cp=m.checkpoint()
            self.assertTrue(math.isfinite(query_nll(m,dev)))
            self.assertTrue(math.isfinite(query_nll(m,dev,erased=True)))
            self.assertEqual(cp,m.checkpoint())

    def test_explicit_episodic_control_fits_and_preserves_public_cue(self):
        tr=public_episodes(ROLES[0],FAMILIES[1])[:12]
        dv=public_episodes(ROLES[2],FAMILIES[1])[:4]
        table=PublicEpisodicCounts()
        table.fit(tr)
        self.assertEqual(table.updates,12)
        cp=table.checkpoint()
        self.assertTrue(all(0<table.predict(ep)<1 for ep in dv))
        self.assertEqual(cp,table.checkpoint())

    def test_forged_hidden_label_and_broken_source_are_rejected(self):
        ep=public_episodes(ROLES[0],FAMILIES[0])[0]
        rows=list(ep)
        rows[0]=(*rows[0],"privileged")
        m=TrainedMemory("GRU_2",17)
        frozen=m.checkpoint()
        with self.assertRaises(ValueError):
            m.fit((tuple(rows),))
        broken=list(ep)
        broken[2]=(1-broken[2][0],broken[2][1],broken[2][2])
        with self.assertRaises(ValueError):
            m.predict(tuple(broken))
        self.assertEqual(frozen,m.checkpoint())


if __name__=="__main__":
    unittest.main()

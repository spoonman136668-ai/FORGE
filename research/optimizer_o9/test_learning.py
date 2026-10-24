"""O9 native falsification: public custody, BPTT update, controls and ablations."""
import math
import unittest

from public_source import (
    FAMILIES,ROLES,COUNTS,STEPS,QUERY_TIMES,ProtectedRoleRefused,
    seed,episode,all_public,query_info,role_digest,
)
from trainable_memory import TrainedMemory,KINDS,STARTS,EPOCHS
from public_controls import PublicQueryCounts,PublicMemoryLogistic
from runner import ARMS,check_protocol,eval_model,fit_select


class O9LearnedMemoryTests(unittest.TestCase):
    def test_frozen_protocol_prior_negative_custody_and_arm_inventory(self):
        p=check_protocol()
        self.assertEqual(tuple(p["models"]),ARMS)
        self.assertEqual(p["fresh_public_source"]["counts"],COUNTS)
        self.assertEqual(p["fresh_public_source"]["length"],STEPS)
        self.assertIn("Q20 scientific negatives",p["preserve"])

    def test_distinct_new_roles_delayed_queries_and_public_input_chain(self):
        for family in FAMILIES:
            role_hashes=[]
            for role in ROLES:
                data=all_public(role,family)
                self.assertEqual(len(data),COUNTS[role])
                self.assertEqual(len(data[0]),STEPS)
                for ep in data:
                    self.assertTrue(all(len(row)==3 and row[0] in (0,1)
                                        and row[1] in (0,1,2)
                                        and row[2] in (0,1)
                                        for row in ep))
                    self.assertTrue(all(ep[i][2]==ep[i+1][0]
                                        for i in range(STEPS-1)))
                    self.assertIn(query_info(ep)["query_t"],QUERY_TIMES)
                role_hashes.append(role_digest(data))
            self.assertEqual(len(set(role_hashes)),len(ROLES))

    def test_protected_and_prior_sources_fail_closed(self):
        for role in ("HELD","ORIGINAL","FIT_TRAIN","Q21N01_HELD",
                     "O8_PUBLIC_TRAIN","O7_DEV","O6_PUBLIC_DEV","DEV"):
            with self.assertRaises(ProtectedRoleRefused):
                episode(role,FAMILIES[0],0)
        for bad in (True,-1,96,1.0,"1"):
            with self.assertRaises(ProtectedRoleRefused):
                seed(ROLES[0],FAMILIES[0],bad)

    def test_model_capacity_and_trainable_write_read_routing(self):
        models={kind:TrainedMemory(kind,17) for kind in KINDS}
        self.assertEqual(models["LEARNED_EXTERNAL_WRITE_READ_1"].dim,1)
        self.assertEqual(models["LEARNED_EXTERNAL_WRITE_READ_2"].dim,2)
        self.assertEqual(models["GRU_2"].dim,2)
        self.assertEqual(models["GRU_4"].dim,4)
        for kind,m in models.items():
            self.assertEqual(len(m._params()),m.parameter_count())
            if kind.startswith("LEARNED"):
                self.assertTrue(len(m.read)==m.dim)
                self.assertEqual(len(m.reset),0)
            else:
                self.assertTrue(len(m.reset)==m.dim)
                self.assertEqual(len(m.read),0)

    def test_actual_query_only_bptt_changes_all_relevant_weights(self):
        data=all_public(ROLES[0],FAMILIES[0])[:4]
        for kind in KINDS:
            with self.subTest(kind=kind):
                m=TrainedMemory(kind,17)
                before=[row[:] for row in m.write]
                before_content=[row[:] for row in m.content]
                before_read=[row[:] for row in m.read]
                cp=m.checkpoint()
                m.fit(data)
                self.assertNotEqual(cp,m.checkpoint())
                self.assertEqual(m.updates,EPOCHS*len(data))
                self.assertNotEqual(before,m.write)
                self.assertNotEqual(before_content,m.content)
                if m.read:
                    self.assertNotEqual(before_read,m.read)
                self.assertTrue(all(math.isfinite(m.predict(ep)) and
                                    0<m.predict(ep)<1 for ep in data))

    def test_bptt_output_bias_moves_toward_training_query_label(self):
        # At first Adam step output-bias derivative is p-y. Its update must
        # move in the correct sign for both GRU and external-memory models.
        for kind in ("GRU_2","LEARNED_EXTERNAL_WRITE_READ_2"):
            for target in (0,1):
                ep=next(ep for ep in all_public(ROLES[0],FAMILIES[0])
                        if query_info(ep)["target"]==target)
                m=TrainedMemory(kind,17)
                old=m.out[0]
                m.fit_episode(ep)
                self.assertTrue((m.out[0]-old)*(2*target-1)>0)

    def test_history_erasure_query_ablation_uses_same_checkpoint(self):
        data=all_public(ROLES[0],FAMILIES[0])[:3]
        m=TrainedMemory("LEARNED_EXTERNAL_WRITE_READ_2",17)
        m.fit(data)
        before=m.checkpoint()
        self.assertTrue(any(abs(m.predict(ep)-m.predict(ep,erased_query=True))>1e-11
                            for ep in data))
        self.assertEqual(before,m.checkpoint())

    def test_no_future_query_answer_leakage(self):
        ep=all_public(ROLES[0],FAMILIES[0])[0]
        q=query_info(ep)["query_t"]
        flipped=list(ep)
        obs,act,y=flipped[q]
        flipped[q]=(obs,act,1-y)
        next_obs,next_act,next_y=flipped[q+1]
        flipped[q+1]=(1-y,next_act,next_y)
        # Also maintain public chain after q+1: it already uses original
        # row q+1 target as row q+2 observation.
        for kind in KINDS:
            m=TrainedMemory(kind,17)
            self.assertAlmostEqual(m.predict(ep),m.predict(tuple(flipped)),
                                   places=12)

    def test_recurrent_controls_fit_identical_train_and_select_only(self):
        training=all_public(ROLES[0],FAMILIES[1])[:3]
        selection=all_public(ROLES[1],FAMILIES[1])[:2]
        dev=all_public(ROLES[2],FAMILIES[1])[:2]
        for kind in KINDS+("O8_GATED_4",):
            m,meta=fit_select(kind,training,selection)
            self.assertIn(meta["selected_seed"],STARTS)
            self.assertTrue(math.isfinite(meta["public_select_nll"]))
            self.assertGreater(m.updates,0)
            frozen=m.checkpoint()
            loss=eval_model(m,dev)
            self.assertTrue(math.isfinite(loss))
            self.assertEqual(frozen,m.checkpoint())

    def test_episodic_and_logistic_controls_actually_learn(self):
        tr=all_public(ROLES[0],FAMILIES[1])[:5]
        dv=all_public(ROLES[2],FAMILIES[1])[:3]
        for m in (PublicQueryCounts("CURRENT_QUERY"),
                  PublicQueryCounts("FULL_PUBLIC_EPISODIC"),
                  PublicMemoryLogistic()):
            before=m.checkpoint()
            m.fit(tr)
            self.assertNotEqual(before,m.checkpoint())
            self.assertGreater(m.updates,0)
            frozen=m.checkpoint()
            self.assertTrue(math.isfinite(eval_model(m,dv)))
            self.assertEqual(frozen,m.checkpoint())

    def test_forged_latent_fields_and_bad_episode_refused(self):
        ep=all_public(ROLES[0],FAMILIES[0])[0]
        forged=list(ep)
        forged[0]=(*forged[0],"hidden_state")
        m=TrainedMemory("GRU_2",17)
        before=m.checkpoint()
        with self.assertRaises(ValueError):
            m.fit((tuple(forged),))
        self.assertEqual(before,m.checkpoint())
        broken=list(ep)
        broken[1]=(1-broken[1][0],broken[1][1],broken[1][2])
        with self.assertRaises(ValueError):
            m.predict(tuple(broken))


if __name__=="__main__":
    unittest.main()

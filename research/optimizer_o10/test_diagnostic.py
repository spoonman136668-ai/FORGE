"""O10 falsification: role custody, temporal target isolation and frozen probes."""
import math
import unittest

from public_source import (
    FAMILIES, ROLES, COUNTS, QUERY_TIMES, STEPS, PublicSourceRefused,
    seed,episode,all_public,query_info,digest,
)
from frozen_o9_memory import TrainedMemory
from diagnostic_probes import (
    RECURRENT_KIND, FrozenStateProbe, PublicHistoryCounts,
    frozen_state_features, selected_model, query_score,
)
from runner import ARMS,check_protocol


class O10FaultIsolationTests(unittest.TestCase):
    def test_prospective_protocol_original_blob_and_full_inventory(self):
        p=check_protocol()
        self.assertEqual(tuple(p["roles"]),ROLES)
        self.assertEqual(len(ARMS),19)
        self.assertEqual(p["episodes_per_family"],COUNTS)
        self.assertEqual(p["episode_length"],32)
        self.assertIn("random reservoir",p["pre_registered_hypotheses"]["H_BASELINE"])

    def test_distinct_roles_and_full_public_chain(self):
        for fam in FAMILIES:
            shas=[]
            for role in ROLES:
                batch=all_public(role,fam)
                self.assertEqual(len(batch),COUNTS[role])
                for ep in batch:
                    self.assertEqual(len(ep),STEPS)
                    self.assertTrue(all(len(r)==3 and r[0] in (0,1)
                                        and r[1] in (0,1,2,3)
                                        and r[2] in (0,1) for r in ep))
                    self.assertTrue(all(ep[i][2]==ep[i+1][0]
                                        for i in range(STEPS-1)))
                    q=query_info(ep)
                    self.assertIn(q["query_t"],QUERY_TIMES)
                    self.assertEqual(ep[q["query_t"]][1],2)
                shas.append(digest(batch))
            self.assertEqual(len(set(shas)),len(ROLES))

    def test_scientific_and_old_dev_roles_rejected(self):
        for role in ("HELD","Q21N01_HELD","O9_PUBLIC_DEV",
                     "O8_PUBLIC_TRAIN","FIT_TRAIN","DEV"):
            with self.assertRaises(PublicSourceRefused):
                episode(role,FAMILIES[0],0)
        for index in (True,-1,64,1.5,"1"):
            with self.assertRaises(PublicSourceRefused):
                seed("O10_PUBLIC_TRAIN",FAMILIES[0],index)
        with self.assertRaises(PublicSourceRefused):
            episode("O10_PUBLIC_TRAIN","PROTECTED",0)

    def test_resettable_parity_is_public_computable_and_actually_resets(self):
        examples=all_public(ROLES[0],"RESETTABLE_PARITY")[:24]
        self.assertTrue(any(any(row[1]==3 for row in ep) for ep in examples))
        for ep in examples:
            details=query_info(ep)
            parity=0
            for _,act,_ in ep[:details["query_t"]]:
                if act==3:
                    parity=0
                elif act==1:
                    parity ^= 1
            self.assertEqual(details["parity"],parity)
            self.assertEqual(details["cue"],ep[0][0])

    def test_o9_original_same_architecture_two_hidden_cells(self):
        for kind in RECURRENT_KIND:
            model=TrainedMemory(kind,17)
            self.assertEqual(model.dim,2)
            self.assertEqual(model.parameter_count(),57)
            ep=all_public(ROLES[0],FAMILIES[1])[0]
            hidden=frozen_state_features(model,ep)
            self.assertEqual(len(hidden),4)
            self.assertTrue(all(math.isfinite(x) for x in hidden))

    def test_frozen_recurrent_checkpoint_and_fitted_probe(self):
        data=all_public(ROLES[0],FAMILIES[0])[:5]
        dev=all_public(ROLES[2],FAMILIES[0])[:4]
        net=TrainedMemory("GRU_2",17)
        net.fit(data)
        checkpoint=net.checkpoint()
        for target in ("target","cue","parity"):
            probe=FrozenStateProbe(target)
            before=probe.checkpoint()
            probe.fit(net,data)
            self.assertEqual(probe.updates,120*len(data))
            self.assertNotEqual(before,probe.checkpoint())
            loss=probe.score(net,dev)
            self.assertTrue(math.isfinite(loss))
            self.assertEqual(net.checkpoint(),checkpoint)

    def test_random_control_same_state_capacity_no_native_learning(self):
        training=all_public(ROLES[0],FAMILIES[1])[:5]
        control=TrainedMemory("LEARNED_EXTERNAL_WRITE_READ_2",31)
        snapshot=control.checkpoint()
        probe=FrozenStateProbe("target")
        probe.fit(control,training)
        self.assertTrue(math.isfinite(probe.score(
            control,all_public(ROLES[2],FAMILIES[1])[:2])))
        self.assertEqual(snapshot,control.checkpoint())

    def test_selection_uses_only_train_and_select(self):
        tr=all_public(ROLES[0],FAMILIES[1])[:4]
        sel=all_public(ROLES[1],FAMILIES[1])[:2]
        dv=all_public(ROLES[2],FAMILIES[1])[:2]
        for kind in RECURRENT_KIND:
            model,meta=selected_model(kind,tr,sel)
            self.assertIn(meta["selected_start"],(17,31))
            before=model.checkpoint()
            self.assertTrue(math.isfinite(query_score(model,dv)))
            self.assertTrue(math.isfinite(query_score(model,dv,erased=True)))
            self.assertEqual(model.checkpoint(),before)

    def test_query_next_label_cannot_leak_into_model_or_probe_inputs(self):
        sample=all_public(ROLES[0],FAMILIES[0])[0]
        q=query_info(sample)["query_t"]
        altered=list(sample)
        obs,act,target=altered[q]
        altered[q]=(obs,act,1-target)
        nxt,a_next,nxt_target=altered[q+1]
        altered[q+1]=(1-target,a_next,nxt_target)
        for kind in RECURRENT_KIND:
            model=TrainedMemory(kind,17)
            self.assertEqual(frozen_state_features(model,sample),
                             frozen_state_features(model,tuple(altered)))
            self.assertAlmostEqual(model.predict(sample),
                                   model.predict(tuple(altered)),places=12)

    def test_fitted_current_and_explicit_history_controls(self):
        tr=all_public(ROLES[0],FAMILIES[1])[:8]
        dv=all_public(ROLES[2],FAMILIES[1])[:4]
        for kind in ("CURRENT","EXPLICIT_RESET_PARITY"):
            model=PublicHistoryCounts(kind)
            model.fit(tr)
            self.assertEqual(model.updates,len(tr))
            cp=model.checkpoint()
            self.assertTrue(math.isfinite(model.score(dv)))
            self.assertEqual(cp,model.checkpoint())

    def test_forged_extra_hidden_state_rejected(self):
        sample=all_public(ROLES[0],FAMILIES[0])[0]
        invalid=list(sample)
        invalid[0]=(*invalid[0],"hidden")
        net=TrainedMemory("GRU_2",17)
        with self.assertRaises(ValueError):
            net.predict(tuple(invalid))
        before=net.checkpoint()
        with self.assertRaises(ValueError):
            FrozenStateProbe("cue").fit(net,(tuple(invalid),))
        self.assertEqual(net.checkpoint(),before)


if __name__=="__main__":
    unittest.main()

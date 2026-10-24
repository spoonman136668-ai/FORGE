"""O10 source fidelity, analytic gradient, trained controls and memory ablations."""
import math
import unittest
from public_source import (
    FAMILIES,ROLES,COUNTS,STEPS,QUERY_STEPS,RoleNotAdmitted,
    seed,episode,role_episodes,role_sha,query_info,public_program,
)
from learned_operator import PublicLearnedOperator,SEEDS,EPOCHS,nll
from conventional import FittedPublicCounts,PublicHistoryLogistic
from o9_gru_original import TrainedMemory
from runner import ARMS,protocol,select_model,query_loss


class O10LearnedCausalMemory(unittest.TestCase):
    def test_frozen_protocol_and_adversarial_source_inventory(self):
        p=protocol()
        self.assertEqual(tuple(p["arms"]),ARMS)
        self.assertEqual(p["episodes_by_role"],COUNTS)
        self.assertIn("Q20 negative",p["preserve"])

    def test_new_public_roles_contiguous_query_and_disjoint_sha(self):
        for family in FAMILIES:
            seen=[]
            for role in ROLES:
                batch=role_episodes(role,family)
                self.assertEqual(len(batch),COUNTS[role])
                for ep in batch:
                    self.assertEqual(len(ep),STEPS)
                    self.assertTrue(all(len(row)==3 and row[0] in (0,1) and
                                        row[1] in (0,1,2) and row[2] in (0,1)
                                        for row in ep))
                    self.assertTrue(all(ep[t][2]==ep[t+1][0]
                                        for t in range(STEPS-1)))
                    self.assertIn(query_info(ep)["query_t"],QUERY_STEPS)
                seen.append(role_sha(batch))
            self.assertEqual(len(set(seen)),3)

    def test_protected_and_previous_role_seeds_fail_closed(self):
        for role in ("HELD","ORIGINAL","DEV","FIT_TRAIN","O9_PUBLIC_DEV",
                     "O8_PUBLIC_TRAIN","Q21N01_VALID"):
            with self.assertRaises(RoleNotAdmitted):
                episode(role,FAMILIES[0],0)
        for index in (-1,True,"1",1.0,COUNTS[ROLES[0]]):
            with self.assertRaises(RoleNotAdmitted):
                seed(ROLES[0],FAMILIES[0],index)
        with self.assertRaises(RoleNotAdmitted):
            role_episodes(ROLES[0],"SECRET_PRIVATE_ORIGINAL")

    def test_markov_operator_real_learning_and_capacities(self):
        train=role_episodes(ROLES[0],FAMILIES[0])[:4]
        for tied,params in ((False,12),(True,8)):
            model=PublicLearnedOperator(17,action_tied=tied)
            self.assertEqual(model.parameters(),params)
            initial=model.checkpoint()
            model.fit(train)
            self.assertNotEqual(initial,model.checkpoint())
            self.assertEqual(model.updates,EPOCHS*len(train))
            self.assertTrue(all(0<model.predict(ep)<1 for ep in train))

    def test_analytic_bptt_finite_difference_on_public_train(self):
        ep=role_episodes(ROLES[0],FAMILIES[1])[0]
        for tied in (False,True):
            model=PublicLearnedOperator(17,action_tied=tied)
            loss,analytic=model.gradient_episode(ep)
            x=model._params()
            self.assertEqual(len(x),len(analytic))
            for index in (0,1,2,3,len(x)-2,len(x)-1):
                step=1e-5
                left=x[:]
                right=x[:]
                left[index]-=step
                right[index]+=step
                model._set(left)
                neg=nll(query_info(ep)["target"],model.predict(ep))
                model._set(right)
                pos=nll(query_info(ep)["target"],model.predict(ep))
                estimate=(pos-neg)/(2*step)
                model._set(x)
                self.assertAlmostEqual(analytic[index],estimate,delta=3e-6)

    def test_no_query_target_leak_and_no_dev_adaptation(self):
        ep=role_episodes(ROLES[0],FAMILIES[1])[0]
        q=query_info(ep)["query_t"]
        changed=list(ep)
        o,a,y=changed[q]
        changed[q]=(o,a,1-y)
        x,na,ny=changed[q+1]
        changed[q+1]=(1-y,na,ny)
        model=PublicLearnedOperator(17)
        self.assertAlmostEqual(model.predict(ep),model.predict(tuple(changed)),12)
        frozen=model.checkpoint()
        self.assertTrue(math.isfinite(query_loss(model,(ep,))))
        self.assertEqual(model.checkpoint(),frozen)

    def test_learned_memory_erasure_uses_same_trained_checkpoint(self):
        train=role_episodes(ROLES[0],FAMILIES[0])[:4]
        m=PublicLearnedOperator(31)
        m.fit(train)
        before=m.checkpoint()
        differences=[abs(m.predict(ep)-m.predict(ep,erased_query=True))
                     for ep in train]
        self.assertTrue(any(d>1e-12 for d in differences))
        self.assertEqual(before,m.checkpoint())

    def test_action_tying_ablation_reduces_actual_parameter_space(self):
        a=PublicLearnedOperator(17)
        b=PublicLearnedOperator(17,action_tied=True)
        self.assertEqual(a.parameters()-b.parameters(),4)
        self.assertNotEqual(a.checkpoint(),b.checkpoint())
        self.assertEqual(len(a.theta),8)
        self.assertEqual(len(b.theta),4)

    def test_same_public_train_baselines_fit_no_dev_updates(self):
        train=role_episodes(ROLES[0],FAMILIES[1])[:4]
        select=role_episodes(ROLES[1],FAMILIES[1])[:2]
        dev=role_episodes(ROLES[2],FAMILIES[1])[:2]
        for name in ("LEARNED_MARKOV_OPERATOR","ACTION_TIED_OPERATOR","O9_GRU_2"):
            model,receipt=select_model(name,train,select)
            self.assertIn(receipt["selected_seed"],SEEDS)
            self.assertTrue(math.isfinite(receipt["public_select_nll"]))
            cp=model.checkpoint()
            self.assertTrue(math.isfinite(query_loss(model,dev)))
            self.assertEqual(cp,model.checkpoint())
        for m in (FittedPublicCounts("PUBLIC_HISTORY"),
                  FittedPublicCounts("CURRENT"),PublicHistoryLogistic(),
                  FittedPublicCounts("ENGINEERED_WITNESS",FAMILIES[1])):
            m.fit(train)
            self.assertGreater(m.updates,0)
            cp=m.checkpoint()
            self.assertTrue(math.isfinite(query_loss(m,dev)))
            self.assertEqual(cp,m.checkpoint())

    def test_engineered_program_witness_is_public_but_privileged_mechanism(self):
        for family in FAMILIES:
            for ep in role_episodes(ROLES[0],family)[:4]:
                self.assertIn(public_program(ep,family),(0,1))
        m=FittedPublicCounts("ENGINEERED_WITNESS",FAMILIES[0])
        m.fit(role_episodes(ROLES[0],FAMILIES[0])[:4])
        self.assertIn(b'oracle_mechanism_privilege":true',m.checkpoint())

    def test_no_hidden_labels_can_be_injected(self):
        ep=role_episodes(ROLES[0],FAMILIES[0])[0]
        model=PublicLearnedOperator(17)
        cp=model.checkpoint()
        altered=list(ep)
        altered[0]=(*altered[0],"hidden_state")
        with self.assertRaises(ValueError):
            model.fit((tuple(altered),))
        self.assertEqual(cp,model.checkpoint())


if __name__=="__main__":
    unittest.main()

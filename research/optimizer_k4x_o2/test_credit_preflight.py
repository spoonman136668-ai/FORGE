"""Source-only mutation/credit tests. Does not import original environments."""
import json
import subprocess
import sys
import unittest
from dataclasses import replace
from credit_preflight import (PublicGrid,Event,LinearTD,features,public_from,
    handwritten_matched_pair,ablate_terminal_reward,preflight,LAM_TRACE,
    PARAMETERS)

class CreditPreflight(unittest.TestCase):
    def test_frozen_features_and_privilege_denial(self):
        state=PublicGrid(3,3,5,3,3,True)
        self.assertEqual(features(state),(1.,.125,0.,.0625,0.,0.,0.,1.,1.))
        raw={'X':3,'Y':3,'GoalX':5,'GoalY':3,'Direction':3,'FrontBlocked':True}
        self.assertEqual(public_from(raw),state)
        for key in ('walls','family','seed','hidden_map','oracle','traces'):
            with self.subTest(key=key),self.assertRaisesRegex(ValueError,'ONLY_SIX'):
                public_from({**raw,key:True})
        with self.assertRaises(ValueError):
            PublicGrid(3,3,5,3,3,1)
        with self.assertRaises(ValueError):
            Event(state,True,state,0.,False,False)

    def test_matched_params_samples_and_delayed_policy_contrast(self):
        fail,success=handwritten_matched_pair()
        self.assertEqual(fail[0].before,success[0].before)
        self.assertEqual([e.action for e in success],[1,2,2])
        self.assertEqual([e.reward for e in success],[0,0,1])
        td=LinearTD(0.);trace=LinearTD(LAM_TRACE)
        for ep in (fail,success):
            td.train(ep);trace.train(ep)
        self.assertEqual(len(td.weights),PARAMETERS)
        self.assertEqual(len(trace.weights),PARAMETERS)
        self.assertEqual((td.events_seen,trace.events_seen),(6,6))
        self.assertEqual(td.choose(success[0].before),2)  # generalization makes blocked forward spuriously attractive
        self.assertEqual(trace.choose(success[0].before),1)  # delayed terminal credit
        self.assertEqual(td.score(success[0].before,1),0.)
        self.assertGreater(trace.score(success[0].before,1),0.)

    def test_terminal_reward_causal_ablation(self):
        fail,success=handwritten_matched_pair()
        full=LinearTD(LAM_TRACE)
        without=LinearTD(LAM_TRACE)
        for ep in (fail,success):
            full.train(ep);without.train(ablate_terminal_reward(ep))
        start=success[0].before
        self.assertGreater(full.score(start,1),without.score(start,1))
        self.assertAlmostEqual(full.score(start,1)-without.score(start,1),
                               .2*(.9*.8)**2*sum(z*z for z in features(start)),places=10)
        self.assertEqual(full.events_seen,without.events_seen)

    def test_zero_consequence_null_and_negative_controls(self):
        s=PublicGrid(3,3,5,3,0,True)
        ep=(Event(s,2,s,0.,False,False),
            Event(s,0,s,0.,False,False),
            Event(s,1,s,0.,False,True))
        td=LinearTD(0.).train(ep)
        trace=LinearTD(LAM_TRACE).train(ep)
        self.assertEqual(td.weights,[0.]*PARAMETERS)
        self.assertEqual(trace.weights,[0.]*PARAMETERS)
        for model in (td,trace):
            self.assertEqual(model.choose(s),0)

    def test_atomic_malformed_sequence_refusal(self):
        fail,success=handwritten_matched_pair()
        m=LinearTD(LAM_TRACE)
        baseline=m.snapshot()
        with self.assertRaisesRegex(ValueError,'PUBLIC_SEQUENCE_DISCONTINUITY'):
            m.train((success[0],fail[1],success[2]))
        self.assertEqual(m.snapshot(),baseline)
        with self.assertRaisesRegex(ValueError,'EARLY_TERMINAL_THEN_MORE_EVENTS'):
            m.train((replace(success[0],terminated=True),)+success[1:])
        self.assertEqual(m.snapshot(),baseline)
        with self.assertRaisesRegex(ValueError,'COMPLETE_EPISODE_REQUIRED'):
            m.train(success[:2])
        self.assertEqual(m.snapshot(),baseline)

    def test_cold_process_checkpoint_and_tamper(self):
        fail,success=handwritten_matched_pair()
        m=LinearTD(LAM_TRACE)
        for ep in (fail,success):m.train(ep)
        raw=m.snapshot()
        self.assertEqual(LinearTD.restore(raw).snapshot(),raw)
        script='from credit_preflight import LinearTD,handwritten_matched_pair; import sys; m=LinearTD.restore(sys.stdin.buffer.read()); print(m.choose(handwritten_matched_pair()[1][0].before))'
        p=subprocess.run([sys.executable,'-B','-c',script],input=raw,capture_output=True,
                         check=True,timeout=10)
        self.assertEqual(p.stdout.strip(),b'1')
        wire=json.loads(raw);wire['payload']['weights'][0]+=1
        with self.assertRaisesRegex(ValueError,'TAMPERED'):
            LinearTD.restore(json.dumps(wire).encode())

    def test_explicit_zero_original_science(self):
        result=preflight()
        self.assertEqual(result['status'],'HANDWRITTEN_CAPACITY_MATCHED_ONLY')
        self.assertEqual(result['native_original_episodes'],0)
        self.assertEqual(result['reserved_fit_check_dev_roles'],0)
        self.assertFalse(result['scientific_fsa_permit'])
        self.assertEqual(result['matched_trainable_parameters_each'],27)
        self.assertEqual(result['matched_training_events_each'],6)
        self.assertEqual(result['td0_first_action'],2)
        self.assertEqual(result['td_lambda_first_action'],1)

if __name__=='__main__':unittest.main()

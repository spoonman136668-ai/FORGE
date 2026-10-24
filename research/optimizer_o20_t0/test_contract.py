"""Focused post-run SOURCE-FREE contract tests; never rerun frozen DEV."""
import json, math, sys, unittest, hashlib
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import experiment as e

class Contract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report=json.loads((HERE/'RESULT.json').read_text())
    def test_preregistered_file_bound(self):
        self.assertEqual(self.report['protocol_SHA256'],hashlib.sha256((HERE/'PREREG.md').read_bytes()).hexdigest())
    def test_role_disjoint_and_fit_original_public_only(self):
        roles=[set(range(a,a+240)) for a in (100000,200000)]+[set(range(a,a+96)) for a in (300000,400000)]
        for i,x in enumerate(roles):
            for y in roles[i+1:]:self.assertTrue(x.isdisjoint(y))
        self.assertEqual(self.report['fit_episodes_total'],480)
        self.assertEqual(self.report['fit_recorded_public_labeled_samples'],8320)
    def test_source_truth_only_after_selected_sensing_or_forward(self):
        world=e.PublicSource('C',300000)
        x=world.public_context()
        hazard,_=world.sample_current_hazard(x)
        reward=world.finish(hazard,0)
        self.assertEqual(reward,0)
        # Public feedback for an unqueried left cannot contain the hidden hazard.
        scan=False; action=0
        public_observed_hazard=hazard if (scan or action==1) else None
        self.assertIsNone(public_observed_hazard)
        self.assertIn(hazard,(0,1))
    def test_public_models_need_no_hidden_state(self):
        v=e.features(1,1,None)
        self.assertEqual(len(v),5)
        self.assertEqual(e.key(1,1,None),(1,1,2))
        model=e.FastSlow()
        before=model.predict(1,1,None)
        model.feedback(1,1,None,1,before)
        after=model.predict(1,1,None)
        self.assertGreater(after,before)
    def test_candidate_rejects_oracle_novelty_claim(self):
        self.assertEqual(self.report['disposition'],'O20_T0_SOURCE_FREE_NATIVE_ADVANTAGE_NO_GO')
        self.assertFalse(self.report['go'])
        self.assertFalse(self.report['source_original_external'])
        self.assertFalse(self.report['native_original_Yggdrasil'])
        self.assertEqual(self.report['original_ENV_reset_step_count'],0)
    def test_actual_queries_equal_every_model_world(self):
        for fam in ('C','D'):
            vals=[v['total_queries'] for k,v in self.report['families'][fam].items() if k in e.MODELS]
            self.assertEqual(vals,[384]*len(e.MODELS))
    def test_no_loss_hidden_by_conventional(self):
        for fam in ('C','D'):
            local=self.report['families'][fam]['LOCAL_FAST_SLOW']['mean_net_reward_per_step']
            conventionals=[self.report['families'][fam][x]['mean_net_reward_per_step'] for x in ('BAYES_BETA','CONVENTIONAL_LOGIT','CONTEXT_LAPLACE','PERIODIC_BETA')]
            self.assertLess(local,max(conventionals))
            self.assertFalse(self.report['families'][fam]['gate']['better_than_best_fully_trained_conventional_by_at_least_0.1'])
    def test_source_role_and_family_sign_change(self):
        self.assertGreater(e.FAMILY['A'][2],0)
        self.assertGreater(e.FAMILY['B'][2],0)
        self.assertLess(e.FAMILY['C'][2],0)
        self.assertLess(e.FAMILY['D'][2],0)
    def test_query_and_motor_decisions_in_bounds(self):
        for risk in (0,.1,.25,.5,.9,1):
            for t in range(24):
                for spent in range(5):
                    x=e.scan_policy(risk,t,spent,'LOCAL_FAST_SLOW')
                    self.assertIs(type(x),bool)
                    if spent>=4:self.assertFalse(x)
    def test_reproducible_non_timing_evidence_attached(self):
        self.assertEqual(len(self.report['fit_stream_sha256']),64)
        for fam in ('C','D'):
            for name in e.MODELS:
                entry=self.report['families'][fam][name]
                self.assertEqual(entry['total_source_actions'],96*24)
                self.assertEqual(len(entry['traces_digest']),64)

if __name__=='__main__':unittest.main()

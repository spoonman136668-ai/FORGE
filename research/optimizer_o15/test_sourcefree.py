"""Source-FREE O15 prospectively frozen memory and source-role preflight tests."""
import sys, unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from runner import (ARMS,DELAYS,REPS,FIT_N,DEV_N,source_seed,
                    LocalVotes,BayesianLag,SoftAttention,LogisticAction,
                    model_fit,observed)

class O15PreSource(unittest.TestCase):
    def test_genuine_original_source_role_identity(self):
        ids=[source_seed(role,di,rep,i)
             for role,n in (("FIT",FIT_N),("DEV",DEV_N))
             for di in range(2) for rep in REPS for i in range(n)]
        self.assertEqual(len(ids),len(set(ids)))
        self.assertEqual(len(ids),2*3*(FIT_N+DEV_N))
        self.assertEqual(len(ARMS),7)
        self.assertEqual(DELAYS,(4,8))
    def test_local_can_learn_lag_from_delayed_public_reward(self):
        for lag in (3,7):
            sample=[]
            for ep in range(12):
                history=[(i*7+ep*3+i//5)%4 for i in range(51)]
                rows=[]
                for t in range(51):
                    action=(t+ep)%4
                    reward=0 if t<lag else (1 if action==history[t-lag] else -1)
                    rows.append({"public_time_step":t,
                       "public_suit_history":tuple(history[:t+1]),
                       "real_original_source_action":action,
                       "real_original_source_reward_sign":reward})
                sample.append({"source_public_observed_original_actions":rows,
                               "source_public_suit_observations":history})
            fitted=LocalVotes();fitted.fit(sample)
            self.assertEqual(fitted.learned_lag(),lag)
            self.assertGreater(fitted.updates,0)
            self.assertEqual(LocalVotes(1).shift,1)
    def test_predictors_accept_only_public_history(self):
        past=[0,1,2,3,0]
        self.assertEqual(observed(past,4,2),2)
        self.assertIsNone(observed(past,4,7))
        self.assertEqual(len(LogisticAction().w),13)
        self.assertEqual(len(SoftAttention().w),12)
        self.assertEqual(len(BayesianLag().loglik),12)
    def test_frozen_model_fit_and_shared_state_for_ablation(self):
        sample=[]
        for ep in range(2):
            sample.append({"source_public_observed_original_actions":[{
                "public_time_step":3,"public_suit_history":(0,1,2,3),
                "real_original_source_action":0,
                "real_original_source_reward_sign":1}],
                "source_public_suit_observations":[0,1,2,3]})
        m,c=model_fit(sample,4)
        self.assertEqual(m[ARMS[6]].v,m[ARMS[0]].v)
        self.assertEqual(m[ARMS[6]].learned_lag(),
                         m[ARMS[0]].learned_lag()%12+1)
        self.assertIn("checkpoint_bytes",c[ARMS[0]])
if __name__=="__main__":unittest.main()

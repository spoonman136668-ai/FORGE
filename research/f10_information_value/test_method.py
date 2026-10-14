"""F10 learned-value causality, budget and zero-first-use tests.

Test fixtures are synthetic and MUST NOT be treated as scientific records.
"""
from copy import deepcopy
import inspect
import unittest
from policy import EPISODES,PROBES,choose,trace_review,SCHEMA,MODEL_STATUS,public_start
from worker import evaluate,SOURCE_COMMIT
from train import train

def model():
    return {"schema":SCHEMA,"status":MODEL_STATUS,
            "source_commit":SOURCE_COMMIT,
            "train_seeds":[67204,67205],
            "validation_seeds":[67206,67207],
            "public_scalar_reads":10,"retained_limit":9,
            "first_use_claims":0,"scientific_dispatch_authorized":False,
            "table":[{"episode":t,"prior_anomaly":flag,"offset":o,
                      "observations":0,"anomalies":0}
                     for t in PROBES for flag in (0,1) for o in range(14)]}

def synthetic_public(model):
    history={}
    for t in EPISODES:
        cells=choose(t,history,model)
        history[t]={cell:(3+5*cell+t)%16 for cell in cells}
    return history

class ValueMethodTests(unittest.TestCase):
    def test_source_and_previous_data_scope(self):
        self.assertEqual(SOURCE_COMMIT,"5797a257a75fe139313e8486cd1a1ae79c44b148")
        self.assertEqual(list(inspect.signature(choose).parameters),
                         ["t","history","model"])
        m=model()
        h=synthetic_public(m)
        result=trace_review(h,m)
        self.assertEqual(result["reads"],10)
        self.assertEqual(result["distinct_nonanchors"],6)
        self.assertEqual(len({x for t in PROBES for x in h[t]}),6)
        self.assertEqual(set(h[0]),{0,1})
        self.assertEqual(set(h[1]),{0,1})
        self.assertTrue(all(len(x)==2 for x in h.values()))

    def test_information_value_is_learned_not_static_sequence(self):
        empty=model()
        baseline=synthetic_public(empty)
        revised=model()
        start=public_start(baseline)
        offset=(2-2-start)%14
        item=revised["table"][offset]
        item["observations"]=8
        item["anomalies"]=0
        self.assertNotIn(2,choose(3,{0:baseline[0],1:baseline[1]},revised))
        self.assertIn(2,choose(3,{0:baseline[0],1:baseline[1]},empty))

    def test_posterior_uses_prior_public_anomaly(self):
        m=model()
        early=synthetic_public(m)
        altered=deepcopy(early)
        k=next(iter(altered[3]))
        altered[3][k]=(altered[3][k]+5)%16
        # A candidate with low value only in the anomaly-observed state.
        cell=4
        start=public_start(early)
        idx=28+((cell-2-start)%14)
        m["table"][idx]["observations"]=8
        m["table"][idx]["anomalies"]=0
        first=choose(5,{t:early[t] for t in (0,1,3)},m)
        second=choose(5,{t:altered[t] for t in (0,1,3)},m)
        self.assertNotEqual(first,second)

    def test_no_future_or_oracle_input(self):
        m=model()
        history=synthetic_public(m)
        with self.assertRaisesRegex(ValueError,"FUTURE_OR_MISSING_HISTORY"):
            choose(3,history,m)
        with self.assertRaises(TypeError):
            choose(3,{0:history[0],1:history[1]},m,true_pair=(8,10))
        m["scientific_dispatch_authorized"]=True
        with self.assertRaisesRegex(ValueError,"INVALID_FROZEN_MODEL"):
            choose(3,{0:history[0],1:history[1]},m)

    def test_candidate_seed_and_pair_fail_closed_before_y070(self):
        for seed in (67204,67205,67240,67600,67640):
            with self.assertRaisesRegex(ValueError,"NEW_FIRST_USE_OR_TRAINING_SEED_REFUSED"):
                evaluate(None,model(),seed,(8,10),"onset1",(1,2,3),"full")
        with self.assertRaisesRegex(ValueError,"UNINSPECTED_PAIR_OR_REGIME_REFUSED"):
            evaluate(None,model(),67206,(6,9),"onset1",(1,2,3),"full")

    def test_no_fake_parent_or_auth_claim(self):
        with self.assertRaisesRegex(ValueError,"PARENT_SOURCE_AND_AUTHORITY"):
            train(b"{}",b"{}")
        m=model()
        m["first_use_claims"]=1
        with self.assertRaisesRegex(ValueError,"INVALID_FROZEN_MODEL"):
            synthetic_public(m)

if __name__=="__main__":unittest.main()

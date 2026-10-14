"""F11 source-only causal policy, exact loss fit and admission negatives."""
from copy import deepcopy
import inspect
import unittest
from policy import (EPISODES,ORDERS,SCHEMA,STATUS,SOURCE,
                    choose,audit,learned_order,start_from_public,
                    TRAIN_SEEDS,TEST_SEEDS)
from worker import evaluate
from advance import initial_model,fit,previous_evidence

def fake_history(model,base=3,force=None):
    values={}
    for t in EPISODES:
        cells=choose(t,values,model,force)
        values[t]={c:(base+5*c+t)%16 for c in cells}
    return values

class F11Tests(unittest.TestCase):
    def test_exact_six_matching_orders_all_same_physical_cells(self):
        m=initial_model()
        hist=[fake_history(m,force=i) for i in range(6)]
        seen=[]
        for i,h in enumerate(hist):
            evidence=audit(h,m,i)
            self.assertEqual(evidence["action_index"],i)
            self.assertEqual(evidence["reads"],10)
            self.assertEqual(evidence["distinct_nonanchors"],6)
            self.assertEqual(len(evidence["physical_cells"]),6)
            seen.append(evidence["physical_cells"])
        self.assertTrue(all(x==seen[0] for x in seen))
        self.assertEqual(len(ORDERS),6)
        self.assertEqual(set(hist[0][3]),set(hist[2][5]))
        self.assertEqual(set(hist[0][5]),set(hist[2][3]))

    def test_frozen_task_value_changes_observation_order_by_public_context(self):
        m=initial_model()
        for s in (9,10):
            for action in range(6):
                row=m["value_table"][s*6+action]
                row["cases"]=4
                row["total_task_loss"]=20
                row["global_loss"]=480
        m["value_table"][9*6+0]["total_task_loss"]=0
        m["value_table"][10*6+2]["total_task_loss"]=0
        first=fake_history(m,base=3)
        second=fake_history(m,base=4)
        self.assertEqual(start_from_public(first),9)
        self.assertEqual(start_from_public(second),10)
        self.assertEqual(learned_order(m,first),0)
        self.assertEqual(learned_order(m,second),2)
        self.assertNotEqual(audit(first,m)["order"],audit(second,m)["order"])
        self.assertEqual(list(inspect.signature(learned_order).parameters),
                         ["model","history"])

    def test_sparse_context_backs_off_to_global_task_loss(self):
        m=initial_model()
        h=fake_history(m)
        self.assertEqual(learned_order(m,h),0)
        s=start_from_public(h)
        for action in range(6):
            m["value_table"][s*6+action]["global_loss"]=400
        m["value_table"][s*6+2]["global_loss"]=35
        self.assertEqual(learned_order(m,h),2)

    def test_no_oracle_or_future_queries(self):
        m=initial_model()
        h=fake_history(m)
        with self.assertRaisesRegex(ValueError,"FUTURE_OR_INCOMPLETE_PUBLIC"):
            choose(3,h,m)
        with self.assertRaises(TypeError):
            choose(3,{0:h[0],1:h[1]},m,true_pair=(8,10))
        bad=deepcopy(m)
        bad["scientific_dispatch_authorized"]=True
        with self.assertRaisesRegex(ValueError,"FROZEN_MODEL"):
            choose(3,{0:h[0],1:h[1]},bad)
        bad=deepcopy(m)
        bad["value_table"][0]["total_task_loss"]=-1
        with self.assertRaisesRegex(ValueError,"NONCANONICAL_TRAINED_VALUES"):
            choose(3,{0:h[0],1:h[1]},bad)

    def test_original_and_unseen_conditions_fail_closed(self):
        m=initial_model()
        for seed in (67240,67600,67640,67800,12345):
            with self.assertRaisesRegex(ValueError,"NEW_OR_UNAUTHORIZED_FIRST_USE"):
                evaluate(None,m,seed,(8,10),"onset1",(1,2,3),"full",0)
        with self.assertRaisesRegex(ValueError,"NEW_PAIR_OR_REGIME"):
            evaluate(None,m,67206,(6,9),"onset1",(1,2,3),"full",0)
        with self.assertRaisesRegex(ValueError,"UNDECLARED_ACTION"):
            evaluate(None,m,67206,(8,10),"onset1",(1,2,3),"full",8)

    def test_training_rejects_missing_counterfactuals_and_fake_parents(self):
        with self.assertRaisesRegex(ValueError,"TRAINING_CASE_COUNT"):
            fit([])
        with self.assertRaisesRegex(ValueError,"F10_PARENT_SOURCE"):
            previous_evidence({},{},{},{})
        m=initial_model()
        self.assertEqual(m["train_seeds"],[67204,67205])
        self.assertEqual(m["validation_seeds"],[67206,67207])
        self.assertEqual(m["source_commit"],SOURCE)
        self.assertTrue(set(TRAIN_SEEDS).isdisjoint(TEST_SEEDS))

if __name__=="__main__":unittest.main()

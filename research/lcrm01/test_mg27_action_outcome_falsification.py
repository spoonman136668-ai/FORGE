#!/usr/bin/env python3
"""MG27 negative-control and temporal-order contract tests. No original env."""
import unittest
from fractions import Fraction
from mg27_original_action_outcome_falsification import (
    probability,update_metric,empty_metrics,checked_event,summary
)
from mg25_original_policy_activation_audit import digest

def public(heading=0):
    return {"direction":heading,"mission":"pick up the red ball",
        "image":[[[1,0,0] for _ in range(7)] for _ in range(7)]}

def event(before,action,after):
    return {"before":before,"after":after,"action":action,
        "reward":0.0,"terminated":False,
        "before_sha256":digest(before),"after_sha256":digest(after)}

class SelectedActionOutcomeFalsificationTests(unittest.TestCase):
    def test_causal_order_same_step_not_used_for_own_prediction(self):
        history=[];metrics=empty_metrics()
        e=event(public(),2,public(1))
        update_metric(metrics,history,e)
        self.assertEqual(metrics["steps"],1)
        self.assertEqual(metrics["original_supported"],0)
        self.assertEqual(metrics["source_changed"],1)
        update_metric(metrics,history,e)
        self.assertEqual(metrics["original_supported"],1)
        self.assertEqual(probability(history,history[0][0],2)[0],Fraction(2,3))
        self.assertEqual(metrics["brier_original"],Fraction(1,9))
    def test_permuted_action_and_inverse_controls(self):
        k="source";history=[(k,0,1),(k,1,0)]
        self.assertEqual(probability(history,k,0)[0],Fraction(2,3))
        self.assertEqual(probability(history,k,0,permuted=True)[0],Fraction(1,2))
        self.assertEqual(probability(history,k,0,inverted=True)[0],Fraction(1,3))
        self.assertEqual(probability(history,k,2,permuted=True)[0],Fraction(1,3))
    def test_fixed_32_previous_events_only(self):
        history=[];metrics=empty_metrics()
        for _ in range(35):
            update_metric(metrics,history,event(public(),3,public()))
        self.assertEqual(len(history),32)
        self.assertEqual(metrics["steps"],35)
        self.assertEqual(metrics["original_supported"],34)
        self.assertEqual(metrics["source_changed"],0)
        self.assertEqual(summary(metrics)["brier_no_signal_on_supported"],"0.2500000000")
    def test_reject_invented_selected_actions_or_tampered_source_digest(self):
        e=event(public(),7,public())
        with self.assertRaises(ValueError):checked_event(e)
        e["action"]=3
        e["after_sha256"]="0"*64
        with self.assertRaises(ValueError):checked_event(e)
    def test_same_source_public_image_direction_mission_required(self):
        e=event(public(),2,public())
        e["after"]["mission"]="use the key to open the door and then get to the goal"
        e["after_sha256"]=digest(e["after"])
        with self.assertRaises(ValueError):checked_event(e)

if __name__=="__main__":unittest.main()

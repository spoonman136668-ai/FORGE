"""NR-M2M exact-source-only causal-prefix invariance and falsifiers."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import unittest

from nr_m2j_source_cycles import public_digest
from nr_m2m_prefix_advisory import assess_prefix_proposal, MOTIF_UNCALIBRATED, STATUS

PREREG = Path(__file__).with_name("NR_M2M_PREREG.json")
POLICY = "MG56_OWN_SELECTED_NOVEL_GOAL_ON"

def view(direction=0, extra=0):
    image = [[[1,0,0] for _ in range(7)] for _ in range(7)]
    if extra:
        image[2][5] = [5,extra,0]
    return {"image":image, "direction":direction, "mission":"pick up the red key"}

def event_chain(actions, headings, extras=None):
    assert len(headings) == len(actions) + 1
    extras = extras if extras is not None else [0] * len(headings)
    rows = []
    for i, action in enumerate(actions):
        b = view(headings[i], extras[i])
        a = view(headings[i+1], extras[i+1])
        rows.append({
            "index":i+1, "before":b, "after":a, "action":action,
            "mission":b["mission"], "reward":0.0, "terminated":False,
            "truncated":False, "before_sha256":public_digest(b),
            "after_sha256":public_digest(a), "external_actions":0,
            "policy_status":POLICY,
        })
    return rows

class NRM2MPrefixOnly(unittest.TestCase):
    def test_frozen_source_only_contract_and_negative_baseline(self):
        p = json.loads(PREREG.read_text(encoding="utf8"))
        self.assertEqual(p["schema"],"forge.nr-m2m.causal-prefix-suffix-invariance-prereg.v1")
        self.assertEqual(p["parent"]["sha"],"fa648f0f91a82fe16d6e96d2b64905ee286bc4ac")
        self.assertEqual(p["original_custody"]["original_artifact"],12945140842)
        self.assertEqual(p["original_data_notes"]["enabled_original_goals"],1)
        self.assertEqual(p["original_data_notes"]["disabled_original_goals"],3)
        self.assertTrue(all(v is False for v in p["prohibitions"].values()))

    def test_inverse_and_fourth_are_no_training_descriptive_only(self):
        hist = event_chain([0],[0,1])
        e = assess_prefix_proposal(hist,view(1),1)
        self.assertTrue(e["inverse_prior_selected_turn"])
        self.assertFalse(e["fourth_consecutive_proposed_turn"])
        self.assertEqual(e["observed_motif_calibration"],MOTIF_UNCALIBRATED)
        self.assertEqual(e["status"],STATUS)
        self.assertFalse(e["source_action_selected"])
        self.assertFalse(e["proposed_action_vetoed"])
        self.assertFalse(e["future_result_predicted"])
        self.assertFalse(e["future_suffix_read"])
        hist = event_chain([0,0,0],[0,1,2,3])
        f=assess_prefix_proposal(hist,view(3),0)
        self.assertTrue(f["fourth_consecutive_proposed_turn"])
        self.assertFalse(f["inverse_prior_selected_turn"])
        self.assertFalse(f["new_original_world_step"])
        self.assertFalse(f["scientific_gain_claimed"])

    def test_same_prefix_divergent_future_suffix_receipts_bit_identical(self):
        full_a = event_chain([0,1,2],[0,1,0,0],extras=[0,0,0,1])
        full_b = event_chain([0,1,2],[0,1,2,3],extras=[0,0,2,0])
        before_a = full_a[1]["before"]
        before_b = full_b[1]["before"]
        self.assertEqual(before_a,before_b)
        self.assertNotEqual(full_a[1]["after_sha256"],full_b[1]["after_sha256"])
        a = assess_prefix_proposal(full_a[:1],before_a,1)
        b = assess_prefix_proposal(full_b[:1],before_b,1)
        self.assertEqual(a,b)
        self.assertTrue(a["inverse_prior_selected_turn"])
        # One fabricated legal future closes and one does not. Neither may
        # cause a known-closure promise or affect any predecision field.
        self.assertEqual(full_a[1]["after_sha256"],full_a[0]["before_sha256"])
        self.assertNotEqual(full_b[1]["after_sha256"],full_b[0]["before_sha256"])
        self.assertNotIn("closed_cycle",a)

    def test_empty_prefix_is_admissible_but_never_calibrated(self):
        x=assess_prefix_proposal([],view(),2)
        self.assertEqual(x["prior_selected_action_count"],0)
        self.assertFalse(x["inverse_prior_selected_turn"])
        self.assertFalse(x["fourth_consecutive_proposed_turn"])
        self.assertEqual(x["source_owner_attestation"],"NOT_ESTABLISHED_BY_SOURCE_ONLY_AUDIT")

    def test_prior_history_integrity_and_original_public_denial(self):
        good=event_chain([0,1],[0,1,0])
        bads=[
            lambda z: z[0].update({"index":2}),
            lambda z: z[0].update({"external_actions":1}),
            lambda z: z[0].update({"action":True}),
            lambda z: z[0].update({"reward":float("nan")}),
            lambda z: z[0].update({"before_sha256":"0"*64}),
            lambda z: z[0]["before"].update({"private_pose":[3,4]}),
            lambda z: z[0].update({"policy_status":"FORGED"}),
            lambda z: z[1].update({"before_sha256":good[0]["before_sha256"]}),
            lambda z: z[1].update({"action":7}),
            lambda z: z[1].update({"mission":"pick up the blue key"}),
        ]
        for edit in bads:
            with self.subTest(edit=edit):
                q=copy.deepcopy(good)
                edit(q)
                with self.assertRaises((ValueError,TypeError)):
                    assess_prefix_proposal(q,view(),0)
        with self.assertRaises(ValueError):
            assess_prefix_proposal(good,dict(view(),map="hidden"),0)
        with self.assertRaises(ValueError):
            assess_prefix_proposal(good,dict(view(),direction=True),0)
        with self.assertRaises(ValueError):
            assess_prefix_proposal(good,view(),True)
        with self.assertRaises(ValueError):
            assess_prefix_proposal(good,view(),7)
        with self.assertRaises(ValueError):
            assess_prefix_proposal([{}]*192,view(),0)
        with self.assertRaises(ValueError):
            assess_prefix_proposal(tuple(good),view(),0)

    def test_noncontiguous_current_is_rejected_not_assumed(self):
        prior=event_chain([0],[0,1])
        with self.assertRaisesRegex(ValueError,"CURRENT_PUBLIC_SOURCE_NOT_CONTIGUOUS"):
            assess_prefix_proposal(prior,view(2),1)
        changed=copy.deepcopy(prior)
        changed[0]["terminated"]=True
        with self.assertRaisesRegex(ValueError,"PROPOSAL_AFTER_ORIGINAL_TERMINAL"):
            assess_prefix_proposal(changed,view(1),1)
        changed=copy.deepcopy(prior)
        changed[0]["truncated"]=True
        with self.assertRaisesRegex(ValueError,"PROPOSAL_AFTER_ORIGINAL_TERMINAL"):
            assess_prefix_proposal(changed,view(1),1)

    def test_forthcoming_action_is_never_recorded_as_selected_history(self):
        hist=event_chain([0],[0,1])
        frozen=copy.deepcopy(hist)
        x=assess_prefix_proposal(hist,view(1),1)
        self.assertEqual(hist,frozen)
        self.assertEqual(x["prior_selected_action_count"],1)
        self.assertEqual(x["proposed_action_only"],1)
        self.assertEqual(x["source_owner_attestation"],"NOT_ESTABLISHED_BY_SOURCE_ONLY_AUDIT")
        self.assertEqual(x,assess_prefix_proposal(copy.deepcopy(hist),copy.deepcopy(view(1)),1))
        self.assertNotEqual(
            x["decision_prefix_receipt_sha256"],
            assess_prefix_proposal(hist,view(1),0)["decision_prefix_receipt_sha256"]
        )

if __name__ == "__main__":
    unittest.main()

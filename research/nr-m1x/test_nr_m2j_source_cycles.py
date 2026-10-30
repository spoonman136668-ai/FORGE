"""NR-M2J: strictly offline original-public cycle-detection falsification tests."""
import copy
import json
from pathlib import Path
import unittest

from nr_m2i_decision_evidence import canonical, sha256
from nr_m2j_source_cycles import (
    EXPOSED_ONLY, SCHEMA, audit_exposed_episode,
    public_digest, symbolic_scene_key,
)

PREREG = Path(__file__).with_name("NR_M2J_PREREG.json")
POLICY = "MG56_OWN_SELECTED_NOVEL_GOAL_ON"

def view(direction=0, extra=False):
    image = [[[1, 0, 0] for _ in range(7)] for _ in range(7)]
    if extra:
        image[2][5] = [5, 0, 0]
    return {"image":image, "direction":direction,
            "mission":"pick up the red key"}

def events_of(actions, directions, extras=None):
    assert len(directions) == len(actions)+1
    extras = [False]*len(directions) if extras is None else extras
    source=[]
    for i, action in enumerate(actions):
        before = view(directions[i], extras[i])
        after = view(directions[i+1], extras[i+1])
        source.append({
            "index":i+1, "before":before, "after":after,
            "action":action, "mission":before["mission"],
            "reward":0.0, "terminated":False, "truncated":False,
            "before_sha256":public_digest(before),
            "after_sha256":public_digest(after),
            "external_actions":0,"policy_status":POLICY,
        })
    return source

def audit(source):
    return audit_exposed_episode(source,sha256(canonical(source)))

class NRM2JSourceOnlyFalsification(unittest.TestCase):
    def test_prereg_is_explicitly_not_new_original_first_use(self):
        p=json.loads(PREREG.read_text(encoding="utf-8"))
        self.assertEqual(p["schema"],"forge.nr-m2j.information-yield-closed-cycle-source-only-v1")
        self.assertEqual(p["parent"]["qualified_commit"],"1ae96b1c61d345ac74a10e758225441026abb471")
        self.assertEqual(p["custodian"]["artifact"],12945140842)
        self.assertEqual(p["custodian"]["source_script_blob"],"6ead3934b56a5ba502ffdab8481d96c18ac5bf8f")
        self.assertTrue(all(not flag for flag in p["restrictions"].values()))
        self.assertIn("EXPOSED",p["status"])

    def test_repeat_opposite_cycles_separate_observation_yield(self):
        src=events_of([0,1,0,1],[0,1,0,1,0])
        a=audit(src)
        self.assertEqual(a["two_step_cycles"],2)
        self.assertEqual(a["four_step_cycles"],0)
        self.assertEqual(a["closed_cycle_action_cost"],4)
        self.assertEqual(a["closed_cycle_zero_new_exact_public_action_cost"],2)
        self.assertEqual(a["closed_cycle_zero_new_symbolic_scene_action_cost"],4)
        self.assertEqual(a["source_selected_turn_actions"],4)
        self.assertFalse(a["new_action_selected"])
        self.assertFalse(a["original_environment_executed"])
        self.assertFalse(a["counterfactual_task_improvement_claimed"])
        self.assertEqual(a["source_status"],EXPOSED_ONLY)
        self.assertEqual(a,audit(copy.deepcopy(src)))

    def test_four_turn_full_rotation_uses_four_unique_observations(self):
        src=events_of([0,0,0,0],[0,1,2,3,0])
        a=audit(src)
        self.assertEqual(a["two_step_cycles"],0)
        self.assertEqual(a["four_step_cycles"],1)
        self.assertEqual(a["closed_cycle_action_cost"],4)
        self.assertEqual(a["closed_cycle_zero_new_exact_public_action_cost"],0)
        self.assertEqual(a["closed_cycle_zero_new_symbolic_scene_action_cost"],4)
        self.assertTrue(a["cycles"][0]["any_new_exact_public_view"])
        self.assertFalse(a["cycles"][0]["any_new_original_symbolic_scene"])

    def test_same_directions_do_not_establish_source_public_closure(self):
        src=events_of([0,1],[0,1,2])
        a=audit(src)
        self.assertEqual(a["closed_cycle_action_cost"],0)
        src=events_of([0,0,0,0],[0,1,2,3,1])
        self.assertEqual(audit(src)["four_step_cycles"],0)
        # Physically unknowable, same eventual view but not turn-only.
        src=events_of([2,2],[0,1,0])
        self.assertEqual(audit(src)["closed_cycle_action_cost"],0)

    def test_symbolic_and_exact_public_novelty_not_interchangeable(self):
        a,b=view(0),view(1)
        self.assertNotEqual(public_digest(a),public_digest(b))
        self.assertEqual(symbolic_scene_key(a),symbolic_scene_key(b))
        self.assertNotEqual(symbolic_scene_key(a),symbolic_scene_key(view(0,True)))

    def test_positive_terminal_is_not_public_novelty(self):
        src=events_of([2],[0,0])
        src[0]["reward"]=0.75
        src[0]["terminated"]=True
        a=audit(src)
        self.assertEqual(a["positive_original_terminal_goal_steps"],1)
        self.assertEqual(a["closed_cycle_action_cost"],0)
        src.append(copy.deepcopy(src[0]))
        src[1]["index"]=2
        with self.assertRaises(ValueError):
            audit(src)

    def test_strict_public_event_custody_and_legacy_source_no_privilege(self):
        good=events_of([0,1],[0,1,0])
        edits=[
            lambda q:q[0].update({"action":True}),
            lambda q:q[0].update({"action":7}),
            lambda q:q[0].update({"external_actions":1}),
            lambda q:q[0].update({"before_sha256":"0"*64}),
            lambda q:q[0].update({"after_sha256":"0"*64}),
            lambda q:q[0]["before"].update({"private_pose":[0,0]}),
            lambda q:q[0]["before"].update({"mission":"get goal"}),
            lambda q:q[0]["before"].update({"direction":True}),
            lambda q:q[0]["before"]["image"][0][0].__setitem__(0,256),
            lambda q:q[0].update({"reward":float("nan")}),
            lambda q:q[0].update({"reward":True}),
            lambda q:q[0].update({"index":2}),
            lambda q:q[0].update({"policy_status":"FORGED"}),
            lambda q:q[0].update({"opaque_extra":9}),
            lambda q:q[1].update({"before_sha256":good[0]["before_sha256"]}),
            lambda q:q[1]["before"].update({"mission":"pick up the blue key"}),
        ]
        for mutate in edits:
            with self.subTest(mutate=mutate):
                q=copy.deepcopy(good)
                mutate(q)
                with self.assertRaises(ValueError):
                    audit(q)

    def test_aggregate_hash_cannot_be_faked_and_empty_rejected(self):
        q=events_of([0,1],[0,1,0])
        expected=sha256(canonical(q))
        with self.assertRaises(ValueError):
            audit_exposed_episode(q,"0"*64)
        with self.assertRaises(ValueError):
            audit_exposed_episode([] ,expected)
        with self.assertRaises(ValueError):
            audit_exposed_episode(q,None)
        self.assertEqual(audit_exposed_episode(q,expected)["source_episode_sha256"],expected)
        self.assertTrue(audit(q)["source_owner_attestation"]=="EXTERNAL_SOURCE_OWNER_REQUIRED")

if __name__=="__main__":
    unittest.main()

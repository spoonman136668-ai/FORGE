"""ITD-01 R6: public event-neutral contract, adversarial source isolation.

Engineering qualification only; never opens original H1/H2 scientific source.
"""
import copy
import inspect
import json
import unittest
from public_dev import PUBLIC_FAMILIES, PublicDevWorld, action, canonical, ContractViolation
from public_dev_r3 import PublicCausalDevWorld
from r5_causal_dev import R5CausalWorld
from r6_neutral_ontology import (
    normalize_public_observation, public_observation_hash,
    public_transition_from_step, is_executable_native_learner,
    NEUTRAL_SCHEMA, EVENT_SCHEMA, PUBLIC_SCHEMA
)


def public_observation(family=PUBLIC_FAMILIES[0]):
    w=PublicDevWorld(family,"DEV-R6-SOURCE",71)
    return w.reset()


class R6NeutralOntology(unittest.TestCase):
    def test_r3_and_r5_share_observable_event_type(self):
        # Only public fields; no private world objects/hidden causal bindings.
        for src_kind in ("relay_pulse","inflow_arrived","feed_pulse","dependence_pulse"):
            raw=public_observation()
            raw["delayed_events"]=[{
                "kind":src_kind,"entity":raw["entities"][0]["id"],
                "status":"ready"}]
            normal=normalize_public_observation(raw)
            self.assertEqual(normal["events"][0]["type"],"observed-effect")
            self.assertEqual(normal["events"][0]["observation"],"ready")
            self.assertEqual(normal["events"][0]["schema"],EVENT_SCHEMA)
            for legacy in ("relay_pulse","feed_pulse","dependence_pulse","inflow_arrived"):
                self.assertNotIn(legacy,canonical(normal).decode())

    def test_completions_are_distinct_from_public_causal_effects(self):
        for kind in ("relay_settled","resource_delivered","relay_stable",
                     "reservoir_balanced","goal_confirmed"):
            raw=public_observation()
            raw["delayed_events"]=[{"kind":kind,"entity":raw["entities"][0]["id"],
                                    "status":"settled"}]
            self.assertEqual(normalize_public_observation(raw)["events"][0]["type"],
                             "observed-confirmation")

    def test_public_decoy_does_not_become_causal_signal(self):
        raw=public_observation()
        raw["delayed_events"]=[{"kind":"ambient_drift",
                                "entity":raw["entities"][0]["id"],"status":"idle"}]
        self.assertEqual(normalize_public_observation(raw)["events"][0]["type"],
                         "incidental-observation")

    def test_public_diagnostics_observed_without_hidden_truth(self):
        raw=public_observation()
        raw["observations"]=[{"kind":"public_diagnostic",
                              "entity":raw["entities"][1]["id"],"signal":"responsive"}]
        got=normalize_public_observation(raw)
        self.assertEqual(got["observations"][0]["type"],"public-sensor")
        self.assertNotIn("required",canonical(got).decode())

    def test_exact_observation_schema_and_bytes(self):
        raw=public_observation(PUBLIC_FAMILIES[1])
        normal=normalize_public_observation(raw)
        self.assertEqual(normal["schema"],NEUTRAL_SCHEMA)
        self.assertEqual(normal["entities"],raw["entities"])
        self.assertEqual(normal["turn"],raw["turn"])
        self.assertEqual(normal["public_goal"],raw["public_goal"])
        self.assertLessEqual(len(canonical(normal)),16384)

    def test_public_action_result_success_and_terminal_are_retained(self):
        w=PublicDevWorld(PUBLIC_FAMILIES[0],"DEV-R6-STEP",19)
        w.reset()
        terminal=w.step(action("commit"))
        n=public_transition_from_step(terminal)
        self.assertTrue(n["done"])
        self.assertEqual(n["reward"],0)
        self.assertEqual(n["observation"]["schema"],NEUTRAL_SCHEMA)

    def test_public_invalid_action_preserved_as_rejection(self):
        w=PublicDevWorld(PUBLIC_FAMILIES[0],"DEV-R6-BAD",19)
        w.reset()
        terminal=w.step({"schema":"itd01.act.v1","verb":"shell",
                          "target":None,"value":None})
        norm=public_transition_from_step(terminal)
        self.assertEqual(norm["observation"]["observations"][0]["type"],
                         "public-rejection")

    def test_unknown_original_event_fails_closed(self):
        for bad in ("private_truth","secret_graph","model_answer",
                    "unknown_new_event","future_success"):
            raw=public_observation()
            raw["delayed_events"]=[{"kind":bad,"entity":raw["entities"][0]["id"],
                                    "status":"ready"}]
            with self.assertRaises(ContractViolation):
                normalize_public_observation(raw)

    def test_excess_event_fields_and_unseen_entity_rejected(self):
        raw=public_observation()
        raw["delayed_events"]=[{"kind":"feed_pulse",
                                "entity":raw["entities"][0]["id"],
                                "status":"ready","hidden_causal_role":"source"}]
        with self.assertRaises(ContractViolation):
            normalize_public_observation(raw)
        raw["delayed_events"][0].pop("hidden_causal_role")
        raw["delayed_events"][0]["entity"]="private_target"
        with self.assertRaises(ContractViolation):
            normalize_public_observation(raw)

    def test_unexpected_top_level_private_data_rejected(self):
        for forbidden in ("truth","hidden_graph","source_birth","task_family"):
            raw=public_observation()
            raw[forbidden]=42
            with self.assertRaises(ContractViolation):
                normalize_public_observation(raw)

    def test_input_objects_cannot_modify_past_public_contract(self):
        raw=public_observation()
        src=copy.deepcopy(raw)
        first=normalize_public_observation(src)
        digest=public_observation_hash(first)
        src["entities"][0]["id"]="attacker"
        first["entities"][1]["id"]="modified-local-copy"
        second=normalize_public_observation(raw)
        self.assertEqual(public_observation_hash(second),digest)

    def test_noncanonical_and_nan_are_rejected(self):
        for value in (float("nan"), float("inf"),object(),{"injection":object()}):
            raw=public_observation()
            raw["delayed_events"]=[value]
            with self.assertRaises(ContractViolation):
                normalize_public_observation(raw)
        raw=public_observation()
        raw["turn"]=True
        with self.assertRaises(ContractViolation):
            normalize_public_observation(raw)

    def test_public_entity_order_and_renaming_not_private_roles(self):
        first=normalize_public_observation(public_observation())
        second=normalize_public_observation(public_observation())
        self.assertEqual(first,second)
        self.assertTrue(all(set(entity)=={"id","legal_values"} for entity in first["entities"]))
        self.assertNotIn("hidden",canonical(first).decode())

    def test_r3_and_r5_both_emit_valid_normalized_public_steps(self):
        for typ in (PublicCausalDevWorld,R5CausalWorld):
            for family in PUBLIC_FAMILIES:
                w=typ(family,"DEV-R6-ACTUAL-"+str(typ.__name__),7109)
                obs=w.reset()
                self.assertEqual(normalize_public_observation(obs)["schema"],NEUTRAL_SCHEMA)
                a=action("intervene",obs["entities"][0]["id"],
                         obs["entities"][0]["legal_values"][0])
                p=public_transition_from_step(w.step(a))
                self.assertEqual(p["observation"]["turn"],1)
                self.assertFalse(p["done"])
                for _ in range(3):
                    p=public_transition_from_step(w.step(action("wait")))
                self.assertTrue(all(e["type"] in
                                    ("observed-effect","observed-confirmation",
                                     "incidental-observation") for e in p["observation"]["events"]))
                self.assertFalse(w.public_trace_receipt()["scientific_first_use"])

    def test_contract_does_not_synthesize_native_cognition(self):
        self.assertFalse(is_executable_native_learner(None))
        self.assertFalse(is_executable_native_learner(object()))
        class Signatures:
            def reset_public(self):pass
            def step_public(self):pass
            def save_learned_state(self):pass
            def restore_learned_state(self):pass
            def learning_update_count(self):pass
        self.assertTrue(is_executable_native_learner(Signatures()))
        # Interface signature alone is not proof of a native trained learner.
        self.assertNotIn("native_verified",canonical({"schema":NEUTRAL_SCHEMA}).decode())

    def test_no_backend_or_scientific_dispatch_imported(self):
        import r6_neutral_ontology
        src=inspect.getsource(r6_neutral_ontology)
        for banned in ("mcp__GitHub__","FORGE__dispatch","broker.Runner",
                       "Coinbase","minigrid.reset","Yggdrasil.reset_original"):
            self.assertNotIn(banned,src)


if __name__ == "__main__":
    unittest.main()

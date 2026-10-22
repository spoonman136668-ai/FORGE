"""Independent, source-free Mass Research R5 interface falsification tests."""
import ast
import copy
import inspect
import unittest
from pathlib import Path

import mass_r5_event_audit as audit
from public_dev import PUBLIC_FAMILIES
from r4_public_experience import PublicTranscript
from r5_causal_dev import R5CausalWorld, public_causal_oracle


class IndependentR5InterfaceChecks(unittest.TestCase):
    def test_each_world_exposes_real_public_events_but_legacy_role_fields_stay_empty(self):
        for family in PUBLIC_FAMILIES:
            for seed in (31,41,59,83):
                with self.subTest(family=family,seed=seed):
                    actual=audit.one_public_trace(family,seed)
                    self.assertTrue(actual["public_task_solvable"])
                    self.assertGreater(actual["number_public_causal_events"],0)
                    self.assertGreater(actual["public_event_counts"]["feed_pulse"],0)
                    self.assertGreater(actual["public_event_counts"]["dependence_pulse"],0)
                    self.assertGreater(actual["public_event_counts"]["goal_confirmed"],0)
                    self.assertEqual(actual[
                        "legacy_transcript_role_bindings_at_causal_events"],0)
                    self.assertEqual(actual[
                        "legacy_causal_feature_nonzero_at_causal_events"],0)
                    self.assertEqual(actual["legacy_public_event_names_recognized"],[])
                    self.assertFalse(actual["scientific_first_use"])
                    self.assertEqual(len(actual["public_action_event_digest"]),64)

    def test_old_r3_names_bind_and_r5_names_do_not(self):
        for family in PUBLIC_FAMILIES:
            world=R5CausalWorld(family,"DEV-MASS-R5-TEST",31)
            obs=world.reset()
            name=obs["entities"][0]["id"]
            older=PublicTranscript(obs)
            newer=PublicTranscript(obs)
            act={"verb":"wait","target":None,"value":None}
            r3=copy.deepcopy(obs)
            r3["delayed_events"]=[
                {"kind":"relay_pulse","entity":name,"status":"ready"}]
            newer_event=copy.deepcopy(obs)
            newer_event["delayed_events"]=[
                {"kind":"feed_pulse","entity":name,"status":"ready"}]
            older.ingest(act,r3)
            newer.ingest(act,newer_event)
            self.assertEqual(older.public_ready,name)
            self.assertTrue(any(older.features()[8:20]))
            self.assertIsNone(newer.public_ready)
            self.assertEqual(newer.active_events[0]["kind"],"feed_pulse")
            self.assertEqual(sum(newer.features()[8:20]),0)
            self.assertEqual(newer.features()[23],0)
            self.assertEqual(newer.memory_key()[3:5],(-1,-1))

    def test_public_event_is_informative_without_hidden_role_labels(self):
        # An explicit after-the-fact public-name remapping suffices to make
        # the legacy feature channel nonzero. This is NOT an R5 baseline fit.
        for family in PUBLIC_FAMILIES:
            world=R5CausalWorld(family,"DEV-MASS-R5-CF",41)
            obs=world.reset()
            public_record=[]
            def step(action):
                res=world.step(action)
                public_record.append((action,res["observation"]))
                return res
            self.assertEqual(public_causal_oracle(obs,step)["reward"],1)
            pair=next((action,row) for action,row in public_record
                      if any(e.get("kind")=="feed_pulse" and
                             e.get("status")=="ready"
                             for e in row["delayed_events"]))
            act,row=pair
            original=PublicTranscript(obs)
            original.ingest(act,row)
            self.assertIsNone(original.public_ready)
            translated=copy.deepcopy(row)
            for event in translated["delayed_events"]:
                if event.get("kind")=="feed_pulse":
                    event["kind"]="relay_pulse"
            after=PublicTranscript(obs)
            after.ingest(act,translated)
            self.assertIsNotNone(after.public_ready)
            self.assertTrue(any(after.features()[8:20]))
            self.assertEqual(original.active_events[0]["kind"],"feed_pulse")

    def test_shared_actor_inputs_fail_to_encode_three_public_r5_event_kinds(self):
        # RNN: features[8:20,23]; planner and episodic memory:
        # public_ready/public_partial/public_confirmed and memory_key indices.
        source=inspect.getsource(PublicTranscript.ingest)
        feature=inspect.getsource(PublicTranscript.features)
        self.assertIn("relay_pulse",source)
        self.assertIn("inflow_arrived",source)
        self.assertIn("relay_stable",source)
        for name in audit.R5_CAUSAL_KINDS:
            self.assertNotIn('"'+name+'"',source)
            self.assertNotIn('"'+name+'"',feature)
        self.assertTrue(set(audit.R5_CAUSAL_KINDS).isdisjoint(
            audit.BASELINE_BOUND_KINDS))

    def test_report_replay_has_immutable_fixed_development_seeds(self):
        first=audit.audit_public_development()
        second=audit.audit_public_development()
        self.assertEqual(first,second)
        self.assertEqual(first["frozen_public_audit_seeds"],[31,41,59,83])
        self.assertEqual(set(first["families"]),set(PUBLIC_FAMILIES))
        self.assertFalse(first["qualifies_R5_fully_trained_comparators"])
        self.assertFalse(first["qualifies_original_H1_H2"])
        self.assertEqual(first["ckb_plane_admission"],"NONE")
        with self.assertRaisesRegex(ValueError,"AUDIT_SEEDS_FROZEN"):
            audit.audit_public_development((7,))

    def test_auditor_cannot_import_training_science_or_controller_dispatch(self):
        source=Path(audit.__file__).read_text(encoding="utf-8")
        tree=ast.parse(source)
        names=set()
        for node in ast.walk(tree):
            if isinstance(node,ast.Call):
                fn=node.func
                names.add(fn.id if isinstance(fn,ast.Name) else
                          fn.attr if isinstance(fn,ast.Attribute) else "?")
        for forbidden in ("train","fit","execute_development",
                          "dispatch","spawn","subprocess","eval","exec"):
            self.assertNotIn(forbidden,names)
        self.assertNotIn("ckb-plane",source)
        self.assertNotIn("original_H1_H2_used",source)


if __name__=="__main__":
    unittest.main()

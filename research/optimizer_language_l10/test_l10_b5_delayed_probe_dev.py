"""Synthetic-only L10-B5 action/delayed feedback/fair-policy negative tests.

No WebNLG/L9/prospective first-use sources. Invented DEV_FIT/DEV_CHECK only.
"""
from dataclasses import replace
from hashlib import sha256
import json
import unittest

import l10_dev_source_custody as src
import l10_b4_effect_local_learning as b4
import l10_b5_delayed_probe_dev as probe

def data():
    cases=src.development_collection("WITHHELD_MAPPING")
    return [f for f in cases if f.split=="DEV_FIT"],[f for f in cases if f.split=="DEV_CHECK"]

class DelayedProbeTests(unittest.TestCase):
    def test_no_immediate_or_early_feedback_two_later_dispatch_ticks(self):
        fit,_=data()
        w=probe.World(fit,"DELAYED_CLEAN")
        t=w.request("P0",0)
        self.assertEqual(t.release_tick,3)
        with self.assertRaisesRegex(ValueError,"future consequence"):
            w.release(t,0)
        w.advance()
        with self.assertRaisesRegex(ValueError,"future consequence"):
            w.release(t,1)
        w.advance()
        with self.assertRaisesRegex(ValueError,"future consequence"):
            w.release(t,2)
        w.advance()
        self.assertEqual(w.release(t,3).code,"P0")
        with self.assertRaisesRegex(ValueError,"duplicate consequence"):
            w.release(t,3)

    def test_three_probe_complete_budget_and_delayed_delivery_on_same_world(self):
        fit,check=data()
        for policy in probe.POLICIES[:-1]:
            with self.subTest(policy=policy):
                r=probe.execute(fit,check,"DELAYED_CLEAN",policy)
                self.assertEqual(r["actual_probes"],3)
                self.assertEqual(r["released_feedback"],3)
                self.assertTrue(all(t>=3 for t in r["actual_delays"]))
                self.assertEqual(r["micro_exact"],1)
                self.assertEqual(r["micro_abstention"],0)
                self.assertEqual(r["source_role"],"L10_SYNTHETIC_DEV")
                self.assertTrue(r["restart_executed"])
                self.assertEqual(len(r["family_metrics"]),3)

    def test_no_query_negative_and_full_denominators(self):
        fit,check=data()
        r=probe.execute(fit,check,"DELAYED_CLEAN","no-query-abstention")
        self.assertEqual(r["actual_probes"],0)
        self.assertEqual(r["released_feedback"],0)
        self.assertEqual(r["micro_exact"],0)
        self.assertEqual(r["micro_abstention"],1)
        self.assertFalse(r["restart_executed"])
        self.assertEqual(sum(x["abstentions"] for x in r["family_metrics"]),12)

    def test_withheld_information_no_false_positives_or_missing_case_drops(self):
        fit,check=data()
        for policy in probe.POLICIES:
            r=probe.execute(fit,check,"DELAYED_NO_FEEDBACK",policy)
            self.assertEqual(r["micro_exact"],0)
            self.assertEqual(r["micro_abstention"],1)
            self.assertEqual(sum(f["examples"] for f in r["family_metrics"]),12)

    def test_wrong_effect_feedback_sensitive_and_wrong_but_confident(self):
        fit,check=data()
        r=probe.execute(fit,check,"DELAYED_PERMUTED","local-uncertainty")
        self.assertEqual(r["micro_exact"],0)
        self.assertEqual(r["micro_abstention"],0)
        self.assertTrue(sum(f["contradictory_claims"]+f["unsupported_claims"]+
                            f["missing_claims"] for f in r["family_metrics"])>0)
        self.assertNotEqual(r["learned_state_sha256"],
                            probe.execute(fit,check,"DELAYED_CLEAN","local-uncertainty")["learned_state_sha256"])

    def test_restart_state_preserves_pending_and_memory_without_world_truth(self):
        fit,_=data()
        world=probe.World(fit,"DELAYED_CLEAN")
        a=world.request("P0",0)
        world.advance()
        b=world.request("P1",1)
        mem=b4.LocalMemory().update(b4.Observation("P0","E0"))
        pending=[b]
        seen={a.ticket_sha256}
        raw=probe.snapshot_public_state(mem,pending,seen,2)
        restored,delayed,already,tick=probe.restore_public_state(raw)
        self.assertEqual(restored.snapshot(),mem.snapshot())
        self.assertEqual(already,seen)
        self.assertEqual(delayed,pending)
        self.assertEqual(tick,2)
        for forbidden in ("located_in","parent_of","owns","AsterF","BorealF"):
            self.assertNotIn(forbidden,raw.decode())
        self.assertEqual(raw,probe.snapshot_public_state(restored,delayed,already,tick))

    def test_modified_action_ticket_or_duplicate_deliveries_rejected(self):
        fit,_=data()
        world=probe.World(fit,"DELAYED_CLEAN")
        a=world.request("P0",0)
        for corrupt in (replace(a,code="P1"),replace(a,release_tick=0),
                        replace(a,ticket_sha256="f"*64),replace(a,action_tick=9)):
            with self.subTest(corrupt=corrupt),self.assertRaises(ValueError):
                world.release(corrupt,10)
        for _ in range(3):world.advance()
        self.assertIsNotNone(world.release(a,3))
        with self.assertRaises(ValueError):
            world.release(a,3)
        with self.assertRaises(ValueError):
            world.request("P0",0)

    def test_modified_resume_pending_queue_and_noncanonical_snapshot_rejected(self):
        mem=b4.LocalMemory()
        ticket=probe.Ticket("a"*64,"P0",1,4)
        raw=probe.snapshot_public_state(mem,[ticket],{"b"*64},3)
        for corrupted in (raw+b" ",raw.replace(b'"next_tick":3',b'"next_tick":2'),
                          raw.replace(b',1,4]',b',1,3]'),
                          raw.replace(b'"P0"',b'"P9"')):
            with self.subTest(corrupted=corrupted[:65]),self.assertRaises((ValueError,TypeError)):
                probe.restore_public_state(corrupted)
        with self.assertRaises(ValueError):
            probe.snapshot_public_state(mem,[ticket,ticket],set(),3)
        with self.assertRaises(ValueError):
            probe.snapshot_public_state(mem,[ticket],{ticket.ticket_sha256},3)

    def test_any_dev_check_or_prospective_source_cannot_enter_fit(self):
        fit,check=data()
        for invalid in (fit[:-1],check,[check[0]]+fit[1:],
                        [replace(fit[0],role=src.PROSPECTIVE_ROLE)]+fit[1:]):
            with self.subTest(length=len(invalid)),self.assertRaises(ValueError):
                probe.World(invalid,"DELAYED_CLEAN")
        with self.assertRaises(ValueError):
            probe.execute(fit,[replace(check[0],split="DEV_FIT")]+check[1:],
                          "DELAYED_CLEAN","local-uncertainty")

    def test_same_source_information_per_policy_and_complete_frozen_grid(self):
        fit,check=data()
        allruns=probe.benchmark(fit,check)
        self.assertEqual(len(allruns["outcomes"]),18)
        self.assertFalse(allruns["scientific_go"])
        self.assertEqual(allruns["prospective_examples_generated_or_used"],0)
        self.assertFalse(allruns["original_l9_webnlg_reused"])
        self.assertEqual(allruns["feedback_delay_ticks"],2)
        for regime in probe.REGIMES:
            group=[r for r in allruns["outcomes"] if r["regime"]==regime]
            self.assertEqual(len(group),6)
            self.assertEqual(len({r["source_custody_sha256"] for r in group}),1)
            self.assertEqual([r["policy"] for r in group],list(probe.POLICIES))
        self.assertEqual([r["micro_exact"] for r in allruns["outcomes"][:5]],[1.]*5)
        self.assertEqual(allruns["outcomes"][5]["micro_exact"],0)

    def test_no_prospective_generation_and_no_model_exposure_of_ground_truth(self):
        self.assertFalse(hasattr(probe,"PROSPECTIVE_SEED"))
        self.assertFalse(hasattr(probe,"generate_prospective"))
        fit,_=data()
        world=probe.World(fit,"DELAYED_CLEAN")
        receipt=world.request("P2",0)
        self.assertEqual(set(receipt.__dataclass_fields__),{
            "ticket_sha256","code","action_tick","release_tick"})
        self.assertNotIn("effect_channel",receipt.__dataclass_fields__)
        self.assertTrue(set(dict(world.fit_code_frequencies))==set(src.PREDICATE_CODES))

if __name__=="__main__":
    unittest.main()

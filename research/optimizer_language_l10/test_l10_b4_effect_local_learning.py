"""L10-B4 adversarial invented DEV-only online learning and causal-information checks.

No L9 or WebNLG data, prospective examples, networks or API calls.
"""
from dataclasses import replace
import json
import unittest

import l10_dev_source_custody as source
import l10_semantic_dev_oracle as oracle
import l10_b4_effect_local_learning as local

def fixture_sets():
    items=source.development_collection("WITHHELD_MAPPING")
    return [x for x in items if x.split=="DEV_FIT"],[x for x in items if x.split=="DEV_CHECK"]

class LocalLearningTests(unittest.TestCase):
    def test_full_experience_custody_no_output_labels_seen_by_model(self):
        fit,check=fixture_sets()
        events=local.make_fit_events(fit,"FEEDBACK_OBSERVED")
        self.assertGreaterEqual(len(events),12)
        self.assertTrue(local.validate_fit_events(fit,events,"FEEDBACK_OBSERVED"))
        self.assertTrue(all(x.role==source.DEV_ROLE and x.effect_channel in local.EFFECTS
                            for x in events))
        observed=[local.public_event(x) for x in events]
        self.assertTrue(all(type(x) is local.Observation for x in observed))
        self.assertTrue(all(not hasattr(x,"target") and not hasattr(x,"predicate")
                            and not hasattr(x,"reference") for x in observed))
        self.assertEqual(len({x.event_sha256 for x in events}),len(events))
        self.assertTrue(all(x.input.public_lexicon==() for x in fit+check))

    def test_online_state_acquisition_persistence_and_restart(self):
        fit,_=fixture_sets()
        events=local.make_fit_events(fit,"FEEDBACK_OBSERVED")
        mem=local.LocalMemory()
        self.assertEqual(mem.events_seen,0)
        self.assertIsNone(local._winner(mem.counts,"P0"))
        for e in events:mem.update(local.public_event(e))
        snap=mem.snapshot()
        restored=local.LocalMemory.restore(snap)
        self.assertEqual(restored.snapshot(),snap)
        self.assertEqual(restored.digest(),mem.digest())
        self.assertEqual(restored.events_seen,len(events))
        self.assertEqual(sum(restored.counts.values()),len(events))
        self.assertEqual(mem.digest(),local._learn_all(events).digest())

    def test_identical_information_strong_fitted_controls(self):
        fit,check=fixture_sets()
        report=local.benchmark_dev(fit,check,"FEEDBACK_OBSERVED")
        arms=report["methods"]
        self.assertEqual(tuple(x["method"] for x in arms),local.METHODS)
        self.assertEqual(arms[0]["micro_exact"],arms[1]["micro_exact"])
        self.assertEqual(arms[0]["micro_exact"],arms[2]["micro_exact"])
        self.assertGreater(arms[0]["micro_exact"],0)
        self.assertEqual(arms[3]["micro_exact"],0)
        self.assertEqual(arms[3]["micro_abstention"],1)
        self.assertEqual(report["families"],3)
        self.assertEqual(report["checked_examples"],12)
        self.assertGreater(report["fit_experience_events"],12)
        self.assertGreater(arms[0]["state_bytes"],0)
        self.assertGreater(report["peak_python_traced_bytes"],0)
        self.assertTrue(report["restart_state_recovery"])
        self.assertFalse(report["native_causal_representation_demonstrated"])
        self.assertFalse(report["scientific_go"])
        output=json.dumps(report)
        for forbidden in ("AsterF","BorealF","JunoF","DEV_CHECKI","Cora resides"):
            self.assertNotIn(forbidden,output)

    def test_withheld_consequence_retains_zero_scored_abstentions(self):
        fit,check=fixture_sets()
        report=local.benchmark_dev(fit,check,"FEEDBACK_WITHHELD")
        self.assertEqual(report["methods"][0]["micro_exact"],0)
        self.assertEqual(report["methods"][0]["micro_abstention"],1)
        self.assertEqual(report["methods"][1]["micro_exact"],0)
        self.assertEqual(report["methods"][2]["micro_exact"],0)
        self.assertEqual(report["methods"][3]["micro_abstention"],1)
        events=local.make_fit_events(fit,"FEEDBACK_WITHHELD")
        self.assertTrue(all(e.effect_channel==local.EMPTY for e in events))

    def test_permuted_consequence_sensitivity_no_false_success(self):
        fit,check=fixture_sets()
        good=local.benchmark_dev(fit,check,"FEEDBACK_OBSERVED")
        altered=local.benchmark_dev(fit,check,"FEEDBACK_PERMUTED")
        self.assertNotEqual(good["event_custody_sha256"],altered["event_custody_sha256"])
        self.assertNotEqual(good["learned_state_sha256"],altered["learned_state_sha256"])
        self.assertLess(altered["methods"][0]["micro_exact"],good["methods"][0]["micro_exact"])
        self.assertEqual(altered["methods"][0]["micro_exact"],0)

    def test_every_event_id_and_order_is_verified(self):
        fit,_=fixture_sets()
        events=local.make_fit_events(fit,"FEEDBACK_OBSERVED")
        for bad in (events[:-1],events[::-1],events[:-1]+events[:1],
                    [replace(events[0],event_sha256="0"*64)]+events[1:],
                    [replace(events[0],effect_channel="E2" if events[0].effect_channel!="E2" else "E1")]+events[1:]):
            with self.subTest(length=len(bad)),self.assertRaises(ValueError):
                local.validate_fit_events(fit,bad,"FEEDBACK_OBSERVED")

    def test_train_on_dev_check_or_prospective_role_rejected(self):
        fit,check=fixture_sets()
        for inp in (fit[:11]+check[:1],check,fit[:-1]+fit[:1],
                    [replace(fit[0],role=source.PROSPECTIVE_ROLE)]+fit[1:]):
            with self.assertRaises(ValueError):
                local.make_fit_events(inp,"FEEDBACK_OBSERVED")
        for regime in ("FUTURE_TEST","SEMANTIC_REFERENCES_OPENED","KNOWN_MAPPING"):
            with self.assertRaises(ValueError):
                local.make_fit_events(fit,regime)

    def test_local_unseen_code_or_tie_abstains(self):
        memory=local.LocalMemory()
        memory.update(local.Observation("P0","E0"))
        memory.update(local.Observation("P0","E1"))
        self.assertIsNone(local._winner(memory.counts,"P0"))
        self.assertIsNone(local._winner(memory.counts,"P1"))
        self.assertIsNone(local._winner(memory.counts,"P0",alpha=.5))
        for bad in (local.Observation("P9","E0"),local.Observation("P0","E9")):
            with self.assertRaises(ValueError):memory.update(bad)

    def test_association_survives_single_interfering_wrong_effect(self):
        state=local.LocalMemory()
        for _ in range(3):state.update(local.Observation("P2","E2"))
        state.update(local.Observation("P2","E1"))
        self.assertEqual(local._winner(state.counts,"P2"),"E2")
        self.assertEqual(local._winner(local.LocalMemory.restore(state.snapshot()).counts,"P2"),"E2")

    def test_corrupt_restart_memory_fails_closed(self):
        mem=local.LocalMemory().update(local.Observation("P1","E1"))
        raw=mem.snapshot()
        for payload in (b"",raw+b" ",b'{"schema":"incorrect"}',
                        raw.replace(b'"events_seen":1',b'"events_seen":0'),
                        raw.replace(b'"P1"',b'"P9"')):
            with self.subTest(payload=payload[:30]),self.assertRaises((ValueError,TypeError,KeyError)):
                local.LocalMemory.restore(payload)

    def test_direct_lexicon_missing_from_dev_check(self):
        fit,check=fixture_sets()
        report=local.benchmark_dev(fit,check,"FEEDBACK_OBSERVED")
        self.assertEqual(report["prospective_examples_used"],0)
        self.assertFalse(report["l9_used"])
        self.assertFalse(report["official_webnlg_test_used"])
        self.assertEqual(report["protection_role"],"L10_SYNTHETIC_DEV")
        self.assertFalse(hasattr(local,"PROSPECTIVE_SEED"))
        self.assertFalse(hasattr(local,"generate_prospective"))

if __name__=="__main__":
    unittest.main()

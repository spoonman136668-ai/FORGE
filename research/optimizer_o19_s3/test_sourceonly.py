import json
import unittest
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from change_memory import TwoTimescaleMemory
from controls import LastObserved, LaplaceHistory, MarkovLaplace, NoMemory
from benchmark import measure

class O19SourceOnly(unittest.TestCase):
    def test_first_observation_is_uncertain_and_prediction_before_update(self):
        m=TwoTimescaleMemory(); self.assertEqual(m.predict(0,(2,2)),.5)
        m.observe(0,(2,2),True)
        self.assertGreater(m.predict(1,(2,2)),.5)

    def test_public_occupancy_flip_is_observed_not_oracle(self):
        m=TwoTimescaleMemory();m.observe(0,(1,2),True);m.observe(1,(1,2),False)
        self.assertEqual(m.change_status((1,2)),"OBSERVED_VARIABLE_OCCUPANCY")
        self.assertLess(m.predict(2,(1,2)),.5)

    def test_unflipped_never_classified_as_wall(self):
        m=TwoTimescaleMemory()
        for t in range(12): m.observe(t,(1,1),True)
        self.assertEqual(m.change_status((1,1)),"STATIC_OR_UNOBSERVED_CHANGE_UNIDENTIFIABLE")
        self.assertEqual(m.change_status((1,3)),"UNOBSERVED")

    def test_bad_sensor_or_clock_is_atomic(self):
        m=TwoTimescaleMemory();m.observe(3,(1,1),False)
        before=m.snapshot()
        for args in [(3,(1,1),True),(4,(1,1),1),(4,(-1,2),False),(4,(1,1),None)]:
            with self.assertRaises(ValueError):m.observe(*args)
            self.assertEqual(m.snapshot(),before)

    def test_bounded_memory_and_atomic_rejection(self):
        m=TwoTimescaleMemory(capacity=2)
        m.observe(0,(0,0),True);m.observe(1,(0,1),False)
        before=m.snapshot()
        with self.assertRaises(ValueError):m.observe(2,(0,2),False)
        self.assertEqual(before,m.snapshot());self.assertEqual(len(m.cells),2)

    def test_cold_roundtrip_and_hash_tamper_rejection(self):
        m=TwoTimescaleMemory();m.observe(0,(0,0),True);m.observe(1,(0,0),False)
        cold=TwoTimescaleMemory.restore(m.snapshot())
        self.assertEqual(m.snapshot(),cold.snapshot())
        self.assertEqual(m.predict(2,(0,0)),cold.predict(2,(0,0)))
        raw=json.loads(m.snapshot());raw["payload"]["cells"]["0,0"]["observed_flips"]=0
        with self.assertRaises(ValueError):TwoTimescaleMemory.restore(json.dumps(raw).encode())

    def test_front_veto_is_identical_to_conventional_guard(self):
        for proposed in (0,1,2):
            for blocked in (False,True):
                reference=0 if proposed==2 and blocked else proposed
                self.assertEqual(TwoTimescaleMemory.guarded_action(proposed,blocked),reference)
        with self.assertRaises(ValueError):TwoTimescaleMemory.guarded_action(2,1)

    def test_strong_conventional_predictors_receive_identical_public_stream(self):
        models=[TwoTimescaleMemory(),LastObserved(),LaplaceHistory(),MarkovLaplace(),NoMemory()]
        for t,cell,b in ((0,(1,1),True),(1,(1,1),False),(2,(1,2),False)):
            ps=[m.predict(t,cell) for m in models]
            self.assertTrue(all(0<=p<=1 for p in ps))
            for m in models:m.observe(t,cell,b)
        self.assertEqual(len(models[0].cells),2)

    def test_invalid_future_prediction_has_no_side_effect(self):
        m=TwoTimescaleMemory(); m.observe(4,(2,2),True)
        frozen=m.snapshot()
        with self.assertRaises(ValueError): m.predict(4,(2,2))
        self.assertEqual(m.snapshot(),frozen)

    def test_benchmark_is_deterministic_and_does_not_claim_science(self):
        a=measure();self.assertEqual(a,measure())
        self.assertEqual(a["handwritten_events"],30)
        self.assertEqual(a["source_original_episodes_executed"],0)
        self.assertFalse(a["scientific_go"])
        self.assertFalse(a["candidate_better_than_best_conventional"])
        self.assertLess(a["brier_mean"]["conventional_markov"],a["brier_mean"]["two_timescale"])
        self.assertEqual(set(a["brier_mean"]),{"two_timescale","conventional_last","conventional_laplace","conventional_markov","no_memory"})

if __name__=="__main__": unittest.main()

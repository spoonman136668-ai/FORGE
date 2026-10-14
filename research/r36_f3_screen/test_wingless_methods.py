"""R36 Wingless method-level qualification; source-only, no original science."""
import math
import unittest
from wingless_methods import train, METHODS

def groups():
    return tuple(tuple((tuple((j%7-i)*0.01 for i in range(16)),1 if j%2 else -1)
                       for j in range(576)) for source in range(3))

class WinglessMethodsTests(unittest.TestCase):
    def test_all_candidates_are_bounded_and_reproducible(self):
        training=groups()
        for method in METHODS:
            with self.subTest(method=method):
                a=train(method,training)
                b=train(method,training)
                self.assertEqual(a,b)
                self.assertEqual(a["epochs"],32)
                self.assertEqual(len(a["weights"]),16)
                self.assertEqual(a["source_training_counts"],(576,576,576))
                self.assertTrue(all(math.isfinite(w) for w in a["weights"]))
    def test_mechanism_capacity_is_preregistered(self):
        training=groups()
        projected=train("W36-C1",training)["mechanism"]
        self.assertEqual(projected["rank"],8)
        self.assertEqual(projected["trained_scalar_count"],16)
        self.assertEqual(len(projected["projector_angles"]),8)
        self.assertEqual(len(projected["prediction_head"]),8)
        risk=train("W36-C3",training)["mechanism"]
        self.assertEqual(risk["shared_weight_dimension"],16)
        self.assertEqual(risk["gate_state_count"],2)
        self.assertEqual(len(risk["learned_risk_logits"]),2)
        memory=train("W36-C4",training)["mechanism"]
        self.assertEqual(memory["memory_slots_per_source"],32)
        conflict=train("W36-C2",training)["mechanism"]
        self.assertEqual(conflict["conflict_projection"],"deterministic_pairwise_orthogonal")

    def test_bad_source_count_fails(self):
        with self.assertRaisesRegex(ValueError,"R36_SOURCE_COUNT"):
            train("W36-C1",groups()[:2])
    def test_bad_source_length_fails(self):
        with self.assertRaisesRegex(ValueError,"R36_EXAMPLE_COUNT"):
            train("W36-C2",(groups()[0][:-1],*groups()[1:]))
    def test_bad_features_and_nonfinite_fail(self):
        g=groups()
        broken=((tuple([float("nan")]*16),1),)+g[0][1:]
        with self.assertRaisesRegex(ValueError,"R36_NONFINITE"):
            train("W36-C3",(broken,*g[1:]))
        with self.assertRaisesRegex(ValueError,"R36_UNKNOWN_METHOD"):
            train("W36-C5",g)

if __name__=="__main__":
    unittest.main()

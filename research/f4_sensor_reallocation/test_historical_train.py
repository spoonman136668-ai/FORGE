"""Engineering-only F4 train/inference separation and capacity tests."""
import unittest
from collections import Counter
from dataclasses import replace
from historical_train import (
    HISTORICAL_TRAIN_SEEDS,TrainingCase,historical_training_cases,
    learn_coverage,serialize_model,digest_model
)

class HistoricalTrainingTests(unittest.TestCase):
    def test_learning_is_deterministic_and_matches_locked_comparators(self):
        from matched_worker import SET_FIXTURE,ORDER_FIXTURE,verify_comparators
        cases=historical_training_cases()
        a=learn_coverage(cases)
        b=learn_coverage(cases)
        self.assertEqual(a,b)
        self.assertEqual(serialize_model(a),serialize_model(b))
        self.assertEqual(digest_model(a),digest_model(b))
        self.assertEqual(a["learned_physical_sensors"],[8,11])
        self.assertEqual(a["set_schedule"],[list(p) for p in SET_FIXTURE])
        self.assertEqual(a["order_control_schedule"],[list(p) for p in ORDER_FIXTURE])
        self.assertEqual(a["f4_development_seeds_consumed"],0)
        self.assertEqual(a["sealed_first_uses"],0)
        self.assertFalse(a["science_admitted"])
        self.assertFalse(a["inference_uses_hidden_pair"])
        check=verify_comparators()
        self.assertEqual(check["F4-SET"],SET_FIXTURE)
        self.assertEqual(Counter(sum(a["set_schedule"],[])),Counter(sum(a["order_control_schedule"],[])))
    def test_new_f4_proposed_dev_seed_is_rejected(self):
        x=list(historical_training_cases())
        x[-1]=replace(x[-1],seed=67600)
        with self.assertRaisesRegex(ValueError,"FORBIDDEN_NEW_OR_REORDERED_SEED"):
            learn_coverage(x)
    def test_new_f4_sealed_seed_is_rejected(self):
        x=list(historical_training_cases())
        x[-1]=replace(x[-1],seed=67640)
        with self.assertRaisesRegex(ValueError,"FORBIDDEN_NEW_OR_REORDERED_SEED"):
            learn_coverage(x)
    def test_duplicate_and_missing_historical_seed_fails_closed(self):
        x=list(historical_training_cases())
        x[2]=x[0]
        with self.assertRaisesRegex(ValueError,"FORBIDDEN_NEW_OR_REORDERED_SEED"):
            learn_coverage(x)
        with self.assertRaisesRegex(ValueError,"TRAINING_SIZE"):
            learn_coverage(x[:-1])
    def test_illegal_labels_and_type_are_rejected(self):
        x=list(historical_training_cases())
        x[-1]=replace(x[-1],legal_pair=(6,9))
        with self.assertRaisesRegex(ValueError,"LEGAL_PAIR_LABEL"):
            learn_coverage(x)
        x=list(historical_training_cases())
        x[0]={"seed":HISTORICAL_TRAIN_SEEDS[0],"legal_pair":(8,10)}
        with self.assertRaisesRegex(ValueError,"INPUT_TYPE"):
            learn_coverage(x)
    def test_no_extra_read_or_oracle_in_inference_signature(self):
        result=learn_coverage(historical_training_cases())
        self.assertEqual(len(result["set_schedule"]),5)
        self.assertEqual(sum(len(x) for x in result["set_schedule"]),10)
        self.assertNotIn("legal_pair",result)
        self.assertEqual(result["status"],"MECHANISM_REHEARSAL_F3_USED_LABELS_ONLY_NOT_F4_TRAINING")

if __name__=="__main__":
    unittest.main()

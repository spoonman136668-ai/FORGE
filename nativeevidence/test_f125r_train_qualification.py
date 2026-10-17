"""F125-R exact source eligibility must precede any learned TRAIN."""
from pathlib import Path
import sys,unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parent))
import f125r_train_qualification as t
import f125r_train_environment as env

class TrainGuard(unittest.TestCase):
    def test_mismatched_advisory_source_is_quarantined(self):
        with self.assertRaises(env.Invalid):
            t.verify_headroom({"schema":"wrong"},{}, "invalid")
    def test_rejected_headroom_never_calls_model_fit(self):
        with patch.object(t.model,"fit",side_effect=AssertionError("trained illegally")):
            with self.assertRaises(env.Invalid):
                t.train({},
                    {"schema":t.headroom.SCHEMA,"source_sha":"a"*40,
                     "disposition":"UNINFORMATIVE_HEADROOM_DO_NOT_SELECT_OTHER_SEEDS"},
                    "a"*40)
    def test_gate_requires_sha256_seals(self):
        with self.assertRaises(OSError):
            t.sealed("/not/a/receipt.json")

if __name__=="__main__":unittest.main()

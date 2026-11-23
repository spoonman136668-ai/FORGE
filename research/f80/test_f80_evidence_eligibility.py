import unittest
from f80_evidence_eligibility import evaluate,PINS
class Test(unittest.TestCase):
 def valid(self,lane):
  p=PINS[lane];return [{"id":p["artifact"],"digest":p["digest"],"expired":False,"workflow_run":{"id":p["run"]}}]
 def test_denies_promotion(self):
  for lane in PINS:
   r=evaluate(lane,PINS[lane]["run"],self.valid(lane))
   self.assertFalse(r["optimizer_training_eligible"])
   self.assertFalse(r["accepted_original"])
 def test_drift_denied(self):
  for lane in PINS:
   rows=self.valid(lane);rows[0]["digest"]="sha256:"+"0"*64
   with self.assertRaises(ValueError):evaluate(lane,PINS[lane]["run"],rows)
 def test_expired_denied(self):
  for lane in PINS:
   rows=self.valid(lane);rows[0]["expired"]=True
   with self.assertRaises(ValueError):evaluate(lane,PINS[lane]["run"],rows)

import copy,unittest
from f83_actual_heldout import audit_rows,NotQualified,METRIC_KEYS
class Audit(unittest.TestCase):
 def make(self):
  rows=[]
  for seed in range(801008,801016):
   for fam in range(1540,1544):
    score={key:0 for key in METRIC_KEYS}
    score["F60_fixed"]=int(seed!=801008)
    score["F63C_trained_reliability"]=int(seed==801009)
    audit={"max_payload_bytes":144,"prefixes":72,
           "publicly_grounded_question":True,"source_independent_F3":False}
    rows.append({"seed":str(seed),"family":str(fam),"score":score,
      "independent_model_audit":audit,"independent_ablation_audit":audit})
  scores={k:sum(row["score"][k] for row in rows) for k in METRIC_KEYS}
  pf={str(i):{"strongest_fair":7,"trained":1} for i in range(1540,1544)}
  return rows,{"registered_validation_cases":32,"strongest_fair":"F60_fixed",
    "scores":scores,"per_family":pf,"strongest_fair_correct":28,"learned_correct":4,"observed_gain":-0.75}
 def test_fails_inconsistent_authoritative_totals(self):
  rows,v=self.make()
  with self.assertRaises(NotQualified):audit_rows(rows,v)
 def test_rejects_repeated_validation_row(self):
  rows,v=self.make();rows[1]=copy.deepcopy(rows[0])
  with self.assertRaises(NotQualified):audit_rows(rows,v)
 def test_rejects_fake_independent_acceptance(self):
  rows,v=self.make();rows[0]["independent_model_audit"]["source_independent_F3"]=True
  with self.assertRaises(NotQualified):audit_rows(rows,v)

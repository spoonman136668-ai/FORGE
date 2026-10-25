#!/usr/bin/env python3
"""F7 independent whole-process exact science comparison, not causal acceptance."""
import argparse
import hashlib
import json
from pathlib import Path
from k4t_f7_delayed_value import SCHEMA,FROZEN,FIT,contract,canon

def stable(x):
 y=dict(x)
 y.pop("resources",None)
 y.pop("original_FIT_source_wall_seconds",None)
 return y
def compare(a,b):
 frozen=contract()
 identity=hashlib.sha256(FROZEN.read_bytes()).hexdigest()
 for name,x in (("A",a),("B",b)):
  if(x.get("schema")!=SCHEMA or x.get("gate")!="LCRM01-K4T-F7"
    or x.get("result") not in (frozen["acceptance"]["passResult"],frozen["acceptance"]["failResult"])
    or x.get("protocol_sha256")!=identity
    or x.get("original_minigrid_commit")!=frozen["source"]["originalMiniGridCommit"]
    or len(x.get("original_public_FIT_selected_action_events",[]))!=12000
    or x.get("scientific_first_use") is not False
    or x.get("scientific_accepted") is not False
    or x.get("observed_logged_selected_action_value_only") is not True
    or x.get("not_unchosen_action_counterfactual") is not True
    or x.get("not_new_R5_navigation_policy") is not True
    or x.get("original_FIT_source_digest_sha256")!=hashlib.sha256(
        canon(x["original_public_FIT_selected_action_events"]).encode()).hexdigest()):
   raise ValueError("F7_UNQUALIFIED_PROSPECTIVE_LOGGED_FIT_"+name)
  if len(x.get("folds",[]))!=4:raise ValueError("F7_FOLD_COUNT_"+name)
  actual={z["seed"] for z in x["original_public_FIT_selected_action_events"]}
  if actual!=set(FIT):raise ValueError("F7_FIT_COHORT_DRIFT_"+name)
  for fold in x["folds"]:
   if(set(fold["test_public_seed_ids"])&set(fold["training_public_seed_ids"])
      or any((seed-FIT[0])%4!=fold["fold"] for seed in fold["test_public_seed_ids"])):
    raise ValueError("F7_INFORMATION_LEAK_FROM_TEST_FOLD_"+name)
 same=stable(a)==stable(b)
 go=same and all(x["result"]==frozen["acceptance"]["passResult"] for x in (a,b))
 return {"schema":"mass.lcrm01.k4t-f7.independent-logged-FIT-repeat-v1",
         "gate":"LCRM01-K4T-F7","science_identical":same,
         "result":("REPEATED_BOUNDED_TRAINING_ONLY_DELAYED_VALUE_PREDICTION_NOT_ACTION_POLICY"
                   if go else "NO_REPEATABLE_TRAINING_ONLY_DELAYED_VALUE_INFORMATION_GAIN"),
         "source_A":a["result"],"source_B":b["result"],
         "no_causal_unchosen_action_claim":True,
         "scientific_first_use":False,"scientific_accepted":False}
def main():
 parser=argparse.ArgumentParser()
 for name in ("first","second","output"):
  parser.add_argument("--"+name,required=True,type=Path)
 args=parser.parse_args()
 if args.output.exists() or not args.output.parent.is_dir():raise ValueError("F7_NONFRESH_REPEAT")
 a=json.loads(args.first.read_text())
 b=json.loads(args.second.read_text())
 result=compare(a,b)
 args.output.write_text(json.dumps(result,sort_keys=True,indent=2)+"\n")
 print("K4T_F7_INDEPENDENT_RESULT="+result["result"])
 print("K4T_F7_EXACT_SOURCE_SCIENCE_AGREEMENT="+str(result["science_identical"]))
 return int(not result["science_identical"])
if __name__=="__main__":raise SystemExit(main())

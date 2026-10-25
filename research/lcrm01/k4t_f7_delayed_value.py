#!/usr/bin/env python3
"""FIT-only original-source logged selected-action delayed-value predictability.
No policy improvement, counterfactual action-value, or scientific transfer claim.
"""
import argparse
from collections import defaultdict
import hashlib
import json
import math
from pathlib import Path
import resource
import time
import traceback

FROZEN=Path(__file__).with_name("k4t_f7_frozen_delayed_value.json")
SCHEMA="mass.lcrm01.k4t-f7.original-fit-logged-action-delayed-value-v1"
FIT=tuple(range(91400,91424))
FAMILIES=("empty","fourrooms")
FIELDS=("X","Y","GoalX","GoalY","Direction","FrontBlocked")
GAMMA=.97
STEP=.01
SMOOTH=32

def canon(x):return json.dumps(x,sort_keys=True,separators=(",",":"),allow_nan=False)
def contract():
 p=json.loads(FROZEN.read_text())
 if(p["schema"]!="mass.lcrm01.k4t-f7.frozen-training-only-delayed-value-v1"
    or p["parentF6Head"]!="ccbd06822c17c585a34069e44b3ea736c9008872"
    or p["freshFitSeeds"]!=[91400,91423] or p["actualFitEvents"]!=12000
    or p["crossValidation"]["folds"]!=4
    or p["model"]["smoothingPriorPseudoCount"]!=SMOOTH
    or p["target"]["gamma"]!=GAMMA or p["target"]["stepCost"]!=STEP
    or p["governance"]["scientificFirstUse"] is not False
    or p["governance"]["scientificAccepted"] is not False):
  raise ValueError("F7_FROZEN_SOURCE_CONTRACT_DRIFT")
 return p
def valid(s):
 return(type(s) is dict and set(s)==set(FIELDS)
  and all(type(s[k]) is int and 0<=s[k]<=64 for k in FIELDS[:4])
  and type(s["Direction"]) is int and s["Direction"] in (0,1,2,3)
  and type(s["FrontBlocked"]) is bool)
def validate(x):
 if(type(x) is not dict or x["family"] not in FAMILIES
    or type(x["seed"]) is not int or x["seed"] not in FIT
    or type(x["action"]) is not int or x["action"] not in (0,1,2)
    or not valid(x["before"]) or not valid(x["after"])
    or not math.isfinite(float(x["reward"])) or type(x["terminal"]) is not bool):
  raise ValueError("F7_UNAUTHENTIC_SELECTED_PUBLIC_ACTION")
def episodes(stream):
 segment=[]
 for x in stream:
  validate(x)
  if segment and (segment[-1]["terminal"] or segment[-1]["family"]!=x["family"]
    or segment[-1]["seed"]!=x["seed"] or segment[-1]["after"]!=x["before"]):
   yield segment
   segment=[]
  segment.append(x)
 if segment:yield segment
def samples(stream):
 out=[];incomplete=completed=0
 for segment in episodes(stream):
  if not segment[-1]["terminal"]:
   incomplete+=len(segment)
   continue
  completed+=1
  future=0.
  scored=[None]*len(segment)
  for i in range(len(segment)-1,-1,-1):
   x=segment[i]
   future=float(x["reward"])-STEP+GAMMA*future
   scored[i]=(x,future)
  out.extend(scored)
 return out,{"completed_actual_public_episodes":completed,
             "incomplete_actual_public_events_excluded":incomplete,
             "FIT_true_labelled_events":len(out)}
def clip(v):return max(-2,min(2,v))
def features(x):
 s=x["before"]
 return(x["family"],x["action"],s["Direction"],s["FrontBlocked"],
        clip(s["GoalX"]-s["X"]),clip(s["GoalY"]-s["Y"]))
def prior(x):return(x["family"],x["action"])
def evaluate(stream):
 if len(stream)!=12000 or {x["family"] for x in stream}!=set(FAMILIES):
  raise ValueError("F7_REAL_FIT_SOURCE_COUNT")
 if any(sum(x["family"]==f for x in stream)!=6000 for f in FAMILIES):
  raise ValueError("F7_UNEQUAL_PUBLIC_FAMILY_FIT")
 labelled,audit=samples(stream)
 folds=[];total=sse0=sse1=covered=0
 for fold in range(4):
  training=[(x,y) for x,y in labelled if (x["seed"]-FIT[0])%4!=fold]
  testing=[(x,y) for x,y in labelled if (x["seed"]-FIT[0])%4==fold]
  if len(testing)<1200:raise ValueError("F7_INSUFFICIENT_TEST_LABELS")
  condition=defaultdict(lambda:[0.,0])
  base=defaultdict(lambda:[0.,0])
  for x,y in training:
   a=condition[features(x)];a[0]+=y;a[1]+=1
   b=base[prior(x)];b[0]+=y;b[1]+=1
  if len(base)!=6:raise ValueError("F7_CONVENTIONAL_BASE_NOT_LEARNED")
  sq0=sq1=confidence=0
  byfamily={f:[0,0.,0.] for f in FAMILIES}
  for x,y in testing:
   b=base[prior(x)]
   estimate0=b[0]/b[1]
   a=condition.get(features(x),(0.,0))
   estimate1=(a[0]+SMOOTH*estimate0)/(a[1]+SMOOTH)
   err0=(estimate0-y)**2
   err1=(estimate1-y)**2
   sq0+=err0;sq1+=err1
   g=byfamily[x["family"]];g[0]+=1;g[1]+=err1;g[2]+=err0
   confidence+=int(a[1]>=8)
  if sq0<=0:raise ValueError("F7_DEGENERATE_BASE")
  folds.append({"fold":fold,"training_actual_events":len(training),
   "test_actual_events":len(testing),
   "training_public_seed_ids":sorted({x["seed"] for x,y in training}),
   "test_public_seed_ids":sorted({x["seed"] for x,y in testing}),
   "model_test_MSE":sq1/len(testing),
   "fitted_action_baseline_test_MSE":sq0/len(testing),
   "relative_MSE_improvement_fraction":1-sq1/sq0,
   "context_count_ge_8_fraction":confidence/len(testing),
   "per_family":{f:{"n":g[0],"model_MSE":g[1]/g[0],"baseline_MSE":g[2]/g[0]}
                 for f,g in byfamily.items() if g[0]>0}})
  total+=len(testing);sse0+=sq0;sse1+=sq1;covered+=confidence
 p=contract()["acceptance"]
 criteria={
  "four_folds_each_gte_10pct_relative_MSE":all(x["relative_MSE_improvement_fraction"]>=p["perFoldMinRelativeMSEImprovementPct"]/100 for x in folds),
  "pooled_gte_20pct_relative_MSE":sse1<=sse0*(1-p["overallMinRelativeMSEImprovementPct"]/100),
  "pooled_context_sufficient_support":covered/total>=p["minimumCoveredFractionContextCountEight"],
  "all_fold_train_validation_seed_disjoint":all(not(set(x["training_public_seed_ids"])&set(x["test_public_seed_ids"])) for x in folds),
  "frozen_real_fit_event_count":len(stream)==p["actualFitEvents"]}
 return {"schema":SCHEMA,"gate":"LCRM01-K4T-F7",
  "result":p["passResult"] if False else (p["acceptance"]["passResult"] if all(criteria.values()) else p["acceptance"]["failResult"]),
  "criteria":criteria,"folds":folds,"fit_label_audit":audit,
  "pooled_relative_MSE_improvement_fraction":1-sse1/sse0,
  "pooled_support_fraction":covered/total,"source_observation_fields":list(FIELDS),
  "observed_logged_selected_action_value_only":True,
  "not_unchosen_action_counterfactual":True,"not_new_R5_navigation_policy":True,
  "scientific_first_use":False,"scientific_accepted":False}
def main():
 parser=argparse.ArgumentParser()
 parser.add_argument("--output",type=Path,required=True)
 a=parser.parse_args()
 if a.output.exists() or not a.output.parent.is_dir():raise ValueError("F7_NONFRESH_EVIDENCE")
 p=contract()
 start=time.perf_counter();cpu=time.process_time()
 try:
  import k4x_curriculum_intervention as k4x
  k4x.FIT_SEEDS=FIT
  stream,rows,starts,audit,wall=k4x.fit_stream("public_bfs_demonstration_equal_budget")
  v=evaluate(stream)
  v.update({"original_minigrid_commit":p["source"]["originalMiniGridCommit"],
    "original_FIT_source_digest_sha256":hashlib.sha256(canon(stream).encode()).hexdigest(),
    "original_public_FIT_selected_action_events":stream,
    "FIT_public_audit":audit,"original_FIT_source_wall_seconds":wall,
    "protocol_sha256":hashlib.sha256(FROZEN.read_bytes()).hexdigest()})
 except Exception as e:
  v={"schema":SCHEMA,"gate":"LCRM01-K4T-F7",
    "result":"ORIGINAL_SOURCE_OR_INFRASTRUCTURE_BLOCKED",
    "error_type":type(e).__name__,"error":str(e),
    "traceback_tail":traceback.format_exc().splitlines()[-12:],
    "scientific_first_use":False,"scientific_accepted":False}
 v["resources"]={"Python_process_CPU_seconds":time.process_time()-cpu,
   "process_wall_seconds":time.perf_counter()-start,
   "peak_RSS_bytes":int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)*1024,
   "native_processes_used":0,"energy_unmeasured":True}
 a.output.write_text(json.dumps(v,sort_keys=True,indent=2,allow_nan=False)+"\n")
 print("K4T_F7_REAL_SOURCE_RESULT="+v["result"])
 if "folds" in v:
  for f in v["folds"]:
   print("K4T_F7_FOLD_"+str(f["fold"])+"_MSE_GAIN_PCT="+str(round(100*f["relative_MSE_improvement_fraction"],2)))
  print("K4T_F7_POOLED_GAIN_PCT="+str(round(100*v["pooled_relative_MSE_improvement_fraction"],2)))
  print("K4T_F7_CRITERIA="+canon(v["criteria"]))
 return int(v["result"]=="ORIGINAL_SOURCE_OR_INFRASTRUCTURE_BLOCKED")
if __name__=="__main__":raise SystemExit(main())

"""FORGE F54 supplementary real evidence: two distinct TRAIN negatives.

Source-free independent read-only recount from original archived rows.
Both prior Y F54 same-cohort failed audits stay failed. No controls promoted.
"""
from __future__ import annotations
import argparse,hashlib,json,math,pathlib

class Rejected(ValueError): pass
def required(ok,reason):
 if not ok: raise Rejected("F54_EXTRA_"+reason)
def sha(b):return hashlib.sha256(b).hexdigest()
def unique(pairs):
 d={}
 for k,v in pairs:
  required(k not in d,"DUP_JSON")
  d[k]=v
 return d
def json_file(path):
 b=pathlib.Path(path).read_bytes()
 required(0<len(b)<4_000_000,"BOUNDED_RAW")
 return json.loads(b,object_pairs_hook=unique)
def read(root,source):
 p=pathlib.Path(root);raw=(p/"result.json").read_bytes()
 required(sha(raw)==source["report_sha256"],"REPORT_DRIFT")
 required((p/"SOURCE_SHA").read_text().strip()==source["head"],"SOURCE_HEAD_DRIFT")
 entries={}
 for line in (p/"manifest.sha256").read_text().splitlines():
  fields=line.split()
  required(len(fields)==2 and fields[1] not in entries,"BAD_MANIFEST")
  entries[fields[1]]=fields[0]
 required(entries=={"result.json":sha(raw),"audit.txt":sha((p/"audit.txt").read_bytes())},
          "ARCHIVE_FILES_MISMATCH")
 required("INDEPENDENT_RECOUNT_PASS" in (p/"audit.txt").read_text(),
          "INDEPENDENT_SOURCE_AUDIT_NOT_PASS")
 return json.loads(raw,object_pairs_hook=unique)
LAWS=("parity","majority","xnor","exactly_one","xor_and","or_not","threshold_two","impl")
def law(n,c):
 a,b,d=c
 return {"parity":a^b^d,"majority":int(a+b+d>=2),"xnor":int(not(a^b)),
    "exactly_one":int(a+b+d==1),"xor_and":(a^b)&d,
    "or_not":int(a or not d),"threshold_two":int(a+b+d==2),
    "impl":int((not a) or b)}[n]
def posterior(anchors,eps):
 w=[math.prod((1-eps if law(n,c)==y else eps) for c,y in anchors)
    for n in LAWS]
 return [x/sum(w) for x in w]
def policy(c,anchors,eps):
 return int(sum(x*law(n,c) for x,n in zip(posterior(anchors,eps),LAWS))>=.5)
def choose(arm,target,anchors,eps):
 from itertools import product
 pool=[c for c in product((0,1),repeat=3)
       if c not in [a[0] for a in anchors] and c!=target]
 if arm=="public_no_purchase":return None
 if arm=="public_fixed_context_purchase":return min(pool)
 if arm=="public_target_nearest_purchase":
  return min(pool,key=lambda c:(sum(x!=y for x,y in zip(c,target)),c))
 if arm=="public_information_gain_purchase":
  w=posterior(anchors,eps)
  def score(c):
   p=sum(x*law(n,c) for x,n in zip(w,LAWS))
   return -(p*(1-p))
  return min(pool,key=lambda c:(score(c),c))
 raise Rejected("UNREGISTERED_W_ARM")
def wing(d,pr):
 arms=pr["decision_arms"];candidate=arms[0];fair=pr["fair_controls"]
 required(d["schema"]=="wingless.f54.active-calibration-identifiability.trainonly.v1"
  and d["stage"]=="PUBLIC_ONCE_PAID_CALIBRATION_TRAIN_ONLY_NOT_ORIGINAL"
  and d["fit_seeds"]==pr["fit_seeds"] and d["diagnostic_seeds"]==pr["diagnostic_seeds"]
  and d["diagnostic_families"]==pr["diagnostic_families"]
  and d["original_seeds_NOT_RESERVED"]==pr["proposed_originals_NOT_RESERVED"]
  and d["cases"]==128 and len(d["rows"])==128 and d["train_examples"]==64
  and d["source_independent_F3"] is False and d["original_executed"] is False
  and d["accepted_ref_mutation"] is False and d["paid_api_calls"]==0
  and d["private_source_law_not_selector_input"] is True
  and set(d["scores"])==set(arms),"W_SOURCE_AND_CONTROLS")
 eps=d["fitted_public_noise"]
 required(eps in (.08,.12,.16,.22),"W_TRAIN_NOISE_FIT")
 seen=set();count={a:0 for a in arms}
 for r in d["rows"]:
  k=(r["seed"],r["family"],r["sample"])
  required(k not in seen and 601100<=k[0]<601116
    and k[1] in pr["diagnostic_families"] and k[2] in (0,1),"W_DUP_OR_OUTSIDE_COHORT")
  seen.add(k)
  target=tuple(r["target"]);anchors=[(tuple(c),bit) for c,bit in r["initial_anchors"]]
  required(len(anchors)==3 and len({c for c,b in anchors})==3
    and target not in [c for c,b in anchors]
    and set(r["predictions"])==set(arms)
    and set(r["observed_contexts"])==set(arms[:-1]),"W_PUBLIC_SETUP")
  for a in arms[:-1]:
   c=choose(a,target,anchors,eps)
   required(r["observed_contexts"][a]==(None if c is None else list(c)),
     "W_PUBLIC_ACTION_RECOUNT")
   extra=[] if c is None else [(c,r["PUBLIC_extra_observations"]["".join(map(str,c))])]
   required(policy(target,anchors+extra,eps)==r["predictions"][a],
      "W_PUBLIC_PREDICTION_RECOUNT")
  required(r["predictions"][arms[-1]]==r["truth"],"W_PRIVATE_ORACLE_SCOPE")
  for a in arms:count[a]+=int(r["predictions"][a]==r["truth"])
 required(len(seen)==128,"W_MISSING_COHORT")
 for a in arms:
  stat=d["scores"][a]
  required(stat["correct"]==count[a] and stat["total"]==128
    and abs(stat["accuracy"]-count[a]/128)<1e-12,"W_TOTAL_SCORE")
 by={}
 for family in pr["diagnostic_families"]:
  sub=[r for r in d["rows"] if r["family"]==family]
  required(len(sub)==32,"W_FAMILY_SIZE")
  by[str(family)]={a:sum(r["predictions"][a]==r["truth"] for r in sub) for a in arms}
  required(by[str(family)]==d["by_family"][str(family)],"W_FAMILY_RECOUNT")
 strongest=max(fair,key=lambda a:count[a]);gain=(count[candidate]-count[strongest])/128
 family_guard=all(by[str(f)][candidate]>=max(by[str(f)][a] for a in fair)
     for f in pr["diagnostic_families"])
 qualified=gain>=pr["threshold_gain_pp"]/100 and family_guard
 required(strongest==d["strongest_fair_control"] and
  abs(d["candidate_gain"]-gain)<1e-12 and
  family_guard==d["per_family_nondegradation"] and
  qualified==d["frozen_gate_met"] and
  d["verdict"]=="TRAIN_ONLY_IDENTIFIABILITY_NOT_SUPPORTED","W_FROZEN_DECISION")
 required((count[candidate],count[strongest])==(94,97) and not qualified,"W_NEGATIVE_IDENTITY")
 return dict(lane="Wingless",source_run=38819060318,candidate_correct=94,
  strongest_fair=strongest,strongest_correct=97,total=128,
  gain_pp=round(100*gain,6),family_guard=family_guard,train_advanced=False,
  disposition="VALID_NEW_TRAIN_NEGATIVE",
  next_F55_hypothesis="TEST_WHEN_EXTRA_PUBLIC_CALIBRATION_HAS_NEGATIVE_VALUE_UNDER_DIFFERENT_LAWS")
def inverse(record):
 return record["to_node"],tuple((r,-d) for r,d in reversed(record["steps"])),record["from_node"]
def answer(mem,q):
 seq=tuple(tuple(x) for x in q["chain"])
 states={(q["start"],0)}
 for _ in range(len(seq)):
  new=set()
  for node,i in states:
   for record in mem:
    possibilities=((record["from_node"],tuple(map(tuple,record["steps"])),record["to_node"]),inverse(record))
    for u,steps,v in possibilities:
     if u==node and seq[i:i+len(steps)]==steps:
      new.add((v,i+len(steps)))
  states|=new
 return int((q["answer"],len(seq)) in states)
def ygg(d,pr):
 arms=pr["controls"];candidate=arms[0];fair=pr["fair_controls"]
 required(d["schema"]=="yggdrasil.f54b.query-blind-multihop-composition.trainonly.v1"
  and d["stage"]=="FRESH_EQUAL_PAYLOAD_TRAIN_ONLY_NO_ORIGINAL"
  and d["fit_seeds"]==pr["fit_seeds"] and d["diagnostic_seeds"]==pr["diagnostic_seeds"]
  and d["diagnostic_families"]==pr["diagnostic_families"]
  and d["original_seeds_NOT_RESERVED"]==pr["proposed_originals_NOT_RESERVED"]
  and d["independent_F3"] is False and d["original_executed"] is False
  and d["accepted_ref_mutation"] is False and d["paid_api_calls"]==0
  and d["future_question_hidden_during_ingestion"] is True
  and d["total_native_576B_residency_qualified"] is False
  and d["serialized_payload_bytes_per_record"]==12
  and d["serialized_payload_budget_bytes"]==144
  and d["cases"]==64 and len(d["rows"])==64 and set(d["scores"])==set(arms),"Y_SOURCE_AND_CONTROLS")
 seen=set();count={a:0 for a in arms}
 for row in d["rows"]:
  k=(row["seed"],row["family"])
  required(k not in seen and 621100<=k[0]<621116
     and k[1] in pr["diagnostic_families"],"Y_COHORT")
  seen.add(k)
  ev=row["public_events"];q=row["question"]
  required(len(ev)==64 and len(q["chain"])==4 and
   set(row["results"])==set(arms) and
   set(row["retained_records"])==set(arms[:-1]),"Y_PUBLIC_STREAM")
  for arm,records in row["retained_records"].items():
   required(len(records)<=12,"Y_RECORD_CAP")
   for record in records:
    ix=record["witness_indices"];steps=record["steps"]
    required(record["serialized_payload_bytes"]==12 and
      len(ix)==len(steps) and len(set(ix))==len(ix) and
      1<=len(steps)<=3 and all(type(i)==int and 0<=i<64 for i in ix),"Y_RECORD_WITNESS")
    at=record["from_node"]
    for (role,direction),index in zip(steps,ix):
     event=ev[index]
     required(role==event[1] and
       (event[0] if direction==1 else event[2])==at,
       "Y_ORIENTATION_OR_ROLE_PROVENANCE")
     at=event[2] if direction==1 else event[0]
    required(at==record["to_node"],"Y_RETAINED_PATH_MISMATCH")
   required(answer(records,q)==row["results"][arm],"Y_ANSWER_RECOUNT")
  required(row["results"][arms[-1]]==1,"Y_UNFAIR_ORACLE")
  for a in arms:count[a]+=row["results"][a]
 required(len(seen)==64,"Y_MISSING_COHORT")
 for a in arms:
  v=d["scores"][a]
  required(v["correct"]==count[a] and v["total"]==64
   and abs(v["accuracy"]-count[a]/64)<1e-12,"Y_SCORES")
 by={}
 for fam in pr["diagnostic_families"]:
  sub=[r for r in d["rows"] if r["family"]==fam]
  required(len(sub)==16,"Y_FAMILY_SIZE")
  by[str(fam)]={a:sum(r["results"][a] for r in sub) for a in arms}
  required(by[str(fam)]==d["by_family"][str(fam)],"Y_FAMILY_METRICS")
 strongest=max(fair,key=lambda a:count[a]);gain=(count[candidate]-count[strongest])/64
 guard=all(by[str(f)][candidate]>=max(by[str(f)][a] for a in fair)
   for f in pr["diagnostic_families"])
 qualifies=gain>=pr["threshold_gain_pp"]/100 and guard
 required(strongest==d["strongest_fair_control"] and
  abs(gain-d["candidate_gain"])<1e-12 and
  guard==d["per_family_nondegradation"] and
  qualifies==d["frozen_gate_met"] and
  d["verdict"]=="TRAIN_ONLY_COMPOSITION_NOT_SUPPORTED","Y_FROZEN_DECISION")
 required((count[candidate],count[strongest])==(0,2) and not qualifies,
   "Y_NEGATIVE_IDENTITY")
 return dict(lane="Yggdrasil",source_run=38820489117,total=64,
  candidate_correct=0,strongest_fair=strongest,strongest_correct=2,
  gain_pp=round(100*gain,6),family_guard=guard,train_advanced=False,
  disposition="VALID_NEW_TRAIN_NEGATIVE",
  next_F55_hypothesis="TEST_IDENTIFIABILITY_OF_QUERY_BLIND_COMPOSITION_BEFORE_MORE_MEMORY_FITTING")
def review(w,y,manifest):
 required(manifest["schema"]=="forge.f54.additional-source-firstuse.v1","MANIFEST_SCHEMA")
 for key in ("no_primary_originals","old_failures_stay_failed"):
  required(manifest["restrictions"][key] is True,"SCIENCE_BOUNDARY")
 for key in ("scientifically_accepted","dream_rsi_prospective_gain_proven",
   "theta_training_authorized","automatic_F55_dispatch_authorized","cloudflare_write_authorized"):
  required(manifest["restrictions"][key] is False,"AUTHORITY_BOUNDARY")
 required(manifest["failed_consumed_previous_y_runs"]==[38819249753,38819267489],
  "Y_FAILED_COHORT_SAFETY")
 results=[wing(read(w,manifest["sources"]["Wingless"]),json_file(pathlib.Path(w)/"prereg.json")),
          ygg(read(y,manifest["sources"]["Yggdrasil"]),json_file(pathlib.Path(y)/"prereg.json"))]
 return dict(schema="forge.f54.supplemental-readonly-feedback-to-f55.v1",
  provenance=manifest["sources"],findings=results,
  newly_recounted_real_train_runs=2,
  previously_failed_y_runs_preserved=manifest["failed_consumed_previous_y_runs"],
  independently_accepted_primary_originals=0,
  scientifically_accepted=False,retained_observational_negatives_only=True,
  dream_rsi_policy_improvement_proven=False,thetaevolve_promotion_allowed=False,
  f55_autonomous_implementation_and_dispatch_permitted=False,
  installed_controller_modified=False)
def main():
 ap=argparse.ArgumentParser()
 ap.add_argument("--root",required=True);ap.add_argument("--manifest",required=True)
 ap.add_argument("--out",required=True);a=ap.parse_args()
 root=pathlib.Path(a.root);manifest=json_file(a.manifest)
 result=review(root/"Wingless",root/"Yggdrasil",manifest)
 pathlib.Path(a.out).write_text(json.dumps(result,sort_keys=True,separators=(",",":"))+"\n")
if __name__=="__main__":main()

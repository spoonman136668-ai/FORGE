"""F47: independently recount real Wingless/Yggdrasil F46 TRAIN evidence.
This is an evidence-to-next-hypothesis advisory, NOT scientific acceptance or
an execution controller. One immutable source per lane, no hidden original use.
"""
from __future__ import annotations
import argparse, hashlib, json, math, pathlib

SOURCES={
 "Wingless":{"run":38803701796,"head":"bd7f18a31369cd913d353477e60b7be6d0d87876",
             "artifact":"W-F46-TRAIN-only-new-value-of-computation"},
 "Yggdrasil":{"run":38803873408,"head":"88963d04511a49e935c0873bf14af15f771274d0",
              "artifact":"Y-F46-TRAIN-only-causal-pair-shuffle"}
}
class Blocked(ValueError): pass
def require(ok,reason):
 if not ok: raise Blocked("F47_"+reason)
def sha(raw): return hashlib.sha256(raw).hexdigest()
def unique(pairs):
 d={}
 for key,value in pairs:
  require(key not in d,"DUPLICATE_JSON_KEY")
  d[key]=value
 return d
def load(root,lane):
 root=pathlib.Path(root)
 report=root/"result.json"; raw=report.read_bytes()
 require(0<len(raw)<=8_000_000,"REPORT_BOUND")
 h=(root/"result.sha256").read_text().split()
 require(len(h)==2 and h[0]==sha(raw) and
         pathlib.Path(h[1]).name=="result.json","REPORT_HASH_DRIFT")
 require((root/"SOURCE_SHA").read_text().strip()==SOURCES[lane]["head"],
         "SOURCE_COMMIT_DRIFT")
 doc=json.loads(raw,object_pairs_hook=unique)
 require(isinstance(doc,dict) and type(doc.get("rows")) is list,"REPORT_SCHEMA")
 require(doc.get("accepted_ref_mutation") is False and
         doc.get("paid_api_calls")==0 and
         doc.get("independent_F3_custody") is False and
         doc.get("native_576_byte_resident_qualified") is False,"UNSUPPORTED_SCIENCE_CLAIM")
 return doc,sha(raw)
def aggregate(rows,arm,key):
 n=len(rows)
 correct=sum(r[key][arm]==r["truth"] for r in rows)
 result={"correct":correct,"total":n,"accuracy":correct/n}
 if key=="predictions":
  fp=sum(bool(r[key][arm]) and not r["truth"] for r in rows)
  fn=sum(not bool(r[key][arm]) and bool(r["truth"]) for r in rows)
  probabilities=[r["probabilities"][arm] for r in rows]
  require(all(type(v) in (float,int) and 0<v<1 for v in probabilities),"UNSAFE_PROBABILITY")
  brier=sum((p-float(r["truth"]))**2 for p,r in zip(probabilities,rows))/n
  logloss=-sum(math.log(p if r["truth"] else 1-p)
     for p,r in zip(probabilities,rows))/n
  result.update(fp=fp,fn=fn,Brier=brier,logloss=logloss)
 return result
def recount_scores(d,key):
 rows=d["rows"];scores=d["scores"]
 require(type(scores) is dict and len(scores)>=5,"MISSING_CONTROLS")
 require(all(set(r[key])==set(scores) for r in rows),"POLICY_IDENTITY_DRIFT")
 for arm,original in scores.items():
  exact=aggregate(rows,arm,key)
  require(all(abs(exact[k]-original[k])<1e-10
              for k in exact),"SCORE_RECOUNT_FAIL")
 return {a:aggregate(rows,a,key) for a in scores}
def wingless(d):
 require(d.get("schema")=="wingless.f46.query-edge-voc.trainonly.v1"
  and d.get("stage")=="TRAIN_ONLY_NOT_ORIGINAL"
  and d.get("questions")==96 and len(d["rows"])==96
  and d.get("original_executed") is False
  and d.get("seeds")==[391100,391112]
  and d.get("reserved_originals_not_consumed")==[392000,392016]
  and d.get("old_originals_not_consumed")==[372000,372016],"W_FROZEN_COHORT")
 counts=recount_scores(d,"answers")
 rows=d["rows"];fair=("one_step_value","exact_entropy","query_frontier","budget_matched_rank")
 cand="query_edge_voc_per_compute"
 require(all(a in counts for a in (*fair,cand)),"W_CONTROL_MISSING")
 require(all(391100<=r["seed"]<391112 and r["family"] in (500,501,502,503)
    and r["length"] in (3,5) for r in rows),"W_RESERVED_SOURCE_TOUCHED")
 require(all(len(r["receipts"][a])<=2 for r in rows for a in r["receipts"]),"W_PAID_CAP")
 work={a:sum(r["work"][a] for r in rows) for a in d["posterior_world_work"]}
 require(work==d["posterior_world_work"],"W_WORK_RECOUNT")
 by_family={str(f):{a:sum(r["answers"][a]==r["truth"] for r in rows if r["family"]==f)
   for a in counts} for f in (500,501,502,503)}
 require(by_family==d["by_family"],"W_FAMILY_RECOUNT")
 strongest=max(fair,key=lambda a:(counts[a]["accuracy"],-work[a]))
 gain=counts[cand]["accuracy"]-counts[strongest]["accuracy"]
 ratio=work[cand]/max(1,work[strongest])
 no_regression=all(by_family[str(f)][cand]>=max(by_family[str(f)][a] for a in fair)
   for f in (500,501,502,503))
 passed=gain>=.03 and ratio<=1.2 and no_regression
 require(strongest==d["strongest_budget_fair_control"] and
   abs(gain-d["candidate_gain"])<1e-12 and
   abs(ratio-d["posterior_work_ratio"])<1e-12 and
   passed==d["frozen_criterion_met"] and
   no_regression==d["family_nondegradation"],"W_FROZEN_DECISION_DRIFT")
 return {"lane":"Wingless","diagnostic_rows":len(rows),
  "candidate_correct":counts[cand]["correct"],"control_correct":counts[strongest]["correct"],
  "gain_percentage_points":round(gain*100,5),"work_ratio":round(ratio,5),
  "frozen_train_criterion_met":passed,
  "frozen_scientific_disposition":"TRAIN_ONLY_SUPPORTED" if passed else "TRAIN_ONLY_NEGATIVE",
  "next_hypothesis":"LEARN_QUERY_CONDITIONAL_VALUE_WITH_DISJOINT_TRAINED_COST_PENALTY"
     if not passed else "REPLICATE_PUBLIC_EDGE_VALUE_UNDER_NEW_TRAIN_STRUCTURES",
  "next_experiment_authorized":False}
def yggdrasil(d):
 require(d.get("schema")=="yggdrasil.f46.paired-vs-shuffled-anchor.trainonly.v1"
  and d.get("stage")=="TRAIN_ONLY_CAUSAL_ABLATION_NOT_PRIMARY_ORIGINAL"
  and d.get("questions")==128 and len(d["rows"])==128
  and d.get("primary_original_not_executed") is True
  and d.get("diagnostic_seeds")==[401100,401108]
  and d.get("reserved_seeds")==[402000,402016]
  and d.get("old_original_reserved_not_touched")==[382000,382016],"Y_FROZEN_COHORT")
 counts=recount_scores(d,"predictions")
 rows=d["rows"]
 cand="learned_intervention_invariant"
 shuffled="count_matched_shuffled_intervention_pairs"
 unpaired="learned_unpaired_ablation"
 fair=("fitted_Gaussian_latent","empirical_conditional_Brier",
       "Gaussian_kernel","public_global_static","source_variance",unpaired,shuffled)
 require(all(a in counts for a in (*fair,cand)),"Y_CONTROL_MISSING")
 require(all(401100<=r["seed"]<401108 and r["family"] in (520,521,522,523)
  and r["mechanism"] in ("nonlinear_hysteresis","cross_channel_flip")
  and r["public_pairs"]==12 and r["public_flat_anchors"]==24
  for r in rows),"Y_RESERVED_SOURCE_TOUCHED")
 require(all(len(rs)==3 and all(len(trace)==2 and trace[0]==0
           and trace[1] in (1,2,3) for trace in rs)
    for r in rows for arm,rs in r["receipts"].items()),"Y_TWO_PAID_READS")
 strongest=max(fair,key=lambda a:counts[a]["accuracy"])
 gain=counts[cand]["accuracy"]-counts[strongest]["accuracy"]
 sh_gain=counts[cand]["accuracy"]-counts[shuffled]["accuracy"]
 un_gain=counts[cand]["accuracy"]-counts[unpaired]["accuracy"]
 mechanisms=("nonlinear_hysteresis","cross_channel_flip")
 for m in mechanisms:
  sub=[r for r in rows if r["mechanism"]==m]
  require(sub and all(abs(aggregate(sub,a,"predictions")[k]-d["by_mechanism"][m][a][k])<1e-10
                   for a in counts for k in ("correct","total","accuracy","fp","fn","Brier","logloss")),
                   "Y_MECHANISM_RECOUNT")
 no_regression=all(d["by_mechanism"][m][cand]["correct"]>=
   max(d["by_mechanism"][m][a]["correct"] for a in fair) for m in mechanisms)
 passed=gain>=.02 and sh_gain>0 and un_gain>0 and no_regression
 require(strongest==d["strongest_fair_control"] and
   abs(gain-d["gain_over_strongest_fair"])<1e-12 and
   abs(sh_gain-d["shuffled_pairs_ablation_gain"])<1e-12 and
   abs(un_gain-d["unpaired_ablation_gain"])<1e-12 and
   no_regression==d["heldout_mechanism_nondegradation"] and
   passed==d["frozen_criterion_met"],"Y_FROZEN_DECISION_DRIFT")
 return {"lane":"Yggdrasil","diagnostic_rows":len(rows),
  "candidate_correct":counts[cand]["correct"],"control_correct":counts[strongest]["correct"],
  "shuffled_control_correct":counts[shuffled]["correct"],
  "unpaired_control_correct":counts[unpaired]["correct"],
  "gain_percentage_points":round(gain*100,5),
  "shuffled_ablation_gain_percentage_points":round(sh_gain*100,5),
  "unpaired_ablation_gain_percentage_points":round(un_gain*100,5),
  "frozen_train_criterion_met":passed,
  "frozen_scientific_disposition":"TRAIN_ONLY_SUPPORTED" if passed else "TRAIN_ONLY_NEGATIVE",
  "next_hypothesis":"DISTINGUISH_CAUSAL_ANCHOR_PAIRING_FROM_CALIBRATION_CAPACITY_WITH_NEW_MECHANISMS"
     if not passed else "REPLICATE_CAUSAL_PAIRED_ANCHOR_ADVANTAGE_ON_DISJOINT_MECHANISMS",
  "next_experiment_authorized":False}
def review(wingless_root,yggdrasil_root):
 w,wh=load(wingless_root,"Wingless")
 y,yh=load(yggdrasil_root,"Yggdrasil")
 return {"schema":"forge.autonomy.f47-authentic-train-outcome-review.v1",
  "mode":"TWO_REAL_TRAIN_RESULT_RECOUNTS_AND_NONAUTHORIZING_SUCCESSORS",
  "sources":{"Wingless":dict(SOURCES["Wingless"],report_sha256=wh),
             "Yggdrasil":dict(SOURCES["Yggdrasil"],report_sha256=yh)},
  "decisions":[wingless(w),yggdrasil(y)],
  "real_train_runs_recounted":2,"independent_primary_originals_executed":0,
  "new_worker_dispatch_authorized":False,"scientifically_accepted":False,
  "dreamrsi_prospective_gain_proven":False,"theta_policy_promotion_authorized":False,
  "owner_accepted_ref_mutations":0}
def main():
 p=argparse.ArgumentParser()
 p.add_argument("--wingless-root",required=True)
 p.add_argument("--yggdrasil-root",required=True)
 p.add_argument("--out",required=True)
 x=p.parse_args()
 data=review(x.wingless_root,x.yggdrasil_root)
 pathlib.Path(x.out).write_text(json.dumps(data,sort_keys=True,separators=(",",":"))+"\n")
if __name__=="__main__":main()

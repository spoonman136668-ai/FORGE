"""F49: independently audit newly executed Wingless/Yggdrasil TRAIN experiments.

This reviewer is intentionally nonauthorizing: both studied cohorts are
TRAIN-only (not independent F3 originals); no accepted refs, model promotions
or science-worker dispatch. F50 records are hypotheses, not executed studies.
"""
import argparse,hashlib,json,math
from pathlib import Path
CATALOG={
 "Wingless":{
  "run_id":38807569165,
  "head":"737120f5522ba6c984119bfca0b7c16f4c94f18c",
  "artifact_id":12005934542,
  "artifact_name":"W-F49-fresh-identifiability-TRAIN-NO-ORIGINAL",
  "artifact_digest":"sha256:069a2d8ee3a609b70491b1fb34db8432dae29c422f4bb56435636eab6b4273da"},
 "Yggdrasil":{
  "run_id":38807773617,
  "head":"b839631fc5dae1ba5df5355a5a0eb2a3248f89e5",
  "artifact_id":12007765048,
  "artifact_name":"Y-F49-public-paired-anchor-TRAIN-NO-ORIGINAL",
  "artifact_digest":"sha256:26c0f59e8875ac32de3598c5acc5d91785e31f50ce6716f92e5bc44fda1c96d1"}
}
class Blocked(ValueError):pass
def require(ok,issue):
 if not ok:raise Blocked("F49_"+issue)
def sha(raw):return hashlib.sha256(raw).hexdigest()
def no_dup(pairs):
 result={}
 for k,v in pairs:
  require(k not in result,"DUPLICATE_JSON_KEY")
  result[k]=v
 return result
def load(folder,lane):
 root=Path(folder)
 raw=(root/"result.json").read_bytes()
 require(0<len(raw)<10_000_000,"INPUT_SIZE")
 manifest=(root/"result.sha256").read_text().split()
 require(len(manifest)==2 and manifest[0]==sha(raw)
   and Path(manifest[1]).name=="result.json","ARCHIVED_SHA256")
 require((root/"SOURCE_SHA").read_text().strip()==CATALOG[lane]["head"],
   "SOURCE_HEAD")
 report=json.loads(raw,object_pairs_hook=no_dup)
 require(type(report)==dict and type(report.get("rows")) is list,"SCHEMA")
 require(report.get("paid_api_calls")==0 and
   report.get("accepted_ref_mutation") is False and
   report.get("independent_F3_custody") is False and
   report.get("native_576_byte_resident_qualified") is False,"PRIVILEGE_DRIFT")
 return report,sha(raw)
def verify_w(d):
 require(d.get("schema")=="wingless.f49.public-identifiability.trainonly.v1"
  and d.get("stage")=="FRESH_PUBLIC_INDISCERNIBILITY_DIAGNOSTIC_NOT_PRIMARY_ORIGINAL"
  and d.get("original_executed") is False
  and d.get("scientific_accepted") is False
  and d.get("diagnostic_seeds")==[461100,461104]
  and d.get("fit_seeds_not_used")==[461000,461004]
  and d.get("reserved_originals_not_consumed")==[462000,462016]
  and d.get("old_reserved_originals_not_consumed")==[412000,412016]
  and d.get("candidate_action_beam")==4,"W_PRECODE_FREEZE")
 rows=d["rows"]
 require(len(rows)==d.get("questions")==32 and
    d["counterfactual_world_evaluations"]==64,"W_ROW_COUNT")
 incompatible=0;public=0;hindsight=0;any_benefit=0
 seen=set()
 for r in rows:
  ident=(r["seed"],r["family"],r["length"])
  require(ident not in seen and 461100<=ident[0]<461104 and
    ident[1] in (700,701,702,703) and ident[2] in (3,5),"W_COHORT_COLLISION")
  seen.add(ident)
  require(r["posterior_world_count"]==1296 and
    len(r["counterfactual_worlds"])==2 and
    len(r["prereg_beam"])==4 and
    len(r["public"])==12,"W_POSTERIOR_OR_BEAM")
  options=[]
  for world in r["counterfactual_worlds"]:
   idx=world["beneficial_action_indices"]
   require(type(idx) is list and len(idx)==len(set(idx)) and
     all(type(k) is int and 0<=k<4 for k in idx),"W_INVALID_BENEFICIAL_ACTION")
   public+=int(world["public_policy_prediction"]==world["truth"])
   hindsight+=int(world["oracle_one_purchase_prediction"]==world["truth"])
   if world["oracle_action"] is not None:
    require(world["oracle_action"] in r["prereg_beam"],"W_ORACLE_NOT_BOUNDED")
   options.append(set(idx))
  conflict=bool(options[0] and options[1] and options[0].isdisjoint(options[1]))
  incompatible+=int(conflict)
  any_benefit+=int(bool(options[0] or options[1]))
  require(conflict==r["incompatible_oracle_actions"],"W_HIDDEN_ACTION_CONFLICT_RECOUNT")
 conflict_rate=incompatible/len(rows)
 headroom=(hindsight-public)/(2*len(rows))
 qualified=conflict_rate>=.25 and headroom>=.10
 require(incompatible==d["distinct_beneficial_action_cases"] and
    any_benefit==d["any_beneficial_action_cases"] and
    public==d["public_one_step_correct"] and
    hindsight==d["unfair_hindsight_oracle_correct"] and
    abs(conflict_rate-d["incompatible_hidden_optimal_action_fraction"])<1e-12 and
    abs(headroom-d["unfair_oracle_headroom_fraction"])<1e-12 and
    qualified==d["criterion_met"] and
    d["verdict"]==("TRAIN_ONLY_IDENTIFIABILITY_BARRIER_SUPPORTED_NOT_F3"
        if qualified else "TRAIN_ONLY_IDENTIFIABILITY_BARRIER_NOT_SHOWN"),
    "W_PREREG_ADVANCEMENT_DRIFT")
 return {"lane":"Wingless","experiment":"W-F49",
  "diagnostic_cases":32,"paired_counterfactual_world_evaluations":64,
  "incompatible_action_cases":incompatible,
  "incompatible_rate":round(conflict_rate,7),
  "public_policy_correct":public,"hindsight_oracle_correct":hindsight,
  "hindsight_headroom_pp":round(100*headroom,5),
  "frozen_criterion_met":qualified,
  "disposition":"TRAIN_ONLY_IDENTIFIABILITY_SUPPORTED_NOT_F3" if qualified
          else "TRAIN_ONLY_NEGATIVE",
  "successor_hypothesis":"STRUCTURAL_WITNESS_OF_PUBLIC_EQUIVALENT_WORLDS_WITH_DIFFERENT_NECESSARY_ACTIONS"
    if not qualified else "REPLICATE_INDISTINGUISHABLE_ACTION_AMBIGUITY_ON_NEW_TRAIN_SOURCES",
  "successor_execution_authorized":False}
def aggregate(rows,arm):
 n=len(rows)
 scores=[r["predictions"][arm] for r in rows]
 probs=[r["probabilities"][arm] for r in rows]
 require(all(type(p) in (float,int) and 0<p<1 for p in probs),"Y_PROBABILITY")
 return dict(total=n,correct=sum(x==r["truth"] for x,r in zip(scores,rows)),
  accuracy=sum(x==r["truth"] for x,r in zip(scores,rows))/n,
  fp=sum(bool(x) and not r["truth"] for x,r in zip(scores,rows)),
  fn=sum(not bool(x) and bool(r["truth"]) for x,r in zip(scores,rows)),
  Brier=sum((p-float(r["truth"]))**2 for p,r in zip(probs,rows))/n,
  logloss=-sum(math.log(p if r["truth"] else 1-p)
               for p,r in zip(probs,rows))/n)
def verify_y(d):
 require(d.get("schema")=="yggdrasil.f49.public-paired-identifiability.trainonly.v1"
  and d.get("stage")=="NEW_PUBLIC_PAIR_DIAGNOSTIC_ONLY_NOT_PRIMARY_ORIGINAL"
  and d.get("primary_original_not_executed") is True
  and d.get("diagnostic_seeds")==[471100,471104]
  and d.get("fit_seeds_not_consumed")==[471000,471004]
  and d.get("reserved_originals_not_consumed")==[472000,472016]
  and d.get("old_originals_not_consumed")==[422000,422016]
  and d.get("public_reference_pairs")==12,"Y_PRECODE_FREEZE")
 rows=d["rows"];scores=d["scores"]
 require(len(rows)==d.get("questions")==64 and type(scores)==dict,"Y_ROW_COUNT")
 seen=set()
 for r in rows:
  ident=(r["seed"],r["family"],r["mechanism"],r["condition"])
  require(ident not in seen and 471100<=ident[0]<471104 and
    ident[1] in (720,721,722,723) and
    ident[2] in ("nonlinear_hysteresis","cross_channel_flip")
    and ident[3] in ("coupled","decoupled"),"Y_COHORT_DRIFT")
  seen.add(ident)
  require(r["public_pairs"]==12 and r["public_flat_anchors"]==24,
      "Y_PUBLIC_ANCHOR_COUNT")
  require(set(r["predictions"])==set(scores) and
          set(r["probabilities"])==set(scores),"Y_SCORE_ARMS")
  require(all(len(traces)==3 and all(len(t)==2 and t[0]==0 and
       t[1] in (1,2,3) for t in traces) for traces in r["receipts"].values()),
       "Y_PAID_CAP")
 verified={a:aggregate(rows,a) for a in scores}
 require(all(all(k in scores[a] and abs(scores[a][k]-v)<1e-10
      for k,v in vals.items()) for a,vals in verified.items()),"Y_ROW_METRICS_RECOUNT")
 for mech in ("nonlinear_hysteresis","cross_channel_flip"):
  group=[r for r in rows if r["mechanism"]==mech]
  require(group and all(
    all(k in d["by_mechanism"][mech][a] and
      abs(v-d["by_mechanism"][mech][a][k])<1e-10
      for k,v in aggregate(group,a).items()) for a in scores),
    "Y_MECHANISM_RECOUNT")
 candidate="paired_public_covariance"
 shuffled="shuffled_public_covariance"
 fair=("shuffled_public_covariance","unpaired_first_channel_calibration",
       "empirical_conditional_Brier","fitted_Gaussian_latent")
 require(all(a in verified for a in (*fair,candidate)),"Y_FAIR_CONTROLS")
 best=max(fair,key=lambda a:verified[a]["accuracy"])
 gain=verified[candidate]["accuracy"]-verified[best]["accuracy"]
 contrast=verified[candidate]["accuracy"]-verified[shuffled]["accuracy"]
 no_degrade=all(
  d["by_mechanism"][m][candidate]["correct"]>=
  max(d["by_mechanism"][m][a]["correct"] for a in fair)
  for m in ("nonlinear_hysteresis","cross_channel_flip"))
 qualified=gain>=.02 and contrast>0 and no_degrade
 require(best==d["strongest_fair_control"] and
    abs(gain-d["gain_over_strongest_fair"])<1e-12 and
    abs(contrast-d["paired_vs_shuffled_gain"])<1e-12 and
    no_degrade==d["heldout_mechanism_nondegradation"] and
    qualified==d["frozen_criterion_met"] and
    d["verdict"]==("TRAIN_ONLY_PAIRING_IDENTIFIABLE_NOT_F3"
      if qualified else "TRAIN_ONLY_PAIRING_NOT_QUALIFIED"),
    "Y_THRESHOLD_OR_ABLATION_DRIFT")
 return {"lane":"Yggdrasil","experiment":"Y-F49",
  "diagnostic_cases":64,
  "paired_correct":verified[candidate]["correct"],
  "shuffled_correct":verified[shuffled]["correct"],
  "strongest_fair_policy":best,
  "strongest_fair_correct":verified[best]["correct"],
  "gain_over_fair_pp":round(gain*100,5),
  "paired_vs_shuffled_gain_pp":round(contrast*100,5),
  "frozen_criterion_met":qualified,
  "public_pair_marginals_recountable_from_report":False,
  "interpretation_limit":"Marginal equivalence must be audited at frozen-source level; report field alone is insufficient",
  "disposition":"TRAIN_ONLY_PAIRING_SUPPORTED_NOT_F3" if qualified else "TRAIN_ONLY_NEGATIVE",
  "successor_hypothesis":"TEST_CAUSAL_PAIR_IDENTIFIABILITY_ON_PUBLIC_ANCHORS_WITH_EXPLICIT_MATCHED_NEGATIVE"
     if not qualified else "REPLICATE_PAIRED_ANCHOR_SIGNAL_ON_DISJOINT_TRAIN_MECHANISMS",
  "successor_execution_authorized":False}
def review(w,y):
 wr,wh=load(w,"Wingless");yr,yh=load(y,"Yggdrasil")
 decisions=[verify_w(wr),verify_y(yr)]
 return {"schema":"forge.autonomy.f49-real-train-to-f50.v1",
   "sources":{"Wingless":dict(CATALOG["Wingless"],result_sha256=wh),
              "Yggdrasil":dict(CATALOG["Yggdrasil"],result_sha256=yh)},
   "decisions":decisions,
   "two_fresh_train_experiments_reviewed":True,
   "prospective_preregistered_f50_ready":False,
   "research_workers_dispatched":0,
   "protected_primary_originals_executed":0,
   "independent_scientific_originals_accepted":0,
   "dream_rsi_prospective_gain_proven":False,
   "theta_policy_improvement_authorized":False,
   "accepted_ref_mutations":0}
def main():
 p=argparse.ArgumentParser()
 p.add_argument("--wingless",required=True);p.add_argument("--yggdrasil",required=True)
 p.add_argument("--out",required=True)
 a=p.parse_args()
 Path(a.out).write_text(json.dumps(review(a.wingless,a.yggdrasil),
   sort_keys=True,separators=(",",":"))+"\n",encoding="utf-8")
if __name__=="__main__":main()

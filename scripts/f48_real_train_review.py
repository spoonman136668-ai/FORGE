"""F48: genuine two-lane TRAIN result -> independent recount -> next study design.

Source-pinned TRAIN observations only; never create primary-original authority,
replay a consumed scientific original, retrain Theta on unaccepted results, or
claim recursive Dream-RSI improvement.
"""
import argparse,hashlib,json,math,pathlib
CATALOG={
 "Wingless":{"run":38805703700,"sha":"0bad6a035e4257f0bc18f593a25e0770d378d17d",
 "artifact":12005084367,"name":"W-F48-disjoint-trained-query-value-train-NO-ORIGINAL"},
 "Yggdrasil":{"run":38805887306,"sha":"b2407c469086c6a0ea99e9f3986c4336ef832e79",
 "artifact":12006805585,"name":"Y-F48-shifted-pair-identifiability-train-NO-ORIGINAL"}
}
class Rejected(ValueError):pass
def need(ok,reason):
 if not ok:raise Rejected("FORGE_F48_"+reason)
def digest(raw):return hashlib.sha256(raw).hexdigest()
def strict(pairs):
 d={}
 for k,v in pairs:
  need(k not in d,"DUPLICATE_JSON_KEY")
  d[k]=v
 return d
def load(root,lane):
 root=pathlib.Path(root)
 raw=(root/"result.json").read_bytes()
 need(0<len(raw)<=12_000_000,"BOUNDED_REPORT")
 sha=(root/"result.sha256").read_text().split()
 need(len(sha)==2 and sha[0]==digest(raw) and pathlib.Path(sha[1]).name=="result.json","SHA_MISMATCH")
 need((root/"SOURCE_SHA").read_text().strip()==CATALOG[lane]["sha"],"SOURCE_DRIFT")
 report=json.loads(raw,object_pairs_hook=strict)
 need(type(report)==dict and type(report.get("rows")) is list and
      type(report.get("scores")) is dict,"SCHEMA")
 need(report.get("paid_api_calls")==0 and report.get("accepted_ref_mutation") is False
  and report.get("independent_F3_custody") is False
  and report.get("native_576_byte_resident_qualified") is False,"FALSE_SCIENCE")
 return report,digest(raw)
def recount(d,key):
 scores=d["scores"];rows=d["rows"]
 need(bool(scores) and all(set(r[key])==set(scores) for r in rows),"POLICY_SET_DRIFT")
 out={}
 for a,claimed in scores.items():
  correct=sum(r[key][a]==r["truth"] for r in rows)
  verified={"correct":correct,"total":len(rows),"accuracy":correct/len(rows)}
  if key=="predictions":
   probs=[r["probabilities"][a] for r in rows]
   need(all(type(p) in (int,float) and 0<p<1 for p in probs),"PROBABILITY_INVALID")
   verified.update(fp=sum(bool(r[key][a]) and not r["truth"] for r in rows),
    fn=sum(not bool(r[key][a]) and bool(r["truth"]) for r in rows),
    Brier=sum((p-float(r["truth"]))**2 for p,r in zip(probs,rows))/len(rows),
    logloss=-sum(math.log(p if r["truth"] else 1-p) for p,r in zip(probs,rows))/len(rows))
  need(all(k in claimed and abs(claimed[k]-v)<1e-10
           for k,v in verified.items()),"RAW_ROW_RECOUNT")
  out[a]=verified
 return out
def wing(d):
 need(d.get("schema")=="wingless.f48.disjoint-trained-query-value.trainonly.v1"
  and d.get("stage")=="ONE_FRESH_FIT_AND_DIAGNOSTIC_NO_PRIMARY_ORIGINAL"
  and d.get("questions")==32 and d.get("training_questions")==32
  and d.get("diagnostic_truth_not_used_for_fit") is True
  and d.get("fit_seeds")==[411000,411004]
  and d.get("diagnostic_seeds")==[411100,411104]
  and d.get("originals_reserved_not_consumed")==[412000,412016]
  and d.get("original_executed") is False,"W_ORIGINAL_GUARD")
 scores=recount(d,"answers");rows=d["rows"]
 cand="learned_query_cost_value"
 fair=("one_step_value","exact_entropy","query_frontier","budget_matched_rank")
 need(all(a in scores for a in (*fair,cand)),"W_CONTROLS")
 need(all(411100<=r["seed"]<411104 and r["family"] in (600,601,602,603)
   and len(r["receipts"][a])<=2 for r in rows for a in r["receipts"]),"W_COHORT_OR_PAID_CAP")
 metered={a:sum(r["work"][a] for r in rows) for a in d["posterior_world_work"]}
 need(metered==d["posterior_world_work"],"W_COMPUTE_RECOUNT")
 family={str(f):{a:sum(r["answers"][a]==r["truth"] for r in rows if r["family"]==f)
                  for a in scores} for f in (600,601,602,603)}
 need(family==d["by_family"],"W_FAMILY_RECOUNT")
 winner=max(fair,key=lambda a:(scores[a]["accuracy"],-metered[a]))
 gain=scores[cand]["accuracy"]-scores[winner]["accuracy"]
 ratio=metered[cand]/max(1,metered[winner])
 stable=all(family[str(f)][cand]>=max(family[str(f)][a] for a in fair)
            for f in (600,601,602,603))
 approved=gain>=.05 and ratio<=1.2 and stable
 need(winner==d["strongest_budget_fair_control"]
  and abs(gain-d["candidate_gain"])<1e-12
  and abs(ratio-d["posterior_work_ratio"])<1e-12
  and approved==d["frozen_criterion_met"]
  and stable==d["family_nondegradation"],"W_ADVANCEMENT_DRIFT")
 return dict(lane="Wingless",candidate_correct=scores[cand]["correct"],
  control_correct=scores[winner]["correct"],total=32,trial_gain_pp=round(gain*100,4),
  compute_ratio=round(ratio,4),training_beta=d["selected_beta_train_only"],
  train_status="TRAIN_THRESHOLD_PASSED_NOT_INDEPENDENT_ACCEPTANCE" if approved else "TRAIN_ONLY_NEGATIVE",
  next_mechanism="TEST_IDENTIFIABILITY_OF_PUBLIC_QUERY_EDGE_VALUE_BEFORE_MORE_FITTING"
                if not approved else "REPLICATE_COST_AWARE_POLICY_ON_NEW_TRAIN_STRUCTURES")
def ygg(d):
 need(d.get("schema")=="yggdrasil.f48.shifted-anchor-identifiability.trainonly.v1"
  and d.get("stage")=="NEW_SHIFTED_SENSING_TRAIN_ONLY_NO_ORIGINAL"
  and d.get("questions")==128 and len(d["rows"])==128
  and d.get("fit_seeds")==[421000,421008]
  and d.get("diagnostic_seeds")==[421100,421108]
  and d.get("reserved_seeds")==[422000,422016]
  and d.get("primary_original_not_executed") is True,"Y_ORIGINAL_GUARD")
 scores=recount(d,"predictions");rows=d["rows"]
 cand="learned_intervention_invariant"
 shuffled="count_matched_shuffled_intervention_pairs"
 unpaired="learned_unpaired_ablation"
 fair=("fitted_Gaussian_latent","empirical_conditional_Brier","Gaussian_kernel",
       "public_global_static","source_variance",unpaired,shuffled)
 need(all(a in scores for a in (*fair,cand)),"Y_CONTROLS")
 need(all(421100<=r["seed"]<421108 and r["family"] in (620,621,622,623)
  and r["public_pairs"]==12 and r["public_flat_anchors"]==24
  for r in rows),"Y_COHORT_OR_ANCHOR")
 need(all(len(traces)==3 and all(len(t)==2 and t[0]==0 and t[1] in (1,2,3) for t in traces)
          for r in rows for traces in r["receipts"].values()),"Y_PHYSICAL_TWO_READS")
 winner=max(fair,key=lambda a:scores[a]["accuracy"])
 gain=scores[cand]["accuracy"]-scores[winner]["accuracy"]
 shuffle_gain=scores[cand]["accuracy"]-scores[shuffled]["accuracy"]
 unpaired_gain=scores[cand]["accuracy"]-scores[unpaired]["accuracy"]
 groups={}
 for m in ("nonlinear_hysteresis","cross_channel_flip"):
  subset=[r for r in rows if r["mechanism"]==m]
  need(subset,"Y_MECHANISM_ABSENT")
  groups[m]={a:sum(r["predictions"][a]==r["truth"] for r in subset) for a in scores}
  need(all(groups[m][a]==d["by_mechanism"][m][a]["correct"] for a in scores),
       "Y_MECHANISM_RECOUNT")
 not_regressed=all(groups[m][cand]>=max(groups[m][a] for a in fair) for m in groups)
 passed=gain>=.02 and shuffle_gain>0 and unpaired_gain>0 and not_regressed
 need(winner==d["strongest_fair_control"] and
  abs(gain-d["gain_over_strongest_fair"])<1e-12
  and abs(shuffle_gain-d["shuffled_pairs_ablation_gain"])<1e-12
  and abs(unpaired_gain-d["unpaired_ablation_gain"])<1e-12
  and not_regressed==d["heldout_mechanism_nondegradation"]
  and passed==d["frozen_criterion_met"],"Y_ADVANCEMENT_DRIFT")
 return dict(lane="Yggdrasil",candidate_correct=scores[cand]["correct"],
  control_correct=scores[winner]["correct"],shuffled_correct=scores[shuffled]["correct"],
  unpaired_correct=scores[unpaired]["correct"],total=128,
  trial_gain_pp=round(100*gain,4),
  shuffled_ablation_pp=round(100*shuffle_gain,4),
  unpaired_ablation_pp=round(100*unpaired_gain,4),
  train_status="TRAIN_THRESHOLD_PASSED_NOT_INDEPENDENT_ACCEPTANCE" if passed else "TRAIN_ONLY_NEGATIVE",
  next_mechanism="TEST_PUBLIC_ANCHOR_CAUSAL_IDENTIFIABILITY_WITHOUT_LEARNED_CAPACITY"
                 if not passed else "REPLICATE_PAIRED_GAIN_ON_NEW_HELDOUT_SOURCE_TYPES")
def review(w,y):
 x,wx=load(w,"Wingless");z,yx=load(y,"Yggdrasil")
 choices=[wing(x),ygg(z)]
 plans=[]
 for lane,choice in zip(("Wingless","Yggdrasil"),choices):
  plans.append(dict(lane=lane,hypothesis=choice["next_mechanism"],
   exact_parent_run=CATALOG[lane]["run"],parent_source_commit=CATALOG[lane]["sha"],
   training_only=True,owner_prereg_committed=False,mechanism_implemented=False,
   experiment_dispatched=False,original_firstuse_cleared=False,
   scientific_accepted=False,theta_promotion_authorized=False))
 return dict(schema="forge.autonomy.f48-authentic-train-to-f49-plans.v1",
  mode="FRESH_F48_REAL_TRAIN_OUTCOMES_RECOUNTED_NOT_ORIGINALS",
  sources={"Wingless":dict(CATALOG["Wingless"],report_sha256=wx),
   "Yggdrasil":dict(CATALOG["Yggdrasil"],report_sha256=yx)},
  decisions=choices,next_precode_proposals=plans,
  research_studies_recounted=2,originals_executed=0,
  independent_science_accepted=False,accepted_ref_mutations=0,
  recursive_dream_rsi_improvement_proven=False,
  worker_dispatch_authorized=False)
def main():
 p=argparse.ArgumentParser()
 p.add_argument("--wingless",required=True);p.add_argument("--yggdrasil",required=True);p.add_argument("--out",required=True)
 a=p.parse_args()
 pathlib.Path(a.out).write_text(json.dumps(review(a.wingless,a.yggdrasil),sort_keys=True,separators=(",",":"))+"\n")
if __name__=="__main__":main()

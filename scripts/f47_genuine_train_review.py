"""F47 genuine TRAIN-only experiment acceptance and next hypotheses. Read-only.
Do not upgrade TRAIN science into F3, consume originals, or learn Theta from this.
"""
import argparse,hashlib,json,math
from pathlib import Path
class Blocked(ValueError):pass
EXPECTED={
 "Wingless":("bd7f18a31369cd913d353477e60b7be6d0d87876",
    "7df9f02dc409ecabb7e9f47d20191b0b2a706923e1f37939064d4d7ad665fac4",38803701796,12005147117),
 "Yggdrasil":("88963d04511a49e935c0873bf14af15f771274d0",
    "2b8806ffc4dd5eb94dc1187d782c8518c22355dad01915d085b0d0744fd7a5b2",38803873408,12005990427)}
def ensure(v,msg):
 if not v:raise Blocked("F47_"+msg)
def sha(v):return hashlib.sha256(v).hexdigest()
def unique(pairs):
 d={}
 for k,v in pairs:
  ensure(k not in d,"DUPLICATE_JSON_KEY")
  d[k]=v
 return d
def load(directory,lane):
 head,expected,run,artifact=EXPECTED[lane]
 root=Path(directory);raw=(root/"result.json").read_bytes()
 ensure(0<len(raw)<=3000000 and sha(raw)==expected,"SOURCE_REPORT_SHA_DRIFT")
 parts=(root/"result.sha256").read_text().split()
 ensure(len(parts)==2 and parts[0]==sha(raw) and Path(parts[1]).name=="result.json","MANIFEST")
 ensure((root/"SOURCE_SHA").read_text().strip()==head,"SOURCE_COMMIT")
 doc=json.loads(raw,object_pairs_hook=unique)
 ensure(doc["paid_api_calls"]==0 and doc["accepted_ref_mutation"] is False and
        doc["independent_F3_custody"] is False,"FALSE_SCIENCE")
 return doc,{"head":head,"report_sha256":expected,"run_id":run,"artifact_id":artifact}
def recount(lane,d):
 rows=d["rows"]; n=len(rows);scores=d["scores"]
 ensure((lane=="Wingless" and n==96) or (lane=="Yggdrasil" and n==128),"ROW_COUNT")
 key="answers" if lane=="Wingless" else "predictions"
 seen=set()
 for row in rows:
  if lane=="Wingless":
   ident=(row["seed"],row["family"],row["length"])
   ensure(391100<=row["seed"]<391112 and row["family"] in (500,501,502,503) and
          row["length"] in (3,5),"W_RESERVED_OR_SOURCE_DRIFT")
  else:
   ident=(row["seed"],row["family"],row["mechanism"],row["condition"])
   ensure(401100<=row["seed"]<401108 and row["family"] in (520,521,522,523)
           and row["public_pairs"]==12 and row["public_flat_anchors"]==24,"Y_RESERVED_OR_SOURCE_DRIFT")
  ensure(ident not in seen and set(row[key])==set(scores),"IDENTITY_OR_ARM_DRIFT")
  seen.add(ident)
  for arm,receipts in row["receipts"].items():
   if lane=="Wingless":
    ensure(len(receipts)<=2,"PAID_LIMIT")
    ensure(len({tuple(x[:2]) for x in receipts})==len(receipts),"DUPLICATE_MAPPING")
   else:
    # Yggdrasil legitimately buys two sensors for EACH of three roles,
    # not two total; outer list is role-wise traces.
    ensure(len(receipts)==3,"ROLE_COUNT")
    ensure(all(len(trace)==2 and trace[0]==0 and trace[1] in (1,2,3)
               for trace in receipts),"PAID_SENSOR")
 result={}
 for arm in scores:
  nright=sum(r[key][arm]==r["truth"] for r in rows)
  ensure(nright==scores[arm]["correct"] and n==scores[arm]["total"],"ROW_RECOUNT")
  result[arm]=nright
  if lane=="Yggdrasil":
   fp=sum(bool(r[key][arm]) and not r["truth"] for r in rows)
   fn=sum(not bool(r[key][arm]) and r["truth"] for r in rows)
   brier=sum((r["probabilities"][arm]-r["truth"])**2 for r in rows)/n
   logloss=-sum(math.log(r["probabilities"][arm] if r["truth"] else 1-r["probabilities"][arm]) for r in rows)/n
   v=scores[arm]
   ensure((fp,fn)==(v["fp"],v["fn"]) and
       abs(brier-v["Brier"])<1e-10 and abs(logloss-v["logloss"])<1e-10,"METRICS_RECOUNT")
  else:
   if arm in d["posterior_world_work"]:
    work=sum(r["work"][arm] for r in rows)
    ensure(work==d["posterior_world_work"][arm],"COMPUTE_RECOUNT")
 return result
def decide(wdir,ydir):
 w,wm=load(wdir,"Wingless")
 y,ym=load(ydir,"Yggdrasil")
 ensure(w["schema"]=="wingless.f46.query-edge-voc.trainonly.v1" and
       w["stage"]=="TRAIN_ONLY_NOT_ORIGINAL" and w["original_executed"] is False and
       w["seeds"]==[391100,391112] and w["reserved_originals_not_consumed"]==[392000,392016],
       "W_SOURCE_STATUS")
 ensure(y["schema"]=="yggdrasil.f46.paired-vs-shuffled-anchor.trainonly.v1" and
       y["stage"]=="TRAIN_ONLY_CAUSAL_ABLATION_NOT_PRIMARY_ORIGINAL" and
       y["primary_original_not_executed"] is True and
       y["diagnostic_seeds"]==[401100,401108] and y["reserved_seeds"]==[402000,402016],
       "Y_SOURCE_STATUS")
 wc=recount("Wingless",w);yc=recount("Yggdrasil",y)
 wtrial=wc["query_edge_voc_per_compute"]
 wctrl=max((wc[a],a) for a in ("one_step_value","exact_entropy","query_frontier","budget_matched_rank"))
 wg=(wtrial-wctrl[0])/96
 work=w["posterior_world_work"]
 ratio=work["query_edge_voc_per_compute"]/max(1,work[w["strongest_budget_fair_control"]])
 family_guard=all(w["by_family"][str(f)]["query_edge_voc_per_compute"]>=
                  max(w["by_family"][str(f)][a] for a in
                      ("one_step_value","exact_entropy","query_frontier","budget_matched_rank"))
                  for f in (500,501,502,503))
 wpass=wg>=.03 and ratio<=1.2 and family_guard
 ensure(w["frozen_criterion_met"]==wpass and abs(wg-w["candidate_gain"])<1e-12
        and abs(ratio-w["posterior_work_ratio"])<1e-12,"W_THRESHOLD_RECOUNT")
 yt=yc["learned_intervention_invariant"]
 fair=("fitted_Gaussian_latent","empirical_conditional_Brier","Gaussian_kernel",
       "public_global_static","source_variance","learned_unpaired_ablation",
       "count_matched_shuffled_intervention_pairs")
 best=max(yc[a] for a in fair)
 gain=(yt-best)/128
 shuffled=(yt-yc["count_matched_shuffled_intervention_pairs"])/128
 unpaired=(yt-yc["learned_unpaired_ablation"])/128
 mech={r["mechanism"] for r in y["rows"]}
 ensure(mech==set(y["heldout_mechanisms"]) and len(mech)==2,"MECHANISM")
 nonregress=all(sum(r["predictions"]["learned_intervention_invariant"]==r["truth"]
                   for r in y["rows"] if r["mechanism"]==m)>=
                  max(sum(r["predictions"][a]==r["truth"]
                    for r in y["rows"] if r["mechanism"]==m) for a in fair) for m in mech)
 ypass=gain>=.02 and shuffled>0 and unpaired>0 and nonregress
 ensure(y["frozen_criterion_met"]==ypass and
        abs(gain-y["gain_over_strongest_fair"])<1e-12 and
        abs(shuffled-y["shuffled_pairs_ablation_gain"])<1e-12 and
        nonregress==y["heldout_mechanism_nondegradation"],"Y_THRESHOLD_RECOUNT")
 return {"schema":"forge.autonomy.f47-genuine-two-train-outcomes.v1",
   "source":{"Wingless":wm,"Yggdrasil":ym},
   "reviews":[
    {"lane":"Wingless","candidate_correct":wtrial,"best_fair_correct":wctrl[0],
     "total":96,"gain_pp":round(100*wg,6),"cost_ratio":round(ratio,6),
     "family_nondegradation":family_guard,
     "frozen_train_criterion_met":wpass,
     "disposition":"TRAIN_ONLY_SUPPORTED_NOT_F3" if wpass else "TRAIN_ONLY_NEGATIVE",
     "next_hypothesis":"MEASURE_QUERY_EDGE_VALUE_RANK_STABILITY_AND_CAUSAL_INFORMATION_VALUE_WITH_NEW_PUBLIC_SOURCE_FAMILIES"
        if not wpass else "REPLICATE_PUBLIC_VOC_ON_NEW_BUDGET_MATCHED_TRAIN_FAMILIES"},
    {"lane":"Yggdrasil","candidate_correct":yt,"best_fair_correct":best,
     "shuffled_pairs_correct":yc["count_matched_shuffled_intervention_pairs"],
     "unpaired_learned_correct":yc["learned_unpaired_ablation"],
     "total":128,"gain_pp":round(100*gain,6),
     "paired_vs_shuffled_pp":round(100*shuffled,6),
     "paired_vs_unpaired_pp":round(100*unpaired,6),
     "heldout_mechanism_nondegradation":nonregress,
     "frozen_train_criterion_met":ypass,
     "disposition":"TRAIN_ONLY_SUPPORTED_NOT_F3" if ypass else "TRAIN_ONLY_NEGATIVE",
     "next_hypothesis":"IDENTIFY_WHEN_PUBLIC_PAIRED_INTERVENTIONS_ADD_CAUSAL_INFORMATION_BEFORE_TRAINING_ANOTHER_POLICY"
       if not ypass else "REPLICATE_PAIRED_CAUSAL_EFFECT_ON_NEW_UNSEEN_MECHANISMS"}],
   "actual_fresh_experiments_executed":2,
   "both_source_qualifications_independently_reviewed":True,
   "primary_originals_executed":0,"originals_replayed":0,
   "new_science_dispatch_authorized":False,"scientific_accepted":False,
   "theta_promotion_eligible":False,"dream_policy_improvement_proven":False,
   "automatic_successor_hypotheses_prepared":True}
def main():
 p=argparse.ArgumentParser()
 p.add_argument("--wingless",required=True)
 p.add_argument("--yggdrasil",required=True)
 p.add_argument("--out",required=True)
 a=p.parse_args()
 Path(a.out).write_text(json.dumps(decide(a.wingless,a.yggdrasil),
                           sort_keys=True,separators=(",",":"))+"\n")
if __name__=="__main__":main()

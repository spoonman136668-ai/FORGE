"""Real F45 two-lane TRAIN-only evidence -> falsifiable mechanism-changing successors.
No owner release, reserved original, accepted-science claim or API mutation.
"""
import argparse
import hashlib
import json
from pathlib import Path

SOURCES={
"Wingless":("w-f45","wingless.f45.cost-capped-selective-lookahead.trainonly.v1",
"ff93c23e7e7f1a01e8187a765ac95c9d47c8189d",38800310426,12003528038),
"Yggdrasil":("y-f45","yggdrasil.f45.paired-intervention-invariance.trainonly.v1",
"9107ddf19ff05a0afa5a085e0c9ee477a7335db6",38800495808,12003268501)}
class Blocked(ValueError):pass
def need(ok,reason):
 if not ok:raise Blocked("F45_"+reason)
def sha(x):return hashlib.sha256(x).hexdigest()
def strict(pairs):
 d={}
 for k,v in pairs:
  need(k not in d,"DUPLICATE_KEY")
  d[k]=v
 return d
def load(root,lane):
 stem,schema,head,run,artifact=SOURCES[lane]
 root=Path(root)
 raw=(root/(stem+"-train.json")).read_bytes()
 need(0<len(raw)<=2_000_000,"RAW_SIZE")
 manifest=(root/(stem+"-train.sha256")).read_text().split()
 need(len(manifest)==2 and manifest[0]==sha(raw)
   and Path(manifest[1]).name==stem+"-train.json","HASH_MISMATCH")
 need((root/(stem+"-head.txt")).read_text().strip()==head,"HEAD_DRIFT")
 doc=json.loads(raw,object_pairs_hook=strict)
 need(doc.get("schema")==schema and type(doc.get("rows")) is list,"SCHEMA")
 need(doc.get("accepted_ref_mutation") is False and
      doc.get("independent_F3_custody") is False and
      doc.get("native_576_byte_resident_qualified") is False and
      doc.get("paid_api_calls")==0,"SCIENCE_AUTHORITY_FALSE")
 original=(doc.get("original_executed") is False if lane=="Wingless"
            else doc.get("primary_original_not_executed") is True)
 need(original,"NOT_TRAIN_ONLY")
 rows=doc["rows"]
 need(len(rows)==doc.get("questions") and len(rows) in (72,128),"ROWS")
 reserved=doc["reserved_seeds"]
 need(type(reserved) is list and len(reserved)==2 and
      all(type(x) is int for x in reserved) and reserved[0]<reserved[1],"RESERVE")
 need(all(type(row.get("seed")) is int and
              not reserved[0]<=row["seed"]<reserved[1] for row in rows),"ORIGINAL_SEED")
 need(set(r["family"] for r in rows).isdisjoint(doc["reserved_families"]),"ORIGINAL_FAMILY")
 policies=set(doc["scores"])
 key="answers" if lane=="Wingless" else "predictions"
 need(all(set(r[key])==policies for r in rows),"ROW_POLICIES")
 counts={name:sum(row[key][name]==row["truth"] for row in rows) for name in policies}
 need(all(doc["scores"][k]["correct"]==v and doc["scores"][k]["total"]==len(rows) and
          abs(doc["scores"][k]["accuracy"]-v/len(rows))<1e-12
          for k,v in counts.items()),"INDEPENDENT_RECOUNT")
 meta={"run_id":run,"artifact_id":artifact,"source_commit":head,
       "report_sha256":sha(raw),"stage":doc["stage"]}
 return doc,counts,meta
def decide(wpath,ypath):
 w,ws,wm=load(wpath,"Wingless")
 y,ys,ym=load(ypath,"Yggdrasil")
 need(w["stage"]=="SYNTHETIC_FRESH_TRAIN_ONLY_NO_ORIGINAL" and
      y["stage"]=="FRESH_TRAIN_ONLY_UNSEEN_MECHANISMS_NOT_ORIGINAL","STAGE")
 wc="selective_budgeted_lookahead";wf=w["strongest_budget_fair_control"]
 need(wf=="one_step_value","W_FROZEN_CONTROL")
 work={k:sum(r["work"][k] for r in w["rows"]) for k in w["posterior_world_work"]}
 need(work==w["posterior_world_work"],"W_WORK_RECOUNT")
 deep=sum(bool(r["deep_gate"]["used_deep"]) for r in w["rows"])
 need(deep==w["deep_gate_count"],"W_GATE_RECOUNT")
 w_gain=(ws[wc]-ws[wf])/len(w["rows"])
 need(abs(w_gain-w["candidate_gain"])<1e-12,"W_GAIN_RECOUNT")
 budget=work[wc]<=work[wf]*1.2 and deep<=.1*len(w["rows"])
 yw="learned_intervention_invariant";yb=y["strongest_fair_control"]
 ya="learned_unpaired_ablation"
 need(yb=="fitted_Gaussian_latent","Y_FROZEN_CONTROL")
 y_gain=(ys[yw]-ys[yb])/len(y["rows"])
 ablate=(ys[yw]-ys[ya])/len(y["rows"])
 need(abs(y_gain-y["gain_over_strongest_fair"])<1e-12 and
      abs(ablate-y["paired_intervention_ablation_gain"])<1e-12,
      "Y_GAIN_ABLATION_RECOUNT")
 mechanisms=set(r["mechanism"] for r in y["rows"])
 need(mechanisms==set(y["heldout_mechanisms"]) and len(mechanisms)>=2,
      "Y_HELDOUT_MECHANISMS")
 nondegrade=all(
   sum(r["predictions"][yw]==r["truth"] for r in y["rows"] if r["mechanism"]==m)>=
   sum(r["predictions"][yb]==r["truth"] for r in y["rows"] if r["mechanism"]==m)
   for m in mechanisms)
 need(nondegrade==y["heldout_mechanism_nondegradation"],"Y_MECHANISM_RECOUNT")
 wwin=w_gain>=.03 and budget and w["family_nondegradation"]
 ywin=y_gain>=.02 and ablate>0 and nondegrade
 return {"schema":"forge.autonomy.f45-real-train-successor.v1",
  "evidence":{"Wingless":wm,"Yggdrasil":ym},
  "decisions":[
   {"lane":"Wingless","trial_correct":ws[wc],"control_correct":ws[wf],
    "total":len(w["rows"]),"gain_pp":round(100*w_gain,5),
    "frozen_criterion_met":wwin,
    "next_hypothesis":"REPLACE_AMBIGUITY_GATE_WITH_PUBLIC_QUERY_EDGE_VALUE_OF_COMPUTATION"
       if not wwin else "REPLICATE_LOOKAHEAD_WITH_NEW_TRAIN_FAMILIES",
    "control_policy":wf,"original_authorized":False},
   {"lane":"Yggdrasil","trial_correct":ys[yw],"control_correct":ys[yb],
    "ablation_correct":ys[ya],"total":len(y["rows"]),
    "gain_pp":round(100*y_gain,5),"ablation_gain_pp":round(100*ablate,5),
    "frozen_criterion_met":ywin,
    "next_hypothesis":"ISOLATE_CAUSAL_PAIRED_INTERVENTION_BENEFIT_FROM_LEARNED_BASELINE"
       if not ywin else "REPLICATE_INDEPENDENT_INTERVENTION_TRANSFER",
    "control_policy":yb,"original_authorized":False}],
  "fresh_train_evidence_recomputed":True,"future_originals_preserved":True,
  "new_science_originals_executed":0,"worker_dispatch_authorized":False,
  "theta_promotion_authorized":False,"recursive_policy_improvement_proven":False}
def main():
 p=argparse.ArgumentParser()
 p.add_argument("--wingless",required=True)
 p.add_argument("--yggdrasil",required=True)
 p.add_argument("--out",required=True)
 a=p.parse_args()
 report=decide(a.wingless,a.yggdrasil)
 Path(a.out).write_text(json.dumps(report,sort_keys=True,separators=(",",":"))+"\n")
if __name__=="__main__":main()

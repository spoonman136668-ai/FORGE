"""F54 supplemental independent review of new, previously unincorporated TRAIN runs.

An auditable observational addition to the existing FORGE F54 record: the old
F54 evidence and two failed Y science attempts remain immutable. Does not
authorize experiment dispatch, accepted reference mutations or optimizer gains.
"""
from __future__ import annotations
import argparse, hashlib, json, math, pathlib

SOURCE = {
 "Wingless": dict(
   run=38819060318, head="d1be885e5d3bbef8f5828a3d195cb3354f755881",
   artifact=12012406590,
   name="W-F54-active-calibration-new-TRAIN-not-F3-original",
   artifact_digest="sha256:d3a984c4b2cbbc34a79e623bdabc7a2f5ed0498390b862765fc419e2279707d0",
   result_sha="dd007fc92fd24081ca66e75d82c233b2d8c4375a2f799aee6eb5b662b5a0ac43",
   audit_sha="ac944795fbe77f8afe56fa15c412ddb3fa8ac4af980353e763ea4d9ce348eef5"),
 "Yggdrasil": dict(
   run=38820489117, head="4ae4066bfbdb7ee5fe1f85abe840cf61f280269d",
   artifact=12013360275,
   name="Y-F54B-new-cohort-corrected-witness-TRAIN-not-F3",
   artifact_digest="sha256:17c84623f3c61226aca71fb9ce85c9379544751ab905c1d186662de2092ede69",
   result_sha="80ecc71dd6c631f2091ef63290f34471efb4f217764d7e2b29599cbc089ea43d",
   audit_sha="7870f4c92731bdf9d6cda491794fc76d2a2b73d5fe811db0e84fbc38bc1d473e")
}
class Blocked(ValueError): pass
def check(v, why):
 if not v: raise Blocked("F54_SUPPLEMENT_"+why)
def digest(b): return hashlib.sha256(b).hexdigest()
def unique(pairs):
 d={}
 for k,v in pairs:
  check(k not in d,"DUPLICATE_JSON_KEY");d[k]=v
 return d
def load(path,lane):
 p=pathlib.Path(path);s=SOURCE[lane]
 raw=(p/"result.json").read_bytes()
 audit=(p/"audit.txt").read_bytes()
 check(0<len(raw)<3_000_000 and digest(raw)==s["result_sha"],"RAW_CONTENT_"+lane)
 check(digest(audit)==s["audit_sha"] and
       (lane[0]+"_F54_INDEPENDENT_RECOUNT_PASS").encode() in audit,"SOURCE_AUDIT_"+lane)
 check((p/"SOURCE_SHA").read_text().strip()==s["head"],"SOURCE_ID_"+lane)
 manifest={}
 for line in (p/"manifest.sha256").read_text().splitlines():
  parts=line.split()
  check(len(parts)==2 and parts[1] not in manifest,"DUPLICATE_MANIFEST_"+lane)
  manifest[parts[1]]=parts[0]
 check(manifest=={"result.json":digest(raw),"audit.txt":digest(audit)},
       "MANIFEST_DRIFT_"+lane)
 d=json.loads(raw,object_pairs_hook=unique)
 check(d.get("original_executed") is False
   and d.get("accepted_ref_mutation") is False and d.get("paid_api_calls")==0,
   "PROTECTED_FIRST_USE_"+lane)
 return d
def count_scores(d,answers):
 scores=d["scores"];rows=d["rows"]
 check(set(scores)==set(rows[0][answers]),"ARM_IDENTITY")
 counts={}
 for arm in scores:
  n=sum(r[answers][arm]==r["truth"] if answers=="predictions"
        else r[answers][arm] for r in rows)
  check(scores[arm]["correct"]==n and scores[arm]["total"]==len(rows) and
    math.isclose(scores[arm]["accuracy"],n/len(rows),abs_tol=1e-12),"ROW_RECOUNT_"+arm)
  counts[arm]=n
 return counts
def wingless(d):
 check(d.get("schema")=="wingless.f54.active-calibration-identifiability.trainonly.v1"
   and d.get("stage")=="PUBLIC_ONCE_PAID_CALIBRATION_TRAIN_ONLY_NOT_ORIGINAL"
   and d.get("source_independent_F3") is False
   and d.get("fit_seeds")==[601000,601008]
   and d.get("diagnostic_seeds")==[601100,601116]
   and d.get("original_seeds_NOT_RESERVED")==[602000,602016]
   and d.get("cases")==128 and len(d["rows"])==128
   and d.get("private_source_law_not_selector_input") is True,"W_FROZEN_SOURCE")
 rows=d["rows"];scores=d["scores"]
 candidate="public_information_gain_purchase"
 fair=("public_no_purchase","public_fixed_context_purchase","public_target_nearest_purchase")
 check(set(scores)==set((candidate,*fair,"private_sign_oracle_UNFAIR")),"W_FAIR_CONTROLS")
 seen=set()
 for row in rows:
  k=(row["seed"],row["family"],row["sample"])
  check(k not in seen and 601100<=k[0]<601116 and k[1] in (1204,1205,1206,1207)
     and k[2] in (0,1),"W_COHORT_COLLISION")
  seen.add(k)
  check(len(row["initial_anchors"])==3 and len(row["target"])==3 and
     row["observed_contexts"][candidate] is not None and
     row["observed_contexts"]["public_no_purchase"] is None and
     row["predictions"]["private_sign_oracle_UNFAIR"]==row["truth"],"W_OBSERVATION")
  check(set(row["predictions"])==set(scores),"W_ROW_ARMS")
 counts=count_scores(d,"predictions")
 by={}
 for f in (1204,1205,1206,1207):
  group=[r for r in rows if r["family"]==f]
  check(len(group)==32,"W_FAMILY_N")
  by[str(f)]={a:sum(r["predictions"][a]==r["truth"] for r in group) for a in scores}
 check(by==d["by_family"],"W_FAMILY_RECOUNT")
 winner=max(fair,key=lambda a:counts[a])
 gain=(counts[candidate]-counts[winner])/128
 stable=all(by[str(f)][candidate]>=max(by[str(f)][a] for a in fair)
        for f in (1204,1205,1206,1207))
 qualified=gain>=.05 and stable
 check(winner==d["strongest_fair_control"] and
   math.isclose(gain,d["candidate_gain"],abs_tol=1e-12) and
   stable==d["per_family_nondegradation"] and
   qualified==d["frozen_gate_met"] and
   counts[candidate]==94 and counts[winner]==97 and not qualified,
   "W_FROZEN_NEGATIVE_DRIFT")
 return dict(lane="Wingless",cases=128,candidate_correct=94,
   strongest_fair=winner,fair_correct=97,gain_pp=round(100*gain,5),
   frozen_criterion_met=False,disposition="VALID_TRAIN_ONLY_NEGATIVE",
   next_hypothesis="TEST_PUBLIC_CALIBRATION_INFORMATION_VALUE_VS_NO_PURCHASE_ON_NEW_SOURCES",
   successor_dispatched=False)
def decode(records,q):
 seq=tuple(tuple(x) for x in q["chain"])
 reached={(q["start"],0)}
 for _ in seq:
  updated=set()
  for node,i in reached:
   for r in records:
    forward=(r["from_node"],tuple(tuple(x) for x in r["steps"]),r["to_node"])
    inverse=(r["to_node"],tuple((role,-direction) for role,direction in
                               reversed(r["steps"])),r["from_node"])
    for start,steps,dest in (forward,inverse):
     if start==node and seq[i:i+len(steps)]==steps:updated.add((dest,i+len(steps)))
  reached|=updated
 return int((q["answer"],len(seq)) in reached)
def yggdrasil(d):
 check(d.get("schema")=="yggdrasil.f54b.query-blind-multihop-composition.trainonly.v1"
   and d.get("stage")=="FRESH_EQUAL_PAYLOAD_TRAIN_ONLY_NO_ORIGINAL"
   and d.get("independent_F3") is False
   and d.get("fit_seeds")==[621000,621008]
   and d.get("diagnostic_seeds")==[621100,621116]
   and d.get("original_seeds_NOT_RESERVED")==[622000,622016]
   and d.get("cases")==64 and len(d["rows"])==64
   and d.get("total_native_576B_residency_qualified") is False
   and d.get("serialized_payload_bytes_per_record")==12 and
   d.get("serialized_payload_budget_bytes")==144 and
   d.get("future_question_hidden_during_ingestion") is True,"Y_FROZEN_SOURCE")
 arms=("fit_public_two_link_composition","fixed_public_two_link_composition",
       "fixed_public_three_link_composition","public_connected_component_raw",
       "public_degree_raw","FIFO_raw","public_hash_raw",
       "private_future_question_oracle_UNFAIR")
 check(set(d["scores"])==set(arms),"Y_REGISTERED_CONTROLS")
 candidate=arms[0];fair=arms[1:-1];seen=set()
 for r in d["rows"]:
  key=(r["seed"],r["family"])
  check(key not in seen and 621100<=key[0]<621116 and
    key[1] in (1244,1245,1246,1247),"Y_COHORT_IDENTITY")
  seen.add(key)
  events=r["public_events"];q=r["question"]
  check(len(events)==64 and len(q["chain"])==4 and
      set(r["results"])==set(arms) and
      set(r["retained_records"])==set(arms[:-1]),"Y_EVENT_ARMS")
  for arm,records in r["retained_records"].items():
   check(len(records)<=12,"Y_PAYLOAD_CAP")
   for record in records:
    idx=record["witness_indices"];steps=record["steps"]
    check(record["serialized_payload_bytes"]==12 and
       len(steps)==len(idx) and len(set(idx))==len(idx) and
       all(type(i)==int and 0<=i<64 for i in idx),"Y_WITNESS")
    node=record["from_node"]
    for (role,d),i in zip(steps,idx):
     edge=events[i]
     check(role==edge[1] and (edge[0] if d==1 else edge[2])==node,"Y_EVENT_ORDER")
     node=edge[2] if d==1 else edge[0]
    check(node==record["to_node"],"Y_DECODE")
   check(decode(records,q)==r["results"][arm],"Y_FUTURE_TASK_RECONSTRUCTION")
  check(r["results"][arms[-1]]==1,"Y_ORACLE")
 counts={a:sum(r["results"][a] for r in d["rows"]) for a in arms}
 for a in arms:
  check(d["scores"][a]["correct"]==counts[a] and
   d["scores"][a]["total"]==64,"Y_SCORE_RECOUNT")
 by={}
 for f in (1244,1245,1246,1247):
  subset=[r for r in d["rows"] if r["family"]==f]
  check(len(subset)==16,"Y_FAMILY_COUNT")
  by[str(f)]={a:sum(r["results"][a] for r in subset) for a in arms}
 check(by==d["by_family"],"Y_FAMILY_RECOUNT")
 winner=max(fair,key=lambda a:counts[a])
 gain=(counts[candidate]-counts[winner])/64
 stable=all(by[str(f)][candidate]>=max(by[str(f)][a] for a in fair)
        for f in (1244,1245,1246,1247))
 qualified=gain>=.05 and stable
 check(winner==d["strongest_fair_control"] and
   math.isclose(gain,d["candidate_gain"],abs_tol=1e-12) and
   stable==d["per_family_nondegradation"] and
   qualified==d["frozen_gate_met"] and
   counts[candidate]==0 and counts[winner]==2 and not qualified,
   "Y_FROZEN_NEGATIVE_DRIFT")
 return dict(lane="Yggdrasil",cases=64,candidate_correct=0,
   strongest_fair=winner,fair_correct=2,gain_pp=round(100*gain,5),
   frozen_criterion_met=False,disposition="VALID_TRAIN_ONLY_NEGATIVE",
   prior_failed_f54_source_status_preserved=True,
   native_576B_memory_verified=False,
   next_hypothesis="TEST_PUBLIC_RELATION_CHAIN_IDENTIFIABILITY_WITHOUT_EXHAUSTING_144_BYTE_PAYLOAD",
   successor_dispatched=False)
def review(w,y):
 d1=load(w,"Wingless");d2=load(y,"Yggdrasil")
 return dict(schema="forge.f54.new-authentic-supplemental-to-f55.v1",
   decisions=[wingless(d1),yggdrasil(d2)],provenance=SOURCE,
   new_first_use_train_records_recounted=2,
   historical_f54_negative_records_unchanged=True,
   historical_failed_same_cohort_runs_unchanged=True,
   protected_originals_executed=0,independent_f3_accepted=0,
   owner_accepted_ref_mutations=0,cloudflare_writes=0,
   recursive_dream_rsi_prospective_gain_proven=False,
   theta_evolve_live_promotion_authorized=False,
   f55_source_committed=False,f55_experiment_dispatched=False)
def main():
 ap=argparse.ArgumentParser()
 ap.add_argument("--wingless",required=True)
 ap.add_argument("--yggdrasil",required=True)
 ap.add_argument("--out",required=True)
 a=ap.parse_args()
 pathlib.Path(a.out).write_text(json.dumps(review(a.wingless,a.yggdrasil),
    sort_keys=True,separators=(",",":"))+"\n",encoding="utf-8")
if __name__=="__main__":main()

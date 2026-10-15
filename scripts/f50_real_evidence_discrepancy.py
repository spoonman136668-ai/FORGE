"""F50: independently inspect genuine archived TRAIN, including a failed source audit.

No new execution, no replay, no original or scientific promotion. F50's
unregistered Yggdrasil control remains an explicit qualification defect.
"""
import argparse,hashlib,json,math,pathlib

W={"run":38809539896,"sha":"646b9db1d48eb03150ad79f1c88b7a44354ab96f",
   "artifact":12006864741,"digest":"sha256:beae9eac93d88a784c286e4ad56c00cf44e14ffd308f768dbaddd73ee8842b97",
   "report_sha":"9168a78e8b1a2b1a7f90fda9b11677e705e2d770ad385c91a6043b8050b10863"}
Y={"run":38809714837,"sha":"ab83bd0cb2df4409f73ca9a9337e803467020477",
   "artifact":12007393564,"digest":"sha256:b7fc9da4c322876650ce09bfa08684ede8a615b074705f6e4cf7a89a81447502",
   "report_sha":"e95e9fb4d144a89c2d5b5ffa5189945cbcc77271923f39268a8b8a609b7ddae6"}
Y_PREREG_CONTROLS={"learned_retention","public_frequency_priority","FIFO_last12",
 "public_hash_reservoir","private_future_query_oracle_unfair"}
class Unsafe(ValueError):pass
def require(ok,reason):
 if not ok:raise Unsafe("F50_"+reason)
def rawjson(path,sha):
 raw=pathlib.Path(path).read_bytes()
 require(len(raw)>0 and len(raw)<=2_000_000,"REPORT_SIZE")
 require(hashlib.sha256(raw).hexdigest()==sha,"REPORT_CONTENT_DRIFT")
 def strict(pairs):
  z={}
  for k,v in pairs:
   require(k not in z,"DUPLICATE_KEY")
   z[k]=v
  return z
 return json.loads(raw,object_pairs_hook=strict)
def compose(row,sign):
 shifts={role:(y-sign*x)%7 for role,x,y in row["public"]}
 value=row["start"]
 for role,direction in row["chain"]:
  value=((sign*value+shifts[role])%7 if direction==1
         else sign*(value-shifts[role])%7)
 return value
def wingless(doc):
 require(doc["schema"]=="wingless.f50.learned-operator-binding.trainonly.v1"
  and doc["stage"]=="DISJOINT_FIT_AND_NOVEL_COMPOSITION_TRAIN_ONLY"
  and doc["diagnostic_seeds"]==[501100,501116]
  and doc["fit_seeds"]==[501000,501016]
  and doc["proposed_original_seeds_NOT_RESERVED"]==[502000,502016]
  and doc["source_independent_F3"] is False
  and doc["original_executed"] is False
  and doc["accepted_ref_mutation"] is False
  and doc["paid_api_calls"]==0,"W_ORIGINAL_OR_SOURCE")
 rows=doc["rows"];scores=doc["scores"]
 require(len(rows)==128 and doc["cases"]==128,"W_COUNT")
 controls=set(scores)
 require("learned_operator_posterior" in controls and
         "private_operator_oracle_unfair" in controls,"W_REQUIRED_ARMS")
 correct={a:0 for a in controls}
 parity=0;perfamily={}
 seen=set()
 for row in rows:
  identity=(row["seed"],row["family"],row["length"])
  require(identity not in seen and 501100<=identity[0]<501116
   and identity[1] in (804,805,806,807) and identity[2] in (3,5),"W_COHORT")
  seen.add(identity)
  require(len(row["public"])==4 and
    {v[0] for v in row["public"]}=={0,1,2,3} and
    all(x in (0,1) for x in row["context"]) and
    set(row["answers"])==controls,"W_PUBLIC_OR_ARMS")
  for arm,answer in row["answers"].items():
   correct[arm]+=int(answer==row["truth"])
   if arm!="private_operator_oracle_unfair":
    require(compose(row,row["chosen_signs"][arm])==answer,
            "W_WRONG_PUBLIC_OPERATOR_RECOMPOSITION")
  sign=-1 if row["context"][0]^row["context"][1]^row["context"][2] else 1
  parity+=int(compose(row,sign)==row["truth"])
 for arm,k in correct.items():
  require(scores[arm]["correct"]==k and scores[arm]["total"]==128
   and math.isclose(scores[arm]["accuracy"],k/128,abs_tol=1e-12),
   "W_RAW_SCORE_MISMATCH")
 for f in (804,805,806,807):
  perfamily[str(f)]={}
  sub=[r for r in rows if r["family"]==f]
  require(len(sub)==32,"W_FAMILY_COUNT")
  for arm in controls:
   n=sum(r["answers"][arm]==r["truth"] for r in sub)
   require(doc["by_family"][str(f)][arm]==n,"W_FAMILY_RECOUNT")
   perfamily[str(f)][arm]=n
 require(parity==112 and correct["learned_operator_posterior"]==112,
         "W_UNDISCLOSED_STRONGER_PUBLIC_CONTROL")
 return {"lane":"Wingless","source_run":W["run"],"source_status":"completed_success",
  "rows":128,"learned_correct":correct["learned_operator_posterior"],
  "preregistered_best_correct":max(correct[a] for a in controls
   if a not in ("learned_operator_posterior","private_operator_oracle_unfair")),
  "additional_three_bit_public_parity_correct":parity,
  "incremental_gain_over_stronger_public_control_pp":round(100*(112-parity)/128,6),
  "disposition":"TRAIN_ONLY_SOURCE_PASS_BUT_PUBLIC_PARITY_TIE_NO_NEW_GENERALIZATION",
  "scientific_original_accepted":False,
  "successor_hypothesis":"BREAK_TRIVIAL_PUBLIC_PARITY_SHORTCUT_ON_DISJOINT_ALGEBRAIC_SOURCE"}
def follow(events,held_indices,query,truth):
 kept=[events[i] for i in held_indices]
 at=query["start"]
 for role,direction in query["chain"]:
  options=[e for e in kept if e[1]==role
      and (e[0] if direction==1 else e[2])==at]
  if len(options)!=1:return 0
  at=options[0][2] if direction==1 else options[0][0]
 return int(at==truth)
def yggdrasil(doc):
 require(doc["schema"]=="yggdrasil.f50.learned-online-retention.trainonly.v1"
  and doc["stage"]=="DISJOINT_TRAIN_ONLY_MEMORY_NO_PRIMARY_ORIGINAL"
  and doc["diagnostic_seeds"]==[511100,511116]
  and doc["fit_seeds"]==[511000,511016]
  and doc["proposed_original_seeds_NOT_RESERVED"]==[512000,512016]
  and doc["source_independent_F3"] is False and
  doc["original_executed"] is False and
  doc["accepted_ref_mutation"] is False and
  doc["paid_api_calls"]==0 and
  doc["future_question_hidden_until_retention_complete"] is True
  and doc["memory_capacity_edges"]==12,"Y_ORIGINAL_OR_SOURCE")
 rows=doc["rows"];scores=doc["scores"];actual=set(scores)
 require(len(rows)==64 and doc["cases"]==64 and
    Y_PREREG_CONTROLS.issubset(actual) and
    actual-Y_PREREG_CONTROLS=={"public_tag_only"},"Y_UNREGISTERED_CONTROL_NOT_ACKNOWLEDGED")
 count={a:0 for a in actual};seen=set()
 for row in rows:
  ident=(row["seed"],row["family"])
  require(ident not in seen and 511100<=ident[0]<511116
   and ident[1] in (824,825,826,827),"Y_COHORT")
  seen.add(ident)
  require(len(row["public_events"])==64
   and len(row["future_query"]["chain"])==3
   and set(row["results"])==actual
   and set(row["retained_event_indices"])==actual-{"private_future_query_oracle_unfair"},
   "Y_PUBLIC_OR_ARMS")
  for arm,indices in row["retained_event_indices"].items():
   require(len(indices)==12 and len(set(indices))==12
    and all(type(i)==int and 0<=i<64 for i in indices),"Y_MEMORY_LIMIT")
   require(row["results"][arm]==follow(row["public_events"],indices,
       row["future_query"],row["truth_answer"]),"Y_RECOUNT")
  require(row["results"]["private_future_query_oracle_unfair"]==1,"Y_ORACLE")
  for arm in actual:count[arm]+=row["results"][arm]
 for a in actual:
  require(scores[a]["correct"]==count[a] and scores[a]["total"]==64 and
    math.isclose(scores[a]["accuracy"],count[a]/64,abs_tol=1e-12),
    "Y_TOTAL_SCORE")
  for family in (824,825,826,827):
   fam=[r for r in rows if r["family"]==family]
   require(len(fam)==16 and doc["by_family"][str(family)][a]==
      sum(r["results"][a] for r in fam),"Y_FAMILY_RECOUNT")
 fair=actual-{"learned_retention","private_future_query_oracle_unfair"}
 best=max(fair,key=lambda arm:count[arm])
 # Even though the record is fully recountable, the original qualifying CI
 # FAILED due preregistered-vs-implemented controls mismatch: never reclassify.
 require(count["learned_retention"]==26 and count[best]==10
   and doc["strongest_fair_control"]==best,"Y_ARCHIVED_COUNTS_DRIFT")
 return {"lane":"Yggdrasil","source_run":Y["run"],"source_status":"completed_failure",
  "rows":64,"learned_correct":count["learned_retention"],
  "best_reported_fair_control":best,
  "best_reported_fair_correct":count[best],
  "observed_gain_pp":round(100*(26-count[best])/64,6),
  "additional_unregistered_control":"public_tag_only",
  "recovered_raw_results_verified":True,
  "disposition":"NOT_SCIENTIFICALLY_QUALIFIED_ORIGINALLY_FAILED_CONTROL_IDENTITY_GATE",
  "new_primary_original_released":False,
  "successor_hypothesis":"REPREREGISTER_MATCHED_STRONG_PUBLIC_TAG_AND_ROLE_GRAPH_CONTROLS_BEFORE_FRESH_TRAIN"}
def run(wdir,ydir):
 w=rawjson(pathlib.Path(wdir)/"w-f50-train.json",W["report_sha"])
 y=rawjson(pathlib.Path(ydir)/"y-f50-result.json",Y["report_sha"])
 require((pathlib.Path(wdir)/"w-f50-head.txt").read_text().strip()==W["sha"],
   "W_HEAD")
 return {"schema":"forge.f50.observational-discrepancy-review.v1",
  "provenance":{"Wingless":W,"Yggdrasil":Y},
  "decisions":[wingless(w),yggdrasil(y)],
  "scientific_originals_executed":0,
  "independently_accepted_scientific_results":0,
  "qualified_research_experiments":1,
  "failed_original_qualification_experiments":1,
  "source_artifact_replayed":False,
  "fresh_f51_precode_authorized":False,
  "dream_rsi_gain_proven":False,
  "theta_promotion_authorized":False,
  "research_worker_dispatch_authorized":False}
def main():
 p=argparse.ArgumentParser()
 p.add_argument("--wingless-dir",required=True)
 p.add_argument("--yggdrasil-dir",required=True)
 p.add_argument("--out",required=True)
 a=p.parse_args()
 data=run(a.wingless_dir,a.yggdrasil_dir)
 pathlib.Path(a.out).write_text(json.dumps(data,sort_keys=True,
  separators=(",",":"))+"\n")
if __name__=="__main__":main()

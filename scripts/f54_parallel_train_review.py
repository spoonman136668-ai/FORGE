"""F54 parallel-study real-archive auditor, without source owner/control authority.

Read-only: two distinct original TRAIN-only experiments that occurred after the
previous F54 primary review. Never relabel prior negative/failed experiments or
trigger scientific work. All provenance and per-row evidence are pinned.
"""
from __future__ import annotations
import argparse, hashlib, json, math
from pathlib import Path

SOURCES={
 "Wingless":dict(
   run=38819060318,
   head="d1be885e5d3bbef8f5828a3d195cb3354f755881",
   artifact_id=12012406590,
   artifact_name="W-F54-active-calibration-new-TRAIN-not-F3-original",
   artifact_digest="sha256:d3a984c4b2cbbc34a79e623bdabc7a2f5ed0498390b862765fc419e2279707d0",
   result_hash="dd007fc92fd24081ca66e75d82c233b2d8c4375a2f799aee6eb5b662b5a0ac43"),
 "Yggdrasil":dict(
   run=38820489117,
   head="4ae4066bfbdb7ee5fe1f85abe840cf61f280269d",
   artifact_id=12013360275,
   artifact_name="Y-F54B-new-cohort-corrected-witness-TRAIN-not-F3",
   artifact_digest="sha256:17c84623f3c61226aca71fb9ce85c9379544751ab905c1d186662de2092ede69",
   result_hash="80ecc71dd6c631f2091ef63290f34471efb4f217764d7e2b29599cbc089ea43d")
}
class InvalidEvidence(ValueError): pass
def require(ok,label):
 if not ok: raise InvalidEvidence("F54_PARALLEL_"+label)
def sha(b):return hashlib.sha256(b).hexdigest()
def strict_pairs(pairs):
 x={}
 for k,v in pairs:
  require(k not in x,"DUPLICATE_JSON_KEY")
  x[k]=v
 return x
def load(root,lane):
 root=Path(root)
 raw=(root/"result.json").read_bytes()
 require(0<len(raw)<=6_000_000 and sha(raw)==SOURCES[lane]["result_hash"],
         "REPORT_CONTENT_SHA_DRIFT")
 require((root/"SOURCE_SHA").read_text().strip()==SOURCES[lane]["head"],
         "SOURCE_HEAD_DRIFT")
 lines=(root/"manifest.sha256").read_text().splitlines()
 checked={}
 for line in lines:
  parts=line.split()
  require(len(parts)==2 and parts[1] in ("result.json","audit.txt"),
          "MANIFEST_UNEXPECTED_FILE")
  require(parts[1] not in checked and sha((root/parts[1]).read_bytes())==parts[0],
          "MANIFEST_BAD_FILE_HASH")
  checked[parts[1]]=parts[0]
 require(set(checked)=={"result.json","audit.txt"},"MISSING_MANIFEST_WITNESS")
 expected="W_F54_INDEPENDENT_RECOUNT_PASS" if lane=="Wingless" else "Y_F54_INDEPENDENT_RECOUNT_PASS"
 require(expected in (root/"audit.txt").read_text(),"ORIGINAL_INDEPENDENT_AUDIT_ABSENT")
 doc=json.loads(raw,object_pairs_hook=strict_pairs)
 require(type(doc)==dict and type(doc.get("rows")) is list and type(doc.get("scores")) is dict,
         "INVALID_SCHEMA")
 return doc

W_POLICY="public_information_gain_purchase"
W_FAIR=("public_no_purchase","public_fixed_context_purchase",
        "public_target_nearest_purchase")
W_ORACLE="private_sign_oracle_UNFAIR"
def wingless(d):
 require(d.get("schema")=="wingless.f54.active-calibration-identifiability.trainonly.v1"
   and d.get("stage")=="PUBLIC_ONCE_PAID_CALIBRATION_TRAIN_ONLY_NOT_ORIGINAL"
   and d.get("fit_seeds")==[601000,601008]
   and d.get("diagnostic_seeds")==[601100,601116]
   and d.get("original_seeds_NOT_RESERVED")==[602000,602016]
   and d.get("cases")==128 and len(d["rows"])==128
   and d.get("extra_calibration_max")==1
   and d.get("public_initial_anchors")==3
   and d.get("source_independent_F3") is False
   and d.get("original_executed") is False
   and d.get("accepted_ref_mutation") is False
   and d.get("paid_api_calls")==0
   and d.get("private_source_law_not_selector_input") is True,"W_PRECODE_OR_AUTHORITY")
 arms=(W_POLICY,*W_FAIR,W_ORACLE)
 require(set(d["scores"])==set(arms),"W_FROZEN_CONTROL_IDENTITY")
 counts={a:0 for a in arms};seen=set()
 for r in d["rows"]:
  key=(r["seed"],r["family"],r["sample"])
  require(key not in seen and 601100<=key[0]<601116 and
      key[1] in (1204,1205,1206,1207) and type(key[2]) is int,
      "W_COHORT_DUPLICATE_OR_DRIFT")
  seen.add(key)
  require(len(r["initial_anchors"])==3 and len(r["target"])==3
     and set(r["predictions"])==set(arms) and
     set(r["observed_contexts"])==set(W_FAIR+(W_POLICY,)),
     "W_ORIGINAL_PUBLIC_EVIDENCE_INCOMPLETE")
  for arm,c in r["observed_contexts"].items():
   if arm=="public_no_purchase":
    require(c is None,"W_FREE_EXTRA_CALIBRATION")
   else:
    require(type(c) is list and len(c)==3 and all(b in (0,1) for b in c),
      "W_INVALID_PUBLIC_EXTRA_CONTEXT")
    require("".join(map(str,c)) in r["PUBLIC_extra_observations"],
      "W_UNVERIFIABLE_PUBLIC_EXTRA_OBSERVATION")
  require(r["predictions"][W_ORACLE]==r["truth"],"W_UNFAIR_ORACLE_INVALID")
  for a in arms:
   counts[a]+=int(r["predictions"][a]==r["truth"])
 require(len(seen)==128,"W_MISSING_DIAGNOSTICS")
 for a in arms:
  require(d["scores"][a]["correct"]==counts[a] and
    d["scores"][a]["total"]==128 and
    math.isclose(d["scores"][a]["accuracy"],counts[a]/128,abs_tol=1e-12),
    "W_RAW_SCORE_MISMATCH")
 by={}
 for fam in (1204,1205,1206,1207):
  group=[r for r in d["rows"] if r["family"]==fam]
  require(len(group)==32,"W_FAMILY_COUNT")
  by[str(fam)]={a:sum(r["predictions"][a]==r["truth"] for r in group) for a in arms}
  require(by[str(fam)]==d["by_family"][str(fam)],"W_FAMILY_SCORE")
 fair=max(W_FAIR,key=lambda a:counts[a])
 gain=(counts[W_POLICY]-counts[fair])/128
 nonreg=all(by[str(f)][W_POLICY]>=max(by[str(f)][a] for a in W_FAIR)
   for f in (1204,1205,1206,1207))
 passed=gain>=.05 and nonreg
 require(d["strongest_fair_control"]==fair
   and math.isclose(d["candidate_gain"],gain,abs_tol=1e-12)
   and d["per_family_nondegradation"]==nonreg
   and d["frozen_gate_met"]==passed,"W_DECISION_RECOUNT")
 require(counts[W_POLICY]==94 and counts[fair]==97 and not passed,"W_NEGATIVE_DRIFT")
 return dict(lane="Wingless",study="W-F54-public-active-calibration",
  candidate_correct=94,strongest_fair=fair,strongest_fair_correct=97,
  cases=128,gain_pp=round(100*gain,5),
  frozen_family_guard_passed=nonreg,scientific_disposition="TRAIN_ONLY_NEGATIVE",
  next_hypothesis="MEASURE_IDENTIFIABILITY_OF_PUBLIC_CALIBRATION_INSTEAD_OF_MORE_OBSERVATION_SELECTION",
  independent_scientific_first_use_approved=False)

Y_POLICY="fit_public_two_link_composition"
Y_FAIR=("fixed_public_two_link_composition","fixed_public_three_link_composition",
   "public_connected_component_raw","public_degree_raw","FIFO_raw","public_hash_raw")
Y_ORACLE="private_future_question_oracle_UNFAIR"
def inverse(rec):
 return rec["to_node"],tuple((role,-direction) for role,direction in reversed(rec["steps"])),rec["from_node"]
def evaluate(records,q):
 seq=tuple(tuple(v) for v in q["chain"])
 reachable={(q["start"],0)}
 for _ in range(len(seq)):
  new=set()
  for node,i in reachable:
   for record in records:
    options=((record["from_node"],tuple(tuple(t) for t in record["steps"]),record["to_node"]),inverse(record))
    for start,steps,end in options:
     if start==node and seq[i:i+len(steps)]==steps:new.add((end,i+len(steps)))
  reachable|=new
 return int((q["answer"],len(seq)) in reachable)
def yggdrasil(d):
 require(d.get("schema")=="yggdrasil.f54b.query-blind-multihop-composition.trainonly.v1"
   and d.get("stage")=="FRESH_EQUAL_PAYLOAD_TRAIN_ONLY_NO_ORIGINAL"
   and d.get("fit_seeds")==[621000,621008]
   and d.get("diagnostic_seeds")==[621100,621116]
   and d.get("original_seeds_NOT_RESERVED")==[622000,622016]
   and d.get("cases")==64 and len(d["rows"])==64
   and d.get("serialized_payload_bytes_per_record")==12
   and d.get("serialized_payload_budget_bytes")==144
   and d.get("total_native_576B_residency_qualified") is False
   and d.get("future_question_hidden_during_ingestion") is True
   and d.get("independent_F3") is False
   and d.get("original_executed") is False
   and d.get("accepted_ref_mutation") is False
   and d.get("paid_api_calls")==0,"Y_PRECODE_OR_AUTHORITY")
 arms=(Y_POLICY,*Y_FAIR,Y_ORACLE)
 require(set(d["scores"])==set(arms),"Y_FROZEN_CONTROL_IDENTITY")
 count={a:0 for a in arms};seen=set();witnessed=0
 for r in d["rows"]:
  ident=(r["seed"],r["family"])
  require(ident not in seen and 621100<=ident[0]<621116 and
          ident[1] in (1244,1245,1246,1247),"Y_COHORT_DRIFT")
  seen.add(ident)
  events=r["public_events"];q=r["question"]
  require(len(events)==64 and len(q["chain"])==4
    and set(r["results"])==set(arms)
    and set(r["retained_records"])==set(arms[:-1]),"Y_PUBLIC_EVENTS")
  for arm,records in r["retained_records"].items():
   require(len(records)<=12,"Y_MEMORY_CAPACITY")
   for rec in records:
    steps=rec["steps"];ix=rec["witness_indices"]
    limit=(1,2,3) if arm=="fixed_public_three_link_composition" else (
      (1,2) if arm in (Y_POLICY,"fixed_public_two_link_composition") else (1,))
    require(rec["serialized_payload_bytes"]==12 and len(steps) in limit
        and len(ix)==len(steps) and len(set(ix))==len(ix)
        and all(type(i) is int and 0<=i<64 for i in ix),"Y_RECEIPT_BOUND")
    pos=rec["from_node"]
    for (role,direction),i in zip(steps,ix):
     a,r,b,t=events[i]
     require(role==r and (a if direction==1 else b)==pos,
       "Y_WITNESS_DIRECTION_OR_ORDER")
     pos=b if direction==1 else a
    require(pos==rec["to_node"],"Y_WITNESS_PATH")
    witnessed+=1
   require(evaluate(records,q)==r["results"][arm],"Y_ANSWER_RECONSTRUCTION")
  require(r["results"][Y_ORACLE]==1,"Y_UNFAIR_ORACLE")
  for a in arms:count[a]+=r["results"][a]
 require(len(seen)==64,"Y_MISSING_SOURCE")
 for a in arms:
  require(d["scores"][a]["correct"]==count[a] and d["scores"][a]["total"]==64
    and math.isclose(d["scores"][a]["accuracy"],count[a]/64,abs_tol=1e-12),
    "Y_SCORE_RECOUNT")
 by={}
 for family in (1244,1245,1246,1247):
  group=[r for r in d["rows"] if r["family"]==family]
  require(len(group)==16,"Y_FAMILY_COUNT")
  by[str(family)]={a:sum(r["results"][a] for r in group) for a in arms}
  require(by[str(family)]==d["by_family"][str(family)],"Y_FAMILY_RECOUNT")
 fair=max(Y_FAIR,key=lambda a:count[a])
 gain=(count[Y_POLICY]-count[fair])/64
 nonreg=all(by[str(f)][Y_POLICY]>=max(by[str(f)][a] for a in Y_FAIR)
            for f in (1244,1245,1246,1247))
 passed=gain>=.05 and nonreg
 require(d["strongest_fair_control"]==fair and
    math.isclose(d["candidate_gain"],gain,abs_tol=1e-12)
    and d["per_family_nondegradation"]==nonreg and
    d["frozen_gate_met"]==passed,"Y_DECISION_RECOUNT")
 require(count[Y_POLICY]==0 and count[fair]==2 and witnessed==5376 and not passed,
         "Y_NEGATIVE_DRIFT")
 return dict(lane="Yggdrasil",study="Y-F54B-registered-two-hop-composition",
   candidate_correct=0,strongest_fair=fair,strongest_fair_correct=2,
   cases=64,public_witnessed_records=witnessed,gain_pp=round(100*gain,5),
   frozen_family_guard_passed=nonreg,
   scientific_disposition="TRAIN_ONLY_NEGATIVE",
   next_hypothesis="QUALIFY_WHETHER_PUBLIC_OBSERVATIONS_CAN_IDENTIFY_FUTURE_FOUR_HOP_CHAIN_UNDER_EQUAL_144_BYTE_PAYLOAD",
   independent_scientific_first_use_approved=False)
def audit(wdir,ydir):
 w=load(wdir,"Wingless");y=load(ydir,"Yggdrasil")
 return dict(
  schema="forge.f54.parallel-new-train-negative-to-f55.v1",
  read_only_observational_training_evidence=True,
  source_identity=SOURCES, decisions=[wingless(w),yggdrasil(y)],
  genuine_new_train_studies_independently_recounted=2,
  original_failed_y_f54_runs_still_failed=[38819249753,38819267489],
  prior_f54_primary_advisory_artifact=12012383183,
  independent_f3_scientific_originals_accepted=0,
  protected_primary_originals_executed=0,
  accepted_ref_mutations=0,
  new_research_worker_dispatch_authorized=False,
  future_f55_studies_owner_preregistered=False,
  dream_rsi_prospective_gain_proven=False,
  theta_policy_promotion_authorized=False)
def main():
 p=argparse.ArgumentParser()
 p.add_argument("--wingless",required=True)
 p.add_argument("--yggdrasil",required=True)
 p.add_argument("--out",required=True)
 z=p.parse_args()
 Path(z.out).write_text(json.dumps(audit(z.wingless,z.yggdrasil),sort_keys=True,separators=(",",":"))+"\n")
if __name__=="__main__":main()

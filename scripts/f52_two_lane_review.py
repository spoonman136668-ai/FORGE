"""F52: auth source + independently recount real TRAIN results into F53 advisories.

Observational/non-authorizing. No F3, accepted refs, original dispatch, or
optimizer policy improvement may be derived from these two TRAIN negatives.
"""
import argparse,hashlib,json,math
from pathlib import Path

PINS={
 "Wingless":{"run":38815134108,"head":"301ef2e5bfe5e1eff701e4cbd49c62965d6cd100",
 "artifact_id":12010237686,
 "artifact_name":"W-F52-public-law-posterior-fresh-TRAIN-NO-ORIGINAL",
 "zip_digest":"sha256:e9eadcee9237185c16fb47c9bf1a7b88258cac143b4b30122cf31799f6e733d6",
 "report_sha256":"0d2e647574af620f576e61b81ea5b5e22c4188b3a4981b21595f50268e858711"},
 "Yggdrasil":{"run":38815175032,"head":"48178ffd200371ba360b8dfb0874e1b758daa8ff",
 "artifact_id":12010975784,
 "artifact_name":"Y-F52-star-bridge-fresh-TRAIN-NO-ORIGINAL",
 "zip_digest":"sha256:7bcef435fab2b19a207f1b099a0a510e61a5982e80571f0b23be1dd13d29211f",
 "report_sha256":"2f7396f1152d976df5e87cf9a44540b9df80cad1756f9329fc34fcabbffd8acc"}
}
class Rejected(ValueError):pass
def demand(ok,why):
 if not ok:raise Rejected("F52_"+why)
def unique(pairs):
 d={}
 for k,v in pairs:
  demand(k not in d,"DUPLICATE_JSON_KEY")
  d[k]=v
 return d
def load(root,lane):
 root=Path(root);raw=(root/"result.json").read_bytes()
 demand(len(raw)>0 and len(raw)<12_000_000,"BOUNDED_SOURCE")
 demand(hashlib.sha256(raw).hexdigest()==PINS[lane]["report_sha256"],"CONTENT_SHA")
 demand((root/"SOURCE_SHA").read_text().strip()==PINS[lane]["head"],"SOURCE_IDENTITY")
 checks={}
 for line in (root/"sha256-manifest.txt").read_text().splitlines():
  hash_,filename=line.split(maxsplit=1)
  demand(filename in ("result.json","independent-audit.txt"),"UNEXPECTED_FILE")
  demand(hashlib.sha256((root/filename).read_bytes()).hexdigest()==hash_,"MANIFEST_TAMPER")
  checks[filename]=hash_
 demand(len(checks)==2 and "INDEPENDENT_RECOUNT_PASS" in
        (root/"independent-audit.txt").read_text(),"INDEPENDENT_AUDIT_ABSENT")
 return json.loads(raw,object_pairs_hook=unique)
def traverse(pub,chain,start,sign):
 shifts={role:(y-sign*x)%7 for role,x,y in pub}
 at=start
 for role,d in chain:
  at=(sign*at+shifts[role])%7 if d==1 else (sign*(at-shifts[role]))%7
 return at
def recount_w(d):
 arms=("public_bayesian_law_posterior","learned_support_attention","public_hamming_nearest",
       "public_support_majority","public_three_bit_parity","public_three_bit_majority",
       "always_shift","always_reflect","private_sign_oracle_unfair")
 cand=arms[0];fair=arms[1:-1]
 demand(d.get("schema")=="wingless.f52.public-law-model-averaging.trainonly.v1"
  and d.get("stage")=="TRAIN_ONLY_UNSEEN_CONTEXT_OPERATOR_LAWS_NOT_ORIGINAL"
  and d.get("fit_seeds")==[561000,561008] and d.get("diagnostic_seeds")==[561100,561116]
  and d.get("original_seeds_NOT_RESERVED")==[562000,562016]
  and d.get("train_examples")==64 and d.get("cases")==128
  and d.get("original_executed") is False and d.get("source_independent_F3") is False
  and d.get("paid_api_calls")==0 and d.get("accepted_ref_mutation") is False,"W_PROTECTED_SOURCE")
 demand(set(d["scores"])==set(arms) and len(d["rows"])==128,"W_SCORE_IDENTITY")
 seen=set();counts={a:0 for a in arms}
 for row in d["rows"]:
  key=(row["seed"],row["family"],row["length"])
  demand(key not in seen and 561100<=key[0]<561116
      and key[1] in (1004,1005,1006,1007) and key[2] in (3,5),"W_COHORT")
  seen.add(key)
  demand(len(row["public"])==4 and len(row["calibration"])==5
   and len(row["context"])==3 and set(row["chosen_signs"])==set(arms[:-1])
   and set(row["answers"])==set(arms),"W_PUBLIC_ACTION_IDENTITY")
  for arm,sign in row["chosen_signs"].items():
   demand(sign in (-1,1) and
    traverse(row["public"],row["chain"],row["start"],sign)==row["answers"][arm],
    "W_PUBLIC_COMPOSITION")
  demand(traverse(row["public"],row["chain"],row["start"],row["evaluator_private_sign"])
    ==row["truth"] and row["answers"]["private_sign_oracle_unfair"]==row["truth"],
    "W_EVALUATOR_TRUTH")
  for a in arms:counts[a]+=int(row["answers"][a]==row["truth"])
 for a in arms:
  demand(d["scores"][a]["correct"]==counts[a] and d["scores"][a]["total"]==128,
        "W_RAW_SCORE_RECOUNT")
 by={}
 for f in (1004,1005,1006,1007):
  subset=[r for r in d["rows"] if r["family"]==f]
  demand(len(subset)==32,"W_FAMILY_SIZE")
  by[str(f)]={a:sum(r["answers"][a]==r["truth"] for r in subset) for a in arms}
  demand(d["by_family"][str(f)]==by[str(f)],"W_FAMILY_RECOUNT")
 winner=max(fair,key=lambda a:counts[a])
 gain=(counts[cand]-counts[winner])/128
 nonreg=all(by[str(f)][cand]>=max(by[str(f)][a] for a in fair) for f in (1004,1005,1006,1007))
 qualifies=gain>=.05 and nonreg
 demand(d["strongest_fair_control"]==winner and abs(gain-d["candidate_gain"])<1e-12
   and nonreg==d["per_family_nondegradation"] and qualifies==d["frozen_gate_met"],
   "W_FROZEN_GATE_DRIFT")
 demand(counts[cand]==106 and counts[winner]==99 and
    by["1006"][cand]==25 and by["1006"]["learned_support_attention"]==29
    and not qualifies,"W_NEGATIVE_IDENTITY_DRIFT")
 return {"lane":"Wingless","cases":128,"candidate_correct":counts[cand],
  "strongest_fair":winner,"fair_correct":counts[winner],
  "gain_pp":round(100*gain,5),"per_family_guard_met":nonreg,
  "frozen_gate_met":qualifies,"disposition":"VALID_TRAIN_NEGATIVE",
  "next_hypothesis":"TEST_GROUP_ROBUST_PUBLIC_LAW_POSTERIOR_UNDER_NEW_DISJOINT_LAW_FAMILIES",
  "next_implementation_authorized":False}
def solve(events,indices,question):
 edges=[events[i] for i in indices];at=question["start"]
 for role,d in question["chain"]:
  options=[edge for edge in edges if edge[1]==role and
           (edge[0] if d==1 else edge[2])==at]
  if len(options)!=1:return None
  edge=options[0];at=edge[2] if d==1 else edge[0]
 return at
def recount_y(d):
 arms=("learned_bridge_retention","learned_topology_retention",
 "public_connected_component","public_degree_adjacency","public_tag_only",
 "FIFO_last12","public_frequency","public_hash",
 "private_future_question_oracle_unfair")
 cand=arms[0];fair=arms[1:-1]
 demand(d.get("schema")=="yggdrasil.f52.bridge-aware-neutral-tags.trainonly.v1"
  and d.get("stage")=="TRAIN_ONLY_UNSEEN_DISTRACTOR_GRAPH_TOPOLOGY_NOT_ORIGINAL"
  and d.get("fit_seeds")==[571000,571016] and d.get("diagnostic_seeds")==[571100,571116]
  and d.get("original_seeds_NOT_RESERVED")==[572000,572016]
  and d.get("events_per_stream")==64 and d.get("memory_cap_edges")==12
  and d.get("future_question_hidden_until_retention_complete") is True
  and d.get("cases")==64 and d.get("train_examples")==4096
  and d.get("original_executed") is False and d.get("source_independent_F3") is False
  and d.get("paid_api_calls")==0 and d.get("accepted_ref_mutation") is False,"Y_PROTECTED_SOURCE")
 rows=d["rows"];counts={a:0 for a in arms};seen=set()
 demand(len(rows)==64 and set(d["scores"])==set(arms),"Y_SCORE_IDENTITY")
 for row in rows:
  key=(row["seed"],row["family"])
  demand(key not in seen and 571100<=key[0]<571116 and
         key[1] in (1024,1025,1026,1027),"Y_COHORT")
  seen.add(key)
  events=row["public_events"];q=row["question"]
  demand(len(events)==64 and len(q["chain"])==4 and
    sum(e[3] for e in events)==32 and set(row["results"])==set(arms) and
    set(row["retained_indices"])==set(arms[:-1]),"Y_EVENT_EVIDENCE")
  for arm,indices in row["retained_indices"].items():
   demand(len(indices)==12 and len(set(indices))==12 and
      all(type(i) is int and 0<=i<64 for i in indices),"Y_MEMORY_CAP")
   demand(row["results"][arm]==int(solve(events,indices,q)==q["answer"]),
       "Y_RAW_RECONSTRUCTION")
  demand(row["results"][arms[-1]]==1,"Y_ORACLE_ONLY")
  for arm in arms:counts[arm]+=row["results"][arm]
 for a in arms:
  demand(d["scores"][a]["correct"]==counts[a] and d["scores"][a]["total"]==64,
       "Y_RAW_SCORE_RECOUNT")
 by={}
 for f in (1024,1025,1026,1027):
  subset=[r for r in rows if r["family"]==f]
  demand(len(subset)==16,"Y_FAMILY_SIZE")
  by[str(f)]={a:sum(r["results"][a] for r in subset) for a in arms}
  demand(d["by_family"][str(f)]==by[str(f)],"Y_FAMILY_RECOUNT")
 winner=max(fair,key=lambda a:counts[a])
 gain=(counts[cand]-counts[winner])/64
 nonreg=all(by[str(f)][cand]>=max(by[str(f)][a] for a in fair) for f in (1024,1025,1026,1027))
 qualifies=gain>=.05 and nonreg
 demand(d["strongest_fair_control"]==winner and abs(gain-d["candidate_gain"])<1e-12
  and nonreg==d["per_family_nondegradation"] and qualifies==d["frozen_gate_met"]
  and math.isclose(d["tag_core_rate"],.5,abs_tol=1e-12)
  and math.isclose(d["tag_distractor_rate"],.5,abs_tol=1e-12),
  "Y_FROZEN_GATE_DRIFT")
 demand(counts[cand]==5 and counts[winner]==8 and not qualifies,"Y_NEGATIVE_IDENTITY_DRIFT")
 return {"lane":"Yggdrasil","cases":64,"candidate_correct":counts[cand],
  "strongest_fair":winner,"fair_correct":counts[winner],
  "gain_pp":round(gain*100,5),"per_family_guard_met":nonreg,
  "frozen_gate_met":qualifies,"disposition":"VALID_TRAIN_NEGATIVE",
  "next_hypothesis":"DIAGNOSE_TOPOLOGY_GENERALIZATION_FAILURE_AND_BUDGETED_RELATION_MEMORY",
  "next_implementation_authorized":False}
def review(w,y):
 d1=load(w,"Wingless");d2=load(y,"Yggdrasil")
 return {"schema":"forge.autonomy.f52-authentic-two-train-results-to-f53.v1",
  "sources":PINS,"decisions":[recount_w(d1),recount_y(d2)],
  "genuine_new_train_experiments_reviewed":2,
  "independent_f3_originals_accepted":0,"primary_originals_executed":0,
  "owner_accepted_ref_mutations":0,"successor_preregistrations_committed":0,
  "successor_worker_dispatch_authorized":False,
  "dream_rsi_prospective_improvement_proven":False,
  "theta_evolve_promotion_authorized":False}
def main():
 p=argparse.ArgumentParser()
 p.add_argument("--wingless",required=True);p.add_argument("--yggdrasil",required=True)
 p.add_argument("--out",required=True)
 a=p.parse_args()
 Path(a.out).write_text(json.dumps(review(a.wingless,a.yggdrasil),sort_keys=True,
    separators=(",",":"))+"\n")
if __name__=="__main__":main()

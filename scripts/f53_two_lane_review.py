"""F53: auth source + independently recount real TRAIN results into F54 advisories.

Observational/non-authorizing. No F3, accepted refs, original dispatch, or
optimizer policy improvement may be derived from these two TRAIN negatives.
"""
import argparse,hashlib,json,math
from pathlib import Path

PINS={
 "Wingless":{"run":38816813059,"head":"7c0d87501ce2c051474fd1b12372fc8298c6eda2",
 "artifact_id":12010549206,
 "artifact_name":"W-F53-public-law-posterior-fresh-TRAIN-NO-ORIGINAL",
 "zip_digest":"sha256:a6e5fa836e3c94b2fff2a7328423a28edb176d33b02001b11614705693e587ec",
 "report_sha256":"90fe2d0abbfa15e3ae97494a4935226073942d73f063f4b8ddb68b659c058c61"},
 "Yggdrasil":{"run":38816998979,"head":"74ff3fa0917e23623d479b2a3311fc4aed5401d0",
 "artifact_id":12010723949,
 "artifact_name":"Y-F53-star-bridge-fresh-TRAIN-NO-ORIGINAL",
 "zip_digest":"sha256:9a99b176bf8a7b602d3e28ddfdd5e5ef41db2d5f5417e0db1c9e84254d8f3187",
 "report_sha256":"cf3414b7a4254e1d8ea417f232ec7c690f071e49aa4e46b78e71e4bdc9782ebe"}
}
class Rejected(ValueError):pass
def demand(ok,why):
 if not ok:raise Rejected("F53_"+why)
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
 arms=("fit_minimax_public_mixture","public_bayesian_law_posterior",
       "learned_support_attention","public_hamming_nearest","public_support_majority",
       "public_three_bit_parity","public_three_bit_majority","always_shift","always_reflect",
       "private_sign_oracle_unfair")
 cand=arms[0];fair=arms[1:-1]
 demand(d.get("schema")=="wingless.f53.group-minimax-public-law.trainonly.v1"
  and d.get("stage")=="TRAIN_ONLY_UNSEEN_CONTEXT_OPERATOR_LAWS_NOT_ORIGINAL"
  and d.get("fit_seeds")==[581000,581008] and d.get("diagnostic_seeds")==[581100,581116]
  and d.get("original_seeds_NOT_RESERVED")==[582000,582016]
  and d.get("train_examples")==64 and d.get("cases")==128
  and d.get("original_executed") is False and d.get("source_independent_F3") is False
  and d.get("paid_api_calls")==0 and d.get("accepted_ref_mutation") is False,"W_PROTECTED_SOURCE")
 demand(set(d["scores"])==set(arms) and len(d["rows"])==128,"W_SCORE_IDENTITY")
 seen=set();counts={a:0 for a in arms}
 for row in d["rows"]:
  key=(row["seed"],row["family"],row["length"])
  demand(key not in seen and 581100<=key[0]<581116
      and key[1] in (1104,1105,1106,1107) and key[2] in (3,5),"W_COHORT")
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
 for f in (1104,1105,1106,1107):
  subset=[r for r in d["rows"] if r["family"]==f]
  demand(len(subset)==32,"W_FAMILY_SIZE")
  by[str(f)]={a:sum(r["answers"][a]==r["truth"] for r in subset) for a in arms}
  demand(d["by_family"][str(f)]==by[str(f)],"W_FAMILY_RECOUNT")
 winner=max(fair,key=lambda a:counts[a])
 gain=(counts[cand]-counts[winner])/128
 nonreg=all(by[str(f)][cand]>=max(by[str(f)][a] for a in fair) for f in (1104,1105,1106,1107))
 qualifies=gain>=.05 and nonreg
 demand(d["strongest_fair_control"]==winner and abs(gain-d["candidate_gain"])<1e-12
   and nonreg==d["per_family_nondegradation"] and qualifies==d["frozen_gate_met"],
   "W_FROZEN_GATE_DRIFT")
 demand(counts[cand]==104 and counts[winner]==106 and
    by["1104"][cand]==28 and by["1104"]["public_bayesian_law_posterior"]==29
    and not qualifies,"W_NEGATIVE_IDENTITY_DRIFT")
 return {"lane":"Wingless","cases":128,"candidate_correct":counts[cand],
  "strongest_fair":winner,"fair_correct":counts[winner],
  "gain_pp":round(100*gain,5),"per_family_guard_met":nonreg,
  "frozen_gate_met":qualifies,"disposition":"VALID_TRAIN_NEGATIVE",
  "next_hypothesis":"TEST_IDENTIFIABILITY_OF_PUBLIC_CALIBRATION_BEFORE_FURTHER_MINIMAX_FITTING",
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
 arms=("fit_role_path_cohesion_retention","learned_bridge_retention",
 "learned_topology_retention","public_role_path_greedy","public_connected_component",
 "public_degree_adjacency","public_tag_only","FIFO_last12","public_frequency",
 "public_hash","private_future_question_oracle_unfair")
 cand=arms[0];fair=arms[1:-1]
 demand(d.get("schema")=="yggdrasil.f53.cross-role-path-memory.trainonly.v1"
  and d.get("stage")=="TRAIN_ONLY_UNSEEN_DISTRACTOR_GRAPH_TOPOLOGY_NOT_ORIGINAL"
  and d.get("fit_seeds")==[591000,591016] and d.get("diagnostic_seeds")==[591100,591116]
  and d.get("original_seeds_NOT_RESERVED")==[592000,592016]
  and d.get("events_per_stream")==64 and d.get("memory_cap_edges")==12
  and d.get("future_question_hidden_until_retention_complete") is True
  and d.get("cases")==64 and d.get("train_examples")==4096
  and d.get("original_executed") is False and d.get("source_independent_F3") is False
  and d.get("paid_api_calls")==0 and d.get("accepted_ref_mutation") is False,"Y_PROTECTED_SOURCE")
 rows=d["rows"];counts={a:0 for a in arms};seen=set()
 demand(len(rows)==64 and set(d["scores"])==set(arms),"Y_SCORE_IDENTITY")
 for row in rows:
  key=(row["seed"],row["family"])
  demand(key not in seen and 591100<=key[0]<591116 and
         key[1] in (1124,1125,1126,1127),"Y_COHORT")
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
 for f in (1124,1125,1126,1127):
  subset=[r for r in rows if r["family"]==f]
  demand(len(subset)==16,"Y_FAMILY_SIZE")
  by[str(f)]={a:sum(r["results"][a] for r in subset) for a in arms}
  demand(d["by_family"][str(f)]==by[str(f)],"Y_FAMILY_RECOUNT")
 winner=max(fair,key=lambda a:counts[a])
 gain=(counts[cand]-counts[winner])/64
 nonreg=all(by[str(f)][cand]>=max(by[str(f)][a] for a in fair) for f in (1124,1125,1126,1127))
 qualifies=gain>=.05 and nonreg
 demand(d["strongest_fair_control"]==winner and abs(gain-d["candidate_gain"])<1e-12
  and nonreg==d["per_family_nondegradation"] and qualifies==d["frozen_gate_met"]
  and math.isclose(d["tag_core_rate"],.5,abs_tol=1e-12)
  and math.isclose(d["tag_distractor_rate"],.5,abs_tol=1e-12),
  "Y_FROZEN_GATE_DRIFT")
 demand(counts[cand]==8 and counts[winner]==10 and not qualifies,"Y_NEGATIVE_IDENTITY_DRIFT")
 return {"lane":"Yggdrasil","cases":64,"candidate_correct":counts[cand],
  "strongest_fair":winner,"fair_correct":counts[winner],
  "gain_pp":round(gain*100,5),"per_family_guard_met":nonreg,
  "frozen_gate_met":qualifies,"disposition":"VALID_TRAIN_NEGATIVE",
  "next_hypothesis":"TEST_BOUNDED_CHAIN_PRESERVATION_VIA_EXPLICIT_STRUCTURAL_COMPRESSION",
  "next_implementation_authorized":False}
def review(w,y):
 d1=load(w,"Wingless");d2=load(y,"Yggdrasil")
 return {"schema":"forge.autonomy.f53-authentic-two-train-results-to-f54.v1",
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

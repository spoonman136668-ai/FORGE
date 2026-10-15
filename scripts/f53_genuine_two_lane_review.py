"""FORGE F53: independently recount two authentic new TRAIN-only negatives.

Runs solely on frozen GitHub-hosted artifacts. Verifies first-attempt source and
content identity in workflow, then independently reconstructs every candidate
and control result, including Yggdrasil path reachability from each held edge.
No experiment dispatch, original use, live Dream/Theta learning or authority.
"""
import argparse
import hashlib
import json
from pathlib import Path

class Blocked(ValueError): pass

def need(ok, reason):
    if not ok: raise Blocked("F53_"+reason)

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def unique(pairs):
    obj={}
    for key,val in pairs:
        need(key not in obj,"DUPLICATE_JSON_KEY")
        obj[key]=val
    return obj

def read_json(path,limit=4000000):
    raw=Path(path).read_bytes()
    need(0<len(raw)<=limit,"BAD_JSON_SIZE")
    return json.loads(raw,object_pairs_hook=unique)

def load(directory, spec):
    root=Path(directory)
    raw=(root/"result.json").read_bytes()
    need(0<len(raw)<=4000000 and sha(raw)==spec["report_sha256"],
         "RESULT_HASH_DRIFT")
    audit=(root/"audit.txt").read_bytes()
    need(0<len(audit)<5000 and sha(audit)==spec["auditor_sha256"],
         "AUDITOR_HASH_DRIFT")
    recorded={}
    for line in (root/"manifest.sha256").read_text().splitlines():
        parts=line.split()
        need(len(parts)==2 and parts[1] in ("result.json","audit.txt")
             and parts[1] not in recorded,"RESULT_MANIFEST_INVALID")
        recorded[parts[1]]=parts[0]
    need(recorded=={"result.json":sha(raw),"audit.txt":sha(audit)},
         "RESULT_MANIFEST_MISMATCH")
    need((root/"SOURCE_SHA").read_text().strip()==spec["head"],
         "SOURCE_HEAD_MISMATCH")
    data=json.loads(raw,object_pairs_hook=unique)
    need(data.get("schema")==spec["study_schema"],"SCHEMA_MISMATCH")
    need(data.get("source_independent_F3") is False
         and data.get("original_executed") is False
         and data.get("accepted_ref_mutation") is False
         and data.get("paid_api_calls")==0,"FALSE_SCIENTIFIC_AUTHORITY")
    need(data.get("fit_seeds")==spec["registered_fit"]
         and data.get("diagnostic_seeds")==spec["registered_diagnostic"]
         and data.get("diagnostic_families")==spec["heldout_families"]
         and data.get("original_seeds_NOT_RESERVED")==spec["future_original_not_consumed"],
         "EXPERIMENT_COHORT_DRIFT")
    return data

def compose(public,chain,start,sign):
    shifts={role:(target-sign*base)%7 for role,base,target in public}
    need(set(shifts)=={0,1,2,3} and sign in (-1,1),"W_PUBLIC_ROLE_SOURCE")
    cur=start
    for role,d in chain:
        need(role in shifts and d in (-1,1),"W_INVALID_ROLE")
        cur=(sign*cur+shifts[role])%7 if d==1 else (sign*(cur-shifts[role]))%7
    return cur

def recount_w(data,spec):
    need(data.get("stage")=="TRAIN_ONLY_UNSEEN_CONTEXT_OPERATOR_LAWS_NOT_ORIGINAL"
         and data.get("cases")==128 and len(data.get("rows",[]))==128
         and data.get("diagnostic_private_sign_never_selector_input") is True,
         "W_STAGE_OR_COUNT")
    scores=data["scores"]
    candidate="fit_minimax_public_mixture";oracle="private_sign_oracle_unfair"
    need(candidate in scores and oracle in scores and len(scores)==10,"W_ARM_COUNT")
    counts={arm:0 for arm in scores}
    families={str(f):{a:0 for a in scores} for f in spec["heldout_families"]}
    seen=set()
    for row in data["rows"]:
        key=(row["seed"],row["family"],row["length"])
        need(spec["registered_diagnostic"][0]<=row["seed"]<spec["registered_diagnostic"][1]
             and row["family"] in spec["heldout_families"]
             and row["length"] in (3,5) and key not in seen,
             "W_DUPLICATE_OR_PROTECTED_ROW")
        seen.add(key)
        need(len(row["context"])==3 and len(row["public"])==4 and
             len(row["calibration"])==5 and len(row["chain"])==row["length"]
             and set(row["answers"])==set(scores)
             and set(row["chosen_signs"])==set(scores)-{oracle},
             "W_PUBLIC_OR_CONTROL_CARDINALITY")
        truth=compose(row["public"],row["chain"],row["start"],row["evaluator_private_sign"])
        need(truth==row["truth"] and row["answers"][oracle]==truth,
             "W_EVALUATOR_TRUTH_RECOUNT")
        for arm in scores:
            if arm!=oracle:
                guess=compose(row["public"],row["chain"],row["start"],row["chosen_signs"][arm])
                need(guess==row["answers"][arm],"W_SIGN_COMPOSITION_RECOUNT")
            hit=int(row["answers"][arm]==truth)
            counts[arm]+=hit
            families[str(row["family"])][arm]+=hit
    need(len(seen)==128 and families==data["by_family"],"W_FAMILY_RECOUNT")
    return result("Wingless",data,spec,counts,families,candidate,oracle)

def solve_path(retained, question):
    at=question["start"]
    for role,direction in question["chain"]:
        need(role in (0,1,2,3) and direction in (-1,1),"Y_ROLE")
        matches=[e for e in retained if e[1]==role and
                 (e[0] if direction==1 else e[2])==at]
        if len(matches)!=1:return None
        edge=matches[0]
        at=edge[2] if direction==1 else edge[0]
    return at

def recount_y(data,spec):
    need(data.get("stage")=="TRAIN_ONLY_UNSEEN_DISTRACTOR_GRAPH_TOPOLOGY_NOT_ORIGINAL"
         and data.get("cases")==64 and len(data.get("rows",[]))==64
         and data.get("events_per_stream")==64 and
         data.get("memory_cap_edges")==12 and
         data.get("future_question_hidden_until_retention_complete") is True
         and abs(data.get("tag_core_rate")-.5)<1e-12
         and abs(data.get("tag_distractor_rate")-.5)<1e-12,
         "Y_STAGE_MEMORY_OR_TAG_BALANCE")
    scores=data["scores"]
    candidate="fit_role_path_cohesion_retention"
    oracle="private_future_question_oracle_unfair"
    need(candidate in scores and oracle in scores and
         "public_role_path_greedy" in scores and len(scores)==11,
         "Y_FROZEN_CONTROL_SET")
    counts={arm:0 for arm in scores}
    families={str(f):{a:0 for a in scores} for f in spec["heldout_families"]}
    seen=set()
    for row in data["rows"]:
        key=(row["seed"],row["family"])
        need(spec["registered_diagnostic"][0]<=row["seed"]<spec["registered_diagnostic"][1]
             and row["family"] in spec["heldout_families"] and key not in seen,
             "Y_DUPLICATE_OR_PROTECTED_ROW")
        seen.add(key)
        events=row["public_events"]
        need(len(events)==64 and sum(e[3] for e in events)==32
             and set(row["results"])==set(scores)
             and set(row["retained_indices"])==set(scores)-{oracle},
             "Y_PUBLIC_STREAM_OR_CONTROL_SET")
        question=row["question"]
        need(row["results"][oracle]==1 and len(question["chain"])==4,
             "Y_ORACLE_OR_QUERY")
        for arm in scores:
            if arm!=oracle:
                indices=row["retained_indices"][arm]
                need(len(indices)==12 and len(set(indices))==12 and
                     all(type(k) is int and 0<=k<64 for k in indices),
                     "Y_MEM_RECEIPTS")
                held=[events[i] for i in indices]
                actual=int(solve_path(held,question)==question["answer"])
                need(actual==row["results"][arm],"Y_REACHABILITY_RECOUNT")
            else:
                actual=1
            counts[arm]+=actual
            families[str(row["family"])][arm]+=actual
    need(len(seen)==64 and families==data["by_family"],"Y_FAMILY_RECOUNT")
    return result("Yggdrasil",data,spec,counts,families,candidate,oracle)

def result(lane,data,spec,counts,families,candidate,oracle):
    n=data["cases"]
    for arm,score in data["scores"].items():
        need(score["correct"]==counts[arm] and score["total"]==n
             and abs(score["accuracy"]-counts[arm]/n)<1e-12,
             "REPORTED_ACCURACY_RECOUNT")
    fair=set(counts)-{candidate,oracle}
    best=max(counts[a] for a in fair)
    strongest={a for a in fair if counts[a]==best}
    gain=(counts[candidate]-best)/n
    guard=all(families[str(f)][candidate]>=max(families[str(f)][a] for a in fair)
              for f in spec["heldout_families"])
    admitted=gain>=spec["frozen_threshold_gain"] and guard
    need(data.get("strongest_fair_control") in strongest
         and abs(data.get("candidate_gain")-gain)<1e-12
         and data.get("per_family_nondegradation")==guard
         and data.get("frozen_gate_met")==admitted
         and admitted is False
         and data.get("verdict")==("TRAIN_ONLY_UNSEEN_OPERATOR_NEGATIVE" if lane=="Wingless"
                                  else "TRAIN_ONLY_STRUCTURAL_MEMORY_NEGATIVE"),
         "FROZEN_GATE_MISCLASSIFICATION")
    need((counts[candidate],best,n)==((104,106,128) if lane=="Wingless"
                                     else (8,10,64)),"SOURCE_OUTCOME_UNEXPECTED")
    return dict(lane=lane,run_id=spec["run_id"],commit=spec["head"],
        report_sha256=spec["report_sha256"],cases=n,
        candidate_correct=counts[candidate],strongest_fair_correct=best,
        gain_pp=round(100*gain,6),family_nondegradation=guard,
        scientific_outcome="TRAIN_ONLY_NEGATIVE",
        original_science_accepted=False,
        next_hypothesis=(
            "PUBLIC_LAW_TRANSFER_UNCERTAINTY_UNDER_DISJOINT_NEW_FAMILIES_AND_REVERSE_ROLE_SHIFT"
            if lane=="Wingless" else
            "NATIVE_MULTI_HOP_RELATION_COMPOSITION_AND_CONNECTIVITY_UNDER_HARD_MEMORY_BUDGET"))

def review(root,manifest):
    need(manifest.get("schema")=="forge.f53.first-use-train-evidence-manifest.v1"
         and set(manifest.get("lanes",{}))=={"Wingless","Yggdrasil"},
         "MANIFEST_IDENTITY")
    restrictions=manifest["restrictions"]
    need(restrictions["f3_authority"] is False
         and restrictions["primary_originals_executed"]==0
         and restrictions["dream_rsi_policy_prospective_improvement_proven"] is False
         and restrictions["thetaevolve_policy_promotion_authorized"] is False
         and restrictions["new_scientific_dispatch_authorized"] is False,
         "MANIFEST_FALSE_PROMOTION")
    outcomes=[]
    for lane in ("Wingless","Yggdrasil"):
        spec=manifest["lanes"][lane]
        raw=load(Path(root)/lane,spec)
        outcomes.append(recount_w(raw,spec) if lane=="Wingless" else recount_y(raw,spec))
    return dict(schema="forge.f53.genuine-two-lane-science-feedback.v1",
        outcomes=outcomes,source_manifest=manifest["lanes"],
        independent_train_negatives_accepted_as_negative=2,
        prospective_originals_executed=0,
        scientific_acceptance_authorized=False,
        dream_rsi_prospective_policy_gain_proven=False,
        theta_evolve_policy_weight_update_authorized=False,
        f54_successor_hypotheses_advisory_only=True,
        automatic_f54_experiment_dispatch_authorized=False)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--root",required=True)
    p.add_argument("--manifest",required=True)
    p.add_argument("--out",required=True)
    a=p.parse_args()
    record=review(a.root,read_json(a.manifest,50000))
    Path(a.out).write_text(json.dumps(record,sort_keys=True,separators=(",",":"))+"\n")

if __name__=="__main__":main()

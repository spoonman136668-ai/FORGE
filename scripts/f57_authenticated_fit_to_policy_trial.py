"""Source-locked independent intake of two actual F57 first-use FIT evaluations.

This tool cannot perform, accept, or promote research-selection trials. Owner
FIT outcomes (including a task accuracy improvement) are NOT genuine policy
selection improvement; their only use here is prospective experiment design.
"""
import argparse
import hashlib
import json
from pathlib import Path

class Blocked(ValueError):pass
def need(x,msg):
    if not x:raise Blocked("F57_"+msg)
def hashed(b):return hashlib.sha256(b).hexdigest()
def pairs(items):
    d={}
    for k,v in items:
        need(k not in d,"DUPLICATE_JSON_KEY")
        d[k]=v
    return d
def read(path):
    b=Path(path).read_bytes()
    need(0<len(b)<3000000,"JSON_SIZE")
    return json.loads(b,object_pairs_hook=pairs),b
def proof(directory,pin,lane):
    root=Path(directory)
    d,raw=read(root/"result.json")
    audit,ab=read(root/"audit.json")
    need(hashed(raw)==pin["report_sha256"] and
         hashed(ab)==pin["audit_sha256"],"REPORT_OR_AUDIT_HASH_"+lane)
    need((root/"SOURCE_SHA").read_text().strip()==pin["head"],
         "SOURCE_HEAD_"+lane)
    claimed={}
    for line in (root/"manifest.sha256").read_text().splitlines():
        bits=line.split()
        need(len(bits)==2 and bits[1] not in claimed,"MALFORMED_MANIFEST")
        claimed[bits[1]]=bits[0]
    need(claimed=={"result.json":hashed(raw),"audit.json":hashed(ab)},
         "MANIFEST_DRIFT_"+lane)
    return d,audit

def wingless(d,a,p):
    need(d["schema"]=="wingless.f57.public-relational-belief.fit-only.v1"
         and d["stage"]==p["stage"]
         and d["train_fit_seeds"]==p["train"]
         and d["fit_validation_seeds"]==p["validation"]
         and d["fit_families"]==p["families"]
         and d["fit_calibration_examples"]==64
         and d["fit_validation_cases"]==p["cases"]==64
         and d["diag_unconsumed"] is True
         and d["original_unconsumed"] is True
         and d["independent_F3"] is False
         and d["physical_native_576B_unverified"] is True,
         "W_FROZEN_SOURCE_BOUNDS")
    seen=set()
    counts={arm:0 for arm in p["expected_scores"]}
    families={str(f):{arm:0 for arm in counts} for f in p["families"]}
    work={arm:0 for arm in counts}
    for row in d["rows"]:
        identity=(row["seed"],row["family"],row["length"])
        need(identity not in seen
             and p["validation"][0]<=row["seed"]<p["validation"][1]
             and row["family"] in p["families"] and row["length"] in (8,10),
             "W_DUPLICATE_OR_UNREGISTERED_ROW")
        seen.add(identity)
        need(len(row["public"])==4 and len(row["chain"])==row["length"]
             and set(row["correct"])==set(counts)==set(row["answers"])
             and set(row["abstract_work"])==set(counts)
             and 0<=row["truth"]<7,"W_PUBLIC_ROW")
        for arm in counts:
            hit=int(row["answers"][arm]==row["truth"])
            need(hit==row["correct"][arm],"W_INCORRECT_ROW_SCORE")
            counts[arm]+=hit
            families[str(row["family"])][arm]+=hit
            v=row["abstract_work"][arm]
            need(type(v) is int and v>0,"W_WORK")
            work[arm]+=v
    need(len(seen)==64 and counts==p["expected_scores"]
         and counts==a["correct"]
         and a["validation_count"]==64
         and a["frozen_controls_reconstructed"] is True
         and a["policy_improvement_proven"] is False
         and a["accepted_original"] is False,
         "W_FIT_AUDIT_RECONCILIATION")
    need(work["learned_public_belief_state"]>work["frozen_F56_posterior_beam"],
         "W_UNEQUAL_WORK_DISCLOSURE")
    need(all(families[str(f)]["learned_public_belief_state"]>=
             max(families[str(f)][arm] for arm in counts if arm!="learned_public_belief_state")
             for f in p["families"]),"W_FAMILY_SCORE_RECOUNT")
    return {"source":"authentic_Wingless_F57_FIT_ONLY","cases":64,
            "correct":counts,"total_work":work,
            "equal_compute_policy_gain_proven":False,
            "FIT_source_families":families}

def yggdrasil(d,a,p):
    need(d["schema"]=="yggdrasil.f57.new-online-component-state.fitonly.v1"
         and d["stage"]==p["stage"]
         and d["fit_seeds"]==p["train"]
         and d["fit_families"]==p["families"]
         and d["cases"]==p["cases"]==64
         and d["diag_unconsumed"] is True
         and d["original_unconsumed"] is True
         and d["native_total_576B_unverified"] is True
         and d["offline_reference_is_extra_work_noncompetitive"] is True
         and d["future_question_hidden_during_ingestion"] is True,
         "Y_FROZEN_SOURCE_BOUNDS")
    counts={arm:0 for arm in p["expected_scores"]}
    seen=set()
    for row in d["rows"]:
        key=(row["seed"],row["family"])
        need(key not in seen and p["train"][0]<=row["seed"]<p["train"][1]
             and row["family"] in p["families"],"Y_DUPLICATE_OR_UNREGISTERED_ROW")
        seen.add(key)
        need(len(row["public_events"])==72
             and sum(e[3] for e in row["public_events"])==36
             and len(row["question"]["ops"]) in (4,6,8)
             and set(row["scores"])==set(counts)
             and set(row["serialized_bytes"])==set(counts)
             and set(row["retained_records"])==set(counts),
             "Y_PUBLIC_RECORD_COUNTS")
        for arm in counts:
            score=row["scores"][arm]
            records=row["retained_records"][arm]
            need(score in (0,1) and len(records)<=12
                 and row["serialized_bytes"][arm]==len(records)*12<=144,
                 "Y_FIT_12B_BUDGET")
            for r in records:
                need(len(bytes.fromhex(r))==12,"Y_FIT_RECEIPT_SIZE")
            counts[arm]+=score
    need(len(seen)==64 and counts==p["expected_scores"]==d["correct"]
         and counts==a["scores"] and a["fit_cases"]==64
         and a["public_source_gate_frozen"] is True
         and a["online_policy_improvement_proven"] is False
         and a["heldout_diagnostic_executed"] is False
         and a["protected_original_executed"] is False,
         "Y_SCIENTIFIC_STATUS")
    return {"source":"authentic_Yggdrasil_F57_FIT_ONLY","cases":64,
            "correct":counts,"learned_online_gain_proven":False,
            "noncompetitive_full_public_offline":True}

def analyze(root,manifest):
    need(manifest["schema"]=="forge.f57.real-firstuse-FIT-to-selection-trial-prereg.v1"
         and set(manifest["FIT_studies"])=={"Wingless","Yggdrasil"},"FROZEN_MANIFEST")
    selection=manifest["independent_selection_trial"]
    need(selection["frozen_policy_identities_available"] is False
         and selection["prospective_randomized_policy_selection_run_available"] is False
         and selection["firstuse_selection_receipts_available"] is False
         and selection["independent_causal_review_available"] is False
         and selection["independently_accepted_results_available"] is False
         and selection["selection_policy_activation_authorized"] is False
         and selection["theta_weight_updates_authorized"] is False
         and selection["controller_cutover_authorized"] is False,
         "UNAUTHENTICATED_POLICY_PROMOTION")
    w=manifest["FIT_studies"]["Wingless"]
    y=manifest["FIT_studies"]["Yggdrasil"]
    x,xa=proof(Path(root)/"Wingless",w,"Wingless")
    z,za=proof(Path(root)/"Yggdrasil",y,"Yggdrasil")
    return {"schema":"forge.f57.genuine-FIT-to-Dream-Pareto-selection-plan.v1",
      "Wingless":wingless(x,xa,w),"Yggdrasil":yggdrasil(z,za,y),
      "next_gate":"REGISTER_AND_AUTHENTICATE_FROZEN_RESEARCH_SELECTION_POLICIES_WITH_EXISTING_AUTHORITY",
      "prospective_policy_trials_executed":0,
      "accepted_originals_executed":0,
      "dream_pareto_live_selection_activated":False,
      "theta_evolve_weight_updates_authorized":False,
      "promptbreeder_dgm_genenv_novelty_advisory_only":True,
      "experiment_dispatch_authorized":False}
if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--root",required=True)
    parser.add_argument("--manifest",required=True)
    parser.add_argument("--out",required=True)
    a=parser.parse_args()
    p,_=read(a.manifest)
    r=analyze(a.root,p)
    Path(a.out).write_text(json.dumps(r,sort_keys=True,separators=(",",":"))+"\n")

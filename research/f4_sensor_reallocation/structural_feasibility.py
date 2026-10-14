"""F4 prospective source-only observability proof, never execute new cohorts.

Y058 transposition changes coordinate(cell) only when cell belongs to the
swapped pair and episode is post-onset, leaving anchor cells 0 and 1 intact.
The original public sensor schedule and the trained F4 candidates are frozen.
If their late public sensors omit both swapped cells, they cannot distinguish
the swap from a steady case by those public measurements.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
from historical_train import historical_training_cases,learn_coverage,digest_model
from matched_worker import CONTROL,Y070_COMMIT,verify_comparators,validate_schedule

PROPOSAL_BLOB="0be94732e08372528f8a7abe0021048652e8f509"
TRANSPOSITION_BLOB="7b125f7df582eb965cf017ec3552bdf91c587954"
TRANSPOSITION_PATH="research/contrib/chatgpt/20261013-y058-anchor-blind/execute.py"
STATUS="UNOBSERVABLE_PROSPECTIVE_SWAPS_SOURCE_LEVEL_NO_SCIENCE"

def blob_sha(raw):
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\x00"+raw).hexdigest()

def require(ok,code):
    if not ok:raise ValueError("F4_SOURCE_FEASIBILITY_"+code)

def validate_pinned_transposition(root):
    root=Path(root).resolve(strict=True)
    def git(*args):
        return subprocess.check_output(["git","-C",str(root),*args],stderr=subprocess.DEVNULL).decode().strip()
    require(git("rev-parse","HEAD")==Y070_COMMIT and not git("status","--porcelain"),"CHECKOUT_DRIFT")
    require(git("ls-files","--error-unmatch",TRANSPOSITION_PATH)==TRANSPOSITION_PATH,"SOURCE_PATH")
    require(blob_sha((root/TRANSPOSITION_PATH).read_bytes())==TRANSPOSITION_BLOB,"TRANSPOSITION_DRIFT")

def load_proposal():
    raw=Path(__file__).with_name("prospective_protocol.json").read_bytes()
    require(blob_sha(raw)==PROPOSAL_BLOB,"PROPOSAL_DRIFT")
    p=json.loads(raw)
    require(p["status"]=="PROPOSED_NOT_FROZEN_NO_SCIENTIFIC_AUTHORITY","AUTHORITY")
    require(p["source_requirements"]["implementation_source_sha"]=="UNRESOLVED_REQUIRED_BEFORE_FREEZE","FREEZE")
    require(p["prereg_parent_evidence"]["y070_immutable_source_commit"]==Y070_COMMIT,"PARENT")
    require(p["proposed_conditions"]["pairs_evaluator_only"] is True,"PAIR_VISIBILITY")
    require(p["proposed_conditions"]["train_label_access"]=="development_training_only_never_at_inference","ORACLE")
    return p

def compare_pair(schedule,pair):
    schedule=validate_schedule(schedule)
    require(type(pair) in (tuple,list) and len(pair)==2 and
            all(type(x) is int and 2<=x<=15 for x in pair) and pair[0]!=pair[1],"PAIR_SHAPE")
    observed=set(c for sample in schedule[3:] for c in sample)
    hits=sorted(observed.intersection(pair))
    return {
        "late_public_sensors":sorted(observed),
        "swap_cells_evaluator_only":list(pair),
        "observed_swapped_cells":hits,
        "publicly_observable_by_schedule":bool(hits),
    }

def review():
    # Compute the model from historical F3 training labels before reading
    # F4 evaluator-only prospective pair identities.
    model=learn_coverage(historical_training_cases())
    digest=digest_model(model)
    schedules=verify_comparators()
    require(model["set_schedule"]==[list(x) for x in schedules["F4-SET"]],"SET_DRIFT")
    require(model["order_control_schedule"]==[list(x) for x in schedules["F4-ORDER-CONTROL"]],"ORDER_DRIFT")
    p=load_proposal()
    pairs=p["proposed_conditions"]["prospective_novel_sealed_evaluation_pairs"]
    require(type(pairs) is list and len(pairs)==2 and
            len({tuple(pair) for pair in pairs})==2,"NOVEL_PAIRS")
    checks={}
    for pair in pairs:
        label=str(pair[0])+"_"+str(pair[1])
        checks[label]={name:compare_pair(schedule,pair) for name,schedule in schedules.items()}
    require(all(not entry["publicly_observable_by_schedule"]
                for case in checks.values() for entry in case.values()),"CONCLUSION_CHANGED")
    return {
        "schema":"forge.f4.source-only.prospective-observability.v1",
        "status":STATUS,
        "protocol_git_blob":PROPOSAL_BLOB,
        "pinned_yggdrasil_commit":Y070_COMMIT,
        "pinned_transposition_source_blob":TRANSPOSITION_BLOB,
        "historical_training_sha256":digest,
        "historically_learned_sensors":model["learned_physical_sensors"],
        "source_only_pair_checks":checks,
        "proof":"Pinned Y058 changes only swapped physical coordinate labels after onset. Neither swapped cell is sampled by any of the three post-onset public schedules. Consequently each arm has identical public measurements with and without the swap for the same seed/family, so a public-only decoder cannot distinguish the regimes.",
        "limit":"This is not a metric, heldout execution, or proof against all different sensing policies.",
        "f4_original_feasibility":"BLOCKED_AS_PROPOSED",
        "candidate_retrained_after_inspecting_novel_pair_labels":False,
        "f4_development_cohort_accesses":0,
        "f4_sealed_cohort_accesses":0,
        "scientific_originals_executed":0,
        "first_use_claims_consumed":0,
        "scientific_winner_selected":False,
        "scientific_dispatch_authorized":False
    }

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--pinned-source-root",required=True)
    ap.add_argument("--out",required=True)
    args=ap.parse_args()
    validate_pinned_transposition(args.pinned_source_root)
    report=review()
    raw=(json.dumps(report,sort_keys=True,separators=(",",":"),allow_nan=False)+"\n").encode()
    with Path(args.out).open("xb") as fd:fd.write(raw)
    print("F4_PROSPECTIVE_OBSERVABILITY=BLOCKED_SOURCE_ONLY")
    print("F4_FEASIBILITY_SHA256="+hashlib.sha256(raw).hexdigest())
    print("F4_NEW_FIRST_USE=ZERO")

if __name__=="__main__":main()

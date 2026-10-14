"""Independent no-oracle evidence-to-next-hypothesis witness."""
import argparse,hashlib,json
from pathlib import Path
from auto_successor import canonical

def require(x,why):
    if not x:raise ValueError("F11_INDEPENDENT_"+why)

def verify(proposal,source_bytes,witness_bytes):
    source=json.loads(source_bytes);witness=json.loads(witness_bytes)
    require(proposal.get("schema")=="forge.f10.automatic-negative-to-f11-design.v1"
            and proposal.get("status")=="ENGINEERING_SUCCESSOR_ONLY_FIRST_USE_BLOCKED"
            and proposal.get("parent_f10_sha256")==hashlib.sha256(source_bytes).hexdigest()
            and proposal.get("independent_f10_review_sha256")==
                hashlib.sha256(witness_bytes).hexdigest(),"PROVENANCE")
    cases=source.get("validation",[])
    require(type(cases) is list and len(cases)==96,"REPLAY_CASES")
    total=0;detect=0;steady=0
    ids=set()
    for row in cases:
        identity=(row["seed"],tuple(row["pair"]),row["regime"],
                  tuple(row["family"]),row["matching_policy"])
        require(identity not in ids and row.get("seed") in (67206,67207)
                and row.get("arm")=="F10-EXPECTED-PUBLIC-VALUE","CASE_ID")
        ids.add(identity)
        pre,post=row["pre_mismatch"],row["post_mismatch"]
        require(type(pre) is int and type(post) is int and 0<=pre<=8 and 0<=post<=8,
                "METRICS")
        total+=pre+post
        detect+=int(row["first_detection"] is not None)
        if row["regime"]=="steady":steady+=pre+post
    summary=source.get("validation_summary",{})
    require(total==summary.get("pre",0)+summary.get("post",0) and
            detect==summary.get("detections") and
            steady==summary.get("steady_errors") and
            summary==witness.get("validation_summary") and
            total==witness.get("f10_historical_mismatches"),"INDEPENDENT_TOTALS")
    control=source.get("f9_used_validation_controls",{}).get("ALWAYS_SWAP",{})
    require(control.get("cases")==96 and control.get("mismatches")==66 and
            witness.get("best_fixed_historical_mismatches")==66,
            "PARENT_FIXED_COMPARATOR")
    negative=total>=66
    choice=("Y-FORGE-F11-TASK-ALIGNED-OBSERVATION-VALUE-PROPOSAL" if negative
            else "Y-FORGE-F11-OBSERVATION-VALUE-REPLICATION-PROPOSAL")
    finding=("HISTORICAL_F10_UNCERTAINTY_VALUE_NOT_BETTER_THAN_FIXED" if negative
             else "HISTORICAL_F10_GAIN_REQUIRES_INDEPENDENT_REPLICATION")
    require(proposal.get("selected_proposal_id")==choice and
            proposal.get("finding")==finding and
            proposal.get("historical_f10_mismatches")==total and
            proposal.get("historical_best_fixed_mismatches")==66 and
            type(proposal.get("hypothesis")) is str and
            "expected" in proposal["hypothesis"] and
            proposal.get("original_f10_model_frozen_no_retuning") is True,
            "PROPOSAL_SELECTION")
    require(proposal.get("proposed_F11_source_and_sealed_cohorts")==
            "UNALLOCATED_CUSTODY_REQUIRED" and
            proposal.get("scientific_dispatch_authorized") is False and
            all(proposal.get(k)==0 for k in (
                "new_first_use_claims","new_scientific_originals",
                "new_data_accesses","paid_api_calls")),"NO_SCIENCE_AUTHORITY")
    return {"schema":"forge.f11.independent-negative-successor-review.v1",
            "status":"F11_DESIGN_PREPARED_NO_PROSPECTIVE_FIRST_USE",
            "selected_id":choice,"replayed_rows":len(ids),
            "historical_f10_total":total,"historical_best_fixed_total":66,
            "first_use_claims":0,"scientific_dispatch_authorized":False}

def main():
    p=argparse.ArgumentParser()
    for arg in ("proposal","parent","witness","out"):
        p.add_argument("--"+arg,required=True)
    a=p.parse_args()
    x=verify(json.loads(Path(a.proposal).read_bytes()),
             Path(a.parent).read_bytes(),Path(a.witness).read_bytes())
    raw=canonical(x)
    with Path(a.out).open("xb") as file:file.write(raw)
    print("F11_INDEPENDENT_SOURCE_TO_HYPOTHESIS=PASS")
    print("F11_PROPOSAL_ID="+x["selected_id"])
    print("F11_NO_FIRST_USE_ORIGINAL=PASS")
if __name__=="__main__":main()

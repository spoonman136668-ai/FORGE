"""Frozen portfolio successor selector; proposal-only and read-only.

Consumes independently qualified *historical* two-lane original evidence. It
cannot call a scientific worker, consume first use, or change authority.
"""
import argparse
import hashlib
import json
import pathlib

FROZEN_BLOB="7cfd170edabcb95de4383a3d6f2a44dd533b92d2"
LANES=("wingless","yggdrasil")
PARENTS={
    "wingless":("W-FORGE-R33-CONDITIONAL-TEMP-01","NO_CONFIRMED_TEMPERATURE_GAIN","a6c70a4d79b9a93dcaf61bc48b3b14e1232eee80"),
    "yggdrasil":("Y-FORGE-PARITY-E2-ONSET1","PARTIAL_EARLY_GAIN","8b77695f56935aad689608866d42e6b069bb8a62")
}
def fail(message):
    raise ValueError("SUCCESSOR_ADMISSION_"+message)
def load(raw):
    def unique(pairs):
        d={}
        for k,v in pairs:
            if k in d:fail("DUPLICATE_KEY")
            d[k]=v
        return d
    return json.loads(raw,object_pairs_hook=unique,parse_constant=lambda _:fail("NONFINITE"))
def digest(raw):
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\x00"+raw).hexdigest()
def verify_frozen(frozen_raw):
    if digest(frozen_raw)!=FROZEN_BLOB:fail("FROZEN_SPEC_DRIFT")
    f=load(frozen_raw)
    if f["schema"]!="forge.real-dual-lane-successor.freeze.v1":fail("SCHEMA")
    lim=f["limits"]
    if any((lim["max_total_prepared"]!=2,lim["max_original_launches"]!=0,
            lim["max_model_calls"]!=0,lim["max_paid_dollars"]!=0,
            f["scope"]["first_use_claims_consumed"]!=0,
            f["scope"]["new_originals_authorized"]!=0,
            f["scope"]["fsa_required"] is not False,
            f["scope"]["ckb_plane_mutation"] is not False,
            f["scope"]["existing_research_queues_unchanged"] is not True)):fail("BUDGET_UNSAFE")
    c=f["candidates"];ids=[x["id"] for x in c]
    if len(c)!=4 or len(set(ids))!=4 or [x["lane"] for x in c]!=["wingless","wingless","yggdrasil","yggdrasil"]:fail("CANDIDATE_ID")
    w=c[0];y=c[2]
    ws=sum(w["development_blocks"],[])+w["sealed_heldout_seeds"]
    ys=y["dev_seeds"]+y["sealed_seeds"]
    if len(ws)!=96 or len(set(ws))!=96 or len(ys)!=24 or len(set(ys))!=24:fail("COHORT_OVERLAP")
    if min(ws)<12000 or max(ws)>=12300 or min(ys)<64600 or max(ys)>=64700:fail("COHORT_BOUNDS")
    if any(p in set(range(9000,10500)) for p in ws):fail("PRIOR_WINGLESS_SEAL_REUSE")
    if any(p in set(range(61000,64000)) for p in ys):fail("PRIOR_YGG_SEAL_REUSE")
    return f
def validate_audit(audit):
    if audit.get("schema")!="forge.two-lane.real-evidence-continuity.v1" or audit.get("mode")!="READ_ONLY_VERIFIED_ARCHIVES_NOT_UNATTENDED_SCIENCE_AUTHORITY" or audit.get("both_real_lanes_verified") is not True or audit.get("new_science_dispatch_authorized") is not False or audit.get("new_originals_executed")!=0 or audit.get("originals_replayed")!=0 or audit.get("ckb_authority_changed") is not False:fail("AUDIT_NOT_ACCEPTED")
    if not isinstance(audit.get("lanes"),dict) or set(audit["lanes"])!=set(LANES):fail("AUDIT_LANES")
    for lane in LANES:
        l=audit["lanes"][lane]
        if l.get("status")!="QUALIFIED_HISTORICAL_TWO_ORIGINAL_CYCLE" or l.get("originals_replayed")!=0 or l.get("new_originals_executed")!=0 or l.get("next_science_dispatch_authorized") is not False:fail("LANE_NOT_ACCEPTED")
        originals=l.get("originals")
        if not isinstance(originals,list) or len(originals)!=2 or any(o.get("independently_validated") is not True or o.get("original_replay_allowed") is not False for o in originals):fail("ORIGINAL_REVIEW")
        parent=originals[-1]
        identity,outcome,_=PARENTS[lane]
        if parent.get("experiment_id")!=identity or parent.get("outcome")!=outcome or not isinstance(parent.get("original_sha256"),str) or len(parent["original_sha256"])!=64:fail("PARENT_OUTCOME_DRIFT")
def propose(frozen_raw,audit_raw):
    f=verify_frozen(frozen_raw)
    audit=load(audit_raw)
    validate_audit(audit)
    chosen=[]
    for lane in LANES:
        outcome=PARENTS[lane][1]
        matches=[c for c in f["candidates"] if c["lane"]==lane and c["rank_if"]==outcome]
        if len(matches)!=1:fail("AMBIGUOUS_HYPOTHESIS_SELECTION")
        c=matches[0]
        if c.get("proposal_only") is True:fail("INACTIVE_ALTERNATIVE_SELECTED")
        chosen.append(c)
    if len(chosen)!=2 or len(set(c["id"] for c in chosen))!=2:fail("CROSS_LANE_ID_CONFLICT")
    return {
        "schema":"forge.real-dual-lane.science-proposals.v1",
        "admission":"PREPARED_NOT_AUTHORIZED",
        "frozen_git_blob":FROZEN_BLOB,
        "parent_live_audit_run":f["source_evidence"]["verified_audit_run_id"],
        "audit_sha256":hashlib.sha256(audit_raw).hexdigest(),
        "lanes":{c["lane"]:{"experiment_id":c["id"],"parent_id":c["parent"],
                           "parent_reviewed_outcome":c["parent_outcome"],
                           "hypothesis":c["hypothesis"],"method":c["method"],
                           "compute_units":c["compute_units"]} for c in chosen},
        "next_originals_authorized":0,
        "first_use_claims_created":0,
        "originals_replayed":0,
        "paid_api_calls":0,
        "external_FSA_activated":False,
        "ckb_authority_changed":False
    }
def main():
    p=argparse.ArgumentParser()
    for key in ("frozen","audit","out"):p.add_argument("--"+key,required=True)
    args=p.parse_args()
    result=propose(pathlib.Path(args.frozen).read_bytes(),pathlib.Path(args.audit).read_bytes())
    path=pathlib.Path(args.out)
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open("x") as output:output.write(json.dumps(result,sort_keys=True,indent=2)+"\n")
    for lane in LANES:print("FORGE_"+lane.upper()+"_NEXT_HYPOTHESIS="+result["lanes"][lane]["experiment_id"])
    print("FROZEN_TWO_LANE_SCIENTIFIC_PROPOSALS=PASS")
    print("FUTURE_ORIGINALS_AUTHORIZED=ZERO")
if __name__=="__main__":main()

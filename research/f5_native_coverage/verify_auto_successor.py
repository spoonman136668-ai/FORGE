"""Independent negative-authorization review for the F5 automatic successor.

Does not call auto_successor.prepare or execute science. Compare the actual
source replay's raw records to the submitted proposal and independently
rederive priority, historical metrics, evidence identities, and boundaries.
"""
import argparse
import hashlib
import json
from pathlib import Path

ARMS=("F5-FIXED","F5-COVERAGE","F5-MINIMAX","F5-MEMORY")
OPTIONS=(
 ("PUBLIC_MEMORY_RECHECK_NO_GAIN","Y-FORGE-F6-UNCERTAINTY-CALIBRATION-PROPOSAL"),
 ("WORST_CASE_GEOMETRY_VS_HISTORICAL_TRADEOFF","Y-FORGE-F6-ROBUST-COVERAGE-PROPOSAL"),
 ("HISTORICAL_EVIDENCE_NOT_DECISIVE","Y-FORGE-F6-BASELINE-REPLICATION-PROPOSAL"),
)

def need(ok,code):
    if not ok:raise ValueError("F5_AUTONOMY_INDEPENDENT_"+code)

def verify(proposal,record_raw,witness_raw,geometry_raw,options_raw):
    record=json.loads(record_raw)
    witness=json.loads(witness_raw)
    options=json.loads(options_raw)
    geometry=json.loads(geometry_raw)
    need(proposal.get("schema")=="forge.f5.automatic-evidence-to-successor-proposal.v1"
         and proposal.get("disposition")=="SUCCESSOR_PREPARED_CUSTODY_BLOCKED_NO_ORIGINAL"
         and proposal.get("lane")=="Yggdrasil"
         and proposal.get("parent_status")=="HISTORICAL_REUSED_F3_ENGINEERING_ONLY"
         and proposal.get("parent_source_commit")==
         "5797a257a75fe139313e8486cd1a1ae79c44b148","SOURCE")
    expected_hashes={key:hashlib.sha256(raw).hexdigest() for key,raw in (
         ("record",record_raw),("independent_replay",witness_raw),
         ("geometry",geometry_raw),("frozen_options",options_raw))}
    need(proposal.get("evidence_sha256")==expected_hashes,"PROVENANCE")
    need(record.get("status")=="F3_USED_DATA_ONLY_NOT_PROSPECTIVE_SCIENCE"
         and record.get("scientific_authority") is False
         and witness.get("status")=="HISTORICAL_SOURCE_REPLAY_ONLY_NO_NEW_FIRST_USE"
         and witness.get("replayed_records")==768,"REPLAY")
    rows=record.get("records")
    need(type(rows) is list and len(rows)==768,"ROWS")
    scores={arm:{"cases":0,"pre":0,"post":0,"detections":0,
                 "steady_errors":0,"memory_reprobe_cases":0} for arm in ARMS}
    for row in rows:
        arm=row.get("arm")
        need(arm in ARMS,"ARM")
        target=scores[arm]
        target["cases"]+=1
        for source,target_key in (("pre_mismatch","pre"),("post_mismatch","post")):
            value=row.get(source)
            need(type(value) is int and 0<=value<=8,"COUNTS")
            target[target_key]+=value
        first=row.get("first_detection")
        need(first in (None,5,7),"DETECTION")
        target["detections"]+=int(first is not None)
        if row.get("regime")=="steady":
            target["steady_errors"]+=row["pre_mismatch"]+row["post_mismatch"]
        trace=row.get("sample_trace",{}).get("addresses")
        need(type(trace) is list and len(trace)==5 and
             all(type(s) is list and len(s)==2 for s in trace),"TRACE")
        if set(trace[3])==set(trace[4]):target["memory_reprobe_cases"]+=1
    need(all(v["cases"]==192 for v in scores.values()),"BALANCE")
    need(scores==record.get("groups")==witness.get("groups"),"GROUPS")
    g=geometry
    need(g.get("optimal",{}).get("worst_pair_exposure")==7 and
         g.get("baseline",{}).get("worst_pair_exposure")==5 and
         g.get("new_first_use_claims")==0,"GEOMETRY")
    cover=scores["F5-COVERAGE"]
    memory=scores["F5-MEMORY"]
    minimax=scores["F5-MINIMAX"]
    c_total=cover["pre"]+cover["post"]
    m_total=memory["pre"]+memory["post"]
    x_total=minimax["pre"]+minimax["post"]
    if memory["memory_reprobe_cases"]>0 and m_total>=c_total:index=0
    elif x_total>c_total:index=1
    else:index=2
    rule,identity=OPTIONS[index]
    candidates=options.get("hypotheses")
    need(type(candidates) is list and
         tuple((v.get("rule"),v.get("id")) for v in candidates)==OPTIONS,"OPTIONS")
    selected=proposal.get("selected",{})
    chosen=candidates[index]
    need(selected=={"proposal_id":identity,"hypothesis":chosen["hypothesis"],
                    "reason":chosen["reason"],"next_action":chosen["next_action"]}
         and proposal.get("selection_rule")==rule,"SELECTION")
    need(proposal.get("evidence_facts")=={
         "coverage_historical_total":c_total,
         "memory_historical_total":m_total,
         "minimax_historical_total":x_total,
         "memory_reprobe_cases":memory["memory_reprobe_cases"],
         "geometry_worst_coverage":5,"geometry_worst_minimax":7},"FACTS")
    need(proposal.get("considered_ids")==[x["id"] for x in candidates],"ARCHIVE")
    need(all(proposal.get(k)==0 for k in (
         "new_seed_allocations","new_scientific_originals","new_first_use_claims",
         "source_or_accepted_ref_changes","paid_api_calls")),"NO_FIRST_USE")
    need(proposal.get("not_a_scientific_winner") is True and
         proposal.get("unverified_first_use_ledger")=="BLOCKED" and
         proposal.get("scientific_dispatch_authorized") is False and
         proposal.get("successor_ready_for_autonomous_method_engineering") is True,
         "NO_FALSE_AUTONOMY")
    return {"schema":"forge.f5.automatic-successor-independent-review.v1",
            "status":"PROPOSAL_HONESTLY_PREPARED_NO_ORIGINAL_AUTHORITY",
            "parent_replayed_records":len(rows),
            "selected_id":identity,
            "proposal_sha256":hashlib.sha256(
                (json.dumps(proposal,sort_keys=True,separators=(",",":"))+"\n").encode()
            ).hexdigest(),
            "scientific_dispatch_authorized":False,
            "first_use_claims":0}

def main():
    parser=argparse.ArgumentParser()
    for x in ("proposal","record","witness","geometry","options","out"):
        parser.add_argument("--"+x,required=True)
    a=parser.parse_args()
    proposal=json.loads(Path(a.proposal).read_bytes())
    raws=[Path(getattr(a,k)).read_bytes() for k in
          ("record","witness","geometry","options")]
    result=verify(proposal,*raws)
    with Path(a.out).open("xb") as fd:
        fd.write((json.dumps(result,sort_keys=True,separators=(",",":"))+"\n").encode())
    print("F5_INDEPENDENT_AUTONOMOUS_SUCCESSOR_REVIEW=PASS")
    print("F5_SUCCESSOR_ORIGINAL_DISPATCH=ZERO")
if __name__=="__main__":main()

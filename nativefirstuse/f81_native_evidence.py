"""F81: FORGE-native reconciliation of real lane continuity + real FIT archives.

Content-linked, read-only and deliberately non-authorizing: GitHub metadata
about archived FIT tests and a working repo-local research runner is not an
independently accepted prospective original. No CKB dependency.
"""
import json
import pathlib
import re
import sys

HERE=pathlib.Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parents[0]/"research"/"f80"))
from f80_evidence_eligibility import PINS,evaluate

SCHEMA="forge.f81.native-live-dual-lane-evidence-review.v1"
LANES={"Wingless","Yggdrasil"}
HEX40=re.compile(r"^[a-f0-9]{40}$")

class Blocked(ValueError):pass

def need(ok,msg):
    if not ok:raise Blocked("F81_"+msg)

def assess(research,archives):
    need(type(research) is dict and research.get("schema")==
         "forge.f74.real-two-lane-native-intake.readonly.v1",
         "NATIVE_LIVE_SOURCE_SCHEMA_INVALID")
    lanes=research.get("lanes")
    need(type(lanes) is list and len(lanes)==2 and type(archives) is dict
         and set(archives)==LANES,"TWO_LANE_COMPLETENESS")
    seen=set()
    qualified=[]
    for record in lanes:
        need(type(record) is dict,"LANE_INVALID")
        lane=record.get("lane")
        need(lane in LANES and lane not in seen,"LANE_DUPLICATE_OR_UNKNOWN")
        seen.add(lane)
        need(record.get("repository")=="spoonman136668-ai/"+lane and
             type(record.get("main_sha")) is str and HEX40.fullmatch(record["main_sha"]) and
             type(record.get("active_research_head")) is str and
             HEX40.fullmatch(record["active_research_head"]) and
             type(record.get("last_continuation_run_confirmed")) is int and
             record["last_continuation_run_confirmed"]>0 and
             record.get("repo_local_research_workflow_confirmed") is True,
             "LIVE_SOURCE_IDENTITY_INCOMPLETE")
        need(record.get("full_original_seed_lease_ledger_independently_observed") is False and
             record.get("current_scientific_owner_independently_authorized") is False and
             record.get("prospective_original_firstuse_available") is False,
             "CALLER_CLAIMED_UNVERIFIED_AUTHORITY")
        try:
            evidence=evaluate(lane,PINS[lane]["run"],archives[lane]["artifacts"])
        except (ValueError,KeyError,TypeError) as exc:
            raise Blocked("F81_AUTHENTIC_ARCHIVE_IDENTITY_DRIFT") from exc
        need(evidence["accepted_original"] is False and
             evidence["prospective_policy_gain_qualified"] is False and
             evidence["optimizer_training_eligible"] is False,
             "FIT_EVIDENCE_NOT_ACCEPTED_ORIGINAL")
        qualified.append({
            "lane":lane,
            "live_research_workflow_source_sha":record["main_sha"],
            "live_research_branch_sha":record["active_research_head"],
            "archive_run":evidence["run_id"],
            "archive_digest_verified":evidence["archive_digest_verified"],
            "historical_fit_only":True,
            "independently_accepted_new_original":False
        })
    need(seen==LANES and
         research.get("private_rbackup_restoration_qualified") is False and
         research.get("cloudflare_time_travel_only_is_independent_backup") is False and
         research.get("atomic_live_original_firstuse_claim_qualified") is False and
         research.get("native_worker_execution_permit_issued") is False and
         research.get("new_protected_originals_dispatched")==0,
         "LIVE_ADMISSION_BOUNDARY_DRIFT")
    return {
        "schema":SCHEMA,
        "lane_evidence":sorted(qualified,key=lambda x:x["lane"]),
        "two_live_lanes_verified":True,
        "two_real_fit_archive_metadata_identities_verified":True,
        "fresh_independently_accepted_originals":0,
        "policy_training_qualified":False,
        "dream_rsi_pareto_promoted":False,
        "cloudflare_firstuse_permit_issued":False,
        "new_original_dispatched":False,
        "scientific_execution_authorized":False,
        "disposition":"VERIFIED_REPO_LOCAL_LANES_AND_FIT_HISTORY_NO_NEW_SCIENCE_AUTHORITY"
    }

def main(args):
    need(len(args)==3,"EXPECTED_LIVE_SOURCE_AND_TWO_ARCHIVE_FILES")
    sources=[]
    for path in args:
        file=pathlib.Path(path)
        need(file.is_file() and not file.is_symlink() and
             0<file.stat().st_size<=131072,"INPUT_UNAVAILABLE_OR_OVERSIZE")
        with file.open(encoding="utf-8") as handle:
            sources.append(json.load(handle))
    report=assess(sources[0],{"Wingless":sources[1],"Yggdrasil":sources[2]})
    print(json.dumps(report,sort_keys=True,separators=(",",":")))
    print("F81_NEW_PROSPECTIVE_SCIENCE=DENIED")
    print("F81_DREAM_PARETO_POLICY_PROMOTION=DENIED")

if __name__=="__main__":
    try:main(sys.argv[1:])
    except (Blocked,ValueError,KeyError,TypeError,OSError) as exc:
        print("F81_EVIDENCE_RECONCILIATION=BLOCKED",file=sys.stderr)
        raise SystemExit(1)

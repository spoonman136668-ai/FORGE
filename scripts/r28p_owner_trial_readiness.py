"""R28P frozen research trial eligibility: read-only, no invented custody."""
import json
import pathlib
import sys

ROOT=pathlib.Path(__file__).resolve().parents[1]
MANIFEST=ROOT/"reference/research-originals/20261015-r28p-owner-prospective-trial.json"
SCHEMA="forge.dreamrsi.r28p-prospective-owner-trial-protocol.v1"
FALSE_FIELDS=(
 "genuine_train_history_available","genuine_validation_history_available",
 "genuinely_frozen_selected_policy","externally_pinned_random_assignment",
 "third_party_source_birth_verified","genuine_once_only_first_use_verified",
 "prospective_holdout_available","original_execution_authorized",
 "original_executed","optimizer_improvement_proven",
 "optimizer_scientifically_accepted","live_optimizer_dispatch_enabled",
)

class Denied(ValueError):pass

def pairs(items):
    out={}
    for key,value in items:
        if key in out:raise Denied("DUPLICATE_FIELD")
        out[key]=value
    return out

def check(raw):
    if not isinstance(raw,bytes) or len(raw)==0 or len(raw)>32768:raise Denied("SOURCE_SIZE")
    try:
        data=json.loads(raw,object_pairs_hook=pairs)
    except (ValueError,UnicodeError) as exc:raise Denied("MALFORMED_SOURCE") from exc
    if not isinstance(data,dict) or data.get("schema")!=SCHEMA or data.get("intent")!="FROZEN_METHOD_REGISTRATION_ONLY_NO_DISPATCH_OR_CUSTODY":raise Denied("SOURCE_SCHEMA")
    if data.get("eligible_lanes")!=["Wingless","Yggdrasil"] or data.get("lane_mode")!="EACH_LANE_INDEPENDENT_ELIGIBILITY_NO_CROSS_LANE_BLOCKING":raise Denied("LANE_MUTATION")
    reg=data.get("registration_context",{})
    if reg.get("source_branch_parent")!="8b2aa4ab715a7ac2d7c6c3ed0b221ae70ba27c50" or reg.get("owner_authority")!="EXISTING_SCIENTIFIC_OWNER_ONLY" or reg.get("source_published_in_repository_is_not_independent_source_birth") is not True:raise Denied("OWNER_BOUNDARY_DRIFT")
    state=data.get("admission_state")
    if not isinstance(state,dict) or set(state)!=set(FALSE_FIELDS) or any(state[k] is not False for k in FALSE_FIELDS):raise Denied("FALSE_SCIENTIFIC_ADMISSION")
    if any(data.get(k) is not True for k in ("no_new_infrastructure","no_cloudflare_writes","no_accepted_ref_mutation","no_ktrade_or_broker_access","no_original_replay")):raise Denied("ISOLATION_DRIFT")
    c=data.get("source_evidence_context")
    if not isinstance(c,list) or len(c)!=2 or [a.get("lane") for a in c]!=["Wingless","Yggdrasil"] or any(a.get("kind")!="TRAIN_ONLY_NONCAUSAL" or a.get("may_be_admitted_as_prospective_optimizer_holdout") is not False for a in c):raise Denied("HISTORICAL_DATA_PROMOTED")
    comp=data.get("preregistered_comparison")
    if not isinstance(comp,dict) or "four" not in comp.get("initial_baselines","") or "four" not in comp.get("primary_comparison","") or "dreamrsi.SafeImprovement" not in comp.get("primary_comparison",""):raise Denied("COMPARATOR_DRIFT")
    before=data.get("mandatory_before_any_first_use")
    after=data.get("mandatory_after_first_use")
    if not isinstance(before,list) or not isinstance(after,list) or len(before)!=6 or len(after)!=4 or any(not isinstance(s,str) or not s for s in before+after):raise Denied("ORIGINAL_FIRSTUSE_GUARD_MISSING")
    return {
      "schema":"forge.dreamrsi.r28p-readiness-observation.v1",
      "protocol":"SOURCE_FROZEN_OWNER_TRIAL_NOT_YET_ELIGIBLE",
      "lane_count":2,
      "authentic_prospective_owner_histories_available":False,
      "independent_firstuse_verified":False,
      "scientific_trial_executed":False,
      "scientific_gain_established":False,
      "controller_or_cloudflare_writes":0,
      "status":"BLOCKED_MISSING_AUTHENTIC_PRETRIAL_OWNER_EVIDENCE",
    }

def main():
    try:
        report=check(MANIFEST.read_bytes())
    except (OSError,Denied,TypeError,AttributeError) as exc:
        print("R28P_SOURCE_ACCEPTANCE_BLOCKED:"+type(exc).__name__,file=sys.stderr)
        return 1
    print(json.dumps(report,sort_keys=True,separators=(",",":")))
    return 0
if __name__=="__main__":
    raise SystemExit(main())

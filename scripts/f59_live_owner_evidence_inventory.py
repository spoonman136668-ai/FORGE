"""F59 real GitHub read-only evidence inventory, not prospective science admission.

Inspects authentic recent GitHub Actions artifact metadata and the frozen
existing-owner R28P source. A name, run success, hash or this inventory
cannot establish an externally held policy, genuine predecision
randomization or independent causal approval.
"""
import argparse,hashlib,json,pathlib

class Blocked(ValueError):pass
def require(ok,reason):
    if not ok:raise Blocked("F59_"+reason)
def safe_object(items):
    d={}
    for k,v in items:
        require(k not in d,"DUPLICATE_JSON_KEY")
        d[k]=v
    return d
def read(path):
    b=pathlib.Path(path).read_bytes()
    require(0<len(b)<=10_000_000,"INPUT_SIZE")
    return json.loads(b,object_pairs_hook=safe_object),b
def classify(snapshot,prereg,artifacts,commitment):
    require(snapshot.get("schema")=="forge.optimizer.f58.frozen-prospective-selection.v1"
            and snapshot.get("parent_source_commit")==commitment["reference_source_commit"],
            "CONTROL_SNAPSHOT_NOT_FROZEN")
    require(commitment["schema"]=="forge.optimizer.f58.immutable-control-snapshot.v1"
            and commitment["first_frozen_conclusion"]=="success"
            and commitment["frozen_before_new_selection_outcomes"] is True
            and commitment["external_custody_independently_verified"] is False
            and commitment["live_prospective_selection_firstuse_executed"] is False,
            "CONTROL_COMMITMENT_DRIFT")
    lanes=snapshot["lanes"]
    require(len(lanes)==2 and [x["lane"] for x in lanes]==["Wingless","Yggdrasil"],
            "LANE_SOURCE_DRIFT")
    for lane in lanes:
        require(len(lane["controls"])==4 and len(lane["challengers"])==2,
                "REGISTERED_ARMS_CHANGED")
        require(all(len(x["policy_sha256"])==64 for x in lane["controls"]),
                "MISSING_FROZEN_IDS")
        require(all(c["externally_accepted_policy_sha256"]=="" and
                c["independent_custodian_receipt_sha256"]==""
                for c in lane["challengers"]),"UNAUTHORIZED_OWNER_ENROLLMENT")
    require(prereg["schema"]=="forge.dreamrsi.r28p-prospective-owner-trial-protocol.v1"
            and prereg["intent"]=="FROZEN_METHOD_REGISTRATION_ONLY_NO_DISPATCH_OR_CUSTODY"
            and prereg["eligible_lanes"]==["Wingless","Yggdrasil"]
            and set(prereg["admission_state"])=={
            "genuine_train_history_available","genuine_validation_history_available",
            "genuinely_frozen_selected_policy","externally_pinned_random_assignment",
            "third_party_source_birth_verified","genuine_once_only_first_use_verified",
            "prospective_holdout_available","original_execution_authorized",
            "original_executed","optimizer_improvement_proven",
            "optimizer_scientifically_accepted","live_optimizer_dispatch_enabled"}
            and all(v is False for v in prereg["admission_state"].values()),
            "OWNER_AUTHORIZATION_STATUS_CHANGED")
    require(type(artifacts.get("total_count")) is int and
            type(artifacts.get("artifacts")) is list and
            0<=len(artifacts["artifacts"])<=100,
            "ACTUAL_GITHUB_INVENTORY_REQUIRED")
    candidate=[]
    seen=set()
    for a in artifacts["artifacts"]:
        require(type(a["id"]) is int and a["id"]>0
                and type(a["name"]) is str and 0<len(a["name"])<=255
                and a["id"] not in seen,"ARTIFACT_METADATA_INVALID")
        seen.add(a["id"])
        name=a["name"].lower()
        if any(s in name for s in ("dream","pareto","owner","randomiz","selection")):
            candidate.append({"artifact_id":a["id"],"name":a["name"],
                              "qualified_as_prospective_owner_custody":False})
    return {"schema":"forge.optimizer.f59.real-github-owner-inventory.v1",
        "observed_repository":"spoonman136668-ai/FORGE",
        "github_artifact_page_limit":100,
        "github_artifacts_observed_on_page":len(artifacts["artifacts"]),
        "github_total_artifact_count_at_observation":artifacts["total_count"],
        "possible_named_evidence_on_scanned_page":sorted(candidate,key=lambda x:x["artifact_id"]),
        "source_frozen_real_control_count":8,
        "prospective_challenger_slots_unfilled":4,
        "owner_authentic_selected_policies_verified":0,
        "real_firstuse_randomized_selections_verified":0,
        "independent_causal_owner_reviews_verified":0,
        "cross_lane_controller_policy_activation":False,
        "real_policy_improvement_established":False,
        "new_science_originals_dispatched":0,
        "theta_updates_authorized":False,
        "status":"F59_WAIT_EXISTING_OWNER_AUTHENTIC_CHALLENGER_POLICY_AND_FIRSTUSE_RANDOMIZATION"}
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--controls",required=True)
    p.add_argument("--commitment",required=True)
    p.add_argument("--owner-prereg",required=True)
    p.add_argument("--github-artifacts",required=True)
    p.add_argument("--out",required=True)
    a=p.parse_args()
    snapshot,raw=read(a.controls)
    commit,_=read(a.commitment)
    require(hashlib.sha256(raw).hexdigest()==commit["frozen_controls_sha256"],
            "ORIGINAL_GITHUB_CONTROL_BYTES_MISMATCH")
    prereg,_=read(a.owner_prereg)
    arts,_=read(a.github_artifacts)
    pathlib.Path(a.out).write_text(json.dumps(classify(snapshot,prereg,arts,commit),
                                sort_keys=True,separators=(",",":"))+"\n")
if __name__=="__main__":main()

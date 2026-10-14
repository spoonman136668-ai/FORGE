"""Read-only, pinned real-science continuity audit for Wingless + Yggdrasil.

No experiment execution, dispatch, scheduling authority, or accepted ref mutation.
Each lane is assessed independently, even if its peer is missing/corrupt.
"""
import argparse
import hashlib
import importlib.util
import json
import pathlib
import sys

W_SHA="2f66a21bd32fea36909582b76e882c71a14b1bba"
Y_SHA="ef0f717de4a86dedae25c192cb9ca302f840a49c"
W_RUN=38494601555
Y_RUN=38530046134

ARTIFACTS={
    "wingless":{ 
        "w32-original":11862697801,
        "w32-review":11862714509,
        "w33-original":11862398345,
        "w33-review":11862782887,
        "w31-parent":11862425556,
    },
    "yggdrasil":{
        "y1-original":11877621056,
        "y1-review":11877463124,
        "y2-original":11877881252,
        "y2-review":11877099312,
    }
}
ARTIFACT_NAMES={
    "w32-original":"forge-r32-firstuse-original",
    "w32-review":"forge-r32-independent-review",
    "w33-original":"forge-r33-autonomous-original",
    "w33-review":"forge-r33-independent-review-and-r32",
    "w31-parent":"forge-r31-independent-review-and-r32",
    "y1-original":"forge-ygg-e1-original",
    "y1-review":"forge-ygg-e1-independent-review",
    "y2-original":"forge-ygg-e2-autonomous-original",
    "y2-review":"forge-ygg-e2-review-and-c3-proposal",
}
CLAIMS={
    "w32":("d1a6739d1b2f6a0e63fbe408c0cf916ba944db5e","W-FORGE-R32-T05-REPLICATION-01",
          "057c14cc786ae3d1a11735c8c8dddde85d339c20","b3bb82dfc6809aeefa8186be4ccec5064b9d82e2","99b5f46467ca38901d18c6d11ab26315895b8dac"),
    "w33":("561939b4525ea70a1c44ee135c370845928c7d0b","W-FORGE-R33-CONDITIONAL-TEMP-01",
          "b587bf20e5b449cabbccd88568487b07f2674b92","a6c70a4d79b9a93dcaf61bc48b3b14e1232eee80","9b7702b40308e01b86fe7dff795ceedc459fdd2d"),
    "y1":("c4414f94e9196816fc40796f36ccf9d59e820cf5","Y-FORGE-PARITY-E1-ONSET1",
          "4fba6ffe85e5f75e9a6c69c91e93a05cc0dd0e28","8b77695f56935aad689608866d42e6b069bb8a62","5794be0b0d3990a020906d40147377f44f0f9a9a"),
    "y2":("f305f0eae802ae70030db3460c10cdd848e14ce0","Y-FORGE-PARITY-E2-ONSET1",
          "4fba6ffe85e5f75e9a6c69c91e93a05cc0dd0e28","8b77695f56935aad689608866d42e6b069bb8a62","5794be0b0d3990a020906d40147377f44f0f9a9a"),
}
EXPECTED_OUTCOMES={"w32":"NO_CONFIRMED_REPLICATION_GAIN","w33":"NO_CONFIRMED_TEMPERATURE_GAIN",
                   "y1":"PARTIAL_EARLY_GAIN","y2":"PARTIAL_EARLY_GAIN"}

def reject(message):
    raise ValueError(message)

def load_json(data):
    def unique(pairs):
        d={}
        for key,value in pairs:
            if key in d:reject("DUPLICATE_FIELD")
            d[key]=value
        return d
    return json.loads(data,object_pairs_hook=unique,
        parse_constant=lambda x: reject("NONFINITE_JSON_NUMBER"))

def read(path):
    p=pathlib.Path(path)
    if not p.is_file() or not 0<p.stat().st_size<=35_000_000:reject("MISSING_OR_OVERSIZED_EVIDENCE")
    return p.read_bytes()

def git_blob(data):
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\x00"+data).hexdigest()

def module(path,expected_sha):
    source=read(path)
    if git_blob(source)!=expected_sha:reject("PINNED_REVIEWER_DRIFT")
    spec=importlib.util.spec_from_file_location("pinned_"+pathlib.Path(path).parent.name, path)
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    return mod

def claim_ok(raw,identity,source,kind):
    sha,experiment,prereg,worker,reviewer=CLAIMS[identity]
    if git_blob(raw)!=sha:reject("FIRST_USE_CLAIM_BLOB_DRIFT")
    c=load_json(raw)
    if c.get("experiment_id")!=experiment or c.get("source_commit")!=source or (
         c.get("first_use_consumed") is not True or c.get("rerun_allowed") is not False
    ):reject("FIRST_USE_NOT_CONSUMED_OR_IDENTITY_DRIFT")
    if c.get("prereg_blob")!=prereg or c.get("budget_claims",c.get("budget_limit"))!=2:
        reject("FIRST_USE_PREREG_OR_BUDGET_DRIFT")
    if kind=="wingless":
        if c.get("execute_blob")!=worker or c.get("review_blob")!=reviewer or c.get("schema")!="forge.r32-r33.first-use-consumed.v1":reject("WINGLESS_CLAIM_DRIFT")
    else:
        if c.get("worker_blob")!=worker or c.get("reviewer_blob")!=reviewer or c.get("schema")!="forge.yggdrasil.e-first-use-consumed.v1":reject("YGGDRASIL_CLAIM_DRIFT")
    if type(c.get("owner_approval_comment_id",c.get("operator_approval_comment_id"))) is not int:reject("FIRST_USE_OWNER_MISSING")
    return experiment

def original_and_review(root,original_name,review_name):
    root=pathlib.Path(root)
    o=read(root/original_name/"original.json")
    check=read(root/original_name/"original.sha256").decode("ascii").strip().split()
    if len(check)!=2 or check[1]!="original.json" or check[0]!=hashlib.sha256(o).hexdigest():
        reject("ORIGINAL_SHA256_MISMATCH")
    v=read(root/review_name/"independent-review.json")
    return o,v

def verify_metadata(root,lane):
    root=pathlib.Path(root)
    run_id=W_RUN if lane=="wingless" else Y_RUN
    meta=load_json(read(root/(lane+"-run.json")))
    if meta.get("id")!=run_id or meta.get("head_sha")!=( 
        "3c41ef3002271877fa5e4ddb3f2189ce2d541cf2" if lane=="wingless" else
        "ed312dbf4f01fea317d075a719b0d550a08d5773"
    ) or meta.get("run_attempt")!=1 or meta.get("status")!="completed":
        reject("GITHUB_ORIGINAL_RUN_IDENTITY")
    if lane=="yggdrasil" and meta.get("conclusion")!="success":reject("YGGDRASIL_RUN_FAILED")
    if lane=="wingless" and meta.get("conclusion")!="failure":reject("HISTORICAL_WINGLESS_RUN_STATUS_DRIFT")
    artifacts=load_json(read(root/(lane+"-artifacts.json")))
    records=artifacts.get("artifacts")
    if not isinstance(records,list):reject("GITHUB_ARTIFACT_LIST_MISSING")
    for slot,artifact_id in ARTIFACTS[lane].items():
        if slot=="w31-parent":
            continue  # This review belongs to the separately qualified R30/R31 run.
        chosen=[item for item in records if item.get("id")==artifact_id]
        if len(chosen)!=1 or chosen[0].get("name")!=ARTIFACT_NAMES[slot] or chosen[0].get("expired") is not False:
            reject("ARTIFACT_ID_NAME_OR_EXPIRY_DRIFT")
    if lane=="wingless":
        prior=load_json(read(root/"wingless-parent-run.json"))
        if prior.get("id")!=38492640534 or prior.get("status")!="completed" or prior.get("conclusion")!="success" or prior.get("run_attempt")!=1:
            reject("WINGLESS_R31_PARENT_RUN_UNQUALIFIED")
        parents=load_json(read(root/"wingless-parent-artifacts.json")).get("artifacts")
        if not isinstance(parents,list) or len([a for a in parents if a.get("id")==11862425556 and a.get("name")==ARTIFACT_NAMES["w31-parent"] and a.get("expired") is False])!=1:
            reject("WINGLESS_R31_PARENT_ARTIFACT_DRIFT")
    jobs=load_json(read(root/(lane+"-jobs.json"))).get("jobs")
    if not isinstance(jobs,list):reject("JOBS_MISSING")
    expected=(["r32-original","r32-independent-review","r33-automatic-original"] if lane=="wingless" else
              ["authorization","e1-original","e1-independent-review","e2-automatic-original","e2-independent-review-and-c3"])
    if any(len([z for z in jobs if z.get("name")==name and z.get("conclusion")=="success"])!=1 for name in expected):
        reject("REAL_SCIENCE_JOB_NOT_SUCCESSFUL")
    if lane=="wingless":
        review=[z for z in jobs if z.get("name")=="r33-independent-review-and-r32"]
        if len(review)!=1 or review[0].get("conclusion")!="failure":reject("HISTORICAL_ARCHIVE_STEP_DRIFT")
        recovered=load_json(read(root/"wingless-recovery-run.json"))
        if recovered.get("id")!=38494829090 or recovered.get("conclusion")!="success":
            reject("INDEPENDENT_ARCHIVE_RECOVERY_NOT_ACCEPTED")

def review_one(root,source_dir,identity,parent=None):
    kind="wingless" if identity.startswith("w") else "yggdrasil"
    source_sha=W_SHA if kind=="wingless" else Y_SHA
    claim_ok(read(pathlib.Path(root)/"claims"/(identity+".json")),identity,source_sha,kind)
    if kind=="wingless":
        subdir="r32-wingless" if identity=="w32" else "r33-wingless"
        src=pathlib.Path(source_dir)/"research"/subdir
        mod=module(src/"review.py",CLAIMS[identity][4])
        pre=read(src/"prereg.json")
        if git_blob(pre)!=CLAIMS[identity][2]:reject("FROZEN_PREREG_DRIFT")
        origin,review=original_and_review(root,identity+"-original",identity+"-review")
        recomputed=mod.verify(pre,origin,parent)
    else:
        src=pathlib.Path(source_dir)/"research"/"forge-ygg-parity-e"
        mod=module(src/"independent_review.py",CLAIMS[identity][4])
        pre=read(src/"prereg.json")
        if git_blob(pre)!=CLAIMS[identity][2]:reject("FROZEN_PREREG_DRIFT")
        origin,review=original_and_review(root,identity+"-original",identity+"-review")
        recomputed=mod.verify(pre,origin,CLAIMS[identity][1],parent)
    prior=load_json(review)
    if recomputed!=prior or recomputed.get("independently_validated") is not True or (
       recomputed.get("original_replay_allowed") is not False or
       recomputed.get("outcome")!=EXPECTED_OUTCOMES[identity]):
        reject("REVIEW_RECOMPUTE_OR_OUTCOME_MISMATCH")
    return {"experiment_id":CLAIMS[identity][1],"outcome":recomputed["outcome"],
            "original_sha256":hashlib.sha256(origin).hexdigest(),
            "independently_validated":True,"original_replay_allowed":False},review

def check_lane(root,source,lane):
    verify_metadata(root,lane)
    if lane=="wingless":
        parent=read(pathlib.Path(root)/"w31-parent"/"independent-review.json")
        first,r1=review_one(root,source,"w32",parent)
        second,_=review_one(root,source,"w33",r1)
    elif lane=="yggdrasil":
        first,r1=review_one(root,source,"y1")
        second,_=review_one(root,source,"y2",r1)
    else:reject("UNRECOGNIZED_LANE")
    return {"status":"QUALIFIED_HISTORICAL_TWO_ORIGINAL_CYCLE",
        "originals":[first,second],"originals_replayed":0,
        "new_originals_executed":0,"next_science_dispatch_authorized":False}

def audit(root,wingless_source,yggdrasil_source):
    report={"schema":"forge.two-lane.real-evidence-continuity.v1",
            "mode":"READ_ONLY_VERIFIED_ARCHIVES_NOT_UNATTENDED_SCIENCE_AUTHORITY",
            "lanes":{},"originals_replayed":0,"new_originals_executed":0,
            "new_science_dispatch_authorized":False,"ckb_authority_changed":False}
    for lane,source in (("wingless",wingless_source),("yggdrasil",yggdrasil_source)):
        try:report["lanes"][lane]=check_lane(root,source,lane)
        except Exception as exc:
            report["lanes"][lane]={"status":"QUARANTINED_NO_REPLAY",
                                  "reason":type(exc).__name__+":"+str(exc)[:150],
                                  "originals_replayed":0,"next_science_dispatch_authorized":False}
    report["both_real_lanes_verified"]=all(r["status"]=="QUALIFIED_HISTORICAL_TWO_ORIGINAL_CYCLE" for r in report["lanes"].values())
    return report

def main():
    p=argparse.ArgumentParser()
    for key in ("root","wingless_source","yggdrasil_source","out"):
        p.add_argument("--"+key.replace("_","-"),required=True)
    args=p.parse_args()
    result=audit(args.root,args.wingless_source,args.yggdrasil_source)
    path=pathlib.Path(args.out)
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(result,sort_keys=True,indent=2)+"\n")
    for lane,status in result["lanes"].items():
        print("REAL_LANE_"+lane.upper()+"="+status["status"]+(" reason="+status.get("reason","") if status["status"]=="QUARANTINED_NO_REPLAY" else ""),flush=True)
    print("LIVE_TWO_LANE_HISTORICAL_ACCEPTANCE="+("PASS" if result["both_real_lanes_verified"] else "QUARANTINED"),flush=True)
    if not result["both_real_lanes_verified"]:sys.exit(1)

if __name__=="__main__":main()

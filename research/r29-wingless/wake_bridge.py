"""One-experiment operator-clearance and CKB wake *signal* verifier.

This does NOT accept a wake run as scientific authority. Only an OWNER-authored,
exact approval for one frozen R29 identity can clear one original. It does not
create or transfer a research scheduler, authority, or production permission.
"""
import argparse
import json
from pathlib import Path

EXPERIMENT = "W-FORGE-R29-SOURCE-ROBUST-SUCCESSOR-01"
PREREG = "66d6908b1cc37a7aa819d1cc5a1c122d8c1ca444"
EXECUTE = "c8e4e5220b1d76e563611c862ed2e678be20dffd"
REVIEW = "a800b062e459026e0a9291fd3692fc5fa65ff030"
WAKE_SHA = "fab36e7c488f930505fcbaeb5f5bf04806e50c5b"
OWNER = "spoonman136668-ai"
WAKE_NAME = "Headless deterministic research loop wake v2"

def strict(data):
    def unique(pairs):
        x = {}
        for k, v in pairs:
            if k in x:
                raise ValueError("R29_DUPLICATE_JSON_FIELD")
            x[k] = v
        return x
    return json.loads(data, object_pairs_hook=unique)

def approval_text(source, wake_id):
    return ("FORGE-R29-ONE-SHOT-AUTHORIZATION\n"
            "experiment_id=" + EXPERIMENT + "\n"
            "source_commit=" + source + "\n"
            "wake_run_id=" + str(wake_id) + "\n"
            "scope=one-wingless-original-only\n"
            "authority=operator-bounded-no-fsa-cutover\n"
            "no_replay=true")

def verify(claim, launch, approval, wake, runs, source, run_id, github_sha):
    if not isinstance(source,str) or len(source)!=40 or any(c not in "0123456789abcdef" for c in source):
        raise ValueError("R29_SOURCE_INVALID")
    if type(run_id) is not int or run_id<=0:
        raise ValueError("R29_RUN_INVALID")
    if not isinstance(launch,dict) or launch!={"schema":"forge.r29.single-start.v1",
            "experiment_id":EXPERIMENT,"source_commit":source,"prereg_blob":PREREG}:
        raise ValueError("R29_LAUNCH_IDENTITY")
    if not isinstance(claim,dict):
        raise ValueError("R29_CLAIM_MISSING")
    wake_id=claim.get("wake_run_id")
    comment_id=claim.get("operator_approval_comment_id")
    if type(wake_id) is not int or wake_id<=0 or type(comment_id) is not int or comment_id<=0:
        raise ValueError("R29_APPROVAL_ID_INVALID")
    expected={"schema":"forge.r29.operator-single-original-claim.v1",
              "experiment_id":EXPERIMENT,"source_commit":source,
              "prereg_blob":PREREG,"execute_blob":EXECUTE,"review_blob":REVIEW,
              "operator_approval_comment_id":comment_id,"wake_run_id":wake_id,
              "first_use_consumed":True,"rerun_allowed":False}
    if claim!=expected:
        raise ValueError("R29_CLAIM_DRIFT")
    if not isinstance(approval,dict) or approval.get("id")!=comment_id or approval.get("body")!=approval_text(source,wake_id):
        raise ValueError("R29_OPERATOR_AUTHORIZATION_MISSING")
    owner=approval.get("user")
    if not isinstance(owner,dict) or owner.get("login")!=OWNER or approval.get("author_association")!="OWNER":
        raise ValueError("R29_APPROVER_NOT_OWNER")
    if approval.get("created_at")!=approval.get("updated_at"):
        raise ValueError("R29_EDITED_OPERATOR_APPROVAL")
    if (not isinstance(wake,dict) or wake.get("id")!=wake_id or
        wake.get("name")!=WAKE_NAME or wake.get("head_sha")!=WAKE_SHA or
        wake.get("run_attempt")!=1 or wake.get("event")!="workflow_dispatch" or
        wake.get("status")!="completed" or wake.get("conclusion")!="success"):
        raise ValueError("R29_WAKE_SIGNAL_INVALID")
    if not isinstance(runs,dict) or type(runs.get("total_count")) is not int or runs["total_count"]!=1:
        raise ValueError("R29_AMBIGUOUS_FIRST_USE_COUNT")
    rows=runs.get("workflow_runs")
    if not isinstance(rows,list) or len(rows)!=1 or rows[0].get("id")!=run_id or rows[0].get("head_sha")!=github_sha or rows[0].get("run_attempt")!=1:
        raise ValueError("R29_DUPLICATE_OR_UNIDENTIFIED_ORIGINAL")
    return {"schema":"forge.r29.single-original-clearance.v1",
            "experiment_id":EXPERIMENT,"source_commit":source,
            "wake_run_id":wake_id,"operator_approval_comment_id":comment_id,
            "original_run_id":run_id,"may_start_once":True,
            "ckb_authority_unchanged":True,"fsa_activated":False}

def main():
    p=argparse.ArgumentParser()
    for x in ("claim","launch","approval","wake","runs","source","run_id","github_sha","out"):
        p.add_argument("--"+x.replace("_","-"),required=True)
    a=p.parse_args()
    docs=[strict(Path(getattr(a,k)).read_text()) for k in ("claim","launch","approval","wake","runs")]
    result=verify(*docs,a.source,int(a.run_id),a.github_sha)
    path=Path(a.out)
    with path.open("x",encoding="utf-8") as f:
        f.write(json.dumps(result,sort_keys=True)+"\n")
    print("R29_OWNER_BOUNDED_FIRST_USE=PASS")
    print("R29_CKB_WAKE_SIGNAL=PASS")
    print("R29_FSA_CUTOVER=FALSE")
if __name__=="__main__":
    main()

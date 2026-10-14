"""Once-only two-lane source-qualified scientific launch budget. No network or dispatch."""
import argparse,hashlib,json,pathlib
IDS=("W-FORGE-R34-MARGIN-SUPPORT-01","Y-FORGE-E3-ONSET-LATENCY-01")
PREREG=("90b07ad0a95d1aeed3910f4f078f92089fc67733","c5406b30e45895af9a70c074ae1b5de5b70df1cf")
WORKER=("7e3db618c055e5228f9b07639e4555bc9250008e","6d663e691149aa1dd383977785808785ad542985")
REVIEWER=("1cc0c56919f47044d1be2a35989a89d5c8670799","ff58469ae2dd458944b44c863fd17941446fe929")
SCHEMA="forge.dual-r34-e3.first-use-consumed.v1"
def reject(code):raise ValueError("R34_E3_BUDGET_"+code)
def approval_text(source):
    return ("FORGE-R34-E3-TWO-LANE-ORIGINAL-BUDGET\n"
            "source_commit="+source+"\n"
            "experiments="+",".join(IDS)+"\n"
            "lanes=Wingless,Yggdrasil\n"
            "max_originals=2\n"
            "paid_model_calls=0\n"
            "retry=forbidden\n"
            "independent_reviews_required=true\n"
            "fsa_activated=false\n"
            "ckb_authority_unchanged=true\n")
def verify(launch,claims,approval,runs,source,run_id,head):
    if len(source)!=40 or len(head)!=40 or not isinstance(run_id,int) or run_id<=0:reject("IDENTITY")
    if launch!={"schema":"forge.dual-r34-e3.single-launch.v1","source_commit":source,
                "experiments":list(IDS),"original_budget":2}:reject("LAUNCH_DRIFT")
    if len(claims)!=2:reject("CLAIM_COUNT")
    approval_id=approval.get("id")
    if (type(approval_id) is not int or approval.get("body")!=approval_text(source)
        or approval.get("user",{}).get("login")!="spoonman136668-ai"
        or approval.get("author_association") not in ("OWNER","MEMBER")
        or approval.get("created_at")!=approval.get("updated_at")):reject("OWNER_APPROVAL")
    for i,claim in enumerate(claims):
        want={"schema":SCHEMA,"experiment_id":IDS[i],"source_commit":source,
              "prereg_blob":PREREG[i],"worker_blob":WORKER[i],
              "reviewer_blob":REVIEWER[i],"owner_approval_comment_id":approval_id,
              "budget_limit":2,"first_use_consumed":True,"rerun_allowed":False}
        if claim!=want:reject("FIRST_USE_REPLAY_OR_BLOB_DRIFT")
    matches=[r for r in runs.get("workflow_runs",[]) if r.get("id")==run_id]
    if runs.get("total_count")!=1 or len(matches)!=1 or matches[0].get("head_sha")!=head or matches[0].get("run_attempt")!=1 or matches[0].get("event")!="push":reject("DUPLICATE_OR_FOREIGN_RUN")
    return {"schema":"forge.dual-r34-e3.budget-clearance.v1","source_commit":source,
            "originals_reserved":list(IDS),"first_uses_consumed":2,
            "reruns_allowed":False,"paid_model_calls":0,"independent_reviews_required":True,
            "ckb_authority_unchanged":True}
def main():
    p=argparse.ArgumentParser()
    for name in ("launch","claim_w","claim_y","approval","runs","source","run_id","head","out"):
        p.add_argument("--"+name.replace("_","-"),required=True)
    a=p.parse_args()
    def load(path):
        return json.loads(pathlib.Path(path).read_bytes())
    receipt=verify(load(a.launch),[load(a.claim_w),load(a.claim_y)],
        load(a.approval),load(a.runs),a.source,int(a.run_id),a.head)
    with pathlib.Path(a.out).open("x") as f:f.write(json.dumps(receipt,sort_keys=True,indent=2)+"\n")
    print("R34_E3_TWO_ORIGINALS_ATOMICALLY_CONSUMED=PASS")
if __name__=="__main__":main()

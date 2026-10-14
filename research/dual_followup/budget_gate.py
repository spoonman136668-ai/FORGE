"""Once-only two-lane source-qualified scientific launch budget. No network or dispatch."""
import argparse,hashlib,json,pathlib
IDS=("W-FORGE-R35-TRAIN-QUARTILE-01","Y-FORGE-F1-CROSS-PAIR-LATENCY-01")
PREREG=("8228c9006777394376549ddca418ecd7efc5b49f","7dec76450e2192427cd60d24035e5087ed52fb40")
WORKER=("c5ee11c469f34289b7af81a46eedacf722e6333f","a19288bf54ca5fb13563eb4041c593923e234631")
REVIEWER=("cca2c27e9bbef7a98ad5df304e2cab9c3fc6a518","40b62bf9aabdfa13e67727d3c3d5ad865da457fa")
SCHEMA="forge.dual-r35-f1.first-use-consumed.v1"
def reject(code):raise ValueError("R35_F1_BUDGET_"+code)
def approval_text(source):
    return ("FORGE-R35-F1-TWO-LANE-ORIGINAL-BUDGET\n"
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
    if launch!={"schema":"forge.dual-r35-f1.single-launch.v1","source_commit":source,
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
    return {"schema":"forge.dual-r35-f1.budget-clearance.v1","source_commit":source,
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
    print("R35_F1_TWO_ORIGINALS_ATOMICALLY_CONSUMED=PASS")
if __name__=="__main__":main()

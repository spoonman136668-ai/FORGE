"""Bounded, owner-scoped two-original authorization; no general FORGE/FSA authority."""
import argparse,json,hashlib
from pathlib import Path
IDs=("W-FORGE-R30-NORMALIZED-GRADIENT-01","W-FORGE-R31-CONDITIONAL-REPLICATION-01")
PREREG=("835def227a9db297424509bbe44d1d5eaec2a6c5","70ff7d722f0e3814e9fba777bdfa1a4134eaf59d")
EXECUTE=("15ef546afe5658f8d24ac876e9849419ff827c9a","c0d666eaad1c344c73dcc57b416a979d9d97f58c")
REVIEW=("e08005a24df52fa49e432f96ef19d2a0a0be382f","df57db6e96f9125c1b3ad70a8233318f643bca1a")
WAKE_RUN_ID=38487981631

def parse(raw):
    def uniq(pairs):
        o={}
        for k,v in pairs:
            if k in o:raise ValueError("CYCLE_DUPLICATE_KEY")
            o[k]=v
        return o
    return json.loads(raw,object_pairs_hook=uniq)

def approval_text(source):
    return ("FORGE-R30-R31-TWO-ORIGINAL-BUDGET\n"
            "source_commit="+source+"\n"
            "experiments="+",".join(IDs)+"\n"
            "wake_run_id="+str(WAKE_RUN_ID)+"\n"
            "max_originals=2\n"
            "max_model_calls=0\n"
            "max_training_epochs_per_original=32\n"
            "max_sealed_seeds_per_original=48\n"
            "next_stage=independent-review-required\n"
            "retry=forbidden\n"
            "scope=Wingless-ONLY-no-controller-transfer\n")

def verify(launch,claims,approval,runs,source,run_id,head):
    if len(source)!=40 or any(c not in "0123456789abcdef" for c in source):
        raise ValueError("CYCLE_BAD_SOURCE")
    if launch!={"schema":"forge.r30-r31.bounded-start.v1","source_commit":source,
               "experiments":list(IDs),"original_budget":2}:
        raise ValueError("CYCLE_LAUNCH_DRIFT")
    if approval.get("user",{}).get("login")!="spoonman136668-ai" or approval.get("author_association")!="OWNER" or approval.get("body")!=approval_text(source) or approval.get("created_at")!=approval.get("updated_at"):
        raise ValueError("CYCLE_OWNER_APPROVAL_NOT_VERIFIED")
    if type(approval.get("id")) is not int or approval["id"]<=0:
        raise ValueError("CYCLE_APPROVAL_ID_INVALID")
    if not isinstance(claims,list) or len(claims)!=2:
        raise ValueError("CYCLE_CLAIM_COUNT")
    for i,claim in enumerate(claims):
        expected={"schema":"forge.r30-r31.first-use-consumed.v1","experiment_id":IDs[i],
          "source_commit":source,"prereg_blob":PREREG[i],"execute_blob":EXECUTE[i],
          "review_blob":REVIEW[i],"owner_approval_comment_id":approval["id"],
          "budget_limit":2,"first_use_consumed":True,"rerun_allowed":False}
        if claim!=expected:raise ValueError("CYCLE_CLAIM_DRIFT")
    if type(run_id) is not int or run_id<=0 or not isinstance(runs,dict) or runs.get("total_count")!=1 or len(runs.get("workflow_runs",[]))!=1:
        raise ValueError("CYCLE_DUPLICATE_DISPATCH")
    r=runs["workflow_runs"][0]
    if r.get("id")!=run_id or r.get("head_sha")!=head or r.get("run_attempt")!=1 or r.get("event")!="push":
        raise ValueError("CYCLE_RUN_IDENTITY_DRIFT")
    return {"schema":"forge.r30-r31.owner-bounded-clearance.v1","source_commit":source,"run_id":run_id,"originals_reserved":list(IDs),"owner_approval_id":approval["id"],"fsa_activated":False,"ckb_authority_unchanged":True}

def main():
    p=argparse.ArgumentParser()
    for key in ("launch","claim_r30","claim_r31","approval","runs","source","run_id","head","out"):
        p.add_argument("--"+key.replace("_","-"),required=True)
    a=p.parse_args()
    items=[parse(Path(getattr(a,k)).read_bytes()) for k in ("launch","claim_r30","claim_r31","approval","runs")]
    clearance=verify(items[0],items[1:3],items[3],items[4],a.source,int(a.run_id),a.head)
    with Path(a.out).open("x",encoding="utf-8") as f:
        f.write(json.dumps(clearance,sort_keys=True)+"\n")
    print("R30_R31_OWNER_CAPPED_FIRST_USE=PASS")
    print("R30_R31_CONSUMED_BEFORE_COMPUTE=PASS")
if __name__=="__main__":main()

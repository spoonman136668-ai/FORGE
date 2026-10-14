"""Two frozen Yggdrasil originals under one owner-scoped first-use authorization; no retries."""
import argparse,json
from pathlib import Path
IDS=("Y-FORGE-PARITY-B1-ONSET1","Y-FORGE-PARITY-B2-ONSET1")
MANIFEST="4c62067e255076ece4df1efa907d146eb230765c"
WORKER="52fc1e427fa15486e2a467989c80c8dd611208b1"
REVIEWER="04a7f5890f764cecc30dd9885dac58bb9a3aa0bb"
def strict(raw):
    def unique(pairs):
        d={}
        for k,v in pairs:
            if k in d:raise ValueError("YGG_B_DUPLICATE_JSON_KEY")
            d[k]=v
        return d
    return json.loads(raw,object_pairs_hook=unique)
def approval_text(source):
    return ("FORGE-YGG-B1-B2-TWO-FRESH-ORIGINAL-BUDGET\n"
            "source_commit="+source+"\n"
            "experiments="+",".join(IDS)+"\n"
            "max_originals=2\n"
            "prior_A1_consumed_and_not_replayed=true\n"
            "model_calls=0\n"
            "retry=forbidden\n"
            "independent_reviews_required=true\n"
            "scope=Yggdrasil-FORGE-no-CKB-FSA-or-Y070-transfer\n")
def verify(launch,claims,approval,runs,source,run_id,head):
    if type(source) is not str or len(source)!=40 or any(x not in "0123456789abcdef" for x in source):raise ValueError("YGG_B_BAD_SHA")
    if launch!={"schema":"forge.yggdrasil.parity-b.single-launch.v1","source_commit":source,
               "experiments":list(IDS),"original_budget":2}:raise ValueError("YGG_B_LAUNCH_DRIFT")
    if approval.get("user",{}).get("login")!="spoonman136668-ai" or approval.get("author_association")!="OWNER" or approval.get("created_at")!=approval.get("updated_at") or approval.get("body")!=approval_text(source) or type(approval.get("id")) is not int:raise ValueError("YGG_B_OWNER_APPROVAL_INVALID")
    if type(run_id) is not int or run_id<=0 or not isinstance(runs,dict) or runs.get("total_count")!=1 or len(runs.get("workflow_runs",[]))!=1:raise ValueError("YGG_B_DUPLICATE_WORKFLOW")
    row=runs["workflow_runs"][0]
    if row.get("id")!=run_id or row.get("head_sha")!=head or row.get("run_attempt")!=1 or row.get("event")!="push":raise ValueError("YGG_B_ONCE_ONLY_DRIFT")
    if not isinstance(claims,list) or len(claims)!=2:raise ValueError("YGG_B_CLAIMS_MISSING")
    for i,claim in enumerate(claims):
        expect={"schema":"forge.yggdrasil.b-first-use-consumed.v1","experiment_id":IDS[i],
                "source_commit":source,"prereg_blob":MANIFEST,"worker_blob":WORKER,
                "reviewer_blob":REVIEWER,"operator_approval_comment_id":approval["id"],
                "first_use_consumed":True,"rerun_allowed":False,"budget_claims":2}
        if claim!=expect:raise ValueError("YGG_B_CLAIM_IDENTITY_DRIFT")
    return {"schema":"forge.yggdrasil.b-bounded-owner-clearance.v1","source_commit":source,
            "originals_consumed":list(IDS),"run_id":run_id,"ckb_authority_changed":False,
            "fsa_activated":False,"paid_api_calls":0}
def main():
    p=argparse.ArgumentParser()
    for x in ("launch","claim_b1","claim_b2","approval","runs","source","run_id","head","out"):
        p.add_argument("--"+x.replace("_","-"),required=True)
    a=p.parse_args()
    docs=[strict(Path(getattr(a,x)).read_bytes()) for x in ("launch","claim_b1","claim_b2","approval","runs")]
    result=verify(docs[0],docs[1:3],docs[3],docs[4],a.source,int(a.run_id),a.head)
    with Path(a.out).open("x") as f:f.write(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print("YGG_B1_B2_OWNER_SINGLE_BUDGET=PASS")
if __name__=="__main__":main()

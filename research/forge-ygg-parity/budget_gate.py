"""Three-reservation owner-scoped single launch, no broad research authority."""
import argparse,hashlib,json
from pathlib import Path
MANIFEST="031fa0e6ed051a439b1c31d334f30ca8c4af5dec"
WORKER="b32246d8839aa591c6817d4f99bc3c180f02143e"
REVIEWER="732603b8c890f39164ea06ce5d0bb4a3760f7b61"
INTERRUPTER="393b04ff0857603010461eb75b381c89dea51e6c"
IDS=("Y-FORGE-REAL-INTERRUPT-01","Y-FORGE-PARITY-A1-ONSET1","Y-FORGE-PARITY-A2-ONSET1")
def strict(s):
    def no_dupe(pairs):
        d={}
        for k,v in pairs:
            if k in d:raise ValueError("YGG_DUPLICATE_CLAIM_KEY")
            d[k]=v
        return d
    return json.loads(s,object_pairs_hook=no_dupe)
def approval_text(source):
    return ("FORGE-YGG-REAL-INTERRUPT-PLUS-TWO-ORIGINAL-BUDGET\n"
      "source_commit="+source+"\n"
      "experiments="+",".join(IDS)+"\n"
      "one_forced_real_worker_interruption=true\n"
      "max_scientific_originals=2\n"
      "maximum_firstuse_claims=3\n"
      "model_calls=0\n"
      "retry=forbidden\n"
      "independent_reviews_required=true\n"
      "scope=Yggdrasil-FORGE-independent-no-CKB-or-FSA-transfer\n")
def verify(launch,claims,approval,runs,source,run_id,head):
    if type(source) is not str or len(source)!=40 or any(c not in "0123456789abcdef" for c in source):raise ValueError("YGG_SOURCE_INVALID")
    expected={"schema":"forge.yggdrasil.parity.single-launch.v1","source_commit":source,
              "experiments":list(IDS),"budget_originals":2,"forced_real_worker_interruptions":1}
    if launch!=expected:raise ValueError("YGG_LAUNCH_IDENTITY_DRIFT")
    if not isinstance(approval,dict) or approval.get("user",{}).get("login")!="spoonman136668-ai" or approval.get("author_association")!="OWNER" or approval.get("created_at")!=approval.get("updated_at") or approval.get("body")!=approval_text(source):
        raise ValueError("YGG_OPERATOR_APPROVAL_INVALID")
    if type(approval.get("id")) is not int or approval["id"]<=0:raise ValueError("YGG_APPROVAL_ID_BAD")
    if type(run_id) is not int or run_id<=0 or not isinstance(runs,dict) or runs.get("total_count")!=1 or len(runs.get("workflow_runs",[]))!=1:
        raise ValueError("YGG_DUPLICATE_FIRST_USE")
    row=runs["workflow_runs"][0]
    if row.get("id")!=run_id or row.get("head_sha")!=head or row.get("run_attempt")!=1 or row.get("event")!="push":
        raise ValueError("YGG_FIRST_USE_RUN_ID_DRIFT")
    if not isinstance(claims,list) or len(claims)!=3:raise ValueError("YGG_CLAIM_COUNT")
    for i,c in enumerate(claims):
        expect={"schema":"forge.yggdrasil.first-use-consumed.v1","experiment_id":IDS[i],
            "source_commit":source,"prereg_blob":MANIFEST,"worker_blob":WORKER,
            "reviewer_blob":REVIEWER,"interrupt_controller_blob":INTERRUPTER,
            "operator_approval_comment_id":approval["id"],
            "first_use_consumed":True,"rerun_allowed":False,"budget_claims":3}
        if c!=expect:raise ValueError("YGG_CLAIM_DRIFT")
    return {"schema":"forge.yggdrasil.parity.single-use-clearance.v1",
        "source_commit":source,"run_id":run_id,"claims_consumed":list(IDS),
        "fsa_activated":False,"ckb_authority_changed":False,"paid_api_calls":0}
def main():
    p=argparse.ArgumentParser()
    for key in ("launch","claim_interrupt","claim_a1","claim_a2","approval","runs","source","run_id","head","out"):
        p.add_argument("--"+key.replace("_","-"),required=True)
    a=p.parse_args()
    raw=[strict(Path(getattr(a,k)).read_bytes()) for k in ("launch","claim_interrupt","claim_a1","claim_a2","approval","runs")]
    receipt=verify(raw[0],raw[1:4],raw[4],raw[5],a.source,int(a.run_id),a.head)
    with Path(a.out).open("x") as f:f.write(json.dumps(receipt,sort_keys=True,indent=2)+"\n")
    print("YGG_3_CLAIMS_OWNER_BUDGET_GATE=PASS",flush=True)
if __name__=="__main__":main()

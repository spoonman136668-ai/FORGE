"""One-shot F2 owner budget. New study only; F1 remains permanently consumed."""
import argparse,json,pathlib
ID="Y-FORGE-F2-LEGAL-PAIR-TRANSFER-01"
PREREG="04bc2ab3cb6c6e0385a9e6cc3e3132f7f254f588"
WORKER="ed1c09bfe3fc1da8f066b6ddec0d5cd0297a659f"
REVIEWER="0e46c7e428323bae0e02a565d483347097f242b5"
SCHEMA="forge.ygg.f2.first-use-consumed.v1"
def reject(text):raise ValueError("F2_BUDGET_"+text)
def approval_text(source):
    return ("FORGE-YGG-F2-SINGLE-LEGAL-PAIR-ORIGINAL\n"
            "source_commit="+source+"\n"
            "experiment_id="+ID+"\n"
            "max_originals=1\n"
            "parent_e3_independent_run_id=38535831669\n"
            "prior_f1_claim_consumed_no_replay=true\n"
            "paid_model_calls=0\n"
            "retry=forbidden\n"
            "independent_review_required=true\n"
            "fsa_activated=false\n"
            "ckb_authority_unchanged=true\n")
def verify(launch,claim,approval,runs,source,run_id,head):
    if len(source)!=40 or len(head)!=40 or type(run_id) is not int or run_id<=0:reject("SOURCE")
    if launch!={"schema":"forge.ygg.f2.single-start.v1","experiment_id":ID,"source_commit":source,"original_budget":1}:
        reject("LAUNCH")
    if approval.get("body")!=approval_text(source) or approval.get("user",{}).get("login")!="spoonman136668-ai" or approval.get("author_association") not in ("OWNER","MEMBER") or approval.get("created_at")!=approval.get("updated_at") or type(approval.get("id")) is not int:
        reject("OWNER_APPROVAL")
    want={"schema":SCHEMA,"experiment_id":ID,"source_commit":source,
          "prereg_blob":PREREG,"worker_blob":WORKER,"reviewer_blob":REVIEWER,
          "owner_approval_comment_id":approval["id"],"budget_limit":1,
          "first_use_consumed":True,"rerun_allowed":False}
    if claim!=want:reject("CLAIM_DRIFT_OR_REPLAY")
    if type(runs.get("total_count")) is not int or runs["total_count"]!=1 or len(runs.get("workflow_runs",[]))!=1:
        reject("DUPLICATE_DISPATCH")
    run=runs["workflow_runs"][0]
    if run.get("id")!=run_id or run.get("head_sha")!=head or run.get("event")!="push" or run.get("run_attempt")!=1:
        reject("FOREIGN_OR_RETRIED_RUN")
    return {"schema":"forge.ygg.f2.clearance.v1","experiment_id":ID,"run_id":run_id,
            "original_consumed":True,"reruns_allowed":False,"paid_model_calls":0,
            "review_required":True,"prior_f1_replayed":False,
            "ckb_authority_unchanged":True}
def main():
    p=argparse.ArgumentParser()
    for name in ("launch","claim","approval","runs","source","run_id","head","out"):
        p.add_argument("--"+name.replace("_","-"),required=True)
    a=p.parse_args()
    def read(path):return json.loads(pathlib.Path(path).read_bytes())
    receipt=verify(read(a.launch),read(a.claim),read(a.approval),read(a.runs),
                   a.source,int(a.run_id),a.head)
    with pathlib.Path(a.out).open("x") as f:f.write(json.dumps(receipt,sort_keys=True,indent=2)+"\n")
    print("F2_ONCE_ONLY_OWNER_APPROVAL=PASS")
if __name__=="__main__":main()

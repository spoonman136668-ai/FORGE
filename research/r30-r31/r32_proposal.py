"""No new dispatch: derive R32 proposal strictly from two independent reviews."""
import argparse,hashlib,importlib.util,json
from pathlib import Path
HERE=Path(__file__).resolve().parent
def reviewer(name):
    path=HERE.parent/name/"review.py"
    spec=importlib.util.spec_from_file_location("check_"+name,path)
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    return m
def propose(r30_manifest,r30_original,r30_review,r31_manifest,r31_original,r31_review):
    first=reviewer("r30-wingless").verify(r30_manifest,r30_original)
    if json.loads(r30_review)!=first or first.get("independently_validated") is not True:raise ValueError("R32_PARENT_R30_INVALID")
    second=reviewer("r31-wingless").verify(r31_manifest,r31_original,r30_review)
    if json.loads(r31_review)!=second or second.get("independently_validated") is not True:raise ValueError("R32_PARENT_R31_INVALID")
    outcome=second["outcome"]
    return {"schema":"forge.r32.scientific-successor-proposal.v1",
        "experiment_id":"W-FORGE-R32-SOURCE-MECHANISM-01",
        "parent_experiment_id":second["experiment_id"],
        "parent_original_sha256":hashlib.sha256(r31_original).hexdigest(),
        "parent_review_sha256":hashlib.sha256(r31_review).hexdigest(),
        "prior_r30_outcome":first["outcome"],
        "prior_r31_outcome":outcome,
        "hypothesis":("Replicate independently in new source families and seeds" if outcome=="ROBUST_CONDITIONAL_GAIN" else "Investigate source-family margin geometry with a novel train-only control and fresh cohorts"),
        "proposal_only":True,"new_original_dispatch_authorized":False,
        "new_science_originals_executed":0,"ckb_authority_unchanged":True}
def main():
    p=argparse.ArgumentParser()
    for x in ("r30_manifest","r30_original","r30_review","r31_manifest","r31_original","r31_review","out"):
        p.add_argument("--"+x.replace("_","-"),required=True)
    a=p.parse_args()
    result=propose(*(Path(getattr(a,x)).read_bytes() for x in ("r30_manifest","r30_original","r30_review","r31_manifest","r31_original","r31_review")))
    with Path(a.out).open("x") as f:f.write(json.dumps(result,sort_keys=True,indent=2)+"\n")
    print("R32_AUTOMATIC_VERIFIED_PROPOSAL=PASS")
    print("R32_ORIGINAL_DISPATCH=FALSE")
if __name__=="__main__":main()

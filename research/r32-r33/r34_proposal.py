"""Prepare R34 proposal from authenticated archived, independently reviewed R32 and R33 originals. No dispatch."""
import argparse,hashlib,importlib.util,json
from pathlib import Path
HERE=Path(__file__).resolve().parent
def reviewer(name):
    path=HERE.parent/name/"review.py"
    spec=importlib.util.spec_from_file_location("qualify_"+name,path)
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    return m
def propose(r31_review,r32_manifest,r32_original,r32_review,r33_manifest,r33_original,r33_review):
    first=reviewer("r32-wingless").verify(r32_manifest,r32_original,r31_review)
    if json.loads(r32_review)!=first or first.get("independently_validated") is not True:
        raise ValueError("R34_PARENT_R32_UNQUALIFIED")
    second=reviewer("r33-wingless").verify(r33_manifest,r33_original,r32_review)
    if json.loads(r33_review)!=second or second.get("independently_validated") is not True:
        raise ValueError("R34_PARENT_R33_UNQUALIFIED")
    outcome=second["outcome"]
    return {"schema":"forge.r34.scientific-successor-proposal.v1",
        "experiment_id":"W-FORGE-R34-REPLICATION-MECHANISM-01",
        "parent_experiment_id":second["experiment_id"],
        "parent_original_sha256":hashlib.sha256(r33_original).hexdigest(),
        "parent_review_sha256":hashlib.sha256(r33_review).hexdigest(),
        "prior_r32_outcome":first["outcome"],
        "prior_r33_outcome":outcome,
        "hypothesis":("Repeat robust gain across new source-generating families under fixed budget" if outcome=="ROBUST_TEMPERATURE_GAIN" else "Diagnose source-family geometry on new disjoint cohorts without tuning against consumed holdouts"),
        "proposal_only":True,"new_original_dispatch_authorized":False,
        "new_science_originals_executed":0,"ckb_authority_unchanged":True}
def main():
    p=argparse.ArgumentParser()
    for x in ("r31_review","r32_manifest","r32_original","r32_review","r33_manifest","r33_original","r33_review","out"):
        p.add_argument("--"+x.replace("_","-"),required=True)
    a=p.parse_args()
    result=propose(*(Path(getattr(a,x)).read_bytes() for x in ("r31_review","r32_manifest","r32_original","r32_review","r33_manifest","r33_original","r33_review")))
    with Path(a.out).open("x") as f:f.write(json.dumps(result,sort_keys=True,indent=2)+"\n")
    print("R34_AUTOMATIC_VERIFIED_PROPOSAL=PASS")
    print("R34_ORIGINAL_DISPATCH=FALSE")
if __name__=="__main__":main()

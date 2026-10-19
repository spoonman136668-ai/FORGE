"""Deterministic and non-dispatching R29 -> R30 successor proposal.

Independent scientific reviewer is run again; no R29 originals are replayed.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

EXPERIMENT="W-FORGE-R29-SOURCE-ROBUST-SUCCESSOR-01"
NEXT="W-FORGE-R30-SOURCE-ROBUST-REPLICATION-01"
def load(raw):
    def unique(pairs):
        result={}
        for k,v in pairs:
            if k in result:raise ValueError("R30_DUPLICATE_JSON")
            result[k]=v
        return result
    return json.loads(raw,object_pairs_hook=unique)
def propose(manifest,original,review):
    spec=importlib.util.spec_from_file_location("r29_reviewer",Path(__file__).with_name("review.py"))
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    computed=mod.verify(manifest,original)
    if load(review)!=computed or computed.get("experiment_id")!=EXPERIMENT or computed.get("independently_validated") is not True:
        raise ValueError("R30_UNACCEPTED_PARENT_EVIDENCE")
    orig=load(original)
    if orig.get("experiment_id")!=EXPERIMENT or not str(orig.get("github_run_id","")).isdecimal():
        raise ValueError("R30_PARENT_IDENTITY")
    outcome=computed["outcome"]
    objective=("Replicate candidate source-family gain on fresh disjoint splits, without reusing R29 sealed seeds"
               if outcome=="ROBUST_SMOOTH_GAIN" else
               "Discriminate smooth objective failure mechanisms on fresh development splits before any new sealed test")
    return {"schema":"forge.r30.independently-reviewed-proposal.v1",
            "lane":"Wingless","experiment_id":NEXT,
            "parent_experiment_id":EXPERIMENT,
            "parent_run_id":int(orig["github_run_id"]),
            "parent_original_sha256":hashlib.sha256(original).hexdigest(),
            "parent_review_sha256":hashlib.sha256(review).hexdigest(),
            "parent_outcome":outcome,
            "scientific_objective":objective,
            "required_next_step":"New independent frozen preregistration and source-birth qualification",
            "parent_replay_allowed":False,
            "new_original_dispatch_authorized":False,
            "ckb_authority_unchanged":True,"fsa_activated":False,
            "new_originals_executed":0}
def main():
    p=argparse.ArgumentParser()
    for key in ("manifest","original","review","output"):
        p.add_argument("--"+key,required=True)
    args=p.parse_args()
    out=propose(*(Path(getattr(args,x)).read_bytes() for x in ("manifest","original","review")))
    with Path(args.output).open("x",encoding="utf-8") as f:
        f.write(json.dumps(out,sort_keys=True,indent=2)+"\n")
    print("R30_PREPARATION_FROM_INDEPENDENT_R29=PASS")
    print("R30_NEW_SCIENCE_DISPATCH=FALSE")
if __name__=="__main__":main()

"""R27 deterministic, fail-closed automatic successor from the consumed R26 original.

No original runner, dispatch token, or source editor. This builds an immutable
proposal from independently verified raw R26 bytes, its signed-off reviewer
record and separately precommitted first-use claim.
"""
import hashlib
import json
from pathlib import Path
import importlib.util
import sys

R26_RUN=38480506640
PARENT="W-FORGE-R26-OUT-OF-COHORT-REPLICATION-01"
PARENT_SHA="e796abc9bafcfa8657bcb6fef6cb64c1ddb37234ffb99a87e3ed17d7570818e4"
CLAIM_SHA="53174dd366a8b1b5c968877a3f1a19485e534536"
FROZEN="ba54fa51807e7135b598ac2cefbe09984f162da6"
ID="W-FORGE-R27-SOURCE-ROBUST-OBJECTIVE-01"
HERE=Path(__file__).resolve().parent

def read(raw):
    if len(raw)>15<<20:raise ValueError("R27_OVERSIZE_INPUT")
    def unique(pairs):
        d={}
        for key,value in pairs:
            if key.casefold() in d:raise ValueError("R27_DUPLICATE_INPUT_KEY")
            d[key.casefold()]=value
        return dict(pairs)
    return json.loads(raw,object_pairs_hook=unique)

def build(manifest,original,review,claim,claim_commit):
    if claim_commit!=CLAIM_SHA:raise ValueError("R27_UNPINNED_FIRST_USE")
    if hashlib.sha256(original).hexdigest()!=PARENT_SHA:raise ValueError("R27_PARENT_ORIGINAL_DRIFT")
    spec=importlib.util.spec_from_file_location("r26_independent",HERE.parent/"r26-wingless"/"review.py")
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    expected=module.verify(manifest,original)
    actual=read(review)
    # Ignore only the non-scientific archive formatting, never scientific data.
    if actual!=expected:raise ValueError("R27_REVIEW_UNAUTHENTICATED")
    if expected["reported_outcome"]!="NO_CONFIRMED_DIVERSITY_GAIN" or not expected["independent_bounded_validation"]:
        raise ValueError("R27_PARENT_NOT_A_VERIFIED_NEGATIVE")
    parent=read(original)
    if int(parent["github_run_id"])!=R26_RUN:raise ValueError("R27_WRONG_ORIGINAL_RUN")
    c=read(claim)
    if c!={"schema":"forge.r26.remote-first-use-claim.v1","experiment_id":PARENT,
           "frozen_blob":FROZEN,"source_commit":"fa6543db0b9eae3fa68e263d9379d47636bdf726",
           "first_use_consumed":True,"rerun_allowed":False}:
        raise ValueError("R27_PARENT_FIRST_USE_IDENTITY_DRIFT")
    return {
      "schema":"forge.r27.automatic-successor-proposal.v1",
      "lane":"Wingless","experiment_id":ID,
      "parent_experiment_id":PARENT,
      "parent_original_sha256":PARENT_SHA,
      "parent_run_id":R26_RUN,
      "parent_claim_commit":CLAIM_SHA,
      "parent_independent_outcome":"NO_CONFIRMED_DIVERSITY_GAIN",
      "parent_replay_allowed":False,
      "next_hypothesis":"Under an unchanged 1728-example and 32-epoch budget, a train-only source-invariant contrastive weighting objective may improve worst-source accuracy relative to the failed fixed balanced full-batch mix, without harming any source.",
      "design_options":["Train-only learned source-aware weighting with frozen policy before sealed test",
                        "Equal-capacity and equal-example affine-only and balanced fixed-batch controls",
                        "New disjoint development and sealed seeds chosen and frozen before implementation",
                        "Retain negative/nonfinalist outcomes and compare per-source harm"],
      "required_gates":["Fresh immutable preregistration and frozen seed sets",
                        "Independent source-birth and no-reuse audit",
                        "Durable new-original first-use claim before any worker start",
                        "Independent original artifact verification and scientific classification"],
      "proposal_only":True,
      "new_scientific_originals_executed":0,
      "new_original_dispatch_authorized":False,
      "ckb_owner_changed":False,
      "fsa_required_now":False
    }
def main(argv):
    if len(argv)!=7:raise SystemExit("Usage: successor.py prereg original review claim claim_commit output")
    _,manifest,original,review,claim,commit,out=argv
    p=build(Path(manifest).read_bytes(),Path(original).read_bytes(),
            Path(review).read_bytes(),Path(claim).read_bytes(),commit)
    Path(out).write_text(json.dumps(p,sort_keys=True,indent=2)+"\n",encoding="utf8")
    print("R27_AUTHENTIC_NEGATIVE_TO_NEW_CANDIDATE=PASS")
    print("R27_NEW_ORIGINALS_EXECUTED=ZERO")
if __name__=="__main__":main(sys.argv)

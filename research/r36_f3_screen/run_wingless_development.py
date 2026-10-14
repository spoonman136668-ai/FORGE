"""R36 Wingless genuine pinned-source *development-only* measurement.

Evaluates all four draft training primitives plus frozen hard-minimax control on
disjoint preregistered development folds. This deliberately does not select a
scientific winner or touch any heldout seed. Surrogates remain fidelity-blocked.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

import pinned_wingless_dev as source
from wingless_methods import METHODS, train

R34_BLOB = "7e3db618c055e5228f9b07639e4555bc9250008e"
FROZEN_BLOB = source.PORTFOLIO_BLOB

def git_blob(raw):
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\x00"+raw).hexdigest()

def audit_frozen():
    path=Path(__file__).resolve().with_name("frozen_portfolio.json")
    raw=path.read_bytes()
    if git_blob(raw)!=FROZEN_BLOB:
        raise ValueError("R36_DEV_PORTFOLIO_BLOB_DRIFT")
    manifest=json.loads(raw)
    expected={x["id"] for x in manifest["wingless"]["candidates"]}
    if expected!=set(METHODS):
        raise ValueError("R36_DEV_METHOD_ID_DRIFT")
    return manifest

def load_evaluator(root):
    from subprocess import check_output, DEVNULL
    root=Path(root).resolve(strict=True)
    if source._git(root,"rev-parse","HEAD")!=source.SOURCE_COMMIT or source._git(root,"status","--porcelain"):
        raise ValueError("R36_DEV_SOURCE_IDENTITY_DRIFT")
    forge_root=Path(__file__).resolve().parents[2]
    if source._git(forge_root,"rev-parse","HEAD:research/r34-wingless/execute.py")!=R34_BLOB:
        raise ValueError("R36_DEV_EVALUATOR_BLOB_DRIFT")
    f=forge_root/"research/r34-wingless/execute.py"
    spec=importlib.util.spec_from_file_location("r36_pinned_r34",f)
    if not spec or not spec.loader:
        raise ValueError("R36_DEV_EVALUATOR_UNAVAILABLE")
    mod=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    w52=mod.load_parent(root/source.SOURCE_PATH)
    return mod,w52

def measure(checkout):
    manifest=audit_frozen()
    w=manifest["wingless"]
    blocks=w["development_blocks"]
    # Every validation seed is a reserved development seed from another block.
    # Neither scorer nor training loader receives the sealed cohort.
    evaluator,scientific=load_evaluator(checkout)
    folds=[]
    for i,block in enumerate(blocks):
        validation=[s for j,other in enumerate(blocks) if j!=i for s in other]
        if len(validation)!=32 or set(block)&set(validation):
            raise ValueError("R36_DEV_FOLD_OVERLAP")
        training=source.load_training(checkout,manifest,i)
        experiments={"CONTROL":evaluator.minimax_fit(scientific,block)}
        for candidate in METHODS:
            experiments[candidate]=train(candidate,training)
        scores={}
        for ident,model in experiments.items():
            if "source_counts" not in model:
                model=dict(model)
                model["source_counts"]={g:576 for g in scientific.GEN}
            measured=evaluator.evaluate(scientific,model,validation)
            if [x["seed"] for x in measured["by_seed"]]!=validation:
                raise ValueError("R36_DEV_EVALUATION_SEED_DRIFT")
            scores[ident]={
                "weights_sha256":model["weights_sha256"],
                "weights":list(model["weights"]),
                "accuracy":measured["accuracy"],
                "family_accuracy":measured["family_accuracy"],
                "by_seed":measured["by_seed"],
            }
        folds.append({"train_block":i,"train_seeds":block,"development_validation_seeds":validation,
                      "scores":scores})
    return {
        "schema":"forge.r36.wingless.development-only-measurement.v1",
        "status":"DEVELOPMENT_MEASURED_METHOD_FIDELITY_NOT_QUALIFIED",
        "wingless_source_commit":source.SOURCE_COMMIT,
        "frozen_portfolio_blob":FROZEN_BLOB,
        "evaluator_blob":R34_BLOB,
        "folds":folds,
        "candidate_ids":list(METHODS),
        "scientific_winners_selected":0,
        "new_scientific_originals_executed":0,
        "new_first_use_claims_created":0,
        "sealed_cohort_accessed":False,
        "source_claim":"Pinned synthetic Wingless development simulations only; not independent scientific acceptance.",
    }

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--wingless-root",required=True)
    ap.add_argument("--out",required=True)
    args=ap.parse_args()
    record=measure(args.wingless_root)
    data=(json.dumps(record,sort_keys=True,separators=(",",":"),allow_nan=False)+"\n").encode()
    target=Path(args.out)
    with target.open("xb") as out:
        out.write(data)
    print("R36_PINNED_REAL_DEVELOPMENT=PASS")
    print("R36_DEV_FOLDS=3")
    print("R36_DEV_CANDIDATES=4")
    print("R36_DEV_RECORD_SHA256="+hashlib.sha256(data).hexdigest())
    print("R36_SEALED_FIRST_USE=ZERO")

if __name__=="__main__":
    main()

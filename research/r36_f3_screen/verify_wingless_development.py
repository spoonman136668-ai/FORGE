"""Independent R36 Wingless source-replay witness over development-only seeds.

Does not call the FORGE evaluator or optimizer. Recomputes each metric from
the pinned Wingless low-level generator using archived weights and fixed
cross-development-fold seed identities. Rejects tampering, sealed access, and
unverifiable scientific-selection assertions. NOT a final science acceptance.
"""
import argparse
import hashlib
import importlib.util
import json
import math
from pathlib import Path

import pinned_wingless_dev as pinned
from wingless_methods import METHODS

EXPECTED_BLOB = pinned.PORTFOLIO_BLOB
IDS = ("CONTROL",)+METHODS

def check(condition, reason):
    if not condition:
        raise ValueError("R36_WITNESS_"+reason)

def close(a,b):
    return math.isfinite(a) and math.isfinite(b) and abs(a-b) <= 1e-9

def replay(record, wingless_root):
    from run_wingless_development import audit_frozen, load_evaluator
    portfolio=audit_frozen()
    folds=record.get("folds")
    check(record.get("schema")=="forge.r36.wingless.development-only-measurement.v1", "SCHEMA")
    check(record.get("status")=="DEVELOPMENT_MEASURED_METHOD_FIDELITY_NOT_QUALIFIED", "STATUS")
    check(record.get("frozen_portfolio_blob")==EXPECTED_BLOB, "PORTFOLIO")
    check(record.get("wingless_source_commit")==pinned.SOURCE_COMMIT, "SOURCE")
    check(record.get("scientific_winners_selected")==0, "SELECTION")
    check(record.get("new_first_use_claims_created")==0, "FIRST_USE")
    check(record.get("new_scientific_originals_executed")==0, "ORIGINAL")
    check(record.get("sealed_cohort_accessed") is False, "SEALED")
    check(record.get("candidate_ids")==list(METHODS), "IDS")
    check(isinstance(folds,list) and len(folds)==3, "FOLD_COUNT")
    _adapter, w52=load_evaluator(wingless_root)
    blocks=portfolio["wingless"]["development_blocks"]
    sealed=set(portfolio["wingless"]["reserved_sealed_heldout_seeds"])
    results=[]
    for index, fold in enumerate(folds):
        dev=[seed for i,b in enumerate(blocks) if i!=index for seed in b]
        check(fold.get("train_block")==index, "BLOCK")
        check(fold.get("train_seeds")==blocks[index], "TRAIN_SEEDS")
        check(fold.get("development_validation_seeds")==dev, "VALIDATION_SEEDS")
        check(len(set(dev))==32 and not (set(dev)&set(blocks[index])) and not(set(dev)&sealed), "SPLIT")
        scores=fold["scores"]
        check(set(scores)==set(IDS), "ARM_SET")
        summaries={}
        for ident in IDS:
            reported=scores[ident]
            weights=reported["weights"]
            check(isinstance(weights,list) and len(weights)==16 and all(type(x) in (float,int) and math.isfinite(x) for x in weights), "WEIGHTS")
            digest=hashlib.sha256(json.dumps(weights,separators=(",",":"),allow_nan=False).encode()).hexdigest()
            check(reported.get("weights_sha256")==digest, "MODEL_HASH")
            rows=reported.get("by_seed")
            check(isinstance(rows,list) and len(rows)==32, "RAW_ROWS")
            family_correct={key:0. for key in w52.GEN}
            total_correct=0.
            for offset, seed in enumerate(dev):
                row=rows[offset]
                check(row.get("seed")==seed and row.get("total")==108, "ROW_SEED")
                check(set(row.get("family_correct",{}))==set(w52.GEN), "ROW_SOURCES")
                seed_total=0.
                for generator in w52.GEN:
                    family_total=0.
                    for site in w52.SITES:
                        for entity in range(9):
                            base,pos,neg=w52.w37.recoded_example(seed,entity,generator,"identity",site,3,False)
                            positive=w52.w42.feature(base,pos)
                            negative=w52.w42.feature(base,neg)
                            margin=sum(a*(b-c) for a,b,c in zip(weights,positive,negative))
                            family_total+=w52.w45.credit(margin,True)+w52.w45.credit(-margin,False)
                    check(close(family_total,row["family_correct"][generator]), "RAW_SCORE")
                    family_correct[generator]+=family_total
                    seed_total+=family_total
                check(close(seed_total,row["correct"]), "SEED_SCORE")
                total_correct+=seed_total
            family_accuracy={g:family_correct[g]/(32*36) for g in w52.GEN}
            accuracy=total_correct/(32*108)
            check(close(accuracy,reported["accuracy"]), "ACCURACY")
            for g in w52.GEN:
                check(close(family_accuracy[g],reported["family_accuracy"][g]), "FAMILY_ACCURACY")
            summaries[ident]={"accuracy":accuracy,"min_family_accuracy":min(family_accuracy.values()),"family_accuracy":family_accuracy}
        results.append({"fold":index,"verified":True,"metrics":summaries})
    return {"schema":"forge.r36.wingless.independent-development-witness.v1",
            "status":"REAL_DEVELOPMENT_METRICS_VERIFIED_NO_SCIENTIFIC_SELECTION",
            "source_commit":pinned.SOURCE_COMMIT,"portfolio_blob":EXPECTED_BLOB,
            "folds":results,"recomputed_candidate_count":4,
            "scientific_winners_selected":0,"scientific_originals_executed":0,
            "sealed_first_use_consumed":0}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--record",required=True)
    p.add_argument("--wingless-root",required=True)
    p.add_argument("--out",required=True)
    args=p.parse_args()
    record=json.loads(Path(args.record).read_bytes())
    witness=replay(record,args.wingless_root)
    with Path(args.out).open("xb") as output:
        output.write((json.dumps(witness,sort_keys=True,indent=2,allow_nan=False)+"\n").encode())
    print("R36_REAL_WINGLESS_DEVELOPMENT_INDEPENDENT_WITNESS=PASS")
    print("R36_DEVELOPMENT_FOLDS=3")
    print("R36_FIRST_USES_CONSUMED=ZERO")

if __name__=="__main__":
    main()

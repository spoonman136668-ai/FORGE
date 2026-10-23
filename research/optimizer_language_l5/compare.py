"""L5 mandatory independent all-native public corpus and output reconciliation.

No internet, training code or optional packages required by comparator.
CPU and wall and highwater differ by OS and are reported not compared.
"""
import json
import math
from pathlib import Path
import sys

ROLES=("L5_TRAIN","L5_SELECT","L5_DEV")
COUNTS={"L5_TRAIN":750,"L5_SELECT":120,"L5_DEV":160}
ARMS=("WORD_PREFIX_LEXICON","CHAR_BIGRAM_BEAM","CHAR_TRIGRAM_BEAM",
      "CHAR_4GRAM_BEAM","CHAR_TRIGRAM_PLUS_CONTEXT","SUFFIX_CHUNK_REUSE")
SOURCE_BLOB="0f25e9af379233267a09623e0c650472f9e463ea"
SCHEMA="forge.optimizer.language.l5.public-subword-receipt.v1"
QUALITY=("full_word_exact_match","unseen_train_target_exact",
         "normalized_edit_distance","position_character_accuracy",
         "novel_output_rate","prefix_violation_rate",
         "prefix_only_abstention_rate")
EXACT=("examples","unseen_train_target_count",
       "unseen_train_target_exact_numerator","output_sha256",
       "lookup_expansion_proxy_not_FLOPs")


def reconcile(a,b):
    for item in (a,b):
        if (item.get("schema")!=SCHEMA or
            item.get("scope")!="PUBLIC_EXTERNAL_PREFIX_DEV_ONLY" or
            item.get("external_git_blob_sha1")!=SOURCE_BLOB or
            item.get("previous_L1_L4_DEV_consumed")!=0 or
            item.get("Q21_FSA_first_use") is not False or
            item.get("native_science_unchanged") is not True or
            item.get("scientific_promotion") is not False or
            item.get("externally_blinded_first_use") is not False or
            item.get("complete_resource_matched_LM_comparison") is not False):
            raise ValueError("L5_PROTECTED_SCIENTIFIC_OR_SOURCE_CUSTODY_VIOLATION")
        if (item.get("role_counts")!=COUNTS or
            set(item.get("source_role_sha256",{}))!=set(ROLES) or
            set(item.get("model_resources",{}))!=set(ARMS) or
            set(item.get("role_evaluations",{}))!=set(ROLES)):
            raise ValueError("L5_SOURCE_MODEL_COVERAGE_FAILURE")
    if (a["external_raw_sha256"]!=b["external_raw_sha256"] or
        a["source_role_sha256"]!=b["source_role_sha256"]):
        raise ValueError("L5_EXTERNAL_OR_ROLE_SHA_DRIFT")
    errors=[]
    compared=0
    for arm in ARMS:
        for field in ("trained_checkpoint_sha256","trained_checkpoint_bytes",
                      "train_examples","source_target_train_vocab_words"):
            if a["model_resources"][arm].get(field)!=b["model_resources"][arm].get(field):
                errors.append({"arm":arm,"field":field})
    for role in ROLES:
        first,second=a["role_evaluations"][role],b["role_evaluations"][role]
        if set(first)!=set(ARMS) or set(second)!=set(ARMS):
            raise ValueError("L5_ALL_ARM_ROLE_RECEIPTS_MISSING")
        for arm in ARMS:
            x,y=first[arm],second[arm]
            for field in EXACT:
                if x.get(field)!=y.get(field):
                    errors.append({"role":role,"arm":arm,"field":field,
                                   "linux":x.get(field),"windows":y.get(field)})
            if x["examples"]!=COUNTS[role]:
                raise ValueError("L5_EXPERIENCE_ROLE_COUNT_DRIFT")
            for field in QUALITY:
                l,r=x.get(field),y.get(field)
                if l is None or r is None:
                    if l is not None or r is not None:
                        errors.append({"role":role,"arm":arm,"field":field})
                    continue
                if not (type(l) in (float,int) and type(r) in (float,int)
                        and math.isfinite(l) and math.isfinite(r)):
                    raise ValueError("L5_NONFINITE_COMPARABLE_QUALITY")
                compared+=1
                if abs(l-r)>1e-12:
                    errors.append({"role":role,"arm":arm,"field":field,
                                   "linux":l,"windows":r})
    if errors:
        for e in errors[:12]:
            print("L5_NATIVE_SOURCE_OR_OUTPUT_DRIFT "+json.dumps(e,sort_keys=True))
        raise ValueError("L5_FROZEN_ALL_NATIVE_ACCEPTANCE_FAIL")
    return {
        "schema":"forge.optimizer.language.l5.native-subword-reconcile.v1",
        "three_corpus_role_digests":"3_OF_3_EXACT",
        "all_18_model_role_prediction_digests":"18_OF_18_EXACT",
        "reconciled_quality_scalars":compared,
        "scientific_first_use":False,
        "model_pareto_qualified":False,
        "status":"L5_PUBLIC_EXTERNAL_SUBWORD_ENGINEERING_REPRODUCIBLE"
    }


def main():
    if len(sys.argv)!=4:
        raise SystemExit("usage: compare.py linux.json windows.json output.json")
    with open(sys.argv[1],encoding="utf-8") as f: l=json.load(f)
    with open(sys.argv[2],encoding="utf-8") as f: w=json.load(f)
    output=reconcile(l,w)
    path=Path(sys.argv[3])
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(output,sort_keys=True,indent=2)+"\n",
                    encoding="utf-8")
    print("L5_EXTERNAL_SOURCE_AND_ROLE_SHA=3_OF_3_PASS")
    print("L5_ALL_NATIVE_PREDICTIONS=18_OF_18_EXACT")
    print("L5_QUALITY_COMPARE_SCALARS="+str(output["reconciled_quality_scalars"]))
    print("L5_INDEPENDENT_SCIENTIFIC_GO=NOT_ELIGIBLE")


if __name__=="__main__":
    main()

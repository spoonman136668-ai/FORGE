"""L6 independent pure-stdlib cross-OS source + learned model comparison.

Count models require exact word prediction digests and quality scalars.
Numerical float RNN may vary cross-native, so .01 exact-quality tolerance
is FROZEN before DEV, while original role/source identities match bytewise.
"""
import json
import math
from pathlib import Path
import sys

ROLES=("L6_TRAIN","L6_SELECT","L6_DEV")
COUNTS={"L6_TRAIN":900,"L6_SELECT":200,"L6_DEV":240}
ARMS=("CLOSED_PREFIX","FLAT_SUFFIX","CHAR_TRIGRAM_BEAM",
      "HIERARCHICAL_STEM_AFFIX","HIERARCHICAL_NO_AFFIX_ABLATION",
      "RNN_CHAR_H20")
SCHEMA="forge.optimizer.language.l6.public-hierarchy-rnn-receipt.v1"
SOURCE_GIT="20c3737a33af2501e4c0597285ad630ef42e8e46"
QUALITY=("full_word_exact","unseen_gold_exact",
         "normalized_edit_distance","position_character_accuracy",
         "novel_predicted_form_fraction","prefix_violation",
         "prefix_only_abstention")


def check(linux,windows):
    for d in (linux,windows):
        if (d.get("schema")!=SCHEMA or
            d.get("source_git_blob_sha1")!=SOURCE_GIT or
            d.get("old_L1_L5_dev_consumed")!=0 or
            d.get("Q21_FSA_HELD_scientific_first_use") is not False or
            d.get("all_active_research_unchanged") is not True or
            d.get("no_scientific_promotion") is not True or
            d.get("external_blinded_science") is not False or
            d.get("fully_computation_matched_controls") is not False or
            d.get("actual_hardware_parallel_generation") is not False or
            d.get("numpy_version")!="2.1.3"):
            raise ValueError("L6_RESEARCH_AUTHORITY_OR_SOURCE_CUSTODY_DRIFT")
        if (d.get("role_count")!=COUNTS or
            set(d.get("source_roles_sha256",{}))!=set(ROLES) or
            set(d.get("model_resources",{}))!=set(ARMS) or
            set(d.get("evaluations",{}))!=set(ROLES)):
            raise ValueError("L6_FROZEN_SOURCE_MODEL_COVERAGE")
    if linux["source_raw_sha256"]!=windows["source_raw_sha256"] or \
            linux["source_roles_sha256"]!=windows["source_roles_sha256"]:
        raise ValueError("L6_CROSS_OS_ORIGINAL_CORPUS_OR_ROLE_SHA_DRIFT")
    mistakes=[]
    compared=0
    for arm in ARMS:
        x,y=linux["model_resources"][arm],windows["model_resources"][arm]
        for field in ("checkpoint_bytes_including_optimizer_if_any",
                      "parameter_count","selected_seed",
                      "optimizer_updates_selected","conceptual_serial_steps"):
            if x.get(field)!=y.get(field):
                mistakes.append({"arm":arm,"field":field,
                                 "linux":x.get(field),"windows":y.get(field)})
        if arm!="RNN_CHAR_H20" and x["checkpoint_sha256"]!=y["checkpoint_sha256"]:
            mistakes.append({"arm":arm,"field":"frozen_checkpoint_sha256"})
    for role in ROLES:
        a,b=linux["evaluations"][role],windows["evaluations"][role]
        if set(a)!=set(ARMS) or set(b)!=set(ARMS):
            raise ValueError("L6_MISSING_EVALUATION_ARM")
        for arm in ARMS:
            l,w=a[arm],b[arm]
            for fld in ("examples","unseen_gold_count","unseen_gold_hits"):
                if l.get(fld)!=w.get(fld):
                    mistakes.append({"role":role,"arm":arm,"field":fld})
            if l["examples"]!=COUNTS[role]:
                raise ValueError("L6_EXAMPLE_COUNT_DRIFT")
            if arm!="RNN_CHAR_H20" and \
                    l["predicted_words_sha256"]!=w["predicted_words_sha256"]:
                mistakes.append({"role":role,"arm":arm,"field":"word_output_sha256"})
            for field in QUALITY:
                x,y=l.get(field),w.get(field)
                if x is None or y is None:
                    if x is not None or y is not None:
                        mistakes.append({"role":role,"arm":arm,"field":field})
                    continue
                if not (type(x) in (float,int) and type(y) in (float,int)
                        and math.isfinite(x) and math.isfinite(y)):
                    raise ValueError("L6_NONFINITE_QUALITY")
                compared+=1
                if abs(x-y)>(.01 if arm=="RNN_CHAR_H20" else 1e-12):
                    mistakes.append({"role":role,"arm":arm,"field":field,
                                     "linux":x,"windows":y})
    if mistakes:
        for m in mistakes[:10]:
            print("L6_NATIVE_REPRODUCIBILITY_DRIFT "+json.dumps(m,sort_keys=True))
        raise ValueError("L6_FROZEN_NUMERIC_OR_SOURCE_RECONCILIATION_FAIL")
    return {
        "schema":"forge.optimizer.language.l6.independent-cross-native.v1",
        "original_external_git_blob_verified":SOURCE_GIT,
        "three_new_source_role_identities":"3_OF_3_EXACT",
        "public_model_by_role_coverage":"18_OF_18_PASS",
        "native_quality_comparisons":compared,
        "rnn_frozen_tolerance":.01,
        "scientific_first_use":False,
        "native_integration":False,
        "status":"L6_PUBLIC_HIERARCHICAL_SUBWORD_NATIVE_ENGINEERING_REPRODUCIBLE"
    }


def main():
    if len(sys.argv)!=4:
        raise SystemExit("usage: compare.py linux.json windows.json result.json")
    with open(sys.argv[1],encoding="utf-8") as fh:
        a=json.load(fh)
    with open(sys.argv[2],encoding="utf-8") as fh:
        b=json.load(fh)
    outcome=check(a,b)
    path=Path(sys.argv[3])
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(outcome,sort_keys=True,indent=2)+"\n",
                    encoding="utf-8")
    print("L6_NEW_EXTERNAL_SOURCE_ROLES=3_OF_3_EXACT")
    print("L6_PUBLIC_CONTROL_AND_HIERARCHICAL_MODELS=18_OF_18_RECONCILED")
    print("L6_EXISTING_NCI_ITD_BIO_Q21_FORGE_WORK=ISOLATED")
    print("L6_SCIENTIFIC_GO=NOT_ELIGIBLE")


if __name__=="__main__":
    main()

"""L1 source-only receipt; do not train or score a language candidate."""
import hashlib
import json
from pathlib import Path
import sys
import time

from public_source import (
    ROLES,COUNTS,public_role,digest,semantic_holdout,canonical
)


def receipt():
    started=time.process_time()
    roles={}
    all_tuples={}
    for role in ROLES:
        batch=public_role(role)
        structs={tuple(s) for s,_ in batch}
        roles[role]={
            "source_sha256":digest(role),
            "records":len(batch),
            "distinct_semantic_tuples":len(structs),
            "heldout_semantic_tuples":sum(semantic_holdout(s)
                                         for s,_ in batch),
            "canonical_source_bytes":len(canonical(batch)),
        }
        all_tuples[role]=structs
    if any(roles[r]["records"]!=COUNTS[r] or
           roles[r]["distinct_semantic_tuples"]!=COUNTS[r] for r in ROLES):
        raise ValueError("L1_SOURCE_ROLE_CARDINALITY_FAIL")
    fit=all_tuples["L1_FIT_TRAIN"]|all_tuples["L1_FIT_SELECT"]
    dev=all_tuples["L1_PUBLIC_DEV_COMPOSE"]
    if fit&dev or all_tuples["L1_FIT_TRAIN"] & all_tuples["L1_FIT_SELECT"]:
        raise ValueError("L1_SEMANTIC_COHORT_IDENTITY_LEAK")
    if roles["L1_FIT_TRAIN"]["heldout_semantic_tuples"] or \
            roles["L1_FIT_SELECT"]["heldout_semantic_tuples"] or \
            roles["L1_PUBLIC_DEV_COMPOSE"]["heldout_semantic_tuples"]!=64:
        raise ValueError("L1_HOLDOUT_CONTRACT_FAIL")
    return {
        "schema":"forge.optimizer.language.l1.sourceonly-receipt.v1",
        "source_generation_cpu_s":time.process_time()-started,
        "governance":"ADDITIVE_NON_DISRUPTIVE",
        "existing_research_priority_changed":False,
        "candidate_model_trained":False,
        "candidate_quality_evaluated":False,
        "scientific_first_use":False,
        "protected_roles_consumed":0,
        "native_wingless_yggdrasil_integration":False,
        "new_controller_or_dispatch":False,
        "roles":roles,
    }


def main():
    if len(sys.argv)!=2:
        raise SystemExit("usage: qualify_source.py /path/receipt.json")
    result=receipt()
    path=Path(sys.argv[1])
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(result,sort_keys=True,indent=2)+"\n",
                    encoding="utf-8")
    for role in ROLES:
        info=result["roles"][role]
        print("L1_PUBLIC_SOURCE_ROLE="+role+
              " COUNT="+str(info["records"])+
              " SHA256="+info["source_sha256"])
    print("L1_FIT_SELECT_DEV_SEMANTIC_LEAKAGE=ZERO")
    print("L1_NEW_LANGUAGE_CANDIDATE_TRAINED=NO")
    print("L1_EXISTING_SCIENTIFIC_FRONTIER_UNCHANGED=PASS")
    print("L1_SOURCE_ONLY_RECEIPT="+str(path))


if __name__=="__main__":
    main()

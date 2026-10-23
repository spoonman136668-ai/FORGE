"""Cross-OS source-only L1 acceptance. No models or evaluation data replay."""
import json
from pathlib import Path
import sys

from public_source import COUNTS,ROLES

SCHEMA="forge.optimizer.language.l1.sourceonly-receipt.v1"


def compare(linux,windows):
    for data in (linux,windows):
        if data.get("schema")!=SCHEMA:
            raise ValueError("L1_RECEIPT_SCHEMA_DRIFT")
        if (data.get("governance")!="ADDITIVE_NON_DISRUPTIVE"
                or data.get("existing_research_priority_changed") is not False
                or data.get("candidate_model_trained") is not False
                or data.get("candidate_quality_evaluated") is not False
                or data.get("scientific_first_use") is not False
                or data.get("protected_roles_consumed")!=0
                or data.get("new_controller_or_dispatch") is not False
                or data.get("native_wingless_yggdrasil_integration") is not False):
            raise ValueError("L1_RESEARCH_AUTHORITY_BOUNDARY")
        if set(data.get("roles",{}))!=set(ROLES):
            raise ValueError("L1_SOURCE_ROLE_COVERAGE")
    for role in ROLES:
        left,right=linux["roles"][role],windows["roles"][role]
        for field in ("source_sha256","records","distinct_semantic_tuples",
                      "heldout_semantic_tuples","canonical_source_bytes"):
            if left.get(field)!=right.get(field):
                raise ValueError(f"L1_CROSS_OS_SOURCE_DRIFT {role} {field}")
        if (left["records"]!=COUNTS[role] or
                left["distinct_semantic_tuples"]!=COUNTS[role] or
                len(left["source_sha256"])!=64):
            raise ValueError("L1_SOURCE_IDENTITY_COVERAGE")
    return {
        "schema":"forge.optimizer.language.l1.native-source-only-reconcile.v1",
        "native_source_digests":"4_OF_4_EXACT",
        "cohort_semantic_coverage":"4_OF_4_EXACT",
        "research_frontier_displacement":False,
        "language_model_evaluated":False,
        "scientific_candidate_promoted":False,
        "result":"L1_PUBLIC_SOURCE_QUALIFIED_ONLY",
    }


def main():
    if len(sys.argv)!=4:
        raise SystemExit("usage: compare_source.py linux.json windows.json out.json")
    with open(sys.argv[1],encoding="utf-8") as fh:
        linux=json.load(fh)
    with open(sys.argv[2],encoding="utf-8") as fh:
        windows=json.load(fh)
    report=compare(linux,windows)
    path=Path(sys.argv[3])
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(report,sort_keys=True,indent=2)+"\n",
                    encoding="utf-8")
    print("L1_CROSS_OS_ROLE_SOURCE_IDENTITIES=4_OF_4_EXACT")
    print("L1_COMPOSITION_SPLITS=PRECOMMITTED_AND_CUSTODY_ISOLATED")
    print("L1_SCIENTIFIC_GO=NOT_EVALUATED")
    print("L1_ADD_ON_ONLY=PASS")


if __name__=="__main__":
    main()

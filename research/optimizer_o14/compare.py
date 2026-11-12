"""O14 independent fail-closed public zero-shot cross-platform acceptance.

Nine frozen role-family SHA256 source identities must match byte for byte;
all 40 model×evaluation-family loss values must agree <=1e-6. Compare
without fitting, selecting, or reopening prior public DEV observations.
"""
import json
import math
from pathlib import Path
import sys
from public_source import FIT_FAMILIES,TRANSFER_FAMILIES,ROLE_COUNTS
from runner import ARMS

TOLERANCE=1e-6
SCHEMA="forge.optimizer.o14.public-structural-zero-shot-receipt.v1"


def reconcile(a,b):
    families=FIT_FAMILIES+TRANSFER_FAMILIES
    expected_shas={
        f"{family}:{role}"
        for role,valid in ROLE_COUNTS.items() for family in valid
    }
    for data in (a,b):
        if data.get("schema")!=SCHEMA or \
                data.get("external_independent_scientific_custody") is not False or \
                data.get("FSA_protected_roles_consumed")!=0 or \
                data.get("previous_O1_O13_dev_roles_consumed")!=0 or \
                data.get("scientific_candidate_promoted") is not False or \
                tuple(data.get("public_fit_family_whitelist",[]))!=FIT_FAMILIES or \
                tuple(data.get("public_transfer_family_blacklist_during_fit",[]))!=TRANSFER_FAMILIES:
            raise ValueError("O14_SOURCE_SCIENTIFIC_CUSTODY_VIOLATION")
        if set(data.get("source_role_sha256",{}))!=expected_shas or \
                len(data["source_role_sha256"])!=9:
            raise ValueError("O14_PUBLIC_SOURCE_COVERAGE")
        if set(data.get("evaluations",{}))!=set(families):
            raise ValueError("O14_ALL_FAMILY_EVALUATION_COVERAGE")
        if set(data.get("fit_model_evidence",{}))!=set(ARMS):
            raise ValueError("O14_MODEL_FIT_EVIDENCE_COVERAGE")
        if (data.get("fit_episodes")!=48
                or data.get("select_episodes")!=16):
            raise ValueError("O14_FROZEN_TRAIN_SELECT_BUDGET")
    if a["source_role_sha256"]!=b["source_role_sha256"]:
        raise ValueError("O14_CROSS_OS_SOURCE_ROLE_DRIFT")
    if a["interleaved_fit_sha256"]!=b["interleaved_fit_sha256"] or \
            a["interleaved_select_sha256"]!=b["interleaved_select_sha256"]:
        raise ValueError("O14_INTERLEAVED_TRAIN_SOURCE_DRIFT")
    errors=[]
    for family in families:
        x,y=a["evaluations"][family],b["evaluations"][family]
        expected_role=("O14_INDOMAIN_DEV" if family in FIT_FAMILIES
                       else "O14_ZERO_SHOT_TRANSFER")
        if x["evaluation_role"]!=expected_role or y["evaluation_role"]!=expected_role:
            raise ValueError("O14_INVALID_FAMILY_ROLE_ASSIGNMENT")
        if x["source_sha256"]!=y["source_sha256"]:
            raise ValueError("O14_SOURCE_SHA_IN_EVALUATION_DRIFT")
        if set(x.get("arms",{}))!=set(ARMS) or set(y.get("arms",{}))!=set(ARMS):
            raise ValueError("O14_8_ARM_COVERAGE")
        for arm in ARMS:
            lv=x["arms"][arm]["nextbit_nll"]
            wv=y["arms"][arm]["nextbit_nll"]
            if not (type(lv) in (float,int) and type(wv) in (float,int)
                    and math.isfinite(lv) and math.isfinite(wv)):
                raise ValueError("O14_NONFINITE_NLL")
            if abs(lv-wv)>TOLERANCE:
                errors.append({"family":family,"arm":arm,
                               "linux":lv,"windows":wv,
                               "absolute_difference":abs(lv-wv)})
    if errors:
        for detail in errors:
            print("O14_CROSS_OS_DEV_NLL_DRIFT "+json.dumps(detail,sort_keys=True))
        raise ValueError("O14_FROZEN_CROSS_OS_NLL_TOLERANCE_FAIL")
    return {
        "schema":"forge.optimizer.o14.independent-zero-shot-native-reconciliation.v1",
        "source_role_digests":"9_OF_9_EXACT",
        "model_evaluation_nll":"40_OF_40_WITHIN_1E-6",
        "scientific_first_use":False,
        "externally_independent_custody":False,
        "model_promoted":False,
        "status":"O14_PUBLIC_ZERO_SHOT_NATIVE_REPRODUCIBILITY_PASS_NOT_SCIENTIFIC_GO",
    }


def main():
    if len(sys.argv)!=4:
        raise SystemExit("usage: compare.py linux.json windows.json result.json")
    with open(sys.argv[1],encoding="utf-8") as fh: linux=json.load(fh)
    with open(sys.argv[2],encoding="utf-8") as fh: windows=json.load(fh)
    outcome=reconcile(linux,windows)
    path=Path(sys.argv[3])
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(outcome,sort_keys=True,indent=2)+"\n",
                    encoding="utf-8")
    print("O14_NEW_PUBLIC_SOURCE_DIGESTS=9_OF_9_PASS")
    print("O14_INDOMAIN_AND_STRUCTURAL_TRANSFER_NLL=40_OF_40_PASS")
    print("O14_SCIENTIFIC_FIRST_USE=ZERO")
    print("O14_CROSS_OS_ACCEPTANCE=PASS")


if __name__=="__main__":
    main()

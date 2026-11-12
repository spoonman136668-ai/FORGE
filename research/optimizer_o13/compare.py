"""O13 mandatory independent native Windows/Linux public result comparison.

Fail closed if any fresh source digest or any 4 x 7 prospectively frozen
DEV mean next-bit NLL drifts by more than 1e-6. No tolerance adjustment,
post hoc selection or retroactive scientific promotion.
"""
import json
import math
from pathlib import Path
import sys

from public_source import FAMILIES,ROLES
from runner import ARMS

TOL=1e-6


def reconcile(linux,windows):
    for row in (linux,windows):
        if row.get("schema")!="forge.optimizer.o13.public-predictive-credit-receipt.v1" or \
                row.get("scientific_first_use") is not False or \
                row.get("FSA_Q21_PROTECTED_ROLES_CONSUMED")!=0 or \
                row.get("old_O1_O12_DEVELOPMENT_ROLES_CONSUMED")!=0:
            raise ValueError("O13_CUSTODY_OR_RECEIPT_SCHEMA_VIOLATION")
    if set(linux["families"])!=set(FAMILIES) or \
            set(windows["families"])!=set(FAMILIES):
        raise ValueError("O13_FAMILY_COVERAGE_VIOLATION")
    deltas=[]
    for family in FAMILIES:
        a,b=linux["families"][family],windows["families"][family]
        if set(a["source_role_sha256"])!=set(ROLES) or \
                set(b["source_role_sha256"])!=set(ROLES):
            raise ValueError("O13_SOURCE_ROLE_COVERAGE")
        for role in ROLES:
            if (a["source_role_sha256"][role]!=b["source_role_sha256"][role]
                or len(a["source_role_sha256"][role])!=64):
                raise ValueError("O13_PUBLIC_SOURCE_DIGEST_DRIFT "+family+" "+role)
        if set(a["arms"])!=set(ARMS) or set(b["arms"])!=set(ARMS):
            raise ValueError("O13_MODEL_ARM_COVERAGE")
        for arm in ARMS:
            x=a["arms"][arm]["public_dev_nextbit_nll"]
            y=b["arms"][arm]["public_dev_nextbit_nll"]
            if not (type(x) in (int,float) and type(y) in (int,float)
                    and math.isfinite(x) and math.isfinite(y)):
                raise ValueError("O13_NONFINITE_NLL")
            if abs(x-y)>TOL:
                deltas.append({"family":family,"arm":arm,
                               "linux":x,"windows":y,"gap":abs(x-y)})
    if deltas:
        for x in deltas:
            print("O13_CROSS_OS_NLL_DRIFT "+json.dumps(x,sort_keys=True))
        raise ValueError("O13_PRECOMMITTED_NUMERIC_ACCEPTANCE_FAIL")
    return {
        "schema":"forge.optimizer.o13.cross-os-qualification.v1",
        "all_public_role_source_digests":"12_OF_12_EXACT",
        "all_public_dev_arm_losses":"28_OF_28_WITHIN_1E-6",
        "scientific_go":False,
        "model_promoted":False,
        "status":"O13_DEV_NUMERIC_REPRODUCIBILITY_PASS_NOT_SCIENCE",
    }


def main():
    if len(sys.argv)!=4:
        raise SystemExit("usage: compare.py linux.json windows.json report.json")
    with open(sys.argv[1],encoding="utf-8") as f: linux=json.load(f)
    with open(sys.argv[2],encoding="utf-8") as f: windows=json.load(f)
    report=reconcile(linux,windows)
    dest=Path(sys.argv[3])
    dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(report,sort_keys=True,indent=2)+"\n",
                    encoding="utf-8")
    print("O13_SOURCE_DIGESTS=12_OF_12_PASS")
    print("O13_ALL_DEV_NLL_CROSS_OS=28_OF_28_PASS")
    print("O13_SCIENTIFIC_FIRST_USE=ZERO")
    print("O13_CROSS_OS_COMPARISON=PASS")


if __name__=="__main__":
    main()

"""O10 qualification-only independent native receipt reconciliation.

The immutable prospective O10 experiment, source roles, hyperparameters and
scientific datasets are UNCHANGED. This script runs AFTER the two separate
native OS jobs and fail-closes if the public results violate their already
preregistered cross-OS identity and numerical acceptance criteria.
"""
import json
import math
import sys

from public_source import FAMILIES,ROLES
from runner import ARMS

SCHEMA="forge.optimizer.o10.public-dev-receipt.v1"
NLL_TOLERANCE=1e-6


def reconcile(linux,windows):
    problems=[]
    if linux.get("schema")!=SCHEMA or windows.get("schema")!=SCHEMA:
        return ["O10_INVALID_RECEIPT_SCHEMA"]
    if linux.get("science_protected_first_use") is not False or \
            windows.get("science_protected_first_use") is not False:
        problems.append("O10_PROTECTED_FIRST_USE_RECEIPT")
    lf,wf=linux.get("families",{}),windows.get("families",{})
    if set(lf)!=set(FAMILIES) or set(wf)!=set(FAMILIES):
        problems.append("O10_INCOMPLETE_FAMILY_COVERAGE")
        return problems
    for family in FAMILIES:
        l,w=lf[family],wf[family]
        if set(l.get("source_role_sha256",{}))!=set(ROLES) or \
                set(w.get("source_role_sha256",{}))!=set(ROLES):
            problems.append(f"O10_SOURCE_ROLE_MISSING {family}")
            continue
        for role in ROLES:
            la=l["source_role_sha256"][role]
            wa=w["source_role_sha256"][role]
            if not (isinstance(la,str) and len(la)==64 and la==wa):
                problems.append(f"O10_ROLE_SOURCE_DRIFT {family} {role}")
        al,aw=l.get("arms",{}),w.get("arms",{})
        if set(al)!=set(ARMS) or set(aw)!=set(ARMS):
            problems.append(f"O10_EIGHT_ARM_COVERAGE_DRIFT {family}")
            continue
        for arm in ARMS:
            ln=al[arm].get("public_dev_query_nll")
            wn=aw[arm].get("public_dev_query_nll")
            if not (type(ln) in (float,int) and type(wn) in (float,int)
                    and math.isfinite(ln) and math.isfinite(wn)):
                problems.append(f"O10_INVALID_NATIVE_NLL {family} {arm}")
            elif abs(ln-wn)>NLL_TOLERANCE:
                problems.append(
                    f"O10_CROSS_OS_NLL_DRIFT family={family} arm={arm} "
                    f"linux={ln:.12f} windows={wn:.12f} "
                    f"abs_difference={abs(ln-wn):.12f} "
                    f"frozen_limit={NLL_TOLERANCE}"
                )
    return problems


def main():
    if len(sys.argv)!=3:
        raise SystemExit("USAGE: cross_os_compare.py linux.json windows.json")
    with open(sys.argv[1],encoding="utf-8") as f:
        linux=json.load(f)
    with open(sys.argv[2],encoding="utf-8") as f:
        windows=json.load(f)
    problems=reconcile(linux,windows)
    if problems:
        for problem in problems:
            print(problem,flush=True)
        print("O10_PUBLIC_NATIVE_CROSS_OS_ACCEPTANCE=FAIL",flush=True)
        raise SystemExit(1)
    print("O10_PUBLIC_SOURCE_DIGESTS=12_OF_12_IDENTICAL")
    print("O10_PUBLIC_NLL=32_OF_32_WITHIN_FROZEN_1E-6")
    print("O10_PUBLIC_NATIVE_CROSS_OS_ACCEPTANCE=PASS")


if __name__=="__main__":
    main()

"""L8 E2E public development cohorts disjoint from all 180 exposed L7 DEV rows.

TRAIN intentionally shares EXACT 700 original L7 supervised MRs to isolate
attribution instead of changing model and data simultaneously. SELECT/DEV
are next unconsumed E2E public development canonical MRs. Official E2E
test remains entirely untouched. Raw files are verified BEFORE parsing.
"""
import hashlib
from pathlib import Path

from l7_source_original import (
    FILES,REV,BASE,verify,acquire,parse_mr,parse_csv,identity,
    cohorts as old_l7_cohorts,canonical,
)

ROLES=("L8_TRAIN","L8_AUDIT_SELECT","L8_AUDIT_DEV")
COUNTS={"L8_TRAIN":700,"L8_AUDIT_SELECT":80,"L8_AUDIT_DEV":160}


def cohorts(trainraw,devraw):
    prior=old_l7_cohorts(trainraw,devraw)
    train=prior["L7_TRAIN"]
    if len(train)!=700 or len(prior["L7_SELECT"])!=80 or len(prior["L7_DEV"])!=100:
        raise ValueError("L8_ORIGINAL_EXPOSED_L7_SOURCE_BOUNDARY_DRIFT")
    old_keys={identity(r["mr"]) for group in prior.values() for r in group}
    if len(old_keys)!=880:
        raise ValueError("L8_L7_ORIGINAL_180_SOURCE_IDENTITY_DRIFT")
    public_select=[]
    public_dev=[]
    new_keys=set()
    for row in parse_csv(devraw,"devset.csv"):
        ident=identity(row["mr"])
        if ident in old_keys or ident in new_keys:
            continue
        new_keys.add(ident)
        dest=public_select if len(public_select)<COUNTS["L8_AUDIT_SELECT"] else public_dev
        dest.append(row)
        if len(public_dev)==COUNTS["L8_AUDIT_DEV"]:
            break
    result={
        "L8_TRAIN":tuple(train),
        "L8_AUDIT_SELECT":tuple(public_select),
        "L8_AUDIT_DEV":tuple(public_dev),
    }
    for role,items in result.items():
        if len(items)!=COUNTS[role]:
            raise ValueError("L8_FROZEN_FRESH_PUBLIC_ROLE_SHORTAGE_"+role)
    old_dev_ids={identity(r["mr"]) for r in (
        prior["L7_SELECT"]+prior["L7_DEV"])}
    for role in ("L8_AUDIT_SELECT","L8_AUDIT_DEV"):
        if any(identity(r["mr"]) in old_dev_ids for r in result[role]):
            raise ValueError("L8_OLD_L7_EXPOSED_DEV_REUSE")
    return result,prior


def load(directory):
    raw={name:(Path(directory)/name).read_bytes() for name in FILES}
    identities={name:verify(data,name) for name,data in raw.items()}
    fresh,original=cohorts(raw["trainset.csv"],raw["devset.csv"])
    return identities,fresh,original


def digest(items):
    return hashlib.sha256(canonical(items)).hexdigest()

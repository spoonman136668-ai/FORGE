#!/usr/bin/env python3
"""NCI-04G7C read-only exact upstream source-intake validator.

Validates public third-party upstream Git object identities, never runs a
candidate or evaluator, downloads a private dataset, consumes first-use, grants
authority or claims a scientific result.
"""
from __future__ import annotations
import argparse
import copy
import json
from pathlib import Path
import re
import subprocess

CATALOG = Path(__file__).with_name("external_sources.json")
SHA40 = re.compile(r"[a-f0-9]{40}\Z")
REQUIRED = {
    "Wingless": ("google/uuid",
                 "2d3c2a9cc518326daf99a383f07c4d3c44317e4d"),
    "Yggdrasil": ("Farama-Foundation/Minigrid",
                  "7f5853792ea7f04f75614661006d87fcf949f26d"),
}

class AdmissionBlocked(ValueError):
    pass

def require(condition, reason):
    if not condition:
        raise AdmissionBlocked("G7C_SOURCE_FAIL_CLOSED_" + reason)

def parse(catalog: dict) -> list[dict]:
    require(type(catalog) is dict
            and catalog.get("schema") ==
            "forge.nci04g7c.external-native-source-intake.v1",
            "SCHEMA")
    require(catalog.get("gate") == "NCI-04G7C"
            and catalog.get("status") ==
            "EXTERNAL_SOURCE_CANDIDATES_NOT_SCIENTIFICALLY_ADMITTED",
            "GATE_OR_STATUS")
    firstuse = catalog.get("first_use")
    require(type(firstuse) is dict
            and firstuse.get("scientific_originals") == 0
            and firstuse.get("independently_admitted") is False
            and firstuse.get("one_shot_intent_issued") is False
            and firstuse.get("protected_holdouts_opened") is False
            and firstuse.get("source_family_eval_started") is False,
            "FIRST_USE_CLOSED")
    isolation = catalog.get("isolation")
    require(type(isolation) is dict
            and all(isolation.get(k) is True for k in (
                "no_ckb_plane", "no_paid_api", "no_model_execution",
                "no_controller_dispatch", "no_accepted_ref_mutation",
                "no_new_sci_authority")),
            "SOURCE_CUSTODY_ISOLATION")
    sources = catalog.get("source_candidates")
    require(type(sources) is list and len(sources) == 2, "CANDIDATE_COUNT")
    require({x.get("lane") for x in sources} == set(REQUIRED),
            "LANE_IDENTITY")
    for x in sources:
        repo, commit = REQUIRED[x["lane"]]
        require(x.get("repo") == repo and x.get("commit") == commit
                and SHA40.fullmatch(commit) is not None,
                "SOURCE_REPO_OR_COMMIT")
        require(x.get("eligible_source_identity") is True
                and x.get("eligible_protected_firstuse") is False,
                "UNSUPPORTED_SCIENTIFIC_ADMISSION")
        require(type(x.get("firstuse_blockers")) is list
                and len(x["firstuse_blockers"]) >= 3,
                "FIRSTUSE_BLOCKERS_MISSING")
        files = x.get("files")
        require(type(files) is list and len(files) == 3
                and len({z.get("path") for z in files}) == 3,
                "BLOB_SET")
        for f in files:
            name, digest, size = f.get("path"), f.get("blob_sha"), f.get("size")
            require(type(name) is str and name and not name.startswith("/")
                    and ".." not in name.split("/")
                    and type(digest) is str and SHA40.fullmatch(digest)
                    and type(size) is int and size > 0,
                    "BLOB_DESCRIPTOR")
    old = catalog.get("consumed_development_precedent", {})
    require(old.get("repo") == "rr-learning/CausalWorld"
            and old.get("commit") == "1045277101a92c506db42704da28f6e7227d401b"
            and old.get("prior_study") == "LCRM01-K4C"
            and old.get("disposition") ==
            "AUTHENTIC_OTHER_WORKSTREAM_DEVELOPMENT_USED_NOT_FRESH_PROTECTED_FIRST_USE",
            "CONSUMED_SOURCE_MISREPRESENTED")
    decision = catalog.get("acceptance", {})
    require(decision.get("scientific_promotion") == "DENIED"
            and decision.get("complete_cpu_and_peak_rss") == "NOT_MEASURED"
            and decision.get("source_sha_verification_only") is True
            and decision.get("zero_hard_false_positive_evidence") ==
            "NOT_EVALUATED"
            and decision.get("baseline_and_learned_control_parity") ==
            "NOT_EVALUATED",
            "EVALUATION_FALSE_CLAIM")
    return sources

def _git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), *args], capture_output=True, text=True,
        timeout=15, check=True)
    return result.stdout.strip()

def verify_external(catalog: dict, lane: str, checkout: Path) -> dict:
    sources = parse(catalog)
    require(lane in REQUIRED, "UNKNOWN_LANE")
    spec = next(s for s in sources if s["lane"] == lane)
    require(checkout.is_dir() and not checkout.is_symlink(),
            "EXTERNAL_CHECKOUT_ABSENT")
    require(_git(checkout, "rev-parse", "HEAD") == spec["commit"],
            "UPSTREAM_EXACT_COMMIT_DRIFT")
    hashes = {}
    for item in spec["files"]:
        rel = item["path"]
        f = checkout / rel
        require(f.is_file() and not f.is_symlink()
                and _git(checkout, "rev-parse", "HEAD:" + rel) ==
                item["blob_sha"] and f.stat().st_size == item["size"],
                "UPSTREAM_GIT_BLOB_DRIFT")
        hashes[rel] = item["blob_sha"]
    require(_git(checkout, "status", "--porcelain", "--untracked-files=all") == "",
            "UPSTREAM_WORKTREE_DIRTY")
    return {"lane": lane, "source": spec["repo"],
            "source_commit": spec["commit"], "verified_blobs": hashes,
            "upstream_source_bytes":"EXACT",
            "independent_holdout_and_firstuse":"NOT_ADMITTED"}

def selftest(catalog: dict) -> None:
    parse(catalog)
    flipped = copy.deepcopy(catalog)
    flipped["source_candidates"][0]["eligible_protected_firstuse"] = True
    try:
        parse(flipped)
    except AdmissionBlocked:
        pass
    else:
        raise AdmissionBlocked("FORGED_FIRSTUSE_ADMISSION_ACCEPTED")
    flipped = copy.deepcopy(catalog)
    flipped["consumed_development_precedent"]["disposition"] = "UNUSED"
    try:
        parse(flipped)
    except AdmissionBlocked:
        pass
    else:
        raise AdmissionBlocked("CONSUMED_COHORT_RELABELED")
    flipped = copy.deepcopy(catalog)
    flipped["acceptance"]["scientific_promotion"] = "AUTHORIZED"
    try:
        parse(flipped)
    except AdmissionBlocked:
        pass
    else:
        raise AdmissionBlocked("UNSUPPORTED_SCIENTIFIC_PROMOTION")
    print("NCI04G7C_TAMPER_NEGATIVES=3_PASS")

def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--wingless-checkout", type=Path)
    p.add_argument("--yggdrasil-checkout", type=Path)
    args = p.parse_args()
    catalog = json.loads(CATALOG.read_text("utf-8"))
    selftest(catalog)
    if args.wingless_checkout is None or args.yggdrasil_checkout is None:
        print("NCI04G7C_SOURCE_IDENTITY=NOT_EXTERNALLY_CHECKED")
        print("NCI04G7C_SCIENTIFIC_ADMISSION=BLOCKED")
        return
    for lane, checkout in (
            ("Wingless", args.wingless_checkout),
            ("Yggdrasil", args.yggdrasil_checkout)):
        result = verify_external(catalog, lane, checkout)
        print("NCI04G7C_SOURCE_BLOBS_VERIFIED=" +
              json.dumps(result,sort_keys=True,separators=(",",":")))
    print("NCI04G7C_EXTERNAL_SOURCE_IDENTITY=PASS")
    print("NCI04G7C_SCIENTIFIC_ADMISSION=BLOCKED")
    print("NCI04G7C_PROTECTED_FIRST_USE=ZERO")

if __name__=="__main__":
    try:
        main()
    except (AdmissionBlocked, OSError, subprocess.SubprocessError, ValueError) as e:
        print("NCI04G7C_SOURCE_INTAKE=BLOCKED " + str(e))
        raise SystemExit(1)

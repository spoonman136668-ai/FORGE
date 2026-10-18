"""Independent provider-object custody audit for F124-BI (read-only).

Independent execution via GitHub-hosted Actions with a fresh checkout and
GitHub REST /git object reads; no scientific first use. Provider proof covers
immutable Git object identity and chronology, NOT external independent
source origination, novelty, or historic consumed-source disjointness.
"""
from __future__ import annotations

import argparse
import ast
import base64
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
DIR = Path(__file__).resolve().parent
REPO = "spoonman136668-ai/FORGE"
BH_HEAD = "0c7e2fdcdcc6ee85873657424aaa85c59e0de1ed"
METHOD = DIR / "f124bi-frozen-method.json"
BIRTHS = {
    "protocol": ("c906adaca213327ab4fdf2b1deaeae54088827a8",
                 "38d489da4b1469896a64ac3e744e9ad9521aebdd",
                 "research/north-star-transfer/f124bh-frozen-protocol.json"),
    "U": ("c62b33a830f61a99f9d28cb88ffec04ef32b0d9a",
          "6fe6b5bbece936bb0dfca97c0a8b454918067a19",
          "research/north-star-transfer/f124bh_u_family.py"),
    "R": ("fa623739ebf1f2352d5636acd0b39614a38b688d",
          "02997a32ffb3fec60073b3b725cfd0aecae4b1f8",
          "research/north-star-transfer/f124bh_r_family.py"),
}
MODEL_BLOBS = {
    "nativeevidence/f124az_joint_public_inverse.py":
        "0122190aa3a0972ffb4a709bc1bdd8179c8ba6c7",
    "research/north-star-transfer/20261018-mass-learned-kernel.py":
        "bf81ed56cc0daa2c413ad7d9c698969f92befe3d",
}


def need(value, code):
    if not value:
        raise RuntimeError("F124BI_PROVENANCE_" + code)


def shell(*args):
    p = subprocess.run(args, cwd=ROOT, capture_output=True, check=False)
    need(p.returncode == 0, "SUBPROCESS_" + Path(args[0]).name)
    return p.stdout


def github_json(endpoint):
    output = shell("gh", "api", "repos/" + REPO + "/" + endpoint)
    return json.loads(output)


def git_blob(raw):
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") +
                        b"\0" + raw).hexdigest()


def verify(local_only=False):
    protocol = json.loads(METHOD.read_text(encoding="utf-8"))
    need(protocol["schema"] ==
         "forge.mass.f124bi.provider-source-and-resource-method.v1",
         "METHOD_SCHEMA")
    need(protocol["source_parent_exact"] == BH_HEAD, "SOURCE_HEAD")
    need(shell("git", "merge-base", BH_HEAD, "HEAD").decode().strip() == BH_HEAD,
         "SOURCE_ANCESTRY")

    local = {}
    provider = {}
    for tag, (commit, blob, path) in BIRTHS.items():
        raw = (ROOT / path).read_bytes()
        need(git_blob(raw) == blob, "LOCAL_BLOB_" + tag)
        born = shell("git", "show", commit + ":" + path)
        need(born == raw, "LOCAL_BIRTH_" + tag)
        local[tag] = {"birth_commit": commit, "git_blob": blob,
                      "source_sha256": hashlib.sha256(raw).hexdigest()}
        if not local_only:
            obj = github_json("git/blobs/" + blob)
            need(obj.get("sha") == blob and obj.get("encoding") == "base64",
                 "PROVIDER_BLOB_IDENTITY_" + tag)
            remote_bytes = base64.b64decode(obj["content"], validate=False)
            need(remote_bytes == born and git_blob(remote_bytes) == blob,
                 "PROVIDER_BLOB_CONTENT_" + tag)
            tree_commit = github_json("git/commits/" + commit)
            need(tree_commit.get("sha") == commit
                 and tree_commit.get("tree", {}).get("sha"),
                 "PROVIDER_COMMIT_" + tag)
            provider[tag] = {
                "git_blob": obj["sha"],
                "provider_tree_sha": tree_commit["tree"]["sha"],
                "source_sha256": hashlib.sha256(remote_bytes).hexdigest(),
                "verified_remote_object": True,
            }
    # Strict original first-parent birth order, not a later rebased ancestry.
    chain = ((BIRTHS["protocol"][0], BH_HEAD),
             (BIRTHS["U"][0], BIRTHS["protocol"][0]),
             (BIRTHS["R"][0], BIRTHS["U"][0]))
    for current, prior in chain:
        if local_only:
            parent = shell("git", "rev-parse", current + "^").decode().strip()
        else:
            obj = github_json("git/commits/" + current)
            need(obj.get("sha") == current and len(obj.get("parents", [])) == 1,
                 "PROVIDER_PARENT_COUNT")
            parent = obj["parents"][0]["sha"]
        need(parent == prior, "BIRTH_FIRST_PARENT_DRIFT")

    need(shell("git", "merge-base", BIRTHS["R"][0], "HEAD").decode().strip()
         == BIRTHS["R"][0], "SOURCE_BRANCH_DRIFT")
    need(not shell("git", "ls-tree", "-r", "--name-only", BH_HEAD)
         .decode().count("f124bi-frozen-method.json"),
         "METHOD_NOT_PREEXISTING")

    # An untrusted algorithm source cannot import candidate or evaluator
    # modules; scan exact bytes at original birth, not mutable HEAD.
    for tag in ("U", "R"):
        path = BIRTHS[tag][2]
        tree = ast.parse((ROOT / path).read_text(encoding="utf-8"))
        imports = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name for alias in node.names)
            if isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module)
        need(imports <= {"__future__", "hashlib", "random"},
             "SOURCE_IMPORT_BOUNDARY_" + tag)
        names = {node.name for node in ast.walk(tree)
                 if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}
        need({"fixture", "_recipe", "forward", "inverse"} <= names,
             "SOURCE_API_" + tag)

    for path, expected in MODEL_BLOBS.items():
        raw = (ROOT / path).read_bytes()
        need(git_blob(raw) == expected, "ORIGINAL_MODEL_DRIFT")
    need(BIRTHS["U"][1] != BIRTHS["R"][1],
         "SAME_SOURCE_BLOB_UNACCEPTABLE")
    return {
        "schema": "mass.f124bi.provider-witnessed-git-source-custody.v1",
        "checked_head": shell("git", "rev-parse", "HEAD").decode().strip(),
        "provider": "GitHub REST immutable Git objects" if not local_only
                    else "local Git objects (provider read pending)",
        "provider_commit_blob_tree_authenticated": not local_only,
        "immutable_births": local,
        "provider_receipts": provider,
        "strict_first_parent_source_birth_chronology": True,
        "algorithm_bodies_distinct": True,
        "source_model_import_boundary": True,
        "registered_case_generated": 0,
        "external_independent_source_origin_confirmed": False,
        "source_novelty_vs_all_historical_ledger_certified": False,
        "scientific_admission_authorized": False,
        "complete_resource_parity": False,
        "science_accepted": False,
        "optimizer_update": False,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--provider", action="store_true")
    ap.add_argument("--output", type=Path, required=True)
    a = ap.parse_args()
    result = verify(local_only=not a.provider)
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n",
                        encoding="utf-8")
    print("F124BI_GIT_PROVIDER_OBJECTS=" +
          ("PASS" if a.provider else "NOT_CHECKED"))
    print("F124BI_EXTERNAL_INDEPENDENT_SOURCE_ORIGIN=false")
    print("F124BI_REGISTERED_COHORTS_GENERATED=0")


if __name__ == "__main__":
    main()

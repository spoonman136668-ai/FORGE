"""F124-BJ pre-first-use source custody gate. No TRAIN construction here.

Independently read original immutable GitHub provider objects and first-parent
birth chronology. This is provider custody, not proof of external independent
scientific origination or novelty across every historical source.
"""
from __future__ import annotations

import ast
import base64
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
DIR = Path(__file__).resolve().parent
REPO = "spoonman136668-ai/FORGE"
BI_HEAD = "fa794c078a0f6fd367ec14d0eae3fd742bf154b7"
FROZEN_COMMIT = "9627b45e4c6f788cf1dd5a47f879f8115e94ae5e"
A_COMMIT = "436a4c15035dfb06ec8e94513efae398e1b24151"
B_COMMIT = "2a2d649c66207e98755ef3e29ed3e379191b6f35"
BIRTHS = (
    ("method", FROZEN_COMMIT, BI_HEAD, "f124bj-train-freeze.json",
     "48c54172f4ded0571d9611635e6a1a575a54d3f4"),
    ("affine", A_COMMIT, FROZEN_COMMIT, "f124bj_affine_source.py",
     "b94ead68d9e953002e790939011fe69ba7017a75"),
    ("shear", B_COMMIT, A_COMMIT, "f124bj_shear_source.py",
     "b098201f16783ed2a3d91981a2b88ccea29ef18b"),
)


def need(ok, reason):
    if not ok:
        raise RuntimeError("F124BJ_CUSTODY_" + reason)


def git(*args):
    p = subprocess.run(["git", *args], cwd=ROOT, capture_output=True)
    need(p.returncode == 0, "GIT_FAIL_" + args[0])
    return p.stdout


def gh(endpoint):
    data = subprocess.run(["gh", "api", "repos/" + REPO + "/" + endpoint],
                          cwd=ROOT, capture_output=True)
    need(data.returncode == 0, "PROVIDER_API")
    return json.loads(data.stdout)


def git_blob(data):
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") +
                        b"\0" + data).hexdigest()


def import_at_birth(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    need(spec and spec.loader, "IMPORT")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def verify(*, provider):
    freeze = json.loads(git("show", FROZEN_COMMIT +
                            ":research/north-star-transfer/f124bj-train-freeze.json"))
    need(freeze["schema"] == "mass.f124bj.preregistered-train-source-and-cost.v1",
         "METHOD_SCHEMA")
    need(freeze["train_id_range"] == [900000, 900191]
         and freeze["train_task_count"] == 192
         and freeze["prebirth_synthetic_fixtures"] == {
             "affine": -950, "shear": -951,
             "source_readiness_cases_consumed": 0, "fixture_never_training": True},
         "FROZEN_IDENTITIES")
    need(git("merge-base", BI_HEAD, "HEAD").decode().strip() == BI_HEAD,
         "BI_FOUNDATION_DRIFT")
    receipts = []
    for tag, commit, parent, name, blob in BIRTHS:
        path = "research/north-star-transfer/" + name
        born = git("show", commit + ":" + path)
        need(git_blob(born) == blob, "BIRTH_BLOB_" + tag)
        need(git("rev-parse", "HEAD:" + path).decode().strip() == blob,
             "HEAD_DRIFT_" + tag)
        need(git("rev-parse", commit + "^").decode().strip() == parent,
             "FIRST_PARENT_" + tag)
        actual_remote_tree = None
        if provider:
            remote = gh("git/blobs/" + blob)
            need(remote.get("sha") == blob
                 and remote.get("encoding") == "base64",
                 "PROVIDER_BLOB_" + tag)
            need(base64.b64decode(remote["content"]) == born,
                 "PROVIDER_BYTE_IDENTITY_" + tag)
            obj = gh("git/commits/" + commit)
            need(obj.get("sha") == commit and len(obj.get("parents", [])) == 1
                 and obj["parents"][0]["sha"] == parent, "PROVIDER_PARENT_" + tag)
            actual_remote_tree = obj["tree"]["sha"]
        if tag != "method":
            # Source generator can't import or introspect candidate, graph,
            # U/R protected generators, or any prior experimental oracle.
            nodes = ast.parse(born.decode("utf-8"))
            modules = []
            for n in ast.walk(nodes):
                if isinstance(n, ast.Import):
                    modules += [x.name for x in n.names]
                if isinstance(n, ast.ImportFrom):
                    modules.append(n.module)
            need(set(modules) <= {"__future__", "hashlib", "random"},
                 "SOURCE_IMPORT_" + tag)
        receipts.append({"source": tag, "commit": commit,
                         "blob": blob, "sha256": hashlib.sha256(born).hexdigest(),
                         "provider_tree": actual_remote_tree})
    a = import_at_birth("bj_affine_witness", DIR / "f124bj_affine_source.py")
    b = import_at_birth("bj_shear_witness", DIR / "f124bj_shear_source.py")
    need(set(a.TRAIN).isdisjoint(b.TRAIN)
         and len(a.TRAIN) == 96 and len(b.TRAIN) == 96
         and a.SALT != b.SALT, "TRAIN_SOURCE_INDEPENDENCE")
    need(set(a.TRAIN).isdisjoint(range(902000, 902128))
         and set(b.TRAIN).isdisjoint(range(903000, 903128)),
         "PROSPECTIVE_COLLISION")
    for mod, seed in ((a, -950), (b, -951)):
        x, priv = mod.make(seed)
        need(len(x[0]) == 40 and len(x[1]) == 8
             and len(priv["corruption_private"]) == 6, "NEGATIVE_FIXTURE")
        for denied in (0, 900192, 901000, 902000, 903000, -939, -940):
            try:
                mod.make(denied)
            except ValueError:
                pass
            else:
                need(False, "DISALLOWED_SOURCE_" + str(denied))
    return {
        "schema": "mass.f124bj.prerequisite-provider-source-custody.v1",
        "source_commit": git("rev-parse", "HEAD").decode().strip(),
        "birth_order": receipts,
        "source_git_provider_authenticated": provider,
        "numeric_training_identity_disjoint": True,
        "not_independent_external_science_issuer": True,
        "historical_source_overlap_comprehensively_audited": False,
        "generated_registered_train": 0,
        "generated_U_or_R": 0,
        "training_scientific_acceptance": False,
        "whole_task_resource_parity": False,
        "optimizer_promotion": False,
    }


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--provider", action="store_true")
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    data = verify(provider=args.provider)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(data, indent=2, sort_keys=True) + "\n"
    args.output.write_text(raw, encoding="utf-8")
    print("F124BJ_GIT_BIRTH_WITNESS=" + ("PASS" if args.provider else "LOCAL_ONLY"))
    print("F124BJ_PROTECTED_COHORTS_GENERATED=0")
    print("F124BJ_TRAIN_GENERATED_DURING_WITNESS=0")


if __name__ == "__main__":
    main()

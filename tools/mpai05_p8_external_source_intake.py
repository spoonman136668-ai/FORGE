"""MP-AI05 P8 external benchmark intake. Read-only; does not open or score tasks.

Validates the *official* public LongMemEval-V2 source at an immutable commit,
before defining any task cohort. This is development-source provenance only:
a public released benchmark is never independently sealed first-use science.
"""
from __future__ import annotations
import hashlib
import json
import pathlib
import re
import subprocess
import sys

UPSTREAM_REPO = "xiaowu0162/LongMemEval-V2"
UPSTREAM_SHA = "2cc8c540bdb87fe6761629b585e727e1c4704520"
BLOBS = {
    "README.md": "b300e054d28dc456797dc975e114843aa055ad61",
    "data/download_data.py": "75f36a8acc054a02b16e05cfd220ea7558bec4a0",
    "data/public_data.py": "e91b858ff5c2fe0f03a49663bb44c9639f80edd5",
    "memory_modules/memory.py": "200909f913f311f1b181e84d09072408b66107ef",
    "evaluation/harness.py": "6a7182440a2cdd3ace6286dd966f7953fc383e8e",
    "evaluation/qa_eval_metrics.py": "6197efa64d1d47bff73c2523f4728c41ec78fd74",
}
FAMILIES = ("static", "dynamic", "procedure", "gotchas", "abstention")
DOMAINS = ("web", "enterprise")
REJECTED_MODELS = ("qwen",)
KNOWN_PUBLIC_BENCHMARK = "LongMemEval-V2"

def require(ok: bool, code: str):
    if not ok: raise ValueError(code)

def gate_record(upstream_sha: str, actual: dict[str,str], readme: str) -> dict:
    require(re.fullmatch(r"[0-9a-f]{40}",upstream_sha) is not None, "UPSTREAM_SHA_SYNTAX")
    require(upstream_sha == UPSTREAM_SHA, "UPSTREAM_COMMIT_DRIFT")
    require(type(actual) is dict and set(actual) == set(BLOBS), "BLOB_SET_DRIFT")
    require(all(type(v) is str and actual[k] == v for k,v in BLOBS.items()),
            "UPSTREAM_SOURCE_BLOB_DRIFT")
    require(type(readme) is str and all(t in readme for t in (
        "LongMemEval-V2", "451 manually curated questions",
        "web and enterprise", "memory_modules/", "evaluation/",
        "memory_context", "query",
    )), "UPSTREAM_INTERFACE_DRIFT")
    # Only pin public methodology identity; never parse questions, gold answers,
    # trajectories, answer ids, screenshots or any prospective hidden cohort.
    statement={
       "schema": "mind-palace.mpai05.p8.external-source-intake.v1",
       "upstream_repo": UPSTREAM_REPO, "upstream_sha": UPSTREAM_SHA,
       "file_blobs": dict(sorted(BLOBS.items())),
       "domains": list(DOMAINS), "candidate_task_families": list(FAMILIES),
       "source_access": "PUBLIC_SOURCE_ONLY",
       "purpose": "UNFAMILIAR_FAMILY_DEVELOPMENT_SOURCE",
       "dataset_revision": "NOT_PINNED",
       "dataset_questions_opened": 0,
       "independently_sealed_first_use": False,
       "independent_grading": False,
       "provider_authenticated_for_science": False,
       "scientific_accepted": False, "composition_authorized": False,
       "model_calls": 0, "accepted_memory_writes": 0,
       "witness": "NOT_PROVISIONED",
       "next_action": "INDEPENDENT_DATASET_AND_SCORER_FREEZE_BEFORE_TASK_EXPOSURE",
    }
    payload=json.dumps(statement,sort_keys=True,separators=(",",":")).encode("utf-8")
    statement["source_intake_sha256"]=hashlib.sha256(payload).hexdigest()
    return statement

def git(repo: pathlib.Path, *argv: str) -> str:
    p=subprocess.run(["git","-C",str(repo),*argv],
        stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=30,text=True)
    require(p.returncode==0,"UPSTREAM_GIT_READ_FAILURE")
    return p.stdout.strip()

def inspect(repo: pathlib.Path) -> dict:
    require(repo.is_dir() and (repo/".git").exists(),"UPSTREAM_REPO_MISSING")
    head=git(repo,"rev-parse","HEAD")
    require(head == UPSTREAM_SHA, "UPSTREAM_COMMIT_DRIFT")
    require(git(repo,"status","--porcelain","--untracked-files=all")=="",
        "UPSTREAM_CHECKOUT_DIRTY")
    actual={name:git(repo,"rev-parse",f"HEAD:{name}") for name in BLOBS}
    # Bounded reading of public README source only. Never read benchmark cases.
    readme=(repo/"README.md").read_text(encoding="utf-8")
    outcome=gate_record(head,actual,readme)
    require(git(repo,"status","--porcelain","--untracked-files=all")=="",
        "UPSTREAM_CHECKOUT_MUTATED")
    return outcome

if __name__=="__main__":
    require(len(sys.argv)==2,"UPSTREAM_ROOT_REQUIRED")
    print(json.dumps(inspect(pathlib.Path(sys.argv[1]).resolve()),sort_keys=True))

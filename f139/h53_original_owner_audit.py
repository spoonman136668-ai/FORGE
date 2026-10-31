"""H53 original-owner audit preflight, inactive until separate release authorization."""
from __future__ import annotations
import json
import os
import pathlib
import subprocess
from f139 import h53_audit_guards as guard
from f139 import h53_github_authority as authority
from f139 import h53_windows_owner as owner
from f139 import h53_native_readonly as native
from f139 import h53_release_manifest as manifest

WORKFLOW=".github/workflows/f139-h53-original-owner-one-shot.yml"
OBSERVER="f139/h53_successor_readonly_observer.py"

def git(*args):
    return subprocess.run(["git",*args],capture_output=True,text=True,
                          check=True,timeout=30).stdout.strip()

def verify_checkout():
    sha=os.environ["GITHUB_SHA"]
    parents=git("rev-list","--parents","-n","1","HEAD").split()
    changed=git("diff","--name-only",guard.SOURCE,"HEAD").splitlines()
    guard.demand(parents == [sha, guard.SOURCE], "NOT_DIRECT_V26_CHILD")
    guard.demand(set(changed) == manifest.REQUIRED and len(changed) == len(manifest.REQUIRED), "SOURCE_DIFF")
    guard.demand(git("rev-parse","HEAD")==sha,"AUDIT_HEAD")
    guard.demand(not git("status","--porcelain","--untracked-files=all"),"AUDIT_DIRTY")
    return sha

def audit():
    guard.demand(os.name=="nt","NOT_ORIGINAL_WINDOWS")
    sha=verify_checkout()
    event=json.loads(pathlib.Path(os.environ["GITHUB_EVENT_PATH"]).read_text(encoding="utf-8"))
    guard.event_guard(event,actor=os.environ["GITHUB_ACTOR"],
                      repository=os.environ["GITHUB_REPOSITORY"],
                      ref=os.environ["GITHUB_REF"],attempt=os.environ["GITHUB_RUN_ATTEMPT"],
                      runner=os.environ["RUNNER_NAME"],sha=sha)
    auth=authority.verify_authority(sha)
    original=owner.inspect_original()
    ledger=native.verify_native(pathlib.Path(original["database"]))
    return {"schema":"forge.f139.h53.original-owner-audit.v1",
            "audit_sha":sha,"authority":auth,
            "installed_source_sha":original["source_sha"],"ledger":ledger,
            "original_database_writes":0,"owner_task_mutations":0,
            "unattended_cycle_verified":False,"scientific_first_use_authorized":False}

if __name__=="__main__":
    print(json.dumps(audit(),sort_keys=True))

"""Validate a future H53 one-shot release bundle without activating it."""
from __future__ import annotations
import pathlib
from f139 import h53_audit_guards as g

WORKFLOW=".github/workflows/f139-h53-original-owner-one-shot.yml"
REQUIRED={
    WORKFLOW,
    "f139/h53_successor_readonly_observer.py",
    "f139/h53_audit_guards.py",
    "f139/h53_github_authority.py",
    "f139/h53_windows_owner.py",
    "f139/h53_native_readonly.py",
    "f139/h53_original_owner_audit.py",
}
def verify_release_manifest(changed, *, parent, source_hashes, expected_hashes):
    g.demand(parent==g.SOURCE,"RELEASE_PARENT")
    g.demand(set(changed)==REQUIRED and len(changed)==len(REQUIRED),"RELEASE_MANIFEST")
    g.demand(set(source_hashes)==REQUIRED and set(expected_hashes)==REQUIRED,
             "RELEASE_PIN_SET")
    g.demand(all(source_hashes[k]==expected_hashes[k] for k in REQUIRED),
             "RELEASE_CONTENT_DRIFT")
    return {"release_parent":parent,"file_count":len(REQUIRED),
            "source_pins_verified":True,"release_authorized":False}

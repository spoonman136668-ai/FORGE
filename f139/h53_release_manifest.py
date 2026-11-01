"""Validate a future H53 one-shot release bundle without activating it."""
from __future__ import annotations
import pathlib
import hashlib
import json
import re
from f139 import h53_audit_guards as g

WORKFLOW=".github/workflows/f139-h53c-original-owner-one-shot.yml"
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

def verify_release_bytes(changed, *, parent, files, expected_hashes):
    """Check actual byte content against immutable SHA-256 pins, not caller labels."""
    g.demand(set(files)==REQUIRED,"RELEASE_BYTES_SET")
    calculated={k:hashlib.sha256(files[k]).hexdigest() for k in REQUIRED}
    return verify_release_manifest(changed,parent=parent,
                                   source_hashes=calculated,
                                   expected_hashes=expected_hashes)

PIN_PREFIX = "          # H53_RUNTIME_PINS "

def template_pins(text):
    lines = [line[len(PIN_PREFIX):] for line in text.splitlines()
             if line.startswith(PIN_PREFIX)]
    g.demand(len(lines) == 1, "TEMPLATE_PIN_RECORD")
    pins = json.loads(lines[0])
    g.demand(set(pins) == REQUIRED - {WORKFLOW}, "TEMPLATE_PIN_SET")
    g.demand(all(isinstance(v, str) and re.fullmatch(r"[a-f0-9]{64}", v)
                 for v in pins.values()), "TEMPLATE_PIN_FORMAT")
    return pins

def verify_template(root):
    """Validate staged bytes without creating an executable ref or workflow."""
    root = pathlib.Path(root)
    path = root / ".github/audit-templates/f139-h53-one-shot-workflow.inactive.yml"
    text = path.read_text(encoding="utf-8")
    pins = template_pins(text)
    g.demand(not (root / WORKFLOW).exists(), "TEMPLATE_ALREADY_ACTIVE")
    for name, expected in pins.items():
        g.demand(hashlib.sha256((root / name).read_bytes()).hexdigest() == expected,
                 "TEMPLATE_RUNTIME_DRIFT")
    g.demand("fetch-depth: 0" in text and "PYTHONDONTWRITEBYTECODE" in text,
             "TEMPLATE_CHECKOUT_GUARD")
    return {"runtime_files": len(pins), "runtime_pins_verified": True,
            "release_authorized": False}

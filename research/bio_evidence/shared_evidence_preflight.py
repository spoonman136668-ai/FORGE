"""Private read-only research evidence lookup from an immutable Mind-Palace checkout."""
import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

CATALOG = "docs/RESEARCH_EVIDENCE_CATALOG.json"
BIO_INDEX = "archive/research/bio/2026-10-23/findings.json"
REPORT_PATH = re.compile(r"^archive/research/bio/2026-10-23/(original_reports|original_decisions)/[A-Za-z0-9_.-]+$")
WORD = re.compile(r"[a-z0-9]+")
STOP = {"the", "and", "for", "from", "with", "into", "that", "are", "was", "were", "this", "does", "how", "can", "use", "our", "its", "on", "not"}

def fail(code):
    raise ValueError("SHARED_EVIDENCE_" + code)

def read(root, rel, maximum):
    path = (root / rel).resolve()
    if not path.is_relative_to(root):
        fail("PATH_ESCAPE")
    raw = path.read_bytes()
    if not raw or len(raw) > maximum:
        fail("SOURCE_BOUNDS")
    return raw

def pin_checkout(root, expected_sha):
    if not re.fullmatch(r"[0-9a-f]{40}", expected_sha):
        fail("INVALID_PIN")
    head = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"], check=True, capture_output=True, text=True).stdout.strip()
    if head != expected_sha:
        fail("SOURCE_PIN_DRIFT")
    dirty = subprocess.run(["git", "-C", str(root), "status", "--porcelain", "--untracked-files=no"], check=True, capture_output=True, text=True).stdout
    if dirty:
        fail("DIRTY_SOURCE")

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

def lookup(root, expected_sha, query, limit=5):
    root = Path(root).resolve()
    if len(query) < 3 or len(query) > 180 or limit < 1 or limit > 8:
        fail("QUERY_BOUNDS")
    terms = set(WORD.findall(query.lower())) - STOP
    terms = {term for term in terms if len(term) >= 3}
    if not terms or len(terms) > 16:
        fail("QUERY_TERMS")
    pin_checkout(root, expected_sha)
    catalog_raw = read(root, CATALOG, 32768)
    catalog = json.loads(catalog_raw)
    if catalog.get("schema") != "mind-palace.research-evidence-catalog.v1" or catalog.get("authority") != "ADVISORY_HISTORICAL_ONLY":
        fail("CATALOG_CONTRACT")
    entries = [item for item in catalog.get("research_archives", []) if item.get("program") == "BIO"]
    if len(entries) != 1 or entries[0].get("index") != BIO_INDEX or entries[0].get("scientific_acceptance") != "NOT_AUTHENTICATED_OR_ESTABLISHED":
        fail("ARCHIVE_CONTRACT")
    idx_raw = read(root, BIO_INDEX, 250000)
    index = json.loads(idx_raw)
    findings = index.get("findings", [])
    if (index.get("schema") != "bio.findings.repo.historical.v1" or
        index.get("status") != "ADVISORY_HISTORICAL_NOT_ACCEPTED" or
        len(findings) != entries[0].get("scientific_finding_count") or
        len(findings) != index.get("record_count")):
        fail("FINDINGS_CONTRACT")
    candidates = []
    seen = set()
    for seq, finding in enumerate(findings):
        fid = finding.get("finding_id")
        if not isinstance(fid, str) or fid in seen:
            fail("FINDING_ID")
        seen.add(fid)
        if finding.get("evidence_status") != "HISTORICAL_PROVISIONAL_ONLY" or finding.get("wingless_yggdrasil_integration") != "NOT_AUTHORIZED":
            fail("ACCEPTANCE_DRIFT")
        body = (finding.get("claim", "") + " " + finding.get("control_comparison", "") + " " + finding.get("limitations", "")).lower()
        found = set(WORD.findall(body)) & terms
        if found:
            candidates.append((len(found), seq, finding))
    candidates.sort(key=lambda item: (-item[0], item[1]))
    results = []

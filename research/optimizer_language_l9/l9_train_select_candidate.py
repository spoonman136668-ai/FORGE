#!/usr/bin/env python3
"""L9 TRAIN->SELECT public-development runner. Not a scientific first-use or audit runner."""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import resource
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

import l9_model_suite as m
import l9_split_builder as split

ROOT = Path(__file__).resolve().parent
EXPECTED_ROLE_SHA = "b9995c1846f5e1d99bf8bc4083dde0ebb41140906284bcf050a7ed6fe0efe726"
EXPECTED_SUMMARY_SHA = "6adfc4387c16d7c9c5e67742e868e4947eb02aa6294602a02aeed6e46f338edf"
RECEIPT_SCHEMA = "forge.optimizer.language.l9.train-select-development-v1"
ROLE_ALLOWED = {"L9_TRAIN", "L9_SELECT"}

def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()

def git_bytes(repo: Path, oid: str) -> bytes:
    return subprocess.run(
        ["git", "-C", str(repo), "cat-file", "blob", oid], check=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    ).stdout

def load_train_select(repo: Path):
    """Role identities first, then TRAIN XML only. No DEV lexicalizations accessed."""
    manifest_path = ROOT / "L9_BLOB_MANIFEST.json"
    manifest, entries = split.load_manifest(manifest_path)
    split.verify_all_blob_identities(repo, entries)
    # This prequalified parser reads DEV graphs for anti-leakage, not DEV target text.
    s = split.build(repo, manifest_path)
    assert s["role_identity_sha256"] == EXPECTED_ROLE_SHA, "L9_ROLE_IDENTITY_DRIFT"
    observed_summary = dict(s)
    observed_summary.pop("role_identity_sha256")
    # Match the frozen summary digest in the existing qualification receipt. This is a
    # separate identity check; do not invent a new digest from this summary dictionary.
    receipt = json.loads((ROOT / "L9_SPLIT_RECEIPT.json").read_text(encoding="utf-8"))
    assert receipt["deterministic_split"]["cross_os_role_identity_sha256"] == EXPECTED_ROLE_SHA
    assert receipt["deterministic_split"]["cross_os_summary_sha256"] == EXPECTED_SUMMARY_SHA
    assert s["counts"]["roles"]["L9_TRAIN"] == 8480
    assert s["counts"]["roles"]["L9_SELECT"] == 2154
    assert s["counts"]["roles"]["L9_AUDIT_DEV"] == 319
    assert s["counts"]["train_audit_graph_overlap"] == 0

    # Only graph IDs of DEV/AUDIT are consulted to quarantine overlapping TRAIN.
    audit_graphs = set()
    for item in entries:
        if item["role"] != "DEV":
            continue
        root = ET.fromstring(git_bytes(repo, item["oid"]))
        for entry in root.iter("entry"):
            category = split.norm_category(entry.attrib.get("category", ""))
            if split.category_partition(category) == "L9_AUDIT_CATEGORY":
                triples = [split.parse_triple(x.text or "") for x in entry.findall("./modifiedtripleset/mtriple")]
                audit_graphs.add(split.graph_identity(triples))

    out = []
    counts = Counter()
    for item in entries:
        if item["role"] != "TRAIN":
            continue
        root = ET.fromstring(git_bytes(repo, item["oid"]))
        for entry in root.iter("entry"):
            category = split.norm_category(entry.attrib.get("category", ""))
            triples_raw = [split.parse_triple(x.text or "") for x in entry.findall("./modifiedtripleset/mtriple")]
            gid = split.graph_identity(triples_raw)
            role = split.example_role("TRAIN", category, gid, audit_graphs=audit_graphs)
            counts[role] += 1
            if role not in ROLE_ALLOWED:
                continue
            lex = entry.findall("./lex")
            if not lex:
                raise ValueError("missing TRAIN/SELECT reference; fail closed")
            # First source-order reference is fixed before first model fit. No DEV refs.
            reference = split.norm_text("".join(lex[0].itertext()))
            if not reference:
                raise ValueError("empty TRAIN/SELECT reference; fail closed")
            triples = tuple(m.Triple(*x) for x in triples_raw)
            out.append(m.Example(role, gid, triples, reference))
    assert counts["L9_TRAIN"] == 8480 and counts["L9_SELECT"] == 2154
    assert len(out) == 10634
    m.assert_audit_not_used(out)
    return out, s

def normalized_words(value: str):
    return m.normalize_space(value).casefold().split()

def relation_proxies(state: dict) -> dict[str, list[str]]:
    """TRAIN-derived connective text proxy; not adjudicated semantic entailment."""
    result = {}
    for pred, ts in state["templates"].items():
        literals = []
        for t in ts:
            text = str(t["template"]).replace("{S}", " ").replace("{O}", " ")
            text = m.normalize_space(text).casefold().strip(" .;!,?")
            if text:
                literals.append(text)
        result[pred] = literals
    return result

def coverage(output: str | None, triples, proxies: dict) -> tuple[int,int]:
    if output is None:
        return (0, len(triples))
    o = m.normalize_space(output).casefold().replace("_", " ")
    hit = 0
    for t in triples:
        subject = m.surface_alias(t.subject).casefold()
        obj = m.surface_alias(t.object).casefold()
        phrase = proxies.get(m.normalize_predicate(t.predicate), [])
        if subject in o and obj in o and any(p in o for p in phrase):
            hit += 1
    return hit, len(triples)

def chrf(hyp: str | None, ref: str) -> float:
    """Documented approximate character n-gram F2, n=1..6, single frozen reference."""
    if not hyp:
        return 0.0
    h, r = m.normalize_space(hyp), m.normalize_space(ref)
    vals = []
    for n in range(1, 7):
        hs = Counter(h[i:i+n] for i in range(max(0, len(h)-n+1)))
        rs = Counter(r[i:i+n] for i in range(max(0, len(r)-n+1)))
        overlap = sum(min(count,rs[gram]) for gram,count in hs.items())
        pp = overlap / sum(hs.values()) if hs else 0.0
        rr = overlap / sum(rs.values()) if rs else 0.0
        vals.append(5*pp*rr/(4*pp+rr) if pp+rr else 0.0)
    return sum(vals)/len(vals)

def evaluate(examples, render, proxies):
    assert examples and set(e.role for e in examples) == {"L9_SELECT"}
    hits = total = 0
    ch = 0.0
    start = time.perf_counter()
    start_cpu = time.process_time()
    for ex in examples:
        output = render(ex.triples)
        x,y = coverage(output, ex.triples, proxies)
        hits += x
        total += y
        ch += chrf(output, ex.reference)
    return {
        "requested_content_proxy_coverage": round(hits / total, 9),
        "missing_triples_proxy": total - hits,
        "chrf_single_reference_proxy": round(ch / len(examples), 9),
        "select_records": len(examples),
        "serial_wall_seconds": round(time.perf_counter()-start, 3),
        "cpu_seconds": round(time.process_time()-start_cpu, 3),
    }

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--webnlg-repo", required=True)
    parser.add_argument("--receipt-out", required=True)
    args = parser.parse_args()
    now = time.time()
    repo = Path(args.webnlg_repo)
    head = subprocess.check_output(["git","-C",str(repo),"rev-parse",split.RELEASE_SHA+"^{commit}"], text=True).strip()
    assert head == split.RELEASE_SHA, "L9_RELEASE_SHA_DRIFT"
    examples, split_summary = load_train_select(repo)
    train = [e for e in examples if e.role == "L9_TRAIN"]
    select = [e for e in examples if e.role == "L9_SELECT"]
    m.assert_audit_not_used(train+select)
    assert not any(e.role == "L9_AUDIT_DEV" for e in train+select)
    begin_cpu = time.process_time()
    model_start = time.perf_counter()
    candidate = m.fit_candidate(train)
    retrieval = m.fit_retrieval(train)
    train_wall = time.perf_counter()-model_start
    train_cpu = time.process_time()-begin_cpu
    proxies = relation_proxies(candidate)
    candidate_state = m.canonical_json_bytes(candidate)
    retrieval_state = m.canonical_json_bytes(retrieval)
    rows = []
    for conf in m.CANDIDATE_GRID:
        score = evaluate(select, lambda triples: m.realize_candidate(candidate, triples, conf), proxies)
        rows.append({
            "config": {"min_template_support": conf.min_template_support,
                       "max_templates_per_predicate": conf.max_templates_per_predicate,
                       "joiner": conf.joiner},
            **score
        })
    rows.sort(key=lambda x: (-x["requested_content_proxy_coverage"],
                             -x["chrf_single_reference_proxy"], x["missing_triples_proxy"],
                             len(candidate_state), x["config"]["min_template_support"],
                             x["config"]["max_templates_per_predicate"],
                             x["config"]["joiner"]))
    retrieval_score = evaluate(select, lambda triples: m.realize_retrieval(retrieval, triples), proxies)
    receipt = {
        "schema": RECEIPT_SCHEMA,
        "status": "DEVELOPMENT_TRAIN_SELECT_NOT_AUDIT",
        "source_release_sha": split.RELEASE_SHA,
        "split_role_sha256": EXPECTED_ROLE_SHA,
        "frozen_suite_sha_from_receipt": "710ce648a30ffc55647f689c5f4aa3ac13b07066",
        "lexical_reference_selection": "first lex node in TRAIN XML document order",
        "trained_roles": ["L9_TRAIN"],
        "selected_roles": ["L9_SELECT"],
        "model_arms": ["COMPOSITIONAL_PATTERN","TRAIN_REFERENCE_RETRIEVAL"],
        "candidate_config_selected": rows[0]["config"],
        "candidate_selection": rows,
        "retrieval_select": retrieval_score,
        "state_sha256": {"candidate":digest(candidate_state),"retrieval":digest(retrieval_state)},
        "state_bytes": {"candidate":len(candidate_state),"retrieval":len(retrieval_state)},
        "fit": {"wall_seconds":round(train_wall,3),"cpu_seconds":round(train_cpu,3)},
        "peak_maxrss_os_units": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "split_counts": {"train":len(train),"select":len(select),"audit_dev_model_consumption":0},
        "official_test_consumed":False,
        "selection_uses_proxy_not_adjudicated_semantics":True,
        "scientific_go":False,
        "completed_unix_seconds":int(time.time()),
    }
    assert len(candidate_state) <= m.INFERENCE_STATE_CEILING
    assert len(retrieval_state) <= m.INFERENCE_STATE_CEILING
    Path(args.receipt_out).write_bytes(m.canonical_json_bytes(receipt))
    print("L9_TRAIN_SELECT_CANDIDATE_RETRIEVAL=PASS")
    print("L9_TRAIN_EXAMPLES=8480")
    print("L9_SELECT_EXAMPLES=2154")
    print("L9_AUDIT_DEV_MODEL_CONSUMPTION=0")
    print("L9_OFFICIAL_TEST_CONSUMED=FALSE")
    print("L9_DEVELOPMENT_RECEIPT_SHA256="+digest(m.canonical_json_bytes(receipt)))

if __name__ == "__main__":
    main()

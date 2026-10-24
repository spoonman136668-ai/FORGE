#!/usr/bin/env python3
import argparse
import hashlib
import json
import pathlib
import re
import subprocess
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict

SCHEMA = "forge.optimizer.language.l9.webnlg-split-manifest-v1"
RELEASE_SHA = "a7ea49b5ffa5011edf81e8530c59b3552a965023"
BLOB_LINES_SHA256 = "07aa8e3d5d5a1f21add3666ef6280b7e4eaf4ce8287e7ecbf72dceab906378f0"
WS = re.compile(r"\s+")

class SplitError(RuntimeError):
    pass

def norm_text(value: str) -> str:
    return WS.sub(" ", (value or "").strip())

def norm_category(value: str) -> str:
    out = norm_text(value).lower()
    if not out:
        raise SplitError("empty category")
    return out

def sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def category_partition(category: str) -> str:
    digest = hashlib.sha256(norm_category(category).encode("utf-8")).digest()
    return "L9_AUDIT_CATEGORY" if digest[0] % 4 == 0 else "L9_TRAIN_CATEGORY"

def parse_triple(raw: str):
    parts = [norm_text(x) for x in (raw or "").split(" | ", 2)]
    if len(parts) != 3 or any(not x for x in parts):
        raise SplitError("malformed RDF triple")
    return tuple(parts)

def graph_identity(triples) -> str:
    canon = sorted(tuple(norm_text(x) for x in t) for t in triples)
    if not canon or any(len(t) != 3 or any(not x for x in t) for t in canon):
        raise SplitError("empty or malformed graph")
    payload = json.dumps(canon, ensure_ascii=False, separators=(",", ":"))
    return sha256_hex(payload)

def provisional_role(source_role: str, category: str) -> str:
    partition = category_partition(category)
    if source_role == "TRAIN":
        return "L9_TRAIN_POOL" if partition == "L9_TRAIN_CATEGORY" else "UNUSED_TRAIN_HELDOUT_CATEGORY"
    if source_role == "DEV":
        return "L9_AUDIT_DEV" if partition == "L9_AUDIT_CATEGORY" else "UNUSED_DEV_TRAIN_CATEGORY"
    raise SplitError("source role must be TRAIN or DEV")

def finalize_train_roles(records):
    audit_graphs = {r["graph_sha256"] for r in records if r["role"] == "L9_AUDIT_DEV"}
    quarantine = 0
    for r in records:
        if r["role"] != "L9_TRAIN_POOL":
            continue
        if r["graph_sha256"] in audit_graphs:
            r["role"] = "QUARANTINED_TRAIN_GRAPH_OVERLAP"
            quarantine += 1
            continue
        first = int(r["graph_sha256"][:2], 16)
        r["role"] = "L9_SELECT" if first % 5 == 0 else "L9_TRAIN"
    return audit_graphs, quarantine

def example_role(source_role: str, category: str, graph_sha256: str, audit_graphs=None) -> str:
    role = provisional_role(source_role, category)
    if role != "L9_TRAIN_POOL":
        return role
    if audit_graphs and graph_sha256 in audit_graphs:
        return "QUARANTINED_TRAIN_GRAPH_OVERLAP"
    first = int(graph_sha256[:2], 16)
    return "L9_SELECT" if first % 5 == 0 else "L9_TRAIN"

def run_git(repo, *args, text=True):
    p = subprocess.run(["git", "-C", str(repo), *args], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return p.stdout.decode("utf-8") if text else p.stdout

def load_manifest(path):
    m = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    if m.get("schema") != "forge.optimizer.language.l9.webnlg-blob-manifest-v1":
        raise SplitError("wrong blob manifest schema")
    if m.get("release_sha") != RELEASE_SHA:
        raise SplitError("release SHA drift")
    if m.get("lines_sha256") != BLOB_LINES_SHA256:
        raise SplitError("blob-line manifest digest drift")
    entries = m.get("entries")
    if not isinstance(entries, list) or len(entries) != 176:
        raise SplitError("expected exactly 176 TRAIN/DEV blob entries")
    validate_manifest_entries(entries)
    return m, entries

def validate_manifest_entries(entries):
    seen_paths = set()
    for item in entries:
        role, path, oid, mode = item.get("role"), item.get("path"), item.get("oid"), item.get("mode")
        if role not in {"TRAIN", "DEV"}:
            raise SplitError("manifest contains non TRAIN/DEV role")
        expected = f"release_v3.0/en/{role.lower()}/"
        if not isinstance(path, str) or not path.startswith(expected) or "/test/" in path.lower():
            raise SplitError("manifest path escapes TRAIN/DEV custody")
        if path in seen_paths:
            raise SplitError("duplicate manifest path")
        seen_paths.add(path)
        if mode != "100644" or not re.fullmatch(r"[0-9a-f]{40}", oid or ""):
            raise SplitError("invalid blob metadata")

def verify_all_blob_identities(repo, entries):
    verified = []
    for item in entries:
        line = run_git(repo, "ls-tree", RELEASE_SHA, "--", item["path"]).strip()
        fields = line.split(None, 3)
        if len(fields) != 4:
            raise SplitError(f"missing source path metadata: {item['path']}")
        mode, kind, oid, path = fields
        if mode != item["mode"] or kind != "blob" or oid != item["oid"] or path != item["path"]:
            raise SplitError(f"blob identity drift: {item['path']}")
        verified.append(item["path"])
    return verified

def parse_blob(xml_bytes: bytes, source_role: str, blob_oid: str):
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError as exc:
        raise SplitError(f"XML parse failure for blob {blob_oid}") from exc
    records = []
    entries = list(root.iter("entry"))
    if not entries:
        raise SplitError(f"no entry nodes in blob {blob_oid}")
    for entry in entries:
        category = entry.attrib.get("category", "")
        category_norm = norm_category(category)
        triples = []
        for node in entry.findall("./modifiedtripleset/mtriple"):
            triples.append(parse_triple(node.text or ""))
        if not triples:
            raise SplitError(f"entry missing modified triples in blob {blob_oid}")
        gid = graph_identity(triples)
        # Final TRAIN/SELECT assignment happens only after the complete audit graph set is known.
        refs = len(entry.findall("./lex"))
        records.append({
            "source_role": source_role,
            "blob_oid": blob_oid,
            "category": category_norm,
            "category_partition": category_partition(category_norm),
            "graph_sha256": gid,
            "role": provisional_role(source_role, category_norm),
            "triple_count": len(triples),
            "reference_count": refs,
        })
    return records

def build(repo, manifest_path):
    manifest, entries = load_manifest(manifest_path)
    # Critical custody boundary: verify all 176 path->blob identities before reading one blob body.
    verify_all_blob_identities(repo, entries)

    records = []
    source_bytes = 0
    blob_reads = 0
    for item in entries:
        raw = run_git(repo, "cat-file", "blob", item["oid"], text=False)
        blob_reads += 1
        source_bytes += len(raw)
        records.extend(parse_blob(raw, item["role"], item["oid"]))

    audit_graphs_prefit, quarantine_count = finalize_train_roles(records)
    role_counts = Counter(r["role"] for r in records)
    category_roles = {}
    category_counts = defaultdict(Counter)
    for r in records:
        category_roles.setdefault(r["category"], r["category_partition"])
        if category_roles[r["category"]] != r["category_partition"]:
            raise SplitError("category partition instability")
        category_counts[r["category"]][r["role"]] += 1

    train_categories = {c for c,p in category_roles.items() if p == "L9_TRAIN_CATEGORY"}
    audit_categories = {c for c,p in category_roles.items() if p == "L9_AUDIT_CATEGORY"}
    if train_categories & audit_categories:
        raise SplitError("category leakage")

    trained_graphs = {r["graph_sha256"] for r in records if r["role"] in {"L9_TRAIN","L9_SELECT"}}
    audit_graphs = {r["graph_sha256"] for r in records if r["role"] == "L9_AUDIT_DEV"}
    if audit_graphs != audit_graphs_prefit:
        raise SplitError("audit graph set changed during finalization")
    semantic_overlap = trained_graphs & audit_graphs
    if semantic_overlap:
        raise SplitError(f"semantic graph leakage across TRAIN/SELECT and AUDIT: {len(semantic_overlap)}")

    minimums = {"L9_TRAIN":1000, "L9_SELECT":150, "L9_AUDIT_DEV":120}
    for role, minimum in minimums.items():
        if role_counts[role] < minimum:
            raise SplitError(f"minimum not met for {role}: {role_counts[role]} < {minimum}")
    audit_present = {r["category"] for r in records if r["role"] == "L9_AUDIT_DEV"}
    if len(audit_present) < 2:
        raise SplitError("fewer than two held-out audit categories")

    role_lines = []
    for r in sorted(records, key=lambda x:(x["role"],x["category"],x["graph_sha256"],x["blob_oid"])):
        role_lines.append("|".join([
            r["role"], r["category"], r["graph_sha256"], r["source_role"],
            r["blob_oid"], str(r["triple_count"]), str(r["reference_count"])
        ]))
    role_identity_sha = hashlib.sha256(("\n".join(role_lines)+"\n").encode("utf-8")).hexdigest()

    categories = []
    for c in sorted(category_roles):
        categories.append({
            "category": c,
            "partition": category_roles[c],
            "partition_sha256": sha256_hex(c),
            "counts": dict(sorted(category_counts[c].items())),
        })

    summary = {
        "schema": SCHEMA,
        "release_sha": RELEASE_SHA,
        "blob_manifest_lines_sha256": BLOB_LINES_SHA256,
        "custody": {
            "all_blob_identities_verified_before_first_content_read": True,
            "blob_reads": blob_reads,
            "source_bytes_read": source_bytes,
            "official_test_content_consumed": False,
            "reference_text_used_for_role_assignment": False,
            "filename_or_entry_id_used_for_role_assignment": False,
        },
        "counts": {
            "records_total": len(records),
            "roles": dict(sorted(role_counts.items())),
            "categories_total": len(category_roles),
            "train_categories": len(train_categories),
            "audit_categories": len(audit_categories),
            "audit_categories_present_in_dev": len(audit_present),
            "train_select_unique_graphs": len(trained_graphs),
            "audit_unique_graphs": len(audit_graphs),
            "train_audit_graph_overlap": 0,
            "quarantined_train_graph_overlap": quarantine_count,
            "triples_total": sum(r["triple_count"] for r in records),
            "references_total": sum(r["reference_count"] for r in records),
        },
        "role_identity_sha256": role_identity_sha,
        "categories": categories,
        "model_fit_count": 0,
    }
    return summary

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--blob-manifest", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    summary = build(pathlib.Path(args.repo), pathlib.Path(args.blob_manifest))
    encoded = json.dumps(summary, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    pathlib.Path(args.out).write_bytes(encoded.encode("utf-8"))
    print("L9_SPLIT_ROLE_IDENTITY_SHA256="+summary["role_identity_sha256"])
    print("L9_SPLIT_RECORDS_TOTAL="+str(summary["counts"]["records_total"]))
    for k,v in summary["counts"]["roles"].items():
        print(f"L9_SPLIT_{k}_COUNT={v}")
    print("L9_SPLIT_AUDIT_CATEGORIES="+str(summary["counts"]["audit_categories_present_in_dev"]))
    print("L9_SPLIT_TRAIN_AUDIT_GRAPH_OVERLAP=0")
    print("L9_SPLIT_QUARANTINED_TRAIN_GRAPH_OVERLAP="+str(summary["counts"]["quarantined_train_graph_overlap"]))
    print("L9_SPLIT_SOURCE_BYTES_READ="+str(summary["custody"]["source_bytes_read"]))
    print("L9_SPLIT_OFFICIAL_TEST_CONTENT_CONSUMED=FALSE")
    print("L9_SPLIT_MODEL_FIT_COUNT=0")
    print("L9_SPLIT_CONSTRUCTION=PASS")

if __name__ == "__main__":
    main()

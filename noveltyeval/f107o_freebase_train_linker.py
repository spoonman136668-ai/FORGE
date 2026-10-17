"""F107-O original FreebaseQA TRAIN-only lexical entity linker diagnostics.

The lexicon is constructed from public TRAIN topic annotations ONLY.
The runtime Link(question, lexicon) has NO access to Parses, Answers, gold
MIDs, relation chains, DEV/EVAL rows, a graph, or F104 optimizer policies.
No question, MID, mention, role, label, or per-row prediction is published.
"""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import unicodedata

SOURCE_REPO = "kelvin-jiang/FreebaseQA"
SOURCE_HEAD = "d16aae5149aaa25e43ff2a7bd00a06f280ca19b9"
TRAIN_FILE = "FreebaseQA-train.json"
TRAIN_BLOB = "24dc4b13a9c4a0ad734732db094c124d086b7d67"
TRAIN_BYTES = 23888089
DEV_FILE = "FreebaseQA-dev.json"
DEV_BLOB = "2e16ac381efb7b9e362cbf9bd0cee90006244ea8"
EVAL_FILE = "FreebaseQA-eval.json"
EVAL_BLOB = "d7d06ae721aedca26a0838d0113cddc1aa6774a8"
TRAIN_ROWS = 20358
MAX_LEXICON = 100000
MAX_TOKENS = 128
MAX_NGRAM = 10
MAX_QUESTION_BYTES = 2048
MID = re.compile(r"/(?:m|g)/[a-z0-9_]{1,64}\Z")
SCHEMA = "forge.optimizer.f107o.freebase-original-train-lexical-linker.v1"

class Denied(Exception):
    pass

def require(ok: bool, reason: str) -> None:
    if not ok:
        raise Denied("F107O_TRAIN_SOURCE_DENIED_" + reason)

def git_meta(root: Path, operation: list[str]) -> str:
    require(operation in (
        ["rev-parse", "HEAD"],
        ["rev-parse", "HEAD:" + TRAIN_FILE],
        ["rev-parse", "HEAD:" + DEV_FILE],
        ["rev-parse", "HEAD:" + EVAL_FILE],
    ), "GIT_METADATA_SCOPE")
    p = subprocess.run(["git", "-C", str(root), *operation],
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                       check=False, timeout=25)
    require(p.returncode == 0, "UPSTREAM_METADATA_MISSING")
    return p.stdout.decode("ascii", "strict").strip()

def original_train_bytes(root: Path) -> bytes:
    cmd = ["git", "-C", str(root), "show", "HEAD:" + TRAIN_FILE]
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                       check=False, timeout=60)
    require(p.returncode == 0 and len(p.stdout) == TRAIN_BYTES, "SOURCE_BYTES_DRIFT")
    return p.stdout

def blob_id(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + bytes([0]) + raw).hexdigest()

def normal_form(text: str, max_bytes: int = 128) -> str | None:
    if not isinstance(text, str) or not text or len(text.encode("utf-8")) > max_bytes:
        return None
    if any(unicodedata.category(c) == "Cc" for c in text):
        return None
    return " ".join(unicodedata.normalize("NFKC", text).casefold().split()) or None

def valid_mid(text: object) -> bool:
    return isinstance(text, str) and MID.fullmatch(text) is not None

def construct_lexicon(rows: list[dict]) -> tuple[dict[str, frozenset[str]], dict]:
    require(0 < len(rows) <= 25000, "TRAIN_POPULATION_BUDGET")
    lex: dict[str, set[str]] = {}
    keys: set[str] = set()
    stat = Counter()
    roles: set[str] = set()
    for row in rows:
        require(isinstance(row, dict), "ORIGINAL_ROW_NOT_OBJECT")
        identifier = row.get("Question-ID")
        raw = row.get("RawQuestion")
        require(isinstance(identifier, str) and identifier and
                len(identifier.encode("utf-8")) <= 256 and identifier not in keys,
                "TRAIN_QUESTION_ID_DUPLICATE_OR_INVALID")
        keys.add(identifier)
        require(isinstance(raw, str) and 0 < len(raw.encode("utf-8")) <= MAX_QUESTION_BYTES
                and not any(unicodedata.category(c) == "Cc" for c in raw),
                "TRAIN_RAW_QUESTION_INVALID")
        parses = row.get("Parses")
        if not isinstance(parses, list) or len(parses) == 0:
            stat["rows_without_parse_list"] += 1
            continue
        stat["rows_with_parse_list"] += 1
        for item in parses:
            stat["parse_entries_total"] += 1
            if not isinstance(item, dict):
                stat["parse_entries_not_object"] += 1
                continue
            chain = item.get("InferentialChain")
            if isinstance(chain, list) and all(isinstance(s, str) for s in chain):
                n = len(chain)
                stat["relation_chains_" + (str(n) if n < 4 else "4plus")] += 1
                roles.update(chain)
            else:
                stat["relation_chains_unusable_structure"] += 1
            identifier_mid = item.get("TopicEntityMid")
            if not valid_mid(identifier_mid):
                stat["parse_entries_without_valid_mid"] += 1
                continue
            variants = set()
            for name in ("PotentialTopicEntityMention", "TopicEntityName"):
                mention = normal_form(item.get(name), 128)
                if mention and len(mention.split()) <= MAX_NGRAM:
                    variants.add(mention)
            if not variants:
                stat["parse_entries_without_eligible_mention"] += 1
                continue
            stat["parse_entries_with_eligible_topic"] += 1
            for mention in variants:
                if mention not in lex:
                    lex[mention] = set()
                    require(len(lex) <= MAX_LEXICON, "TRAIN_LEXICON_BUDGET")
                lex[mention].add(identifier_mid)
    stats = {
        "original_train_rows": len(rows),
        "train_row_ids_unique": len(keys),
        "parse_structures": dict(sorted(stat.items())),
        "lexicon_distinct_normalized_mentions": len(lex),
        "lexicon_unique_mid_mentions": sum(len(m) == 1 for m in lex.values()),
        "lexicon_ambiguous_mid_mentions": sum(len(m) > 1 for m in lex.values()),
        "distinct_training_role_strings": len(roles),
    }
    return {name: frozenset(mids) for name, mids in lex.items()}, stats

def link(raw_question: str, lexicon: dict[str, frozenset[str]]) -> str:
    """Returns one abstention/status category, NEVER a MID or gold answer."""
    norm = normal_form(raw_question, MAX_QUESTION_BYTES)
    if norm is None:
        return "invalid_question"
    tokens = norm.split(" ")
    if len(tokens) > MAX_TOKENS:
        return "oversize_question_tokens"
    matched: set[str] = set()
    for i in range(len(tokens)):
        for end in range(i + 1, min(len(tokens), i + MAX_NGRAM) + 1):
            phrase = " ".join(tokens[i:end])
            if phrase in lexicon:
                matched.add(phrase)
    if not matched:
        return "no_lexical_anchor"
    if any(len(lexicon[mention]) != 1 for mention in matched):
        return "ambiguous_train_lexicon"
    distinct_mids = {next(iter(lexicon[mention])) for mention in matched}
    if len(distinct_mids) != 1:
        return "multiple_candidate_anchors"
    return "lexical_anchor_resolved"

def audit(root: Path) -> dict:
    root = root.resolve(strict=True)
    require(root.is_dir(), "SOURCE_FOLDER_NOT_FOUND")
    require(git_meta(root, ["rev-parse", "HEAD"]) == SOURCE_HEAD,
            "SOURCE_UPSTREAM_HEAD_DRIFT")
    for file, blob in ((TRAIN_FILE, TRAIN_BLOB),
                       (DEV_FILE, DEV_BLOB), (EVAL_FILE, EVAL_BLOB)):
        require(git_meta(root, ["rev-parse", "HEAD:" + file]) == blob,
                "ORIGINAL_GIT_OBJECT_DRIFT")
    require(not (root / DEV_FILE).exists() and not (root / EVAL_FILE).exists(),
            "DEV_OR_EVAL_FILE_MATERIALIZED")
    raw = original_train_bytes(root)
    require(blob_id(raw) == TRAIN_BLOB, "ORIGINAL_TRAIN_CONTENT_DRIFT")
    try:
        doc = json.loads(raw.decode("utf-8", "strict"))
    except (UnicodeError, ValueError) as ex:
        raise Denied("F107O_TRAIN_JSON_PARSE_DENIED") from ex
    require(isinstance(doc, dict) and
            "Dataset" in doc and "Version" in doc and
            isinstance(doc.get("Questions"), list) and
            len(doc["Questions"]) == TRAIN_ROWS,
            "ORIGINAL_TRAIN_ROOT_OR_DENOMINATOR")
    rows = doc["Questions"]
    lexicon, stats = construct_lexicon(rows)
    diagnostics = Counter(link(item["RawQuestion"], lexicon) for item in rows)
    require(sum(diagnostics.values()) == TRAIN_ROWS,
            "INCOMPLETE_TRAIN_QUESTION_ACCOUNTING")
    return {
        "schema": SCHEMA,
        "status": "PUBLIC_FREEBASE_TRAIN_ONLY_LEXICAL_LINKER_DIAGNOSTIC",
        "source_repo": SOURCE_REPO,
        "source_commit": SOURCE_HEAD,
        "train_git_blob": TRAIN_BLOB,
        "train_source_sha256": hashlib.sha256(raw).hexdigest(),
        "train_original_bytes": len(raw),
        "dev_git_blob_metadata_only": DEV_BLOB,
        "eval_git_blob_metadata_only": EVAL_BLOB,
        "source_train_population": TRAIN_ROWS,
        "link_status_counts": dict(sorted(diagnostics.items())),
        "link_status_denominator": sum(diagnostics.values()),
        "train_annotation_lexicon_stats": stats,
        "max_ngram_tokens": MAX_NGRAM,
        "max_question_tokens": MAX_TOKENS,
        "trained_on_public_original_train_labels": True,
        "train_answer_labels_read_by_adapter": False,
        "dev_or_eval_question_bytes_read": False,
        "dev_or_eval_qa_scored": False,
        "per_question_output_published": False,
        "any_mid_mention_or_role_name_published": False,
        "qualified_independent_entity_linking": False,
        "qualified_freebase_role_translation": False,
        "qualified_original_freebase_knowledge_graph": False,
        "independent_scientific_firstuse": False,
        "generalization_qualified": False,
        "accepted_science": False,
        "accepted_ref_mutation": False,
        "dream_pareto_promotion": False,
        "thetaevolve_accepted_training": False,
        "science_dispatch": False,
        "model_calls": 0,
        "codex_calls": 0,
        "cloudflare_writes": 0,
    }

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--upstream", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    require(not args.out.exists(), "OUTPUT_ALREADY_EXISTS")
    evidence = audit(args.upstream)
    payload = (json.dumps(evidence, sort_keys=True, indent=2, ensure_ascii=True) + "\n").encode("utf-8")
    with args.out.open("xb") as stream:
        stream.write(payload)
    print("F107O_ORIGINAL_TRAIN_QUESTIONS=20358")
    print("F107O_ENTITY_LINKING_COUNTS_AGGREGATE_ONLY")
    print("F107O_DEV_EVAL_BYTES_AND_SCIENTIFIC_FIRSTUSE=ZERO")

if __name__ == "__main__":
    try:
        main()
    except (Denied, OSError, UnicodeError, subprocess.SubprocessError, KeyError) as exc:
        print("F107O_TRAIN_ONLY_SOURCE_QUALIFICATION_DENIED:", exc, file=sys.stderr)
        sys.exit(1)

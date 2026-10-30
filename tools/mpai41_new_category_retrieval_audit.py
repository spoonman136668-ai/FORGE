"""MP-AI41: untouched LoCoMo category-3/4 source-evidence diagnostic.

Reuses exact P37 IDF, P39 BM25, P40 session-neighbor mechanisms with no
retuning. Categories 3/4 were not in P37-P40's frozen 25 category-1/2/5
question cohort. Same underlying conversations: this is near-transfer
development, NOT independently custodied first-use science.
No model execution, gold in ranking, memory admission, or controller changes.
"""
import argparse
from collections import Counter
import hashlib
import json
import os
import re
import sys
import tempfile
from pathlib import Path

import mpai37_external_memory_effect as p37
import mpai38_original_evidence_coverage_audit as p38
import mpai39_original_bm25_retrieval_comparison as p39
import mpai40_session_neighbors as p40

P37_FROZEN = "123411ed33446deded98c45dd3c5e54a98620b8565a8612b7bea1c594131c5b8"
P37_BLOB = "f1305323279cf56c1fdda068a5d14933dfbe6ca7"
P38_BLOB = "bae5ddce69e17b8f3b5682799840405828784e63"
P39_BLOB = "3b892d8ccdf0316990a06ed353b565be864a55cd"
P40_BLOB = "080f6b64239d1c458c9496972752aa3c320b9663"
SEED = "mpai41-new-category-3-4-per-sample-first-source-hash-v2-backed-up"
CATEGORIES = ("3", "4")
ARMS = ("idf", "bm25", "session_neighbor")
STAGE = "INIT"

def need(condition, code):
    if not condition:
        raise RuntimeError("MPAI41_" + code)

def canon(obj):
    return json.dumps(obj, sort_keys=True, ensure_ascii=True, separators=(",", ":"))

def digest(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def choose(data):
    original, frozen = p37.freeze(data)
    need(frozen == P37_FROZEN and len(original) == 25, "ORIGINAL_SOURCE_IDENTITY")
    old = {(item["sample"], item["index"]) for item in original}
    chosen = []
    missing = []
    need(len(data) == 10, "SOURCE_SAMPLE_COUNT")
    for i, sample in enumerate(data):
        sample_id = str(sample["sample_id"])
        for category in CATEGORIES:
            options = [j for j, qa in enumerate(sample["qa"])
                       if str(qa.get("category")) == category]
            if not options:
                missing.append((i, category))
                continue
            index = min(options, key=lambda j: digest(
                SEED + "|" + sample_id + "|" + category + "|" + str(j)))
            need((i, index) not in old, "EXPOSED_QUESTION_OVERLAP")
            chosen.append({"sample": i, "sample_id": sample_id,
                           "index": index, "category": category})
    # Original LoCoMo sample 1 has no category-3 questions. Fill any absent
    # sample/category slot from an unused QA row in another source sample.
    # Choose by frozen metadata hash only; never consult question or gold.
    for missing_sample, category in missing:
        used = old | {(x["sample"], x["index"]) for x in chosen}
        candidates = []
        for donor_i, donor in enumerate(data):
            donor_id = str(donor["sample_id"])
            for j, qa in enumerate(donor["qa"]):
                if str(qa.get("category")) != category or (donor_i, j) in used:
                    continue
                key = digest(SEED + "|backfill|" + str(missing_sample)
                             + "|" + donor_id + "|" + category + "|" + str(j))
                candidates.append((key, donor_i, j))
        need(bool(candidates), "CATEGORY_BACKFILL_UNAVAILABLE")
        _, donor_i, index = min(candidates)
        chosen.append({"sample": donor_i,
                       "sample_id": str(data[donor_i]["sample_id"]),
                       "index": index, "category": category})
    need(len(chosen) == 20 and Counter(x["category"] for x in chosen)
         == {"3": 10, "4": 10}, "CATEGORY_BALANCE")
    need(len({(x["sample"], x["index"]) for x in chosen}) == 20,
         "DUPLICATE_QUESTION")
    return chosen

def protocol(chosen):
    return digest(canon({
        "schema": "mpai41-source-only-new-category-retrieval-v2",
        "upstream_locomo_git_blob": p37.source.LOCOMO_BLOB,
        "original_p37_task_commitment": P37_FROZEN,
        "original_source_blobs": [P37_BLOB, P38_BLOB, P39_BLOB, P40_BLOB],
        "selection_rule": SEED,
        "missing_category_strategy": "hash-ranked unused-source-QA backfill; source sample may repeat",
        "selected_source_metadata_only": chosen,
        "retrieval_arms": ARMS,
        "retriever_parameters": "unchanged imported P37/P39/P40 functions",
        "limits": {"max_source_turns": 12, "max_context_chars": 6500,
                   "turn_truncation_chars": 700},
        "scorer": "human original qa.evidence dia_id selection recall",
        "category_5": "excluded, never count abstention as answerable",
        "annotations_used_for_ranking": False,
        "source_conversations_overlap_prior_dev": True,
        "independent_first_use": False,
        "model_calls": 0,
        "accepted_memory_writes": 0,
        "scientific_admission": False
    }))

def rollup(rows, arm):
    evidence = sum(r["n"] for r in rows)
    need(evidence > 0, "ZERO_ANNOTATION_DENOMINATOR")
    hits = sum(r[arm] for r in rows)
    return {
        "questions": len(rows),
        "human_citations": evidence,
        "retrieved_citations": hits,
        "recall": round(hits / evidence, 4),
        "any": sum(r[arm] > 0 for r in rows),
        "all": sum(r[arm] == r["n"] for r in rows),
        "none": sum(r[arm] == 0 for r in rows),
        "context_chars": sum(r[arm + "_chars"] for r in rows),
        "source_turns": sum(r[arm + "_turns"] for r in rows)
    }

def main():
    global STAGE
    cli = argparse.ArgumentParser()
    cli.add_argument("--phase", required=True, choices=("freeze", "audit"))
    cli.add_argument("--expected-protocol", default="")
    args = cli.parse_args()
    need(os.getenv("GITHUB_REPOSITORY") == "spoonman136668-ai/FORGE",
         "REPOSITORY_SCOPE")
    need(os.getenv("GITHUB_RUN_ATTEMPT") == "1", "FIRST_ATTEMPT_ONLY")
    need(not os.getenv("OPENAI_API_KEY"), "NO_PAID_API")
    if args.phase == "audit":
        need(bool(re.fullmatch(r"[0-9a-f]{64}", args.expected_protocol)),
             "MISSING_INDEPENDENT_FREEZE")
    STAGE = "AUTHENTIC_UPSTREAM_SOURCE"
    with tempfile.TemporaryDirectory(prefix="mpai41-source-") as temp:
        data = p37.get_data(Path(temp))
        chosen = choose(data)
        frozen = protocol(chosen)
        print("MPAI41_FROZEN_PROTOCOL_SHA256=" + frozen, flush=True)
        print("MPAI41_UNUSED_CATEGORY_3_4_QUESTIONS=20", flush=True)
        if args.phase == "freeze":
            print("MPAI41_NO_GOLD_OR_EVIDENCE_ACCESSED_BY_SELECTOR=PASS", flush=True)
            print("MPAI41_SOURCE_ONLY_PREREG=PASS", flush=True)
            return
        need(frozen == args.expected_protocol, "FROZEN_PROTOCOL_DRIFT")
        STAGE = "RETRIEVE_ALL_QUESTIONS_BEFORE_GOLD"
        cache = {i: p38.reconstructed(sample) for i, sample in enumerate(data)}
        selected = []
        for item in chosen:
            turns, source_ids, _ = cache[item["sample"]]
            qa = data[item["sample"]]["qa"][item["index"]]
            question = qa.get("question")
            need(isinstance(question, str) and question.strip(),
                 "ORIGINAL_QUESTION_SCHEMA")
            idf, idf_context = p39.original_retriever_indexes(turns, question)
            bm25, bm25_context = p39.select_context(
                turns, p39.rank_bm25(turns, question))
            neighbor, neighbor_chars, _ = p40.neighbors(turns, question)
            contexts = {
                "idf": (set(idf), len(idf_context)),
                "bm25": (set(bm25), len(bm25_context)),
                "session_neighbor": (set(neighbor), neighbor_chars)
            }
            for arm, (indices, char_count) in contexts.items():
                need(4 <= len(indices) <= 12 and char_count <= 6500,
                     "CONTEXT_BUDGET")
            selected.append((item, source_ids, contexts))
        need(len(selected) == 20, "INCOMPLETE_RETRIEVAL")
        print("MPAI41_ALL_60_CONTEXTS_FROZEN_BEFORE_GOLD=PASS", flush=True)
        STAGE = "EXTERNAL_HUMAN_CITATION_SCORING"
        rows = []
        for item, source_ids, contexts in selected:
            qa = data[item["sample"]]["qa"][item["index"]]
            evidence = qa.get("evidence")
            need(isinstance(evidence, list) and evidence and
                 all(isinstance(x, str) and x.strip() for x in evidence),
                 "ANNOTATION_SCHEMA")
            gold = set(x.strip() for x in evidence)
            need(len(gold) == len(evidence) and gold.issubset(set(source_ids)),
                 "ORIGINAL_SOURCE_ANNOTATION_IDENTITY")
            row = {"category": item["category"], "n": len(gold)}
            for arm, (indices, char_count) in contexts.items():
                selected_ids = {source_ids[i] for i in indices}
                row[arm] = len(selected_ids & gold)
                row[arm + "_chars"] = char_count
                row[arm + "_turns"] = len(indices)
            rows.append(row)
        for category in CATEGORIES:
            subset = [row for row in rows if row["category"] == category]
            need(len(subset) == 10, "CATEGORY_DENOMINATOR")
            for arm in ARMS:
                print("MPAI41_CATEGORY_" + category + "_" + arm.upper() +
                      "=" + canon(rollup(subset, arm)), flush=True)
        for arm in ARMS:
            print("MPAI41_ANSWERABLE_" + arm.upper() + "=" +
                  canon(rollup(rows, arm)), flush=True)
        print("MPAI41_SOURCE_GOLD_NOT_USED_FOR_SELECTION=PASS", flush=True)
        print("MPAI41_DEVELOPMENT_ONLY_SAME_SOURCE_CONVERSATIONS=TRUE", flush=True)
        print("MPAI41_MODEL_INFERENCE_CALLS=0", flush=True)
        print("MPAI41_DEPLOYED_MINDPALACE=NOT_TESTED", flush=True)
        print("MPAI41_INDEPENDENT_FIRST_USE=NOT_ATTESTED", flush=True)
        print("MPAI41_SCIENTIFIC_ACCEPTANCE=FALSE", flush=True)
        print("MPAI41_ACCEPTED_MEMORY_WRITES=0", flush=True)
    print("MPAI41_SOURCE_SCRATCH_CLEAN=PASS", flush=True)

if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        message = str(error)
        code = message if re.fullmatch(r"MPAI41_[A-Z0-9_]{3,80}", message) else "MPAI41_EXCEPTION"
        print("MPAI41_SAFE_FAILURE=" + code, flush=True)
        print("MPAI41_SAFE_STAGE=" + STAGE, flush=True)
        print("MPAI41_SAFE_TYPE=" + type(error).__name__, flush=True)
        sys.exit(2)

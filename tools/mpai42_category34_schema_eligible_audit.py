"""MP-AI42: separately frozen LoCoMo category-3/4 retrieval development audit.

P41R failed after it selected a QA with unusable human evidence annotations.
This new, visibly contaminated development-only cohort declares its evidence-
schema eligibility policy before question selection. It reads only category,
sample/index, and the *shape* of human evidence; never human evidence IDs,
question text, or answers for selecting cases. Human reference IDs are used
only after all 60 retrieval contexts have been formed and frozen in memory.

Source conversations overlap P37-P41. Not independent scientific first use,
not production Mind-Palace recall, not a retriever promotion or model study.
"""
from collections import Counter
from pathlib import Path
import argparse
import hashlib
import json
import os
import re
import sys
import tempfile

import mpai37_external_memory_effect as p37
import mpai38_original_evidence_coverage_audit as p38
import mpai39_original_bm25_retrieval_comparison as p39
import mpai40_session_neighbors as p40
import mpai41_new_category_retrieval_audit as p41

P37_FROZEN = "123411ed33446deded98c45dd3c5e54a98620b8565a8612b7bea1c594131c5b8"
P41_BLOB = "51568fdc5480b83b483054c3deca0eb65cc69767"
SOURCE_BLOBS = (
    "f1305323279cf56c1fdda068a5d14933dfbe6ca7",
    "bae5ddce69e17b8f3b5682799840405828784e63",
    "3b892d8ccdf0316990a06ed353b565be864a55cd",
    "080f6b64239d1c458c9496972752aa3c320b9663",
    P41_BLOB,
)
SEED = "mpai42-new-qa-schema-eligible-category34-development-v1"
CATEGORIES = ("3", "4")
ARMS = ("idf", "bm25", "session_neighbor")
STAGE = "INIT"


def need(ok, key):
    if not ok:
        raise RuntimeError("MPAI42_" + key)


def canon(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=True,
                      separators=(",", ":"))


def digest(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def schema_ok(qa):
    """Evidence shape only, never inspect/copy human reference ID values."""
    value = qa.get("evidence")
    return (isinstance(value, list) and bool(value) and
            all(isinstance(x, str) and bool(x.strip()) for x in value))


def eligible_metadata(data):
    need(len(data) == 10, "SOURCE_SAMPLE_COUNT")
    counts = Counter()
    fingerprint = []
    choices = []
    for i, sample in enumerate(data):
        sid = str(sample["sample_id"])
        for j, qa in enumerate(sample["qa"]):
            category = str(qa.get("category"))
            if category not in CATEGORIES:
                continue
            ok = schema_ok(qa)
            counts[category + "_total"] += 1
            counts[category + ("_eligible" if ok else "_excluded")] += 1
            fingerprint.append([i, j, category, ok])
            if ok:
                choices.append((i, sid, j, category))
    need(counts["3_excluded"] > 0, "EXPECTED_SCHEMA_INCOMPLETENESS_DRIFT")
    need(sum(counts[x + "_eligible"] for x in CATEGORIES) > 20,
         "INSUFFICIENT_ELIGIBLE_SOURCE")
    return choices, dict(counts), digest(canon(fingerprint))


def choose(data):
    previous, p37_commit = p37.freeze(data)
    need(p37_commit == P37_FROZEN and len(previous) == 25,
         "ORIGINAL_P37_IDENTITY")
    p41_previous = p41.choose(data)
    need(len(p41_previous) == 20, "PREVIOUS_P41_COHORT_DRIFT")
    excluded = {(x["sample"], x["index"]) for x in previous + p41_previous}
    choices, counts, eligibility_hash = eligible_metadata(data)
    remaining = [entry for entry in choices if (entry[0], entry[2]) not in excluded]
    selected = []
    missing = []
    for i in range(10):
        for category in CATEGORIES:
            pool = [entry for entry in remaining
                    if entry[0] == i and entry[3] == category]
            if not pool:
                missing.append((i, category))
                continue
            best = min(pool, key=lambda item: digest(
                SEED + "|per-sample|" + item[1] + "|" + category +
                "|" + str(item[2])))
            selected.append({"sample": best[0], "sample_id": best[1],
                             "index": best[2], "category": category})
    for missing_i, category in missing:
        used = excluded | {(x["sample"], x["index"]) for x in selected}
        pool = [item for item in remaining
                if item[3] == category and (item[0], item[2]) not in used]
        need(bool(pool), "BACKFILL_UNAVAILABLE")
        best = min(pool, key=lambda item: digest(
            SEED + "|backfill|" + str(missing_i) + "|" + item[1] +
            "|" + category + "|" + str(item[2])))
        selected.append({"sample": best[0], "sample_id": best[1],
                         "index": best[2], "category": category})
    need(len(selected) == 20 and Counter(x["category"] for x in selected)
         == {"3": 10, "4": 10}, "BALANCED_COHORT")
    need(len({(x["sample"], x["index"]) for x in selected}) == 20,
         "DUPLICATE_COHORT")
    need(not {(x["sample"], x["index"]) for x in selected} & excluded,
         "EXPOSED_QUESTION_OVERLAP")
    return selected, counts, eligibility_hash, len(missing)


def protocol(selected, counts, eligibility_hash, missing):
    return digest(canon({
        "schema": "mpai42-category34-schema-eligibility-source-audit-v1",
        "original_upstream_git_blob": p37.source.LOCOMO_BLOB,
        "p37_frozen_selection": P37_FROZEN,
        "source_blobs": SOURCE_BLOBS,
        "seed": SEED,
        "eligibility": "category3/4 QA.evidence is nonempty list of nonblank strings; shape only; no reference values used",
        "eligibility_fingerprint": eligibility_hash,
        "eligible_counts": counts,
        "backfill_missing_slots": missing,
        "excluded_previously_exposed_cohorts": ["P37_25", "P41R_20"],
        "selected_qa_metadata_only": selected,
        "arms": ARMS,
        "limits": {"source_turns": 12, "context_chars": 6500,
                   "turn_truncation_chars": 700},
        "scorer": "original human dia_id citation recall; never used in ranking",
        "empty_annotation_policy": "exclude at cohort eligibility, never discard/reselect after scoring; fail closed on drift",
        "no_retriever_retuning": True,
        "source_conversations_reused": True,
        "hidden_first_use": False,
        "model_calls": 0,
        "memory_writes": 0,
        "scientific_admission": False,
    }))


def rollup(rows, arm):
    n = sum(x["n"] for x in rows)
    need(n > 0, "ZERO_CITATION_DENOMINATOR")
    got = sum(x[arm] for x in rows)
    return {
        "questions": len(rows), "human_citations": n,
        "retrieved_citations": got, "recall": round(got / n, 4),
        "any": sum(x[arm] > 0 for x in rows),
        "all": sum(x[arm] == x["n"] for x in rows),
        "none": sum(x[arm] == 0 for x in rows),
        "context_chars": sum(x[arm + "_chars"] for x in rows),
        "source_turns": sum(x[arm + "_turns"] for x in rows),
    }


def main():
    global STAGE
    cli = argparse.ArgumentParser()
    cli.add_argument("--phase", choices=("freeze", "audit"), required=True)
    cli.add_argument("--expected-protocol", default="")
    args = cli.parse_args()
    need(os.getenv("GITHUB_REPOSITORY") == "spoonman136668-ai/FORGE",
         "REPO_SCOPE")
    need(os.getenv("GITHUB_RUN_ATTEMPT") == "1", "FIRST_ATTEMPT_ONLY")
    need(not os.getenv("OPENAI_API_KEY"), "PAID_API_FORBIDDEN")
    if args.phase == "audit":
        need(bool(re.fullmatch(r"[0-9a-f]{64}", args.expected_protocol)),
             "INDEPENDENT_PROTOCOL_REQUIRED")
    with tempfile.TemporaryDirectory(prefix="mpai42-source-") as temp:
        STAGE = "VERIFY_UPSTREAM"
        data = p37.get_data(Path(temp))
        selected, counts, eligibility_hash, missing = choose(data)
        frozen = protocol(selected, counts, eligibility_hash, missing)
        print("MPAI42_FROZEN_PROTOCOL_SHA256=" + frozen, flush=True)
        print("MPAI42_SCHEMA_COUNTS=" + canon(counts), flush=True)
        print("MPAI42_BALANCED_NEW_QUESTIONS=20", flush=True)
        print("MPAI42_QUESTION_AND_HUMAN_REF_VALUES_UNUSED_FOR_COHORT=PASS",
              flush=True)
        if args.phase == "freeze":
            print("MPAI42_SOURCE_ONLY_FREEZE=PASS", flush=True)
        else:
            need(frozen == args.expected_protocol, "PROTOCOL_DRIFT")
            STAGE = "RETRIEVAL_BEFORE_HUMAN_GOLD"
            cache = {i: p38.reconstructed(s) for i, s in enumerate(data)}
            retrieved = []
            for item in selected:
                turns, source_ids, _ = cache[item["sample"]]
                qa = data[item["sample"]]["qa"][item["index"]]
                question = qa.get("question")
                need(isinstance(question, str) and question.strip(),
                     "SOURCE_QUESTION_SCHEMA")
                idf, idf_text = p39.original_retriever_indexes(turns, question)
                bm25, bm_text = p39.select_context(
                    turns, p39.rank_bm25(turns, question))
                neighbor, nc, _ = p40.neighbors(turns, question)
                contexts = {"idf": (set(idf), len(idf_text)),
                            "bm25": (set(bm25), len(bm_text)),
                            "session_neighbor": (set(neighbor), nc)}
                for indices, chars in contexts.values():
                    need(4 <= len(indices) <= 12 and chars <= 6500,
                         "MATCHED_RETRIEVAL_BUDGET")
                retrieved.append((item, source_ids, contexts))
            need(len(retrieved) == 20, "ALL_CONTEXTS_PRESENT")
            print("MPAI42_ALL_60_CONTEXTS_SELECTED_BEFORE_HUMAN_GOLD=PASS",
                  flush=True)
            STAGE = "SCORING_AFTER_RETRIEVAL"
            rows = []
            for item, source_ids, contexts in retrieved:
                qa = data[item["sample"]]["qa"][item["index"]]
                need(schema_ok(qa), "ELIGIBILITY_CHANGED_AT_SCORING")
                human = qa["evidence"]
                gold = {x.strip() for x in human}
                need(len(gold) == len(human) and
                     gold.issubset(set(source_ids)),
                     "HUMAN_CITATION_SOURCE_INCONSISTENT")
                row = {"category": item["category"], "n": len(gold)}
                for arm, (indices, chars) in contexts.items():
                    ids = {source_ids[i] for i in indices}
                    row[arm] = len(ids & gold)
                    row[arm + "_chars"] = chars
                    row[arm + "_turns"] = len(indices)
                rows.append(row)
            for category in CATEGORIES:
                subset = [r for r in rows if r["category"] == category]
                need(len(subset) == 10, "CATEGORY_COMPLETE")
                for arm in ARMS:
                    print("MPAI42_CATEGORY_" + category + "_" +
                          arm.upper() + "=" + canon(rollup(subset, arm)),
                          flush=True)
            for arm in ARMS:
                print("MPAI42_ANSWERABLE_" + arm.upper() + "=" +
                      canon(rollup(rows, arm)), flush=True)
            print("MPAI42_HUMAN_GOLD_USED_FOR_RANKING=FALSE", flush=True)
            print("MPAI42_INFERENCE_CALLS=0", flush=True)
            print("MPAI42_DEPLOYED_MINDPALACE=NOT_TESTED", flush=True)
            print("MPAI42_INDEPENDENT_FIRST_USE=FALSE", flush=True)
            print("MPAI42_SCIENTIFIC_ACCEPTANCE=FALSE", flush=True)
            print("MPAI42_ACCEPTED_MEMORY_WRITES=0", flush=True)
    print("MPAI42_SOURCE_SCRATCH_CLEAN=PASS", flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as err:
        message = str(err)
        code = (message if re.fullmatch(r"MPAI42_[A-Z0-9_]{3,80}", message)
                else "MPAI42_PRIVATE_EXCEPTION")
        print("MPAI42_SAFE_FAILURE=" + code, flush=True)
        print("MPAI42_SAFE_STAGE=" + STAGE, flush=True)
        print("MPAI42_SAFE_TYPE=" + type(err).__name__, flush=True)
        sys.exit(2)

"""MP-AI28 source-locked task selection and scorer calibration.

Two separate CI jobs invoke --phase freeze then --phase calibrate.
Freeze accesses ONLY public sample IDs, row offsets, category labels and
QUESTION COUNTS; no gold/reference text is used for selection. Calibration
subsequently reads gold in temporary private scratch but publishes only
aggregates. Neither a first-use witnessed holdout nor independent scoring.
No model, controller, accepted-memory writer, or paid API.
"""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import re
import string
import sys
import tempfile
import urllib.request

from mpai27_external_source_custody import FILES, LOCOMO_BLOB, file_bytes, inspect

SELECT_SEED = "MPAI28-EXTERNAL-SOURCE-METADATA-ONLY-PREREG-v1"
FAMILIES = ("LOCOMO", "MAB_CR", "MAB_TTL")
PER_FAMILY = 4
STAGE = "INIT"

def require(v, code):
    if not v:
        raise RuntimeError("MPAI28_" + code)

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def canon(o):
    return json.dumps(o, sort_keys=True, separators=(",", ":"), ensure_ascii=True)

def rank(*data):
    return sha(("|".join(map(str, (SELECT_SEED,) + data))).encode())

def normalize(s):
    require(isinstance(s, str), "ANSWER_NOT_STRING")
    t = s.lower()
    t = "".join(" " if c in string.punctuation else c for c in t)
    t = re.sub(r"\b(a|an|the)\b", " ", t)
    return " ".join(t.split())

def gold_strings(answer):
    # Calibration only; flatten multilingual nested answer alternatives.
    if isinstance(answer, str):
        xs = [answer]
    elif isinstance(answer, (tuple, list)):
        xs = []
        for a in answer:
            if isinstance(a, str):
                xs.append(a)
            elif isinstance(a, (list, tuple)):
                xs.extend(x for x in a if isinstance(x, str))
    else:
        xs = []
    return tuple(x for x in xs if x.strip() and normalize(x))

def score(pred, gold, rule):
    require(rule in ("strict", "exact", "substring"), "RULE")
    p = normalize(pred)
    if not p:
        return False
    gs = tuple(normalize(g) for g in gold if normalize(g))
    if not gs:
        return False
    if rule == "substring":
        # Official MAB CR: normalized reference contained in prediction.
        return any(g in p for g in gs)
    return any(g == p for g in gs)

def wrong_for(gold, rule):
    # Deliberately corrupt, non-semantic negative controls.
    # Find a nonempty string with zero shared normalized exact/substring
    # matches, rejecting instead of silently generating a false negative.
    for w in ("zqxv 123456789", "wqzx 987654321", "zzzyyyxxx 12345"):
        if not score(w, gold, rule):
            return w
    raise RuntimeError("MPAI28_NEGATIVE_COLLISION")

def source_downloads(private):
    raw = {}
    for spec in FILES:
        path, size = file_bytes(spec, private)
        _, hashvalue, count = inspect(spec, path, size)
        raw[spec["label"]] = (spec, path, size, hashvalue, count)
    require(set(raw) == set(FAMILIES), "SOURCE_COUNT")
    return raw

def locomo_metadata(path):
    # The selection loop *never* indexes question/answer/evidence text.
    data = json.loads(path.read_text("utf-8"))
    require(type(data) is list and len(data) == 10, "LOCOMO_SCHEMA")
    descriptors = []
    for row_index, sample in enumerate(data):
        sid = sample.get("sample_id")
        qa = sample.get("qa")
        require(sid is not None and type(qa) is list, "LOCOMO_QA_SCHEMA")
        for qa_idx in range(len(qa)):
            # Only independently assigned sample ID, position, and category
            # as a structural label; never content fields.
            category = qa[qa_idx].get("category")
            descriptors.append({"family": "LOCOMO",
                "source": str(sid), "row": row_index, "q": qa_idx,
                "category": str(category)})
    require(len(descriptors) >= 24, "LOCOMO_QA_CAPACITY")
    # One item per conversation, first four independently hashed samples.
    group = {}
    for d in descriptors:
        key = d["source"]
        if key not in group or rank("item", key, d["q"]) < rank("item", key, group[key]["q"]):
            group[key] = d
    require(len(group) == 10, "LOCOMO_CONVERSATION_COUNT")
    return sorted(group.values(), key=lambda d: rank("sample", d["source"]))[:PER_FAMILY]

def mab_metadata(path, family):
    # pyarrow is used on the machine solely to read structural columns.
    import pyarrow.parquet as pq
    pf = pq.ParquetFile(path)
    columns = set(pf.schema_arrow.names)
    require("questions" in columns and "answers" in columns, "MAB_REQUIRED_COLUMNS")
    extra = [k for k in ("source", "qa_pair_ids") if k in columns]
    # Do NOT read the answers column during task selection.
    samples = pq.read_table(path, columns=["questions"] + extra).to_pylist()
    require(len(samples) >= 4, "MAB_ROW_CAPACITY")
    descriptor = []
    for row_idx, row in enumerate(samples):
        q = row.get("questions")
        if not isinstance(q, list):
            continue
        source = row.get("source")
        source = str(source) if isinstance(source, (str, int)) else "unspecified"
        for qi in range(len(q)):
            descriptor.append({"family": family, "source": source,
                    "row": row_idx, "q": qi})
    require(len(descriptor) >= 16, "MAB_QA_CAPACITY")
    # Prefer different upstream data rows: no family overlap introduced
    # by treating distinct questions in one conversation as independent.
    best = {}
    for d in descriptor:
        rid = d["row"]
        if rid not in best or rank(family, rid, d["q"]) < rank(family, rid, best[rid]["q"]):
            best[rid] = d
    require(len(best) >= PER_FAMILY, "MAB_INDEPENDENT_ROW_CAPACITY")
    return sorted(best.values(),
                  key=lambda d: rank(family, d["source"], d["row"]))[:PER_FAMILY]

def selection(files):
    loc = locomo_metadata(files["LOCOMO"][1])
    cr = mab_metadata(files["MAB_CR"][1], "MAB_CR")
    ttl = mab_metadata(files["MAB_TTL"][1], "MAB_TTL")
    selected = sorted(loc + cr + ttl,
                      key=lambda d:(d["family"], d["source"], d["row"], d["q"]))
    require(len(selected) == 12, "TASK_COUNT")
    require(Counter(d["family"] for d in selected) ==
        {"LOCOMO": 4, "MAB_CR": 4, "MAB_TTL": 4}, "FAMILY_BALANCE")
    require(len({(d["family"], d["row"], d["q"]) for d in selected}) == 12,
            "TASK_ID_DUPLICATE")
    # No actual question or answer included in the commitment.
    inputs = {k: {"sha256": v[3], "bytes": v[2]} for k,v in sorted(files.items())}
    freeze = {"schema": "mpai28.source-only-task-freeze.v1",
          "seed": SELECT_SEED, "tasks": selected,
          "source_bytes_and_sha": inputs,
          "scoring_protocol": {"LOCOMO": "exact_proxy_no_semantic_grade",
              "MAB_CR": "upstream_substring_exact_match",
              "MAB_TTL": "upstream_exact_match"},
          "independent_blind_first_use": False,
          "raw_question_text_in_manifest": False,
          "gold_answers_in_manifest": False}
    return selected, sha(canon(freeze).encode())

def calibrate(files, selected):
    # Calibrator runs only AFTER separate prior CI task-freeze job
    # records a matching commitment.
    import pyarrow.parquet as pq
    locomo = json.loads(files["LOCOMO"][1].read_text("utf-8"))
    data = {
      "MAB_CR": pq.read_table(files["MAB_CR"][1],
                      columns=["answers"]).to_pylist(),
      "MAB_TTL": pq.read_table(files["MAB_TTL"][1],
                      columns=["answers"]).to_pylist(),
    }
    counts = Counter()
    positive = Counter()
    negative = Counter()
    wrong_blank = Counter()
    for d in selected:
        family = d["family"]
        if family == "LOCOMO":
            gold = locomo[d["row"]]["qa"][d["q"]].get("answer")
            rule = "strict"
        else:
            row = data[family][d["row"]]
            a = row["answers"]
            require(isinstance(a, list) and len(a) > d["q"], "ANSWER_PAIR_MISSING")
            gold = a[d["q"]]
            rule = "substring" if family == "MAB_CR" else "exact"
        gold = gold_strings(gold)
        require(len(gold) > 0, "UNSCORABLE_GOLD")
        # Positive, explicit corrupted, and blank controls on *real*
        # gold strings; gold and task inputs never printed.
        correct = score(gold[0], gold, rule)
        wrong = score(wrong_for(gold, rule), gold, rule)
        blank = score("", gold, rule)
        require(correct is True and wrong is False and blank is False,
                "GOLD_CONTROL_MISCLASSIFICATION")
        counts[family] += 1
        positive[family] += int(correct)
        negative[family] += int(not wrong)
        wrong_blank[family] += int(not blank)
    require(all(counts[k] == PER_FAMILY for k in FAMILIES), "CALIBRATED_COUNT")
    for family in FAMILIES:
        print("MPAI28_"+family+"_SCORER_POSITIVES="+str(positive[family]), flush=True)
        print("MPAI28_"+family+"_WRONG_ANSWERS_REJECTED="+str(negative[family]), flush=True)
        print("MPAI28_"+family+"_BLANK_ANSWERS_REJECTED="+str(wrong_blank[family]), flush=True)
    print("MPAI28_TOTAL_GOLD_CONTROL_CASES=12", flush=True)
    print("MPAI28_ALL_36_SCORER_CONTROLS=PASS", flush=True)
    print("MPAI28_LOCOMO_SEMANTIC_SCORER=NOT_QUALIFIED", flush=True)

def main():
    global STAGE
    p = argparse.ArgumentParser()
    p.add_argument("--phase", choices=("freeze", "calibrate"), required=True)
    p.add_argument("--expected-selection-sha", default=None)
    args = p.parse_args()
    require(os.environ.get("GITHUB_REPOSITORY") ==
            "spoonman136668-ai/FORGE", "REPOSITORY_ID")
    require(os.environ.get("GITHUB_RUN_ATTEMPT") == "1", "NO_REPLAY")
    require(not os.environ.get("OPENAI_API_KEY"), "PAID_API_NOT_ALLOWED")
    if args.phase == "calibrate":
        require(bool(args.expected_selection_sha and
                 re.fullmatch(r"[a-f0-9]{64}", args.expected_selection_sha)),
                 "PREREG_COMMITMENT_MISSING")
    STAGE = "IMMUTABLE_SOURCE"
    with tempfile.TemporaryDirectory(prefix="mpai28-private-") as scratch:
        files = source_downloads(Path(scratch))
        STAGE = "METADATA_ONLY_SELECT"
        chosen, frozen_sha = selection(files)
        print("MPAI28_SELECTION_SHA256="+frozen_sha, flush=True)
        print("MPAI28_SELECTED_TASKS=12", flush=True)
        print("MPAI28_EXTERNAL_SOURCE_FAMILIES=3", flush=True)
        print("MPAI28_SELECTION_USES_GOLD=FALSE", flush=True)
        if args.phase == "freeze":
            print("MPAI28_PREREGISTRATION_ONLY=PASS", flush=True)
            print("MPAI28_GOLD_READ_BY_SCORER=FALSE", flush=True)
        else:
            require(frozen_sha == args.expected_selection_sha,
                    "PREREG_COMMITMENT_CHANGED")
            print("MPAI28_PREREGISTRATION_MATCH=PASS", flush=True)
            STAGE = "PRIVATE_GOLD_CALIBRATION"
            calibrate(files, chosen)
            print("MPAI28_GOLD_PRIVATE_ONLY=PASS", flush=True)
    print("MPAI28_SCRATCH_CLEANED=PASS", flush=True)
    print("MPAI28_MODEL_INFERENCE_CALLS=0", flush=True)
    print("MPAI28_ACCEPTED_MEMORY_WRITES=0", flush=True)
    print("MPAI28_INDEPENDENT_FIRST_USE_CUSTODY=NOT_ATTESTED", flush=True)
    print("MPAI28_MODEL_PRETRAINING_CONTAMINATION=UNKNOWN", flush=True)
    print("MPAI28_SCIENTIFIC_ACCEPTANCE=FALSE", flush=True)

if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        label = str(exc)
        code = label if re.fullmatch(r"MPAI28_[A-Z0-9_]{3,110}", label) else "MPAI28_PRIVATE_EXCEPTION"
        print("MPAI28_SAFE_FAILURE="+code, flush=True)
        print("MPAI28_SAFE_STAGE="+STAGE, flush=True)
        print("MPAI28_SAFE_TYPE="+type(exc).__name__, flush=True)
        sys.exit(2)

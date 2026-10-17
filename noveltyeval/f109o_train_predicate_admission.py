"""F109-O frozen original TRAIN-only Freebase single-predicate syntax audit.

The source "InferentialChain" is ONE whole label-annotated predicate, never
a predicted graph traversal. Its dot segments are NOT multi-hop edges.
Original Freebase graph remains unqualified and may NOT be executed.
"""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import sys

import f109o_train_chain_shape as stage_a

SOURCE_COMMIT=stage_a.SOURCE_COMMIT
TRAIN_BLOB=stage_a.TRAIN_BLOB
TRAIN_ROWS=stage_a.ROWS
PARSE_ROWS=stage_a.PARSES
# Strict preregistered one-predicate syntax; ASCII dot is part of ONE role.
PREDICATE=re.compile(r"[A-Za-z_][A-Za-z0-9_]*(?:[.][A-Za-z_][A-Za-z0-9_]*)+\Z",
                     flags=re.ASCII)
SCHEMA="forge.optimizer.f109o.original-freebase-train-one-predicate.v1"
GRAPH_STATUS="FREEBASE_GRAPH_SOURCE_NOT_QUALIFIED"

class Denied(Exception):
    pass

def require(check,reason):
    if not check:raise Denied("F109O_PREDICATE_SOURCE_DENIED_"+reason)

def admit_one_predicate(value):
    """Return (single source label, reason); never a direction or steps."""
    if not isinstance(value,str):
        return None,"invalid_segment_syntax"
    if not value:
        return None,"empty"
    if len(value.encode("utf-8"))>512:
        return None,"too_long"
    if any(ord(c)<32 or ord(c)>126 for c in value):
        return None,"control_or_non_ascii"
    if "." not in value:
        return None,"no_dotted_structure"
    if PREDICATE.fullmatch(value) is None:
        return None,"invalid_segment_syntax"
    return value,"accepted_one_opaque_predicate"

def can_admit_original_freebase_graph(_untrusted_manifest=None):
    # No original source identity, verified huge graph checksum, streaming
    # capability, custody, or authorization: no manifest can bypass this.
    return GRAPH_STATUS

def syntax_inventory(doc,expected_rows=TRAIN_ROWS,expected_parses=PARSE_ROWS):
    require(isinstance(doc,dict) and isinstance(doc.get("Questions"),list)
            and "Dataset" in doc and "Version" in doc
            and len(doc["Questions"])==expected_rows,"WHOLE_TRAIN_ROWS")
    counts=Counter()
    ids=set()
    unique_valid=set() # transient role strings only, never output
    for row in doc["Questions"]:
        require(isinstance(row,dict),"QUESTION_OBJECT")
        key=row.get("Question-ID")
        raw=row.get("RawQuestion")
        parses=row.get("Parses")
        require(isinstance(key,str) and 0<len(key.encode("utf-8"))<=256
                and key not in ids,"ORIGINAL_QUESTION_ID")
        ids.add(key)
        require(isinstance(raw,str) and 0<len(raw.encode("utf-8"))<=2048
                and all(ord(c)>=32 and ord(c)!=127 for c in raw),
                "QUESTION_ORIGINAL_SCHEMA")
        require(isinstance(parses,list),"PARSES_NOT_ARRAY")
        for item in parses:
            counts["original_parse_entries"]+=1
            require(isinstance(item,dict),"PARSE_NOT_OBJECT")
            for field in ("InferentialChain","TopicEntityMid",
                          "TopicEntityName","PotentialTopicEntityMention"):
                require(isinstance(item.get(field),str),"FROZEN_FLAT_ORIGINAL_FIELDS")
            predicate,reason=admit_one_predicate(item["InferentialChain"])
            counts[reason]+=1
            if predicate is not None:unique_valid.add(predicate)
            # Do not dereference any Answers member or compute gold accuracy.
    require(len(ids)==expected_rows and
            counts["original_parse_entries"]==expected_parses,
            "ORIGINAL_PARSE_POPULATION")
    outcomes=("empty","too_long","control_or_non_ascii",
              "no_dotted_structure","invalid_segment_syntax",
              "accepted_one_opaque_predicate")
    require(sum(counts[k] for k in outcomes)==expected_parses,
            "STRICT_EXHAUSTIVE_PREDICATE_CATEGORIES")
    return {
        "original_train_rows":len(ids),
        "original_train_unique_ids":len(ids),
        "original_parse_entries":counts["original_parse_entries"],
        "predicate_status_counts":{k:counts[k] for k in outcomes},
        "unique_whole_valid_predicates":len(unique_valid),
        "single_predicate_not_hop_chain":True,
        "original_source_direction_provided":False,
        "original_predicate_names_published":False,
        "source_answer_fields_read":False,
    }

def audit(root):
    root=root.resolve(strict=True)
    require(stage_a.metadata(root,["rev-parse","HEAD"])==SOURCE_COMMIT,
            "ORIGINAL_SOURCE_HEAD")
    for file,expected in (
        (stage_a.TRAIN,stage_a.TRAIN_BLOB),
        (stage_a.DEV,stage_a.DEV_BLOB),
        (stage_a.EVAL,stage_a.EVAL_BLOB),
    ):
        require(stage_a.metadata(root,["rev-parse","HEAD:"+file])==expected,
                "ORIGINAL_SOURCE_GIT_BLOBS")
    require(not (root/stage_a.DEV).exists() and
            not (root/stage_a.EVAL).exists(),"DEV_EVAL_MATERIALIZED")
    raw=stage_a.original_train(root)
    try:doc=json.loads(raw.decode("utf-8","strict"))
    except (ValueError,UnicodeError) as exc:
        raise Denied("F109O_ORIGINAL_JSON") from exc
    data=syntax_inventory(doc)
    require(can_admit_original_freebase_graph() == GRAPH_STATUS,
            "FREEBASE_GRAPH_NEVER_AUTHORIZED")
    return {
        "schema":SCHEMA,
        "status":"PUBLIC_FREEBASE_TRAIN_ONE_PREDICATE_GRAMMAR_ONLY",
        "source_repo":"kelvin-jiang/FreebaseQA",
        "source_commit":SOURCE_COMMIT,
        "train_blob":TRAIN_BLOB,
        "train_sha256":hashlib.sha256(raw).hexdigest(),
        "train_bytes":len(raw),
        "dev_blob_metadata_only":stage_a.DEV_BLOB,
        "eval_blob_metadata_only":stage_a.EVAL_BLOB,
        "source_data":data,
        "original_train_json_annotations_decoded":True,
        "source_answers_interpreted":False,
        "dev_eval_source_contents_accessed":False,
        "source_predicate_values_published":False,
        "freebase_graph_admission_status":GRAPH_STATUS,
        "independent_direction_mapping_qualified":False,
        "freebase_qa_model_qualified":False,
        "freebase_graph_queries":0,
        "real_question_answer_sets_compared":0,
        "scientific_firstuse":False,
        "accepted_science":False,
        "accepted_ref_mutation":False,
        "dream_pareto_promotion":False,
        "thetaevolve_accepted_training":False,
        "science_dispatch":False,
        "model_calls":0,"codex_calls":0,"cloudflare_writes":0,
    }

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--upstream",required=True,type=Path)
    p.add_argument("--out",required=True,type=Path)
    args=p.parse_args()
    require(not args.out.exists(),"EVIDENCE_OVERWRITE")
    output=(json.dumps(audit(args.upstream),sort_keys=True,
                       indent=2,ensure_ascii=True)+"\n").encode("utf-8")
    with args.out.open("xb") as f:f.write(output)
    print("F109O_ORIGINAL_TRAIN_20358_QUESTIONS_37306_RELATION_STRINGS_ACCOUNTED")
    print("F109O_UNKNOWN_DIRECTION_AND_UNQUALIFIED_GRAPH_HARD_BLOCKED")
    print("F109O_NO_EVAL_QA_SCORE_OR_SCIENTIFIC_PROMOTION")

if __name__=="__main__":
    try:main()
    except (Denied,stage_a.Denied,OSError,UnicodeError,
            ValueError,KeyError) as exc:
        print("F109O_TRAIN_ONE_PREDICATE_NOT_QUALIFIED:",exc,file=sys.stderr)
        sys.exit(1)

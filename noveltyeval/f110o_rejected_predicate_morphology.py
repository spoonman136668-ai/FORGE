"""F110-O: immutable original FreebaseQA TRAIN-only rejected-role morphology.

EXHAUSTIVE original F109 positive/negative cohort is preserved. NEVER
inspect gold answers, publish role strings, modify frozen grammar or read DEV/EVAL.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import f109o_train_chain_shape as source
import f109o_train_predicate_admission as baseline

SCHEMA="forge.optimizer.f110o.original-train-predicate-rejection-morphology.v1"
EXPECTED=37306
BASELINE_ACCEPTED=25498
BASELINE_REJECTED=11808

BUCKETS=(
    "empty","over_512_bytes","control_or_non_ascii","no_dot",
    "contains_hash","contains_dash","contains_colon","contains_whitespace",
    "contains_slash_pipe_comma_semicolon","contains_empty_dot_segment",
    "leading_digit_any_segment","invalid_other",
)

class Denied(Exception): pass

def require(ok,why):
    if not ok: raise Denied("F110O_ORIGINAL_SOURCE_DENIED_"+why)

def category(text:str)->str:
    if text=="":return "empty"
    if len(text.encode("utf-8"))>512:return "over_512_bytes"
    if any(ord(c)<32 or ord(c)>126 for c in text):return "control_or_non_ascii"
    if "." not in text:return "no_dot"
    if "#" in text:return "contains_hash"
    if "-" in text:return "contains_dash"
    if ":" in text:return "contains_colon"
    if any(c.isspace() for c in text):return "contains_whitespace"
    if any(c in "/|,;" for c in text):return "contains_slash_pipe_comma_semicolon"
    pieces=text.split(".")
    if any(not p for p in pieces):return "contains_empty_dot_segment"
    if any(p[0].isdigit() for p in pieces):return "leading_digit_any_segment"
    return "invalid_other"

def inventory(doc:object, expected_rows:int=20358,expected_parses:int=EXPECTED)->dict:
    require(isinstance(doc,dict) and "Dataset" in doc and "Version" in doc
            and isinstance(doc.get("Questions"),list)
            and len(doc["Questions"])==expected_rows,"FULL_ORIGINAL_TRAIN_DENOMINATOR")
    counts=Counter()
    originals=defaultdict(set) # ephemeral label values only for cardinality
    seen=set()
    frozen_reasons=Counter()
    for row in doc["Questions"]:
        require(isinstance(row,dict),"QUESTION_NOT_OBJECT")
        qid=row.get("Question-ID")
        question=row.get("RawQuestion")
        parses=row.get("Parses")
        require(isinstance(qid,str) and 0<len(qid.encode("utf-8"))<=256
                and qid not in seen,"ORIGINAL_QUESTION_ID")
        seen.add(qid)
        require(isinstance(question,str) and 0<len(question.encode("utf-8"))<=2048
                and all(ord(c)>=32 and ord(c)!=127 for c in question),
                "ORIGINAL_QUESTION_TEXT")
        require(isinstance(parses,list),"ORIGINAL_PARSE_ARRAY")
        for parse in parses:
            counts["original_parse_instances"]+=1
            require(isinstance(parse,dict),"ORIGINAL_PARSE_OBJECT")
            for field in ("TopicEntityMid","TopicEntityName",
                          "PotentialTopicEntityMention","InferentialChain"):
                require(isinstance(parse.get(field),str),"ORIGINAL_FLAT_SOURCE_SCHEMA")
            label=parse["InferentialChain"]
            _,status=baseline.admit_one_predicate(label)
            frozen_reasons[status]+=1
            if status=="accepted_one_opaque_predicate":
                counts["f109_accepted"]+=1
                originals["f109_accepted"].add(label)
            else:
                bucket=category(label)
                require(bucket in BUCKETS,"UNFORESEEN_REJECTION_BUCKET")
                counts[bucket]+=1
                originals[bucket].add(label)
            # Never inspect parse["Answers"], source target MIDs or topic names.
    require(counts["original_parse_instances"]==expected_parses
            and len(seen)==expected_rows,"ORIGINAL_WHOLE_POPULATION")
    require(sum(counts[b] for b in BUCKETS)+counts["f109_accepted"]==expected_parses,
            "ALL_ORIGINAL_PREDICATES_ACCOUNTED")
    if expected_rows==20358 and expected_parses==EXPECTED:
        require(counts["f109_accepted"]==BASELINE_ACCEPTED
                and sum(counts[b] for b in BUCKETS)==BASELINE_REJECTED
                and frozen_reasons["invalid_segment_syntax"]==11807
                and frozen_reasons["no_dotted_structure"]==1
                and sum(frozen_reasons.values())==EXPECTED,
                "PREREGISTERED_F109_BASELINE_DRIFT")
    return {
        "original_train_rows":expected_rows,
        "unique_source_question_ids":len(seen),
        "original_parse_instances":expected_parses,
        "f109_unchanged_status_counts":dict(sorted(frozen_reasons.items())),
        "exclusive_morphology_counts":{
            b:counts[b] for b in ("f109_accepted",*BUCKETS)
        },
        "distinct_source_predicate_cardinalities":{
            b:len(originals[b]) for b in ("f109_accepted",*BUCKETS)
        },
        "original_source_predicate_values_published":False,
        "question_answer_values_published":False,
        "source_answers_examined":False,
        "f109_source_grammar_modified":False,
    }

def audit(root:Path)->dict:
    root=root.resolve(strict=True)
    require(source.metadata(root,["rev-parse","HEAD"])==source.SOURCE_COMMIT,
            "SOURCE_REPOSITORY_HEAD")
    for path,sha in ((source.TRAIN,source.TRAIN_BLOB),
                     (source.DEV,source.DEV_BLOB),
                     (source.EVAL,source.EVAL_BLOB)):
        require(source.metadata(root,["rev-parse","HEAD:"+path])==sha,
                "SOURCE_BLOB_ID")
    require(not (root/source.DEV).exists() and not (root/source.EVAL).exists(),
            "DEV_EVAL_UNSEALED_IN_WORKTREE")
    raw=source.original_train(root)
    try:doc=json.loads(raw.decode("utf-8","strict"))
    except (UnicodeError,ValueError) as ex:raise Denied("F110O_ORIGINAL_TRAIN_JSON") from ex
    data=inventory(doc)
    return {
        "schema":SCHEMA,
        "status":"PUBLIC_FREEBASE_TRAIN_PREDICATE_REJECTION_MORPHOLOGY_ONLY",
        "source_repo":"kelvin-jiang/FreebaseQA",
        "source_commit":source.SOURCE_COMMIT,
        "train_git_blob":source.TRAIN_BLOB,
        "train_sha256":hashlib.sha256(raw).hexdigest(),
        "train_bytes":len(raw),
        "dev_git_blob_metadata_only":source.DEV_BLOB,
        "eval_git_blob_metadata_only":source.EVAL_BLOB,
        "cohort":data,
        "original_train_json_annotations_decoded":True,
        "original_answer_values_interpreted":False,
        "dev_eval_question_content_read":False,
        "freebase_original_graph_admission":"FREEBASE_GRAPH_SOURCE_NOT_QUALIFIED",
        "original_graph_archive_read":False,
        "original_graph_queries":0,
        "role_predictions_made":0,
        "qa_answers_scored":0,
        "independent_scientific_firstuse":False,
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
    a=p.parse_args()
    require(not a.out.exists(),"EVIDENCE_WOULD_OVERWRITE")
    payload=(json.dumps(audit(a.upstream),indent=2,sort_keys=True,
                        ensure_ascii=True)+"\n").encode("utf-8")
    with a.out.open("xb") as f:f.write(payload)
    print("F110O_COMPLETE_20358_TRAIN_QUESTIONS_37306_PARSES_ACCOUNTED")
    print("F110O_FROZEN_F109_ACCEPTANCE_AND_REJECTION_COUNTS_PRESERVED")
    print("F110O_ZERO_ANSWER_SCORES_NO_DEV_OR_EVAL")

if __name__=="__main__":
    try:main()
    except (Denied,source.Denied,OSError,UnicodeError,ValueError,
            KeyError,subprocess.SubprocessError) as ex:
        print("F110O_REJECTION_MORPHOLOGY_DENIED:",ex,file=sys.stderr)
        sys.exit(1)

"""F110-O Stage B: ONE preselected leading-dot source predicate candidate.

Source author TRAIN labels only. Never predicts question-to-role or answers.
Original F109 acceptance stays invariant and all source negatives accounted.
"""
from __future__ import annotations
import argparse
from collections import Counter,defaultdict
import hashlib
import json
from pathlib import Path
import re
import sys

import f109o_train_predicate_admission as base
import f110o_rejected_predicate_morphology as original

SCHEMA="forge.optimizer.f110o.original-train-leading-dot-candidate.v1"
SOURCE_STATUS="PUBLIC_FREEBASE_TRAIN_EMPTY_DOT_CANDIDATE_DIAGNOSTIC"
PRESELECTED=re.compile(r"\.[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)+\Z",
                       flags=re.ASCII)
CLASS=("leading_and_trailing_dot","leading_dot_only","trailing_dot_only",
       "interior_repeated_dot","other_empty_segment")

class Denied(Exception):pass
def need(value,reason):
    if not value:raise Denied("F110O_CANDIDATE_DENIED_"+reason)

def subtype(label:str)->str:
    if label.startswith(".") and label.endswith("."):
        return "leading_and_trailing_dot"
    if label.startswith("."):
        return "leading_dot_only"
    if label.endswith("."):
        return "trailing_dot_only"
    if ".." in label:
        return "interior_repeated_dot"
    return "other_empty_segment"

def candidate_one_role(label:object)->tuple[str|None,str]:
    if not isinstance(label,str):
        return None,"unsupported_original_type"
    if 0<len(label.encode("utf-8"))<=512 and PRESELECTED.fullmatch(label):
        return label,"candidate_one_leading_dot_accepted"
    return None,"candidate_additional_rejected"

def inspect(doc,rows=20358,parses=37306)->dict:
    need(isinstance(doc,dict) and
         isinstance(doc.get("Questions"),list) and
         len(doc["Questions"])==rows and
         "Dataset" in doc and "Version" in doc,"ORIGINAL_ROOT_COHORT")
    count=Counter()
    variants=defaultdict(set)
    qids=set()
    for row in doc["Questions"]:
        need(isinstance(row,dict),"ORIGINAL_ROW_NOT_OBJECT")
        qid=row.get("Question-ID")
        question=row.get("RawQuestion")
        parts=row.get("Parses")
        need(isinstance(qid,str) and 0<len(qid.encode("utf-8"))<=256 and
             qid not in qids,"ORIGINAL_QUESTION_ID")
        qids.add(qid)
        need(isinstance(question,str) and
             0<len(question.encode("utf-8"))<=2048 and
             all(ord(c)>=32 and ord(c)!=127 for c in question),
             "ORIGINAL_QUESTION_CONTROL")
        need(isinstance(parts,list),"ORIGINAL_PARSE_ARRAY")
        for rowparse in parts:
            count["original_parses"]+=1
            need(isinstance(rowparse,dict),"ORIGINAL_PARSE_OBJECT")
            for field in ("TopicEntityMid","TopicEntityName",
                          "PotentialTopicEntityMention","InferentialChain"):
                need(isinstance(rowparse.get(field),str),"ORIGINAL_FLAT_FIELDS")
            label=rowparse["InferentialChain"]
            _,status=base.admit_one_predicate(label)
            if status=="accepted_one_opaque_predicate":
                count["f109_accepted"]+=1
                variants["f109_accepted"].add(label)
            elif original.category(label)=="contains_empty_dot_segment":
                cls=subtype(label)
                need(cls in CLASS,"UNREGISTERED_SUBTYPE")
                count[cls]+=1
                variants[cls].add(label)
                opaque,disposition=candidate_one_role(label)
                count[disposition]+=1
                if opaque is not None:
                    variants[disposition].add(opaque)
                else:
                    variants[disposition].add(label)
            else:
                count["f109_non_empty_dot_rejected"]+=1
                variants["f109_non_empty_dot_rejected"].add(label)
            # No source answers, source MIDs, labels to role planner.
    need(len(qids)==rows and count["original_parses"]==parses,
         "ORIGINAL_COMPLETE_POPULATION")
    need(count["f109_accepted"]+
         sum(count[k] for k in CLASS)+count["f109_non_empty_dot_rejected"]==parses,
         "ALL_ORIGINAL_LABELS")
    need(count["candidate_one_leading_dot_accepted"]+
         count["candidate_additional_rejected"]==sum(count[k] for k in CLASS),
         "ALL_ORIGINAL_EMPTY_DOT_CANDIDATES")
    if rows==20358 and parses==37306:
        need(count["f109_accepted"]==25498 and
             sum(count[k] for k in CLASS)==11807 and
             count["f109_non_empty_dot_rejected"]==1,
             "FROZEN_F109_F110A_DENOMINATOR_DRIFT")
    names=("f109_accepted","f109_non_empty_dot_rejected",
           *CLASS,"candidate_one_leading_dot_accepted",
           "candidate_additional_rejected")
    return {
        "original_train_rows":rows,
        "source_unique_question_ids":len(qids),
        "original_parse_instances":parses,
        "exclusive_original_subtype_counts":{
            k:count[k] for k in ("f109_accepted","f109_non_empty_dot_rejected",*CLASS)
        },
        "one_preselected_candidate_status_counts":{
            k:count[k] for k in ("candidate_one_leading_dot_accepted",
                                "candidate_additional_rejected")
        },
        "source_label_cardinalities_only":{k:len(variants[k]) for k in names},
        "f109_predicate_grammar_modified":False,
        "original_source_predicate_values_published":False,
        "source_label_is_question_prediction":False,
        "source_answers_inspected":False,
        "role_direction_inferred":False,
    }

def audit(root:Path)->dict:
    root=root.resolve(strict=True)
    original_source=original.source
    need(original_source.metadata(root,["rev-parse","HEAD"])==
         original_source.SOURCE_COMMIT,"ORIGINAL_COMMIT")
    for rel,sha in ((original_source.TRAIN,original_source.TRAIN_BLOB),
                    (original_source.DEV,original_source.DEV_BLOB),
                    (original_source.EVAL,original_source.EVAL_BLOB)):
        need(original_source.metadata(root,["rev-parse","HEAD:"+rel])==sha,
             "ORIGINAL_SOURCE_GIT_OBJECT")
    need(not (root/original_source.DEV).exists() and
         not (root/original_source.EVAL).exists(),"RESERVED_SOURCE_UNSEALED")
    raw=original_source.original_train(root)
    try:doc=json.loads(raw.decode("utf-8","strict"))
    except (ValueError,UnicodeError) as ex:raise Denied("F110O_ORIGINAL_JSON") from ex
    from f110o_graph_custody_policy import evaluate_manifest
    graph=evaluate_manifest(None)
    need(graph["status"]=="FREEBASE_GRAPH_SOURCE_NOT_QUALIFIED" and
         graph["real_graph_calls"]==0,"GRAPH_ADMISSION_MUST_REMAIN_BLOCKED")
    return {
        "schema":SCHEMA,
        "status":SOURCE_STATUS,
        "source_repo":"kelvin-jiang/FreebaseQA",
        "source_commit":original_source.SOURCE_COMMIT,
        "source_train_git_blob":original_source.TRAIN_BLOB,
        "source_train_sha256":hashlib.sha256(raw).hexdigest(),
        "source_train_bytes":len(raw),
        "dev_blob_metadata_only":original_source.DEV_BLOB,
        "eval_blob_metadata_only":original_source.EVAL_BLOB,
        "candidate":inspect(doc),
        "original_freebase_graph_custody":graph,
        "train_annotation_objects_decoded":True,
        "train_answers_interpreted":False,
        "dev_eval_qa_read":False,
        "real_graph_source_read":False,
        "qa_answers_compared":0,
        "original_graph_queries":0,
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
    opts=p.parse_args()
    need(not opts.out.exists(),"NEW_AGGREGATE_OUTPUT_ONLY")
    payload=(json.dumps(audit(opts.upstream),indent=2,
                        sort_keys=True,ensure_ascii=True)+"\n").encode("utf-8")
    with opts.out.open("xb") as output:
        output.write(payload)
    print("F110O_FROZEN_ORIGINAL_TRAIN_37306_SUBTYPE_AND_CANDIDATE_COMPLETE")
    print("F110O_NO_QA_SCORING_NO_DIRECTION_NO_FREEBASE_GRAPH_OR_DEV_EVAL")

if __name__=="__main__":
    try:main()
    except (Denied,original.Denied,original.source.Denied,
            OSError,UnicodeError,ValueError,KeyError) as ex:
        print("F110O_SINGLE_LEADING_DOT_NOT_QUALIFIED:",ex,file=sys.stderr)
        sys.exit(1)

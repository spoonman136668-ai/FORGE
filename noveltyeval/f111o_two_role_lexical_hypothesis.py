"""F111-O: preregistered TWO dotted names separated by one ".." hypothesis.

This is a structural source-label parse on original FreebaseQA TRAIN only.
It does NOT predict a role from the question or infer graph traversal direction.
"""
from __future__ import annotations
import argparse
from collections import Counter,defaultdict
import hashlib
import json
from pathlib import Path
import sys

import f109o_train_predicate_admission as original_f109
import f110o_rejected_predicate_morphology as original_f110
import f110o_graph_custody_policy as graph_custody

SCHEMA="forge.optimizer.f111o.original-train-double-dot-two-role-hypothesis.v1"
STATUS="PUBLIC_FREEBASE_TRAIN_DOUBLE_DOT_TWO_ROLE_LEXICAL_DIAGNOSTIC"
EXPECTED_ROWS=20358
EXPECTED_PARSES=37306
EXPECTED_SINGLE=25498
EXPECTED_DOUBLE=11807
EXPECTED_OTHER=1
REASONS=("candidate_two_roles_lexically_admitted",
         "multiple_double_dot_delimiters",
         "left_predicate_invalid","right_predicate_invalid",
         "both_predicates_invalid","unsupported_other_source_label")

class Denied(Exception):pass

def require(ok:bool,reason:str):
    if not ok:raise Denied("F111O_SOURCE_TWO_ROLE_DENIED_"+reason)

def parse_two(value:object)->tuple[tuple[str,str]|None,str]:
    # Return source substrings to caller in ephemeral memory, never in report.
    if (not isinstance(value,str) or len(value.encode("utf-8"))>512 or
        not value or value.startswith(".") or value.endswith(".") or
        any(ord(c)<32 or ord(c)>126 for c in value) or ".." not in value):
        return None,"unsupported_other_source_label"
    if value.count("..")!=1:
        return None,"multiple_double_dot_delimiters"
    left,right=value.split("..",1)
    left_ok=original_f109.PREDICATE.fullmatch(left) is not None
    right_ok=original_f109.PREDICATE.fullmatch(right) is not None
    if left_ok and right_ok:
        return (left,right),"candidate_two_roles_lexically_admitted"
    if not left_ok and not right_ok:
        return None,"both_predicates_invalid"
    return None,"left_predicate_invalid" if not left_ok else "right_predicate_invalid"

def inventory(doc:object,expected_rows:int=EXPECTED_ROWS,
              expected_parses:int=EXPECTED_PARSES)->dict:
    require(isinstance(doc,dict) and "Dataset" in doc and "Version" in doc
            and isinstance(doc.get("Questions"),list)
            and len(doc["Questions"])==expected_rows,"COMPLETE_TRAIN_ROOT")
    counts=Counter()
    distinct=defaultdict(set) # ephemeral source values; only cardinality released
    qids=set()
    for record in doc["Questions"]:
        require(isinstance(record,dict),"ORIGINAL_QUESTION_OBJECT")
        qid=record.get("Question-ID")
        question=record.get("RawQuestion")
        parses=record.get("Parses")
        require(isinstance(qid,str) and 0<len(qid.encode("utf-8"))<=256 and
                qid not in qids,"ORIGINAL_UNIQUE_QUESTION_ID")
        qids.add(qid)
        require(isinstance(question,str) and
                0<len(question.encode("utf-8"))<=2048 and
                all(ord(c)>=32 and ord(c)!=127 for c in question),
                "ORIGINAL_BOUNDED_QUESTION")
        require(isinstance(parses,list),"ORIGINAL_PARSE_LIST")
        for p in parses:
            counts["original_parse_entries"]+=1
            require(isinstance(p,dict),"ORIGINAL_PARSE_OBJECT")
            for name in ("InferentialChain","TopicEntityMid","TopicEntityName",
                         "PotentialTopicEntityMention"):
                require(isinstance(p.get(name),str),"ORIGINAL_FLAT_FIELDS")
            relation=p["InferentialChain"]
            _,old=original_f109.admit_one_predicate(relation)
            if old=="accepted_one_opaque_predicate":
                counts["f109_original_single_accepted"]+=1
                distinct["f109_original_single_accepted"].add(relation)
                continue
            if original_f110.category(relation)!="contains_empty_dot_segment":
                counts["f109_original_other_rejected"]+=1
                distinct["f109_original_other_rejected"].add(relation)
                continue
            counts["f110_original_interior_double_dot"]+=1
            distinct["f110_original_interior_double_dot"].add(relation)
            require(".." in relation,"ORIGINAL_REJECTION_SUBTYPE_CHANGED")
            parts,status=parse_two(relation)
            require(status in REASONS,"UNREGISTERED_HYPOTHESIS_OUTCOME")
            counts[status]+=1
            distinct[status].add(relation)
            if parts is not None:
                require(len(parts)==2 and all(
                    original_f109.PREDICATE.fullmatch(s) for s in parts),
                    "PARTIAL_OR_NON_DOTTED_COMPONENTS")
            # Answers never inspected; no MID, topic, source role value published.
    require(len(qids)==expected_rows and
            counts["original_parse_entries"]==expected_parses and
            counts["f109_original_single_accepted"]+
            counts["f110_original_interior_double_dot"]+
            counts["f109_original_other_rejected"]==expected_parses,
            "ORIGINAL_COMPLETE_PREDICATE_DENOMINATOR")
    require(sum(counts[n] for n in REASONS)==
            counts["f110_original_interior_double_dot"],
            "ALL_ORIGINAL_DOUBLE_DOT_REJECTIONS_CLASSIFIED")
    if expected_rows==EXPECTED_ROWS and expected_parses==EXPECTED_PARSES:
        require(counts["f109_original_single_accepted"]==EXPECTED_SINGLE and
                counts["f110_original_interior_double_dot"]==EXPECTED_DOUBLE and
                counts["f109_original_other_rejected"]==EXPECTED_OTHER,
                "F110_PREREGISTERED_COHORT_DRIFT")
    all_names=("f109_original_single_accepted",
               "f110_original_interior_double_dot",
               "f109_original_other_rejected",*REASONS)
    return {
        "original_train_rows":expected_rows,
        "original_unique_question_ids":len(qids),
        "original_parse_entries":expected_parses,
        "f109_original_single_accepted":counts["f109_original_single_accepted"],
        "f110_original_interior_double_dot":counts["f110_original_interior_double_dot"],
        "f109_original_other_rejected":counts["f109_original_other_rejected"],
        "exclusive_two_role_hypothesis_outcomes":{n:counts[n] for n in REASONS},
        "source_label_cardinalities_only":{n:len(distinct[n]) for n in all_names},
        "two_roles_are_source_labels_not_predictions":True,
        "role_direction_known":False,
        "two_hop_graph_semantics_qualified":False,
        "answer_values_accessed":False,
        "source_relation_strings_published":False,
    }

def audit(root:Path)->dict:
    root=root.resolve(strict=True)
    source=original_f110.source
    require(source.metadata(root,["rev-parse","HEAD"])==source.SOURCE_COMMIT,
            "PINNED_EXTERNAL_HEAD")
    for path,expect in ((source.TRAIN,source.TRAIN_BLOB),
                        (source.DEV,source.DEV_BLOB),
                        (source.EVAL,source.EVAL_BLOB)):
        require(source.metadata(root,["rev-parse","HEAD:"+path])==expect,
                "ORIGINAL_SOURCE_GIT_ID")
    require(not (root/source.DEV).exists() and not (root/source.EVAL).exists(),
            "RESERVED_DEV_EVAL_MATERIALIZED")
    raw=source.original_train(root) # checks original object SHA1 and bytes
    try:
        source_doc=json.loads(raw.decode("utf-8","strict"))
    except (UnicodeError,ValueError) as e:
        raise Denied("ORIGINAL_SOURCE_JSON_INVALID") from e
    graph=graph_custody.evaluate_manifest(None)
    require(graph["status"]=="FREEBASE_GRAPH_SOURCE_NOT_QUALIFIED" and
            not graph["admitted"] and graph["real_graph_calls"]==0,
            "GRAPH_CUSTODY_MUST_REMAIN_DENIED")
    return {
        "schema":SCHEMA,"status":STATUS,
        "source_repository":"kelvin-jiang/FreebaseQA",
        "source_commit":source.SOURCE_COMMIT,
        "original_train_blob":source.TRAIN_BLOB,
        "original_train_sha256":hashlib.sha256(raw).hexdigest(),
        "original_train_bytes":len(raw),
        "dev_blob_metadata_only":source.DEV_BLOB,
        "eval_blob_metadata_only":source.EVAL_BLOB,
        "training_chain_census":inventory(source_doc),
        "source_graph_admission_status":graph["status"],
        "original_json_source_annotation_objects_decoded":True,
        "answers_interpreted_or_compared":False,
        "dev_eval_qa_content_read":False,
        "per_question_or_role_value_published":False,
        "question_to_role_predictor_qualified":False,
        "original_freebase_graph_queries":0,
        "real_qa_scores":0,
        "independent_scientific_firstuse":False,
        "accepted_science":False,
        "accepted_ref_mutation":False,
        "dream_pareto_promotion":False,
        "thetaevolve_accepted_training":False,
        "scientific_dispatch":False,
        "model_calls":0,"codex_calls":0,"cloudflare_writes":0,
    }

def main()->None:
    ap=argparse.ArgumentParser()
    ap.add_argument("--upstream",type=Path,required=True)
    ap.add_argument("--out",type=Path,required=True)
    args=ap.parse_args()
    require(not args.out.exists(),"DO_NOT_OVERWRITE_EVIDENCE")
    payload=(json.dumps(audit(args.upstream),sort_keys=True,
                       indent=2,ensure_ascii=True)+"\n").encode("utf-8")
    with args.out.open("xb") as stream:stream.write(payload)
    print("F111O_COMPLETE_PINNED_TRAIN_RELATION_LABEL_CENSUS=37306")
    print("F111O_NO_GOLD_QA_NO_EVAL_NO_DIRECTION_OR_REAL_GRAPH")

if __name__=="__main__":
    try:main()
    except (Denied,original_f110.Denied,original_f110.source.Denied,
            OSError,UnicodeError,ValueError,KeyError,
            original_f110.source.subprocess.SubprocessError) as exc:
        print("F111O_TWO_ROLE_LEXICAL_SOURCE_DENIED:",exc,file=sys.stderr)
        sys.exit(1)

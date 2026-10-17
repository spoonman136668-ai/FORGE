"""F109-O: unmodified original FreebaseQA TRAIN-only InferentialChain SHAPE.

The report contains ONLY counts, source cryptographic digests and deny flags.
No relation strings, field values, answers, MIDs or individual rows are emitted.
"""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import subprocess
import sys

SOURCE_COMMIT="d16aae5149aaa25e43ff2a7bd00a06f280ca19b9"
TRAIN="FreebaseQA-train.json"
TRAIN_BLOB="24dc4b13a9c4a0ad734732db094c124d086b7d67"
TRAIN_BYTES=23888089
DEV="FreebaseQA-dev.json"
DEV_BLOB="2e16ac381efb7b9e362cbf9bd0cee90006244ea8"
EVAL="FreebaseQA-eval.json"
EVAL_BLOB="d7d06ae721aedca26a0838d0113cddc1aa6774a8"
ROWS=20358
PARSES=37306
CHARS={".":"dot","/":"slash",",":"comma",";":"semicolon",
       "|":"pipe","#":"hash",":":"colon",">":"gt","<":"lt"}
COUNTER_SCHEMA="forge.optimizer.f109o.original-train-chain-shape.v1"

class Denied(Exception):pass
def ensure(ok:bool,reason:str):
    if not ok:raise Denied("F109O_CHAIN_SOURCE_DENIED_"+reason)

def metadata(root:Path,args:list[str])->str:
    ensure(args in (["rev-parse","HEAD"],["rev-parse","HEAD:"+TRAIN],
                    ["rev-parse","HEAD:"+DEV],["rev-parse","HEAD:"+EVAL]),
           "ONLY_METADATA_GIT_COMMANDS")
    p=subprocess.run(["git","-C",str(root),*args],stdout=subprocess.PIPE,
                     stderr=subprocess.PIPE,check=False,timeout=30)
    ensure(p.returncode==0,"GIT_IDENTITY_UNAVAILABLE")
    return p.stdout.decode("ascii","strict").strip()

def original_train(root:Path)->bytes:
    p=subprocess.run(["git","-C",str(root),"show","HEAD:"+TRAIN],
                     stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                     check=False,timeout=65)
    ensure(p.returncode==0 and len(p.stdout)==TRAIN_BYTES,
           "ORIGINAL_GIT_BYTES_UNAVAILABLE_OR_DRIFT")
    sha=hashlib.sha1(b"blob "+str(len(p.stdout)).encode("ascii")+
                     bytes([0])+p.stdout).hexdigest()
    ensure(sha==TRAIN_BLOB,"ORIGINAL_GIT_BLOB_IDENTITY_DRIFT")
    return p.stdout

def band(text:str)->str:
    size=len(text.encode("utf-8"))
    if size==0:return "empty"
    if size<=32:return "bytes_001_032"
    if size<=128:return "bytes_033_128"
    if size<=512:return "bytes_129_512"
    return "bytes_513_plus"

def arity(count:int)->str:
    if count<=0:return "zero"
    if count==1:return "one"
    if count==2:return "two"
    if count==3:return "three"
    return "four_plus"

def inventory(doc:object,expected_rows:int=ROWS,expected_parses:int=PARSES)->dict:
    ensure(isinstance(doc,dict) and "Dataset" in doc and "Version" in doc and
           isinstance(doc.get("Questions"),list) and
           len(doc["Questions"])==expected_rows,"COMPLETE_ORIGINAL_TRAIN_ROWS")
    seen=set()
    source_values=set() # transient distinctness only; never returned
    counts=Counter()
    for row in doc["Questions"]:
        ensure(isinstance(row,dict),"ORIGINAL_QUESTION_NOT_OBJECT")
        key=row.get("Question-ID")
        question=row.get("RawQuestion")
        parses=row.get("Parses")
        ensure(isinstance(key,str) and 0<len(key.encode("utf-8"))<=256
               and key not in seen,"REPEATED_OR_BAD_ORIGINAL_QID")
        seen.add(key)
        ensure(isinstance(question,str) and
               0<len(question.encode("utf-8"))<=2048 and
               all(ord(c)>=32 and ord(c)!=127 for c in question),
               "ORIGINAL_QUESTION_FIELD_INVALID")
        ensure(isinstance(parses,list),"PARSE_LIST_SCHEMA")
        counts["source_question_rows"]+=1
        for record in parses:
            counts["original_parse_entries"]+=1
            ensure(isinstance(record,dict),"ORIGINAL_PARSE_NOT_OBJECT")
            for field in ("TopicEntityMid","TopicEntityName",
                          "PotentialTopicEntityMention","InferentialChain"):
                ensure(isinstance(record.get(field),str),"FROZEN_FLAT_SOURCE_FIELD")
            counts["answer_subtree_presence_only"]+=int("Answers" in record)
            value=record["InferentialChain"]
            source_values.add(value)
            counts["chain_"+band(value)]+=1
            counts["chain_printable_ascii"]+=int(all(32<=ord(c)<=126 for c in value))
            counts["chain_contains_non_ascii"]+=int(any(ord(c)>=128 for c in value))
            counts["chain_has_control"]+=int(any(ord(c)<32 or ord(c)==127 for c in value))
            counts["chain_has_whitespace"]+=int(any(c.isspace() for c in value))
            counts["chain_starts_slash"]+=int(value.startswith("/"))
            for char,label in CHARS.items():
                counts["chain_contains_"+label]+=int(char in value)
            counts["chain_comma_split_"+arity(len(value.split(",")))]+=1
            counts["chain_whitespace_split_"+arity(len(value.split()))]+=1
    ensure(counts["source_question_rows"]==expected_rows and
           len(seen)==expected_rows and
           counts["original_parse_entries"]==expected_parses,
           "ORIGINAL_TRAIN_FULL_PARSE_DENOMINATOR")
    return {
        "original_train_rows":counts["source_question_rows"],
        "original_train_distinct_ids":len(seen),
        "original_parse_entries":counts["original_parse_entries"],
        "distinct_full_opaque_chain_strings":len(source_values),
        "source_only_count_categories":dict(sorted(counts.items())),
        "actual_chain_values_published":False,
        "source_question_strings_published":False,
        "answer_subtree_walked":False,
    }

def audit(root:Path)->dict:
    root=root.resolve(strict=True)
    ensure(metadata(root,["rev-parse","HEAD"])==SOURCE_COMMIT,"ORIGINAL_HEAD_DRIFT")
    for rel,want in ((TRAIN,TRAIN_BLOB),(DEV,DEV_BLOB),(EVAL,EVAL_BLOB)):
        ensure(metadata(root,["rev-parse","HEAD:"+rel])==want,"ORIGINAL_BLOB_DRIFT")
    ensure(not (root/DEV).exists() and not (root/EVAL).exists(),
           "DEV_OR_EVAL_SOURCE_MATERIALIZED")
    data=original_train(root)
    try:doc=json.loads(data.decode("utf-8","strict"))
    except (ValueError,UnicodeError) as ex:raise Denied("F109O_ORIGINAL_JSON_INVALID") from ex
    return {
        "schema":COUNTER_SCHEMA,
        "status":"PUBLIC_FREEBASE_TRAIN_CHAIN_SHAPE_ENGINEERING_ONLY",
        "source_repo":"kelvin-jiang/FreebaseQA",
        "source_commit":SOURCE_COMMIT,
        "train_original_git_blob":TRAIN_BLOB,
        "train_original_sha256":hashlib.sha256(data).hexdigest(),
        "train_bytes":len(data),
        "dev_git_blob_metadata_only":DEV_BLOB,
        "eval_git_blob_metadata_only":EVAL_BLOB,
        "source_shape":inventory(doc),
        "original_train_annotation_objects_json_decoded":True,
        "source_answers_inspected":False,
        "source_roles_values_published":False,
        "dev_eval_qa_read":False,
        "source_role_planner_qualified":False,
        "source_graph_admission_qualified":False,
        "independent_scientific_firstuse":False,
        "accepted_science":False,
        "accepted_ref_mutation":False,
        "dream_pareto_promotion":False,
        "thetaevolve_accepted_training":False,
        "science_dispatch":False,
        "model_calls":0,"codex_calls":0,"cloudflare_writes":0,
    }

def main()->None:
    p=argparse.ArgumentParser()
    p.add_argument("--upstream",required=True,type=Path)
    p.add_argument("--out",required=True,type=Path)
    a=p.parse_args()
    ensure(not a.out.exists(),"NO_EVIDENCE_OVERWRITE")
    payload=(json.dumps(audit(a.upstream),sort_keys=True,
                        indent=2,ensure_ascii=True)+"\n").encode("utf-8")
    with a.out.open("xb") as f:f.write(payload)
    print("F109O_TRAIN_CHAIN_SHAPE_ONLY_20358_QUESTIONS_37306_PARSES")
    print("F109O_NO_ROLE_LABEL_VALUES_NO_QA_SCORE_NO_DEV_EVAL")

if __name__=="__main__":
    try:main()
    except (Denied,OSError,UnicodeError,ValueError,
            KeyError,subprocess.SubprocessError) as ex:
        print("F109O_ORIGINAL_TRAIN_CHAIN_DENIED:",ex,file=sys.stderr)
        sys.exit(1)

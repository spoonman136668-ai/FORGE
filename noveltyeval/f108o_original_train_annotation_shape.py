"""F108-O strict TRAIN-only original annotation PATH/TYPE audit.

No actual question string, MID, topic mention, relationship or answer value is
stored, printed or exported. Answers subtree is NEVER descended into.
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

UPSTREAM="d16aae5149aaa25e43ff2a7bd00a06f280ca19b9"
TRAIN="FreebaseQA-train.json"
TRAIN_BLOB="24dc4b13a9c4a0ad734732db094c124d086b7d67"
DEV="FreebaseQA-dev.json"
DEV_BLOB="2e16ac381efb7b9e362cbf9bd0cee90006244ea8"
EVAL="FreebaseQA-eval.json"
EVAL_BLOB="d7d06ae721aedca26a0838d0113cddc1aa6774a8"
TRAIN_BYTES=23888089
TRAIN_ROWS=20358
KEY=re.compile(r"^[A-Za-z][A-Za-z0-9_ -]{0,63}$")
MAX_PATHS=512
MAX_DEPTH=6

class Denied(Exception):pass

def require(ok:bool,reason:str):
    if not ok: raise Denied("F108O_TRAIN_SHAPE_DENIED_"+reason)

def git_info(root:Path,op:list[str])->str:
    require(op in (["rev-parse","HEAD"],["rev-parse","HEAD:"+TRAIN],
                   ["rev-parse","HEAD:"+DEV],["rev-parse","HEAD:"+EVAL]),
            "GIT_METADATA_SCOPE")
    p=subprocess.run(["git","-C",str(root),*op],stdout=subprocess.PIPE,
                     stderr=subprocess.PIPE,check=False,timeout=30)
    require(p.returncode==0,"SOURCE_COMMIT_UNAVAILABLE")
    return p.stdout.decode("ascii","strict").strip()

def source_train(root:Path)->bytes:
    p=subprocess.run(["git","-C",str(root),"show","HEAD:"+TRAIN],
                     stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=False,timeout=65)
    require(p.returncode==0 and len(p.stdout)==TRAIN_BYTES,"SOURCE_SIZE")
    return p.stdout

def blob_id(raw:bytes)->str:
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+bytes([0])+raw).hexdigest()

def kind(value)->str:
    if value is None:return "null"
    if isinstance(value,bool):return "boolean"
    if isinstance(value,str):return "string"
    if isinstance(value,(int,float)):return "number"
    if isinstance(value,dict):return "object"
    if isinstance(value,list):return "array"
    raise Denied("F108O_UNEXPECTED_JSON_TYPE")

def shape(value,path:str,counter:Counter,unsafe:Counter,depth=0):
    if depth>MAX_DEPTH:
        counter[(path,"depth_budget_refused")]+=1
        return
    counter[(path,kind(value))]+=1
    require(len(counter)<=MAX_PATHS,"SOURCE_PATH_CARDINALITY")
    if isinstance(value,dict):
        for name,child in value.items():
            if not isinstance(name,str) or KEY.fullmatch(name) is None:
                unsafe["unsafe_original_object_keys"]+=1
                continue
            # Do not follow any label/answer subtree whatsoever.
            if name.casefold()=="answers" or name.casefold().startswith("answers"):
                unsafe["skipped_answer_subtree_occurrences"]+=1
                counter[(path+"."+name,"skipped_answer_subtree")]+=1
                require(len(counter)<=MAX_PATHS,"SOURCE_PATH_CARDINALITY")
                continue
            shape(child,path+"."+name,counter,unsafe,depth+1)
    elif isinstance(value,list):
        for child in value:
            shape(child,path+"[]",counter,unsafe,depth+1)

def inventory(raw:bytes)->dict:
    require(0<len(raw)<=30*1024*1024,"SOURCE_BUDGET")
    try:doc=json.loads(raw.decode("utf-8","strict"))
    except (UnicodeError,ValueError) as exc:raise Denied("F108O_SOURCE_JSON_INVALID") from exc
    require(isinstance(doc,dict) and
            all(n in doc for n in ("Dataset","Version","Questions")) and
            isinstance(doc["Questions"],list) and len(doc["Questions"])==TRAIN_ROWS,
            "ORIGINAL_QUESTION_DENOMINATOR")
    counter=Counter()
    unsafe=Counter()
    ids=set()
    original_parse_entries=0
    for row in doc["Questions"]:
        require(isinstance(row,dict) and "Question-ID" in row
                and "RawQuestion" in row and "Parses" in row,"ORIGINAL_QUESTION_SCHEMA")
        identifier=row["Question-ID"]
        question=row["RawQuestion"]
        require(isinstance(identifier,str) and 0<len(identifier.encode("utf-8"))<=256
                and identifier not in ids,"ID_DUPLICATE_OR_INVALID")
        ids.add(identifier)
        require(isinstance(question,str) and 0<len(question.encode("utf-8"))<=2048
                and all(ord(c)>=32 and ord(c)!=127 for c in question),
                "QUESTION_INVALID")
        parses=row["Parses"]
        if isinstance(parses,list):
            original_parse_entries+=len(parses)
        shape(parses,"Questions[].Parses",counter,unsafe)
    # Sort only schema paths/types, never source values.
    return {
        "original_train_rows":len(doc["Questions"]),
        "unique_question_ids":len(ids),
        "original_parse_entries":original_parse_entries,
        "schema_occurrences":[
            {"path":p,"json_type":typ,"count":count}
            for (p,typ),count in sorted(counter.items())
        ],
        "unsafe_original_key_count":unsafe["unsafe_original_object_keys"],
        "answers_subtrees_skipped":unsafe["skipped_answer_subtree_occurrences"],
        "path_type_entries":len(counter),
        "no_source_scalar_values_published":True,
        "no_answer_subtree_walked":True,
    }

def audit(root:Path)->dict:
    root=root.resolve(strict=True)
    require(git_info(root,["rev-parse","HEAD"])==UPSTREAM,"UPSTREAM_HEAD")
    for name,digest in ((TRAIN,TRAIN_BLOB),(DEV,DEV_BLOB),(EVAL,EVAL_BLOB)):
        require(git_info(root,["rev-parse","HEAD:"+name])==digest,"UPSTREAM_GIT_OBJECT")
    require(not (root/DEV).exists() and not (root/EVAL).exists(),
            "DEV_OR_EVAL_MATERIALIZED")
    raw=source_train(root)
    require(blob_id(raw)==TRAIN_BLOB,"ORIGINAL_TRAIN_CONTENT")
    return {
        "schema":"forge.optimizer.f108o.original-freebase-train-annotation-shape.v1",
        "status":"PUBLIC_FREEBASE_TRAIN_SCHEMA_SHAPE_ONLY",
        "source_repo":"kelvin-jiang/FreebaseQA",
        "source_commit":UPSTREAM,
        "train_git_blob":TRAIN_BLOB,
        "train_bytes_sha256":hashlib.sha256(raw).hexdigest(),
        "train_original_bytes":len(raw),
        "dev_git_blob_metadata_only":DEV_BLOB,
        "eval_git_blob_metadata_only":EVAL_BLOB,
        "field_depth_budget":MAX_DEPTH,
        "source_data":inventory(raw),
        "dev_or_eval_qa_bytes_read":False,
        "train_original_field_values_published":False,
        "train_answers_used_for_linking":False,
        "trained_linker_modified":False,
        "new_scientific_firstuse":False,
        "qualified_entity_linker":False,
        "qualified_role_translator":False,
        "qualified_freebase_graph":False,
        "accepted_science":False,
        "accepted_ref_mutation":False,
        "dream_pareto_promotion":False,
        "thetaevolve_accepted_training":False,
        "science_dispatch":False,
        "model_calls":0,"codex_calls":0,"cloudflare_writes":0,
    }

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--upstream",required=True,type=Path)
    ap.add_argument("--out",required=True,type=Path)
    a=ap.parse_args()
    require(not a.out.exists(),"OUTPUT_OVERWRITE")
    result=audit(a.upstream)
    with a.out.open("xb") as stream:
        stream.write((json.dumps(result,sort_keys=True,indent=2,ensure_ascii=True)+"\n").encode("utf-8"))
    print("F108O_TRAIN_SCHEMA_SHAPE_ONLY=PASS")
    print("F108O_FULL_TRAIN_QUESTION_AND_PARSE_DENOMINATOR_PRESERVED")
    print("F108O_ZERO_ANSWER_VALUES_DEV_EVAL_AND_SCIENCE")

if __name__=="__main__":
    try:main()
    except (Denied,OSError,ValueError,KeyError,UnicodeError,subprocess.SubprocessError) as ex:
        print("F108O_TRAIN_SHAPE_BLOCKED:",ex,file=sys.stderr)
        sys.exit(1)

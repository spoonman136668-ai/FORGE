"""F106-O complete ORIGINAL FreebaseQA TRAIN/DEV structural question inventory.

Original JSON annotation objects are decoded by json.loads as part of the
source file, but label-side Pars es/Answers/InferentialChain fields are never
inspected, forwarded into an adapter, compared or published. Eval remains sealed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

REPO = "kelvin-jiang/FreebaseQA"
HEAD = "d16aae5149aaa25e43ff2a7bd00a06f280ca19b9"
MAX_BYTES = 30 * 1024 * 1024
MAX_ROWS = 25000
SPLITS = {
    "train": ("FreebaseQA-train.json", "24dc4b13a9c4a0ad734732db094c124d086b7d67", 23888089, 20358),
    "dev": ("FreebaseQA-dev.json", "2e16ac381efb7b9e362cbf9bd0cee90006244ea8", 4656349, 3994),
}
EVAL_FILE = "FreebaseQA-eval.json"
EVAL_BLOB = "d7d06ae721aedca26a0838d0113cddc1aa6774a8"

class Denied(Exception):
    pass

def require(ok: bool, why: str) -> None:
    if not ok:
        raise Denied("F106O_ORIGINAL_DEV_SOURCE_DENIED_" + why)

def git_metadata(root: Path, op: list[str]) -> str:
    allowed = (
        op == ["rev-parse", "HEAD"]
        or (len(op)==2 and op[0]=="rev-parse" and op[1].startswith("HEAD:") and
            op[1][5:] in (EVAL_FILE, *(t[0] for t in SPLITS.values())))
    )
    require(allowed, "GIT_OPERATION_NOT_AUTHORIZED")
    p = subprocess.run(["git", "-C", str(root), *op],
                       check=False, stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE, timeout=25)
    require(p.returncode==0, "GIT_METADATA_MISSING")
    return p.stdout.decode("ascii", "strict").strip()

def git_dev_bytes(root: Path, rel: str) -> bytes:
    require(rel in {c[0] for c in SPLITS.values()},
            "EVALUATION_BYTES_UNAUTHORIZED")
    p = subprocess.run(["git","-C",str(root),"show","HEAD:"+rel],
                       check=False,stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE,timeout=60)
    require(p.returncode == 0 and 0 < len(p.stdout) <= MAX_BYTES,
            "DEVELOPMENT_GIT_BLOB_NOT_AVAILABLE_OR_OVERSIZED")
    return p.stdout

def blob_sha1(b: bytes) -> str:
    return hashlib.sha1(b"blob "+str(len(b)).encode("ascii")+bytes([0])+b).hexdigest()

def question_length_band(value: str) -> str:
    n=len(value.encode("utf-8"))
    if n<=128: return "001_128"
    if n<=256: return "129_256"
    if n<=512: return "257_512"
    return "513_2048"

def inventory(raw: bytes, expected_rows: int) -> dict:
    require(0 < len(raw) <= MAX_BYTES, "BYTE_CAP")
    try:
        doc=json.loads(raw.decode("utf-8","strict"))
    except (UnicodeError,ValueError) as exc:
        raise Denied("F106O_INVALID_ORIGINAL_JSON") from exc
    require(isinstance(doc,dict) and
            "Dataset" in doc and "Version" in doc and "Questions" in doc,
            "DOCUMENTED_ROOT_SCHEMA")
    entries=doc["Questions"]
    require(isinstance(entries,list) and 0 < len(entries) <= MAX_ROWS and
            len(entries)==expected_rows,
            "WHOLE_ORIGINAL_TRAIN_DEV_DENOMINATOR_DRIFT")
    ids=set()
    lengths={"001_128":0,"129_256":0,"257_512":0,"513_2048":0}
    for row in entries:
        require(isinstance(row,dict), "QUESTION_SCHEMA_NOT_OBJECT")
        require("Question-ID" in row and "RawQuestion" in row and
                "ProcessedQuestion" in row and "Parses" in row,
                "ORIGINAL_QUESTION_FIELD_MISSING")
        identifier=row["Question-ID"]
        question=row["RawQuestion"]
        require(isinstance(identifier,str) and 0 < len(identifier) <= 256,
                "INVALID_QUESTION_ID")
        require(identifier not in ids, "ORIGINAL_QUESTION_IDS_NOT_UNIQUE")
        ids.add(identifier)
        require(isinstance(question,str) and 0 < len(question.encode("utf-8")) <= 2048,
                "INVALID_RAW_QUESTION_SIZE")
        require(all(ord(c)>=32 and ord(c)!=127 for c in question),
                "INVALID_RAW_QUESTION_CONTROL")
        lengths[question_length_band(question)]+=1
        # Explicitly NEVER look inside row["Parses"], never inspect answer
        # labels, inferred chains, processed question, or topic MID values.
    require(sum(lengths.values())==expected_rows and len(ids)==expected_rows,
            "INCOMPLETE_POPULATION_ACCOUNTING")
    return {
        "original_questions":expected_rows,
        "unique_question_ids":len(ids),
        "raw_question_length_bands":lengths,
        "question_values_published":False,
        "annotation_values_accessed_by_adapter":False,
        "development_labels_used_for_planning":False,
    }

def audit(root: Path) -> dict:
    root=root.resolve(strict=True)
    require(root.is_dir(), "SOURCE_ROOT_NOT_DIRECTORY")
    require(git_metadata(root,["rev-parse","HEAD"])==HEAD,
            "INDEPENDENT_SOURCE_COMMIT_DRIFT")
    require(git_metadata(root,["rev-parse","HEAD:"+EVAL_FILE])==EVAL_BLOB,
            "EVAL_ORIGINAL_SOURCE_IDENTITY_DRIFT")
    require(not (root/EVAL_FILE).exists(), "EVAL_SPARSE_SOURCE_MATERIALIZED")
    sources={}
    for split,(rel,expected_blob,expected_bytes,expected_rows) in SPLITS.items():
        require(git_metadata(root,["rev-parse","HEAD:"+rel])==expected_blob,
                "ORIGINAL_DEV_BLOB_REFERENCE_DRIFT")
        raw=git_dev_bytes(root,rel)
        require(blob_sha1(raw)==expected_blob and len(raw)==expected_bytes,
                "IMMUTABLE_DEV_OBJECT_OR_SIZE_DRIFT")
        inv=inventory(raw,expected_rows)
        sources[split]={
            "source_git_blob":expected_blob,
            "source_sha256":hashlib.sha256(raw).hexdigest(),
            "source_bytes":len(raw),
            **inv,
        }
    return {
        "schema":"forge.optimizer.f106o.cross-kg-dev-question-schema.v1",
        "status":"PUBLIC_CROSS_KG_DEV_INTERFACE_ONLY",
        "source_repo":REPO,
        "source_commit":HEAD,
        "source_license":"CC-BY-4.0",
        "dev_splits":sources,
        "full_original_dev_population":sum(x["original_questions"] for x in sources.values()),
        "evaluation_git_blob_metadata":EVAL_BLOB,
        "eval_file_materialized":False,
        "eval_question_bytes_read":False,
        "eval_questions_scored":0,
        "raw_question_values_published":False,
        "development_annotation_objects_decoded_with_json":True,
        "development_annotation_values_interpreted":False,
        "development_annotation_values_supplied_to_adapter":False,
        "cross_graph_entity_linker_qualified":False,
        "cross_graph_role_translator_qualified":False,
        "independent_freebase_graph_qualified":False,
        "external_generalization_qualified":False,
        "new_scientific_firstuse":False,
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
    require(not a.out.exists(),"OUTPUT_EXISTS")
    evidence=audit(a.upstream)
    data=(json.dumps(evidence,sort_keys=True,indent=2,ensure_ascii=True)+"\n").encode("utf-8")
    with a.out.open("xb") as f:
        f.write(data)
    print("F106O_COMPLETE_FREEBASEQA_DEVELOPMENT_ROWS="+str(evidence["full_original_dev_population"]))
    print("F106O_EVAL_BYTES_ANSWERS_SCORES=ZERO")
    print("F106O_CROSS_GRAPH_LINKER_ROLE_TRANSLATOR_AND_ACCEPTED_SCIENCE=UNQUALIFIED")

if __name__=="__main__":
    try:
        main()
    except (Denied,OSError,UnicodeError,KeyError,subprocess.SubprocessError) as exc:
        print("F106O_ORIGINAL_TRAIN_DEV_READ_ONLY_DENIED:",exc,file=sys.stderr)
        sys.exit(1)

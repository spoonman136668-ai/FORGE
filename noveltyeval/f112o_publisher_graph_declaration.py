"""F112-O authenticate original publisher README/license, NOT Freebase graph bytes.

Sparse publisher documentation only. Original TRAIN/DEV/EVAL/partial QA files
must never be read, decoded, downloaded or checked out in this gate.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

from f110o_graph_custody_policy import evaluate_manifest

REPO="kelvin-jiang/FreebaseQA"
HEAD="d16aae5149aaa25e43ff2a7bd00a06f280ca19b9"
SOURCE_OBJECTS={
    "README.md":("dd4c65cbe5428b2a86afc47ae2309cb11328b31b",3564),
    "LICENSE":("10fabd90118f7ce38bb2e4753e105e744442a429",18658),
}
DENIED_SPLITS=(
    "FreebaseQA-train.json","FreebaseQA-dev.json",
    "FreebaseQA-eval.json","FreebaseQA-partial.json",
)
GRAPH_LINK="https://www.dropbox.com/sh/a25p7j2ir8gqnvx/AABJvjoI9mbHYj3hyfuxSdGaa?dl=0"
SCHEMA="forge.optimizer.f112o.publisher-graph-declaration-custody.v1"

class Denied(Exception):pass
def require(ok:bool,why:str):
    if not ok:raise Denied("F112O_PUBLISHER_DOC_DENIED_"+why)

def git_metadata(root:Path,cmd:list[str])->str:
    require(cmd==["rev-parse","HEAD"] or
            (len(cmd)==2 and cmd[0]=="rev-parse" and
             cmd[1] in ("HEAD:README.md","HEAD:LICENSE")) or
            (len(cmd)==3 and cmd[:2]==["cat-file","-s"] and
             cmd[2] in ("HEAD:README.md","HEAD:LICENSE")),
            "GIT_METADATA_SCOPE")
    p=subprocess.run(["git","-C",str(root),*cmd],
                     stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                     check=False,timeout=20)
    require(p.returncode==0,"PINNED_SOURCE_GIT_METADATA_UNAVAILABLE")
    return p.stdout.decode("ascii","strict").strip()

def document_bytes(root:Path,name:str)->bytes:
    require(name in SOURCE_OBJECTS,"QA_SOURCE_READ_FORBIDDEN")
    p=subprocess.run(["git","-C",str(root),"show","HEAD:"+name],
                     stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                     check=False,timeout=20)
    want_id,want_bytes=SOURCE_OBJECTS[name]
    require(p.returncode==0 and len(p.stdout)==want_bytes,
            "DOCUMENT_BYTES_NOT_ORIGINAL")
    sha=hashlib.sha1(b"blob "+str(len(p.stdout)).encode("ascii")+bytes([0])+p.stdout).hexdigest()
    require(sha==want_id,"DOCUMENT_ORIGINAL_GIT_BLOB_DRIFT")
    return p.stdout

def interpret_declaration(readme:str,license_text:str)->dict:
    require("FreebaseQA (v1.0)" in readme,
            "ORIGINAL_FREEBASEQA_VERSION")
    require("2.2GB zip" in readme and "16M" in readme and
            "182M" in readme,"PUBLISHER_APPROX_GRAPH_COUNTS")
    require(GRAPH_LINK in readme,"PUBLISHER_GRAPH_URL_DRIFT")
    require("from the topic entity node to the answer node" in readme,
            "AUTHOR_LOGICAL_TOPIC_TO_ANSWER_ORDER_DRIFT")
    require("CC-BY-4.0" in readme and "Attribution 4.0 International" in license_text,
            "AUTHOR_ATTRIBUTION_LICENSE_DRIFT")
    require("triple" in readme.lower(),"PUBLISHER_SOURCE_TRIPLE_CONTEXT")
    return {
        "publisher_graph_zip_approx_2_2_gb_documented":True,
        "publisher_approx_entities_16m_documented":True,
        "publisher_approx_triples_182m_documented":True,
        "publisher_original_external_archive_link_documented":True,
        "author_declares_logical_topic_to_answer_path":True,
        "logical_order_is_graph_edge_orientation":False,
        "original_graph_archive_sha256_provided_in_readme":False,
        "exact_original_graph_edge_denominator_measured":False,
        "original_graph_archive_bytes_read":False,
        "original_graph_archive_link_downloaded":False,
        "source_member_layout_verified":False,
        "independent_edge_direction_witness":False,
        "original_graph_ready_for_query":False,
    }

def audit(root:Path)->dict:
    root=root.resolve(strict=True)
    require(root.is_dir(),"SOURCE_FOLDER")
    require(git_metadata(root,["rev-parse","HEAD"])==HEAD,
            "PUBLISHER_COMMIT_DRIFT")
    docs={}
    for name,(want_id,want_size) in SOURCE_OBJECTS.items():
        require(git_metadata(root,["rev-parse","HEAD:"+name])==want_id,
                "PUBLISHER_DOC_BLOB_DRIFT")
        require(git_metadata(root,["cat-file","-s","HEAD:"+name])==str(want_size),
                "PUBLISHER_DOC_SIZE_DRIFT")
        raw=document_bytes(root,name)
        docs[name]={
            "original_git_blob":want_id,
            "original_sha256":hashlib.sha256(raw).hexdigest(),
            "original_bytes":len(raw),
        }
    for path in DENIED_SPLITS:
        require(not (root/path).exists(),"QA_SPLIT_MATERIALIZED")
    raw_readme=document_bytes(root,"README.md").decode("utf-8","strict")
    raw_license=document_bytes(root,"LICENSE").decode("utf-8","strict")
    declaration=interpret_declaration(raw_readme,raw_license)
    graph=evaluate_manifest(None)
    require(graph["status"]=="FREEBASE_GRAPH_SOURCE_NOT_QUALIFIED" and
            not graph["admitted"] and graph["real_graph_calls"]==0,
            "GRAPH_POLICY_COULD_NOT_BE_QUALIFIED")
    return {
        "schema":SCHEMA,
        "status":"PUBLISHER_GRAPH_DECLARATION_VERIFIED_ARCHIVE_UNQUALIFIED",
        "source_repository":REPO,
        "source_commit":HEAD,
        "publisher_original_docs":docs,
        "publisher_declaration":declaration,
        "graph_source_missing_or_invalid_fields":graph["missing_or_invalid_metadata_fields"],
        "graph_custody_status":graph["status"],
        "real_freebase_archive_read":False,
        "original_qa_split_contents_read":False,
        "source_qa_answers_read":False,
        "original_graph_edge_orientation_qualified":False,
        "graph_queries_executed":0,
        "independent_scientific_firstuse":False,
        "accepted_science":False,
        "accepted_ref_mutation":False,
        "dream_pareto_promotion":False,
        "thetaevolve_accepted_training":False,
        "scientific_dispatch":False,
        "model_calls":0,"codex_calls":0,"cloudflare_writes":0,
    }

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--upstream-sparse",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    args=p.parse_args()
    require(not args.out.exists(),"REFUSE_OUTPUT_OVERWRITE")
    out=(json.dumps(audit(args.upstream_sparse),sort_keys=True,
                    indent=2,ensure_ascii=True)+"\n").encode("utf-8")
    with args.out.open("xb") as stream:stream.write(out)
    print("F112O_PUBLISHER_GRAPH_DECLARATION_AND_IMMUTABLE_DOCS_VERIFIED")
    print("F112O_REAL_ARCHIVE_ORIENTATION_ANSWERS_AND_SCIENCE_NOT_QUALIFIED")

if __name__=="__main__":
    try:main()
    except (Denied,OSError,ValueError,UnicodeError,subprocess.SubprocessError) as ex:
        print("F112O_PUBLISHER_SOURCE_OR_ARCHIVE_CUSTODY_DENIED:",ex,file=sys.stderr)
        sys.exit(1)

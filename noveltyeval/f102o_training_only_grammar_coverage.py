"""F102-O TRAIN-only whole-cohort deterministic grammar coverage; no QA prediction."""
from __future__ import annotations
import argparse
import hashlib
import json
import pathlib
import subprocess
import sys

HEAD="826ee617e4da5b087584b0e03c70fe76642c6188"
COHORTS=(
 (2,"metaqa/original/2-hop/qa_train.txt","d2ce0a9f3670769f4239baa4eb6bf7bdc91d9468",118980),
 (3,"metaqa/original/3-hop/qa_train.txt","77409d56af8d1fde7a4bec23cf5e1df1e0a08e59",114196),
)

class Denied(Exception):
    pass

def require(check: bool,reason: str):
    if not check: raise Denied("F102O_TRAIN_ONLY_DENIED_"+reason)

def git_blob(data: bytes) -> str:
    return hashlib.sha1(b"blob "+str(len(data)).encode("ascii")+b"\x00"+data).hexdigest()

def question_only(data: bytes,expected: int) -> bytes:
    require(0<len(data)<=30*1024*1024,"ORIGINAL_SOURCE_BYTE_BUDGET")
    lines=data.splitlines()
    require(len(lines)==expected,"WHOLE_TRAIN_COHORT_DENOMINATOR_DRIFT")
    qlist=[]
    for line in lines:
        q,sep,_=line.partition(b"\t")
        require(sep==b"\t" and len(q)>0,"MALFORMED_TRAIN_SOURCE_ROW")
        require(b"\r" not in q and b"\n" not in q,"QUESTION_CONTROL")
        qlist.append(q)
    return b"\n".join(qlist)+b"\n"

def count_only_questions(payload: bytes,hops: int,expected: int) -> dict:
    p=subprocess.run(["go","run","./cmd/forge-f102o-grammar-count","--hops",str(hops)],
                     input=payload,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                     check=False,timeout=200)
    require(p.returncode==0,"FROZEN_TRAIN_GRAMMAR_PROCESS_DENIED")
    try: report=json.loads(p.stdout.decode("utf-8"))
    except (UnicodeError,ValueError) as ex: raise Denied("F102O_BAD_AGGREGATE_JSON") from ex
    require(report["schema"]=="forge.optimizer.f102o.train-only-expanded-grammar-count.v1" and
            report["status"]=="PUBLIC_TRAIN_ONLY_EXPANDED_GRAMMAR_COVERAGE" and
            report["hops"]==hops and report["questions"]==expected,
            "FROZEN_COHORT_MISMATCH")
    require(report["matched"]+report["abstained"]==expected and
            sum(report["reasons"].values())==report["abstained"],
            "PUBLIC_TRAIN_POPULATION_MISSING")
    require(report["question_only_data_flow"] is True and
            report["answers_read"]==report["model_calls"]==0 and
            report["scientific_dispatch"] is False and
            report["accepted_ref_mutation"] is False,"FALSE_AUTHORITY_OR_LEAKAGE")
    return report

def audit(upstream: pathlib.Path) -> dict:
    p=subprocess.run(["git","-C",str(upstream),"rev-parse","HEAD"],
                     stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=False,timeout=20)
    require(p.returncode==0 and p.stdout.decode("ascii").strip()==HEAD,"UPSTREAM_COMMIT_DRIFT")
    results=[]
    for hops,path,blob,expected in COHORTS:
        p=subprocess.run(["git","-C",str(upstream),"show","HEAD:"+path],
                         stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                         check=False,timeout=40)
        require(p.returncode==0 and git_blob(p.stdout)==blob,"ORIGINAL_TRAIN_GIT_BLOB_DRIFT")
        payload=question_only(p.stdout,expected)
        counts=count_only_questions(payload,hops,expected)
        results.append({
            "hops":hops,"original_git_blob":blob,
            "original_train_bytes_sha256":hashlib.sha256(p.stdout).hexdigest(),
            "population":expected,"counts":counts,
        })
    return {
        "schema":"forge.optimizer.f102o.train-only-grammar-coverage.v1",
        "status":"PUBLIC_TRAIN_ONLY_EXPANDED_GRAMMAR_COVERAGE",
        "source_repository":"tiantiangao7/kalm-qa",
        "source_commit":HEAD,"additional_train_grammars":46,
        "preserved_f101_fixed_grammars":8,
        "whole_original_train_population":sum(c["population"] for c in results),
        "cohorts":results,
        "test_corpus_read":False,"answers_forwarded":False,
        "question_answers_compared":False,"predictions_made":False,
        "qa_accuracy_computed":False,"independent_scientific_firstuse":False,
        "accepted_science":False,"dream_pareto_promotion":False,
        "thetaevolve_accepted_training":False,"accepted_ref_mutation":False,
        "model_calls":0,"codex_calls":0,"cloudflare_writes":0,
    }

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--upstream",required=True,type=pathlib.Path)
    p.add_argument("--output",required=True,type=pathlib.Path)
    a=p.parse_args()
    require(not a.output.exists(),"OUTPUT_OVERWRITE")
    report=audit(a.upstream)
    a.output.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print("F102O_TRAIN_WHOLE_POPULATION="+str(report["whole_original_train_population"]))
    for cohort in report["cohorts"]:
        c=cohort["counts"]
        print("F102O_TRAIN_%d_HOPS_MATCHED=%d_ABSTAINED=%d"%
              (cohort["hops"],c["matched"],c["abstained"]))
    print("F102O_TEST_CUSTODY_LABELS_QA_ACCURACY=ZERO")

if __name__=="__main__":
    try:
        main()
    except (Denied,OSError,UnicodeError,KeyError,subprocess.SubprocessError) as ex:
        print("F102O_TRAIN_ONLY_DENIED:",ex,file=sys.stderr)
        sys.exit(1)

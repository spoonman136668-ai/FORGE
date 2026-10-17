"""F102-O. TRAINING-ONLY immutable question-family inventory. No answer, target path or QA score."""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import json
import pathlib
import subprocess
import sys

HEAD = "826ee617e4da5b087584b0e03c70fe76642c6188"
FILES = (
    (2, "metaqa/original/2-hop/qa_train.txt", "d2ce0a9f3670769f4239baa4eb6bf7bdc91d9468"),
    (3, "metaqa/original/3-hop/qa_train.txt", "77409d56af8d1fde7a4bec23cf5e1df1e0a08e59"),
)
MAX_BYTES = 30 * 1024 * 1024
MAX_ROWS = 300_000
TOP_N = 40

class Denied(Exception):
    pass

def require(ok: bool, reason: str):
    if not ok:
        raise Denied("F102O_DENIED_" + reason)

def blob_id(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\x00" + data).hexdigest()

def source_bytes(root: pathlib.Path, rel: str) -> bytes:
    p=subprocess.run(["git","-C",str(root),"show","HEAD:"+rel],check=False,
                     stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=35)
    require(p.returncode==0, "IMMUTABLE_GIT_OBJECT_MISSING")
    return p.stdout

def mask_family(q: bytes) -> str | None:
    """Output only the normalized question grammar with bracketed topic fully replaced."""
    if not q or len(q)>1024 or q.count(b"[")!=1 or q.count(b"]")!=1:
        return None
    i=q.index(b"[")
    j=q.index(b"]")
    if j<=i+1 or len(q[i+1:j])>512:
        return None
    try:
        before=q[:i].decode("utf-8","strict")
        after=q[j+1:].decode("utf-8","strict")
    except UnicodeDecodeError:
        return None
    grammar=(before+"[]"+after).strip()
    if grammar.endswith("?") or grammar.endswith("."):
        grammar=grammar[:-1]
    # ASCII-only grammatical case fold, not entity case-fold; the entity is erased.
    grammar="".join(c.lower() if "A"<=c<="Z" else c for c in grammar)
    if not grammar or any(ord(c)<32 or ord(c)==127 for c in grammar):
        return None
    return grammar

def count_public_train(data: bytes) -> dict:
    require(len(data)>0 and len(data)<=MAX_BYTES, "SOURCE_BYTE_BUDGET")
    rows=data.splitlines()
    require(0<len(rows)<=MAX_ROWS, "TRAIN_ROWS_BUDGET")
    counts=Counter()
    malformed=0
    for row in rows:
        # Preserve denominator; protect answer path by discarding everything from TAB on.
        q,sep,_ = row.partition(b"\t")
        if not sep or not q:
            malformed += 1
            continue
        family=mask_family(q)
        if family is None:
            malformed+=1
        else:
            counts[family]+=1
    return {
        "rows":len(rows),
        "valid_bracket_question_rows":sum(counts.values()),
        "malformed_or_unsupported_topic_structure":malformed,
        "unique_masked_families":len(counts),
        "top_40_question_only_families":[
            {"masked_grammar":k,"frequency":v}
            for k,v in sorted(counts.items(),key=lambda x:(-x[1],x[0]))[:TOP_N]
        ]
    }

def audit(root: pathlib.Path) -> dict:
    result=subprocess.run(["git","-C",str(root),"rev-parse","HEAD"],check=False,
                          stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=25)
    require(result.returncode==0 and result.stdout.decode("ascii").strip()==HEAD,
            "ORIGINAL_COMMIT_DRIFT")
    cohorts=[]
    for hops,path,blob in FILES:
        raw=source_bytes(root,path)
        require(blob_id(raw)==blob,"TRAIN_BLOB_DRIFT")
        cohort=count_public_train(raw)
        require(cohort["rows"]==cohort["valid_bracket_question_rows"]+
                cohort["malformed_or_unsupported_topic_structure"],
                "TRAIN_POPULATION_MISACCOUNTED")
        cohorts.append({
            "hops":hops,"original_git_blob":blob,
            "original_train_sha256":hashlib.sha256(raw).hexdigest(),
            "source_bytes":len(raw),**cohort,
        })
    return {
        "schema":"forge.optimizer.f102o.original-train-only-masked-question-inventory.v1",
        "status":"PUBLIC_TRAIN_ONLY_LANGUAGE_FAMILY_INVENTORY",
        "source_repository":"tiantiangao7/kalm-qa","source_commit":HEAD,
        "cohorts":cohorts,
        "full_training_denominator":sum(c["rows"] for c in cohorts),
        "test_cohorts_read":False,"answer_values_used":False,
        "per_question_or_topic_published":False,
        "answer_accuracy_computed":False,"independent_scientific_firstuse":False,
        "accepted_science":False,"dream_pareto_promotion":False,
        "thetaevolve_accepted_training":False,"accepted_ref_mutation":False,
        "model_calls":0,"codex_calls":0,"cloudflare_writes":0,
    }

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--upstream",type=pathlib.Path,required=True)
    p.add_argument("--output",type=pathlib.Path,required=True)
    args=p.parse_args()
    require(not args.output.exists(),"OUTPUT_OVERWRITE")
    report=audit(args.upstream)
    args.output.write_text(json.dumps(report,indent=2,ensure_ascii=True,sort_keys=True)+"\n",encoding="utf-8")
    print("F102O_TRAIN_SOURCE_ROWS="+str(report["full_training_denominator"]))
    for c in report["cohorts"]:
        print("F102O_TRAIN_HOPS_%d_ROWS=%d_FAMILIES=%d_INVALID=%d" %
              (c["hops"],c["rows"],c["unique_masked_families"],
               c["malformed_or_unsupported_topic_structure"]))
    print("F102O_TEST_LABELS_MODEL_SCIENCE=ZERO")

if __name__=="__main__":
    try:
        main()
    except (Denied, OSError, UnicodeError, subprocess.SubprocessError) as ex:
        print("F102O_SOURCE_DENIED:",ex,file=sys.stderr)
        sys.exit(1)

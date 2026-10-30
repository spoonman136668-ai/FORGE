"""MP-AI27: independent-upstream memory-benchmark source custody.

Source-only authenticity gate. ZERO benchmark questions or answers printed,
ZERO model calls, ZERO accepted-memory writes. This is NOT a claim of an
independently witnessed first-use holdout, agent improvement, or science.
The two source authors, repositories, licensing and file revisions are
separate from MP-AI26's internally authored development-question families.
"""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import re
import struct
import sys
import tempfile
import urllib.request

LOCOMO_COMMIT = "3eb6f2c585f5e1699204e3c3bdf7adc5c28cb376"
LOCOMO_BLOB = "d95b872480b413d935821fdc3c84f8a8f5f29e73"
LOCOMO_BYTES = 2805274
MAB_HF_COMMIT = "7ea066982b140a19337e17e60d45d4076e042faf"
MAB_CODE_COMMIT = "538026089d1a8a8eff05121d0db89b388f360eba"
FILES = (
    {
      "family": "locomo_dialogue_temporal_multihop",
      "label": "LOCOMO",
      "url": "https://raw.githubusercontent.com/snap-research/locomo/"+LOCOMO_COMMIT+"/data/locomo10.json",
      "max_bytes": LOCOMO_BYTES,
      "git_blob": LOCOMO_BLOB,
      "ext": "json",
      "license": "CC-BY-NC-4.0",
    },
    {
      "family": "memoryagentbench_conflict_resolution",
      "label": "MAB_CR",
      "url": "https://huggingface.co/datasets/ai-hyz/MemoryAgentBench/resolve/"+MAB_HF_COMMIT+
             "/data/Conflict_Resolution-00000-of-00001.parquet?download=true",
      "max_bytes": 4000000,
      "sha256": "24d5c3f09ce0ce15625cb9f8a98f44f0d864ca6c94d7b4ad04eb697ca3a5ff45",
      "ext": "parquet",
      "license": "MIT",
    },
    {
      "family": "memoryagentbench_test_time_learning",
      "label": "MAB_TTL",
      "url": "https://huggingface.co/datasets/ai-hyz/MemoryAgentBench/resolve/"+MAB_HF_COMMIT+
             "/data/Test_Time_Learning-00000-of-00001.parquet?download=true",
      "max_bytes": 7000000,
      "sha256": "5338753be48f925d03318eed66117286e3489025fabe050a547bd086cd7d79c0",
      "ext": "parquet",
      "license": "MIT",
    },
)
STAGE="INIT"
def must(value,code):
    if not value: raise RuntimeError("MPAI27_"+code)
def canonical_sha256(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,
           separators=(",",":"),ensure_ascii=True).encode()).hexdigest()
def file_bytes(desc,private_dir):
    assert desc["label"] in {"LOCOMO","MAB_CR","MAB_TTL"}
    req=urllib.request.Request(desc["url"],headers={"User-Agent":"MPAI27-immutable-source-custody/1"})
    path=private_dir/(desc["label"]+"."+desc["ext"])
    count=0
    with urllib.request.urlopen(req,timeout=50) as response, path.open("xb") as out:
        repo_id=response.headers.get("x-repo-commit")
        if repo_id and desc["label"].startswith("MAB"):
            must(repo_id==MAB_HF_COMMIT,"MAB_REVISION_DRIFT")
        while True:
            chunk=response.read(1024*1024)
            if not chunk: break
            count+=len(chunk)
            must(count<=desc["max_bytes"],"SOURCE_SIZE_CAP")
            out.write(chunk)
    must(count>16,"SOURCE_EMPTY")
    return path,count
def inspect(desc,path,size):
    data=path.read_bytes()
    must(len(data)==size,"READ_TRUNCATED")
    sha256=hashlib.sha256(data).hexdigest()
    if desc["ext"]=="json":
        must(size==LOCOMO_BYTES,"LOCOMO_SOURCE_BYTES")
        blob=hashlib.sha1(b"blob "+str(size).encode()+b"\\0"+data).hexdigest()
        must(blob==desc["git_blob"],"LOCOMO_BLOB_DRIFT")
        parsed=json.loads(data)
        must(type(parsed) is list and len(parsed)==10,"LOCOMO_SCHEMA_COUNT")
        must(all(type(x) is dict and x.get("sample_id") is not None and
                 "conversation" in x and "qa" in x for x in parsed),"LOCOMO_SCHEMA")
        must(len({str(x["sample_id"]) for x in parsed})==10,"LOCOMO_DUPLICATE_ID")
        # Only the source count and content hash leave the private scratch.
        return size,sha256,len(parsed)
    must(sha256==desc["sha256"],"MAB_SHA256_DRIFT")
    must(data[:4]==b"PAR1" and data[-4:]==b"PAR1","MAB_PARQUET_MAGIC")
    metadata_len=struct.unpack("<I",data[-8:-4])[0]
    must(32<=metadata_len<size-8,"MAB_FOOTER_LENGTH")
    return size,sha256,None
def main():
    global STAGE
    must(os.environ.get("GITHUB_REPOSITORY")=="spoonman136668-ai/FORGE",
         "GITHUB_SOURCE_ID")
    must(os.environ.get("GITHUB_RUN_ATTEMPT")=="1","NO_REPLAY")
    must(not os.environ.get("OPENAI_API_KEY"),"PAID_API_DENIED")
    must(len(FILES)==3 and len({x["family"] for x in FILES})==3,"FAMILY_DISJOINT")
    must(LOCOMO_COMMIT!=MAB_HF_COMMIT and MAB_CODE_COMMIT!=LOCOMO_COMMIT,
         "INDEPENDENT_REPOSITORY_PIN")
    freeze={
      "schema":"mind-palace.mpai27-upstream-source-freeze.v1",
      "independent_upstream_projects":2,
      "family_names":sorted(x["family"] for x in FILES),
      "source_specs":FILES,
      "locomo_commit":LOCOMO_COMMIT,"locomo_blob":LOCOMO_BLOB,
      "memoryagentbench_dataset_commit":MAB_HF_COMMIT,
      "memoryagentbench_code_commit":MAB_CODE_COMMIT,
      "evaluation_questions_exposed":False,
      "model_inference_authorized":False,
      "independent_hidden_holdout_certified":False,
    }
    print("MPAI27_PRE_SOURCE_CUSTODY_PROTOCOL_SHA256="+canonical_sha256(freeze),flush=True)
    print("MPAI27_INDEPENDENT_UPSTREAM_PROJECTS=2",flush=True)
    print("MPAI27_CANDIDATE_SOURCE_FAMILIES=3",flush=True)
    with tempfile.TemporaryDirectory(prefix="mpai27-private-") as scratch:
        private=Path(scratch)
        for desc in FILES:
            STAGE="SOURCE_"+desc["label"]
            path,size=file_bytes(desc,private)
            size,sha,count=inspect(desc,path,size)
            print("MPAI27_"+desc["label"]+"_AUTHENTIC_SOURCE=PASS",flush=True)
            print("MPAI27_"+desc["label"]+"_BYTES="+str(size),flush=True)
            print("MPAI27_"+desc["label"]+"_SHA256="+sha,flush=True)
            if count is not None: print("MPAI27_"+desc["label"]+"_SOURCE_SAMPLES="+str(count),flush=True)
        print("MPAI27_PRIVATE_INPUTS_VALIDATED=3",flush=True)
    print("MPAI27_TEMP_SOURCE_DATA_DISCARDED=TRUE",flush=True)
    print("MPAI27_MODEL_INFERENCE_CALLS=0",flush=True)
    print("MPAI27_PRIVATE_GOLD_OR_QUESTIONS_PRINTED=FALSE",flush=True)
    print("MPAI27_EXTERNAL_SOURCE_AUTHENTICITY=PASS",flush=True)
    print("MPAI27_HOLDOUT_SOURCE_AUTHORSHIP=INDEPENDENT",flush=True)
    print("MPAI27_INDEPENDENT_FIRST_USE_CUSTODY=NOT_ATTESTED",flush=True)
    print("MPAI27_UNKNOWN_MODEL_PRETRAINING_CONTAMINATION=TRUE",flush=True)
    print("MPAI27_SEMANTIC_SCORER_CALIBRATION=NOT_RUN",flush=True)
    print("MPAI27_SCIENTIFIC_ACCEPTANCE=FALSE",flush=True)
    print("MPAI27_AUTONOMOUS_AGENT_LEARNING=NOT_PROVEN",flush=True)
    print("MPAI27_PRODUCTION_MEMORY_WRITES=0",flush=True)
if __name__=="__main__":
    try:main()
    except Exception as exc:
        msg=str(exc)
        code=msg if re.fullmatch(r"MPAI27_[A-Z0-9_]{3,80}",msg) else "MPAI27_PRIVATE_EXCEPTION"
        print("MPAI27_SAFE_FAILURE="+code,flush=True)
        print("MPAI27_SAFE_STAGE="+STAGE,flush=True)
        print("MPAI27_SAFE_EXCEPTION="+type(exc).__name__,flush=True)
        sys.exit(2)

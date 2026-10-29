"""MP-AI05 P9 — source-pinned *public development* cohort freeze, no model use.

Public upstream dataset, not independent first-use custody. This file selects
16 text-only development questions using public ID/domain/type metadata ONLY.
It never prints questions, answers, trajectories, full IDs or screenshots.
No production accepted .ice, science authority, scheduler or paid APIs.
"""
from __future__ import annotations

from collections import Counter
import hashlib
import json
import pathlib
import re
import sys
import urllib.request

REPO="xiaowu0162/longmemeval-v2"
REVISION="f152293e235517d504809563c833d7190b8c713b"
RESEARCH_SOURCE="2cc8c540bdb87fe6761629b585e727e1c4704520"
SELECTION_SEED="MPAI05-P9-PUBLIC-DEVELOPMENT-COHORT-v1"
FILE_HASHES={
    "questions.jsonl":"0a3ae5ebea938c24d7800e1e0b0828e08ae1646f939a53853b2b8cdc08e292b7",
    "haystacks/lme_v2_small.json":"9b5301defb23a088a5f06e45ff8d5f35e569d78305a66d492046a9fff9b46593",
    "SCHEMA.md":"0672cf47cf16c30365648770628b433076bb3f5b73edded673af7dd6d5f3246f",
}
MAX_FILE_BYTES={
    "questions.jsonl":1_000_000,
    "haystacks/lme_v2_small.json":3_000_000,
    "SCHEMA.md":20_000,
    "checksums.sha256":20_000,
}
DOMAIN_COUNT={"web":8,"enterprise":8}
TYPES=frozenset({
    "static-environment","static-environment-abs",
    "dynamic-environment","dynamic-environment-abs",
    "procedure","procedure-abs","errors-gotchas",
})
FAMILIES={"static-environment":"static","static-environment-abs":"static",
    "dynamic-environment":"dynamic","dynamic-environment-abs":"dynamic",
    "procedure":"procedure","procedure-abs":"procedure",
    "errors-gotchas":"gotchas"}

def require(ok: bool,reason: str):
    if not ok: raise ValueError("MPAI05_P9_"+reason)

def sha(raw:bytes)->str:
    return hashlib.sha256(raw).hexdigest()

def check_manifest(raw: bytes):
    result={}
    for line in raw.decode("utf-8").splitlines():
        m=re.fullmatch(r"([0-9a-f]{64})\s+\*?(\S+)",line.strip())
        require(m is not None,"CHECKSUM_MANIFEST_FORMAT")
        digest,path=m.groups()
        require(path not in result,"CHECKSUM_MANIFEST_DUPLICATE")
        result[path]=digest
    for name,expected in FILE_HASHES.items():
        require(result.get(name)==expected,"PUBLISHED_DATA_HASH_DRIFT")
    return True

def download(name:str)->bytes:
    require(name in MAX_FILE_BYTES,"FILE_NOT_ALLOWED")
    req=urllib.request.Request(
        f"https://huggingface.co/datasets/{REPO}/resolve/{REVISION}/{name}?download=true",
        headers={"User-Agent":"MindPalace-P9-public-development-intake/1"})
    with urllib.request.urlopen(req,timeout=45) as stream:
        rev=stream.headers.get("x-repo-commit")
        require(rev is None or rev==REVISION,"REMOTE_COMMIT_DRIFT")
        data=stream.read(MAX_FILE_BYTES[name]+1)
    require(0<len(data)<=MAX_FILE_BYTES[name],"FILE_SIZE_CAP")
    return data

def choose(rows:list[dict],haystacks:dict)->dict:
    require(type(rows) is list and len(rows)==451,"QUESTION_COUNT_OR_TYPE")
    require(type(haystacks) is dict,"HAYSTACK_TYPE")
    ids=set()
    candidates=[]
    for row in rows:
        require(type(row) is dict,"QUESTION_ROW_TYPE")
        qid=row.get("id")
        require(type(qid) is str and 1<=len(qid)<=128
                and re.fullmatch(r"[a-zA-Z0-9_-]+",qid) is not None,
                "QUESTION_ID")
        require(qid not in ids,"DUPLICATE_QUESTION_ID")
        ids.add(qid)
        domain=row.get("domain")
        kind=row.get("question_type")
        require(domain in DOMAIN_COUNT and kind in TYPES,"QUESTION_TYPE_OR_DOMAIN")
        # Never use question text, gold answer, evaluator configuration or
        # trajectories to choose cases. Screenshots are not accessed.
        if row.get("image") is None:
            key=sha((SELECTION_SEED+"|"+qid).encode("utf-8"))
            candidates.append((domain,key,qid,kind))
    require(set(haystacks)==ids,"HAYSTACK_QUESTION_ID_PARITY")
    selected=[]
    for domain,wanted in DOMAIN_COUNT.items():
        available=sorted((r for r in candidates if r[0]==domain),key=lambda r:r[1])
        require(len(available)>=wanted,"TEXT_ONLY_CAPACITY")
        selected.extend(available[:wanted])
    require(len(selected)==16 and len({r[2] for r in selected})==16,"COHORT_COUNT")
    require(len({FAMILIES[r[3]] for r in selected})>=3,"COHORT_FAMILY_COVERAGE")
    cohort=[]
    for domain,key,qid,kind in sorted(selected):
        trajectories=haystacks.get(qid)
        require(type(trajectories) is list and len(trajectories)==100
           and len(set(trajectories))==100
           and all(type(t) is str and len(t)>0 for t in trajectories),
           "SMALL_HAYSTACK_INVALID")
        cohort.append({"id":qid,"domain":domain,"kind":kind,
            "haystack_ids_sha256":sha(json.dumps(trajectories,
                separators=(",",":"),ensure_ascii=True).encode("utf-8"))})
    # Cohort identifiers and trajectory IDs stay in disposable scratch.
    canonical=json.dumps(cohort,sort_keys=True,separators=(",",":")).encode("utf-8")
    return {"cohort_sha256":sha(canonical),
        "questions":len(cohort),"domain_counts":dict(Counter(x["domain"] for x in cohort)),
        "family_counts":dict(sorted(Counter(FAMILIES[x["kind"]] for x in cohort).items())),
        "text_only":True,"cohort":cohort}

def freeze(question_raw:bytes,small_raw:bytes,schema_raw:bytes,checksums_raw:bytes)->dict:
    check_manifest(checksums_raw)
    for name,raw in (("questions.jsonl",question_raw),
          ("haystacks/lme_v2_small.json",small_raw),("SCHEMA.md",schema_raw)):
        require(sha(raw)==FILE_HASHES[name],"DATA_BYTES_DRIFT")
    schema=schema_raw.decode("utf-8")
    require(all(x in schema for x in
        ("questions.jsonl","trajectories.jsonl","question_type","eval_function",
         "lme_v2_small.json","100")),"SCHEMA_INTERFACE_DRIFT")
    rows=[json.loads(line) for line in question_raw.decode("utf-8").splitlines() if line.strip()]
    haystacks=json.loads(small_raw)
    chosen=choose(rows,haystacks)
    return {
      "schema":"mind-palace.mpai05.p9.frozen-public-development-source.v1",
      "dataset_repo":REPO,"dataset_revision":REVISION,
      "official_research_source":RESEARCH_SOURCE,
      "dataset_file_sha256":FILE_HASHES,
      "cohort_selection_seed":SELECTION_SEED,
      "cohort_sha256":chosen["cohort_sha256"],
      "development_case_count":chosen["questions"],
      "domains":chosen["domain_counts"],
      "families":chosen["family_counts"],
      "benchmark_questions_read":451,
      "scored_questions":0,
      "answer_gold_used_to_select":False,
      "full_cohort_identifiers_in_public_output":False,
      "trajectory_payloads_read":0,
      "model_calls":0,"paid_api_calls":0,"accepted_memory_writes":0,
      "first_use_holdout":False,"independent_scientific_custody":False,
      "independent_blind_grading":False,"scientific_acceptance":False,
      "model_promotion_authorized":False,
      "next":"freeze original evaluator and pinned text trajectories for fair matched development evaluation",
    }

def main():
    require(len(sys.argv)==1,"ARGUMENTS")
    raw={name:download(name) for name in ("checksums.sha256","SCHEMA.md",
                                         "questions.jsonl","haystacks/lme_v2_small.json")}
    receipt=freeze(raw["questions.jsonl"],raw["haystacks/lme_v2_small.json"],
                   raw["SCHEMA.md"],raw["checksums.sha256"])
    print(json.dumps(receipt,sort_keys=True,separators=(",",":")))
if __name__=="__main__":
    main()

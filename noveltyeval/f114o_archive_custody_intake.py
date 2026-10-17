"""F114-O original FreebaseQA archive custody intake — FAIL CLOSED.

Only a synthetic fixture can pass a test stream digest check. No original
publisher ZIP is available with an independently witnessed original hash.
A pair of arbitrary names in a JSON manifest is NOT independent custody.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import tempfile

SCHEMA="forge.optimizer.f114o.original-archive-custody-intake.v1"
ORIGINAL_STATUS="ORIGINAL_FREEBASE_ARCHIVE_EXTERNAL_WITNESS_MISSING"
SYNTH_STATUS="SYNTHETIC_ARCHIVE_WITNESS_MECHANISM_TESTED"
PUBLISHER_REPO="kelvin-jiang/FreebaseQA"
PUBLISHER_COMMIT="d16aae5149aaa25e43ff2a7bd00a06f280ca19b9"
README_ID="dd4c65cbe5428b2a86afc47ae2309cb11328b31b"
LICENSE_ID="10fabd90118f7ce38bb2e4753e105e744442a429"
ORIGINAL_URL="https://www.dropbox.com/sh/a25p7j2ir8gqnvx/AABJvjoI9mbHYj3hyfuxSdGaa?dl=0"
AUTH="SYNTHETIC_FIXTURE_ONLY"
MAX_SYNTHETIC_BYTES=1024*1024
MAX_ORIGINAL_COMPRESSED_BYTES=8*1024*1024*1024
CHUNK=65536
HEX=re.compile(r"[0-9a-f]{64}\Z",re.ASCII)
PERSON=re.compile(r"[A-Za-z][A-Za-z0-9_.:-]{2,63}\Z",re.ASCII)
FIXTURE=(b"F114-O SYNTHETIC ARCHIVE BYTES; NOT ORIGINAL FREEBASEQA GRAPH\n" * 7)

class Denied(Exception): pass

def need(ok:bool,reason:str):
    if not ok: raise Denied("F114O_SOURCE_CUSTODY_DENIED_"+reason)

def witness_manifest(raw:bytes)->dict:
    # Synthetic-only self-authored fixture. Nothing here is an independent
    # witness for the original publisher's unverified multi-GB archive.
    return {
        "schema":SCHEMA,
        "source_type":"synthetic_fixture",
        "publisher_repository":PUBLISHER_REPO,
        "publisher_git_commit":PUBLISHER_COMMIT,
        "publisher_readme_git_blob":README_ID,
        "publisher_graph_url":ORIGINAL_URL,
        "precommitted_archive_bytes":len(raw),
        "precommitted_archive_sha256":hashlib.sha256(raw).hexdigest(),
        "witness_principal":"synthetic_witness_A",
        "executor_principal":"synthetic_executor_B",
        "source_authority":"SYNTHETIC_FIXTURE_ONLY",
    }

def verify_synthetic_fixture(path:Path,manifest:dict)->dict:
    need(isinstance(path,Path) and isinstance(manifest,dict),
         "SYNTHETIC_INPUT_TYPES")
    need(manifest.get("schema")==SCHEMA and
         manifest.get("source_type")=="synthetic_fixture" and
         manifest.get("source_authority")==AUTH,
         "SYNTHETIC_NAMESPACE_ONLY")
    for key,value in (
        ("publisher_repository",PUBLISHER_REPO),
        ("publisher_git_commit",PUBLISHER_COMMIT),
        ("publisher_readme_git_blob",README_ID),
        ("publisher_graph_url",ORIGINAL_URL)
    ):
        need(manifest.get(key)==value,"PUBLISHER_METADATA_OR_URL_DRIFT")
    a=manifest.get("witness_principal")
    b=manifest.get("executor_principal")
    need(isinstance(a,str) and isinstance(b,str) and
         PERSON.fullmatch(a) is not None and
         PERSON.fullmatch(b) is not None and a!=b,
         "CLAIMED_SYNTHETIC_PRINCIPAL_SEPARATION")
    length=manifest.get("precommitted_archive_bytes")
    checksum=manifest.get("precommitted_archive_sha256")
    need(isinstance(length,int) and not isinstance(length,bool) and
         0<length<=MAX_SYNTHETIC_BYTES,"SYNTHETIC_LENGTH_BUDGET")
    need(isinstance(checksum,str) and HEX.fullmatch(checksum) is not None,
         "SYNTHETIC_DIGEST_FORMAT")
    try:
        original_stat=path.lstat()
    except OSError as exc:
        raise Denied("F114O_MISSING_SYNTHETIC_FILE") from exc
    need(stat.S_ISREG(original_stat.st_mode),"SYMLINK_OR_NONREGULAR_INPUT")
    need(original_stat.st_size==length,"INITIAL_INPUT_LENGTH_MISMATCH")
    flags=os.O_RDONLY
    if hasattr(os,"O_NOFOLLOW"):flags|=os.O_NOFOLLOW
    fd=None
    try:
        fd=os.open(path,flags)
        st_before=os.fstat(fd)
        need(stat.S_ISREG(st_before.st_mode) and
             st_before.st_size==length and
             st_before.st_dev==original_stat.st_dev and
             st_before.st_ino==original_stat.st_ino,
             "FILE_CHANGED_BEFORE_OPEN")
        total=0
        digest=hashlib.sha256()
        with os.fdopen(fd,"rb") as stream:
            fd=None
            while True:
                chunk=stream.read(CHUNK)
                if not chunk:break
                total+=len(chunk)
                need(total<=MAX_SYNTHETIC_BYTES and total<=length,
                     "BOUNDED_STREAM_OVERFLOW")
                digest.update(chunk)
            st_after=os.fstat(stream.fileno())
        need(st_after.st_dev==st_before.st_dev and
             st_after.st_ino==st_before.st_ino and
             st_after.st_size==st_before.st_size and
             st_after.st_mtime_ns==st_before.st_mtime_ns and
             st_after.st_ctime_ns==st_before.st_ctime_ns,
             "FILE_MUTATED_DURING_STREAM")
        need(total==length and digest.hexdigest()==checksum,
             "SYNTHETIC_EXACT_SHA256_OR_BYTE_COUNT_DRIFT")
    except OSError as exc:
        raise Denied("F114O_OPEN_OR_READ_DENIED") from exc
    finally:
        if fd is not None:os.close(fd)
    return {
        "status":SYNTH_STATUS,
        "fixture_archive_bytes_checked":total,
        "fixture_archive_sha256_checked":checksum,
        "stream_chunk_cap_bytes":CHUNK,
        "synthetic_claimed_principals_distinct":True,
        "genuine_external_source_witness":False,
        "publisher_original_archive_authenticated":False,
        "original_graph_members_inspected":False,
        "original_freebase_graph_admitted":False,
        "real_graph_queries":0,
    }

def verify_original_archive(_path=None,_manifest=None):
    # There is no original FreebaseQA archive hash and independent custodian
    # in this environment. No caller-supplied metadata can substitute for it.
    raise Denied("F114O_ORIGINAL_ARCHIVE_INDEPENDENT_SOURCE_WITNESS_MISSING")

def original_custody_status()->dict:
    return {
        "status":ORIGINAL_STATUS,
        "publisher_repository":PUBLISHER_REPO,
        "publisher_git_commit":PUBLISHER_COMMIT,
        "publisher_readme_git_blob":README_ID,
        "publisher_license_git_blob":LICENSE_ID,
        "publisher_graph_download_location_documented":True,
        "original_archive_actual_bytes_available":False,
        "original_archive_sha256_independently_published":False,
        "independent_archive_witness_present":False,
        "whole_extracted_member_layout_verified":False,
        "original_edge_serialization_verified":False,
        "original_edge_orientation_verified":False,
        "original_freebase_graph_admitted":False,
        "original_graph_archive_downloaded":False,
        "original_graph_query_count":0,
    }

def audit()->dict:
    with tempfile.TemporaryDirectory(prefix="f114o-synthetic-") as folder:
        source=Path(folder)/"synthetic-archive.bin"
        source.write_bytes(FIXTURE)
        proof=verify_synthetic_fixture(source,witness_manifest(FIXTURE))
    original=original_custody_status()
    return {
        "schema":SCHEMA,
        "status":"SYNTHETIC_ARCHIVE_CUSTODY_MECHANISM_ONLY_ORIGINAL_MISSING",
        "synthetic_receipt":proof,
        "original_custody":original,
        "synthetic_original_data_equivalence":False,
        "reserved_train_dev_eval_json_read":False,
        "original_freebase_archive_read_or_downloaded":False,
        "real_graph_queries":0,
        "real_qa_answers_compared":0,
        "independent_scientific_firstuse":False,
        "accepted_science":False,
        "accepted_ref_mutation":False,
        "dream_pareto_promotion":False,
        "thetaevolve_accepted_training":False,
        "science_dispatch":False,
        "model_calls":0,"codex_calls":0,"cloudflare_writes":0,
    }

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--out",type=Path,required=True)
    args=parser.parse_args()
    need(not args.out.exists(),"OUTPUT_OVERWRITE_FORBIDDEN")
    payload=(json.dumps(audit(),sort_keys=True,indent=2,ensure_ascii=True)+"\n").encode()
    with args.out.open("xb") as target:target.write(payload)
    print("F114O_SYNTHETIC_LOCAL_ARCHIVE_HASH_STREAM_PASS")
    print("F114O_ORIGINAL_FREEBASEQA_ARCHIVE_WITNESS_MISSING_NO_GRAPH_NO_QA")

if __name__=="__main__":main()

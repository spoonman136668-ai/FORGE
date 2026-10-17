"""F113-O source-neutral, synthetic-only SQLite disk index.

This file format is NOT the real FreebaseQA graph schema. The original graph
archive is not available or qualified. No network, archive download, QA rows
or FreebaseQA graph query is allowed by any entry point in this module.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import stat
import tempfile
from urllib.parse import quote

from f110o_graph_custody_policy import evaluate_manifest

SCHEMA="forge.optimizer.f113o.synthetic-disk-index.v1"
STATUS="SYNTHETIC_DISK_INDEX_ENGINEERING_ONLY_ORIGINAL_FREEBASE_ARCHIVE_UNQUALIFIED"
ORIGINAL_UPSTREAM="d16aae5149aaa25e43ff2a7bd00a06f280ca19b9"
PUBLISHER_README_GIT_ID="dd4c65cbe5428b2a86afc47ae2309cb11328b31b"
AUTH="SYNTHETIC_FIXTURE_ONLY"
MAX_RAW_BYTES=1024*1024
MAX_DB_BYTES=8*1024*1024
MAX_ROWS=4096
MAX_LINE=768
MAX_FIELD=256
MAX_FRONTIER=128
FIELDS=re.compile(rb"[A-Za-z0-9_./:-]{1,256}\Z",re.ASCII)
SHA=re.compile(r"[0-9a-f]{64}\Z",re.ASCII)

class Denied(Exception):pass

def need(ok,reason):
    if not ok:raise Denied("F113O_SYNTHETIC_DISK_SOURCE_DENIED_"+reason)

def digest_bytes(value:bytes)->str:
    return hashlib.sha256(value).hexdigest()

def sha256_file(path:Path,limit:int)->tuple[int,str]:
    h=hashlib.sha256()
    total=0
    with path.open("rb") as inp:
        while True:
            part=inp.read(65536)
            if not part:break
            total+=len(part)
            need(total<=limit,"SOURCE_OR_INDEX_SIZE_CAP")
            h.update(part)
    return total,h.hexdigest()

def _regular_not_symlink(path:Path)->bool:
    try:
        st=path.lstat()
        return stat.S_ISREG(st.st_mode)
    except OSError:
        return False

def _parse(line:bytes)->tuple[str,str,str]:
    need(0<len(line)<=MAX_LINE and line.endswith(b"\n") and
         not line.endswith(b"\r\n"),"SOURCE_COMPLETE_BOUNDED_LF_LINE")
    values=line[:-1].split(b"\t")
    need(len(values)==3 and all(FIELDS.fullmatch(x) is not None for x in values),
         "SOURCE_THREE_ASCII_FIELDS")
    return tuple(v.decode("ascii") for v in values)

def build_fixture(source:Path,db_path:Path,sha256:str,size:int,rows:int)->dict:
    need(isinstance(source,Path) and isinstance(db_path,Path),"PATH_TYPE")
    need(_regular_not_symlink(source),"SYNTHETIC_REGULAR_SOURCE_ONLY")
    need(isinstance(sha256,str) and SHA.fullmatch(sha256) is not None,
         "SOURCE_DIGEST_FORMAT")
    need(all(isinstance(x,int) and not isinstance(x,bool) for x in (size,rows))
         and 0<size<=MAX_RAW_BYTES and 1<=rows<=MAX_ROWS,
         "DECLARED_ORIGINAL_SYNTHETIC_BUDGET")
    need(db_path.suffix==".sqlite" and
         db_path.parent.is_dir() and not db_path.exists() and
         not db_path.is_symlink(),"NEW_DESTINATION_ONLY")
    need(source.resolve().parent!=db_path.parent.resolve(),
         "SOURCE_MUST_BE_OUTSIDE_INDEX_DIR")
    measured_size,measured_digest=sha256_file(source,MAX_RAW_BYTES)
    need(measured_size==size and measured_digest==sha256,
         "ORIGINAL_FIXTURE_DIGEST_OR_SIZE_CHANGED")
    descriptor,tmp_name=tempfile.mkstemp(
        prefix=".f113o-unpublished-",suffix=".sqlite",dir=db_path.parent)
    os.close(descriptor)
    scratch=Path(tmp_name)
    published=False
    connection=None
    try:
        connection=sqlite3.connect(str(scratch),timeout=2)
        connection.execute("PRAGMA page_size=4096")
        connection.execute("PRAGMA journal_mode=DELETE")
        connection.execute("PRAGMA synchronous=FULL")
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("BEGIN IMMEDIATE")
        connection.execute("""
            CREATE TABLE edges(
             subject TEXT NOT NULL, relation TEXT NOT NULL, object TEXT NOT NULL,
             PRIMARY KEY(subject,relation,object)
            ) WITHOUT ROWID
        """)
        connection.execute(
            "CREATE INDEX idx_reverse ON edges(object,relation,subject)")
        connection.execute("CREATE TABLE meta(key TEXT PRIMARY KEY,value TEXT NOT NULL)")
        count=0
        second_hash=hashlib.sha256()
        second_size=0
        with source.open("rb") as stream:
            while True:
                line=stream.readline(MAX_LINE+1)
                if not line:break
                need(len(line)<=MAX_LINE,"ORIGINAL_FIXTURE_LINE_OVERSIZE")
                second_size+=len(line)
                need(second_size<=MAX_RAW_BYTES,"SECOND_READ_SOURCE_BUDGET")
                second_hash.update(line)
                subject,relation,obj=_parse(line)
                try:
                    connection.execute(
                        "INSERT INTO edges(subject,relation,object) VALUES(?,?,?)",
                        (subject,relation,obj))
                except sqlite3.IntegrityError as ex:
                    raise Denied("F113O_DUPLICATE_GRAPH_TRIPLE") from ex
                count+=1
                need(count<=MAX_ROWS,"SECOND_READ_ROWS_OVER_BUDGET")
        need(count==rows and second_size==size and
             second_hash.hexdigest()==sha256,
             "SECOND_READ_DIGEST_OR_ROW_DRIFT")
        for key,value in (
            ("schema",SCHEMA),("authorization",AUTH),
            ("source_sha256",sha256),("source_bytes",str(size)),
            ("source_rows",str(rows))):
            connection.execute("INSERT INTO meta(key,value) VALUES(?,?)",(key,value))
        connection.commit()
        connection.close()
        connection=None
        db_size,db_sha=sha256_file(scratch,MAX_DB_BYTES)
        need(db_size<=MAX_DB_BYTES,"SCRATCH_SQLITE_DISK_BUDGET")
        # Hard link fails instead of overwriting an existing destination, on
        # the same scratch filesystem. Do not publish a partial transaction.
        os.link(scratch,db_path)
        published=True
        return {
            "status":"SYNTHETIC_INDEX_BYTES_VERIFIED_ONLY",
            "source_rows":count,
            "source_bytes":size,
            "source_sha256":sha256,
            "sqlite_file_bytes":db_size,
            "sqlite_sha256":db_sha,
            "transaction_published":True,
            "original_freebase_source_admitted":False,
        }
    except (sqlite3.Error,OSError) as ex:
        raise Denied("F113O_SQLITE_OR_FILESYSTEM_DENIED") from ex
    finally:
        if connection is not None:
            connection.close()
        scratch.unlink(missing_ok=True)
        if not published:
            need(not db_path.exists(),"PARTIAL_DESTINATION_MUST_NOT_EXIST")

def resolve_fixture(db_path:Path,source_sha256:str,index_sha256:str,
                    root:str,steps:list[tuple[str,str]],auth:str,
                    max_frontier:int=MAX_FRONTIER)->list[str]:
    need(auth==AUTH,"REAL_FREEBASE_GRAPH_NAMESPACE_HARD_DENIED")
    need(isinstance(db_path,Path) and _regular_not_symlink(db_path),
         "INDEX_NOT_REGULAR")
    need(SHA.fullmatch(source_sha256) is not None and
         SHA.fullmatch(index_sha256) is not None,
         "INDEX_OR_SOURCE_DIGEST_FORMAT")
    size,actual=sha256_file(db_path,MAX_DB_BYTES)
    need(size>0 and actual==index_sha256,"INDEX_TAMPER_OR_SIZE")
    need(isinstance(root,str) and root and
         FIELDS.fullmatch(root.encode("utf-8")) is not None,
         "ROOT_IDENTITY_FORMAT")
    need(isinstance(steps,(list,tuple)) and 1<=len(steps)<=2,
         "EXPLICIT_ONE_OR_TWO_STEPS_ONLY")
    for step in steps:
        need(isinstance(step,(list,tuple)) and len(step)==2 and
             isinstance(step[0],str) and
             FIELDS.fullmatch(step[0].encode("utf-8")) is not None and
             step[1] in ("forward","reverse"),
             "EXPLICIT_EXACT_RELATION_AND_DIRECTION_REQUIRED")
    need(isinstance(max_frontier,int) and not isinstance(max_frontier,bool)
         and 1<=max_frontier<=MAX_FRONTIER,"FRONTIER_HARD_CAP")
    uri="file:"+quote(str(db_path.resolve()),safe="/:")+"?mode=ro"
    try:
        with sqlite3.connect(uri,uri=True,timeout=2) as conn:
            conn.execute("PRAGMA query_only=ON")
            conn.execute("PRAGMA busy_timeout=2000")
            meta=dict(conn.execute("SELECT key,value FROM meta").fetchall())
            need(meta.get("schema")==SCHEMA and
                 meta.get("authorization")==AUTH and
                 meta.get("source_sha256")==source_sha256,
                 "INDEX_SOURCE_METADATA_NOT_AUTHENTIC")
            frontier={root}
            for role,direction in steps:
                next_nodes=set()
                sql=("SELECT object FROM edges WHERE subject=? AND relation=? LIMIT ?"
                     if direction=="forward" else
                     "SELECT subject FROM edges WHERE object=? AND relation=? LIMIT ?")
                for node in sorted(frontier):
                    vals=conn.execute(sql,(node,role,max_frontier+1)).fetchall()
                    need(len(vals)<=max_frontier,"PER_ANCHOR_FRONTIER_OVER_BUDGET")
                    next_nodes.update(v[0] for v in vals)
                    need(len(next_nodes)<=max_frontier,"GLOBAL_FRONTIER_OVER_BUDGET")
                frontier=next_nodes
                if not frontier:break
            return sorted(frontier)
    except sqlite3.Error as ex:
        raise Denied("F113O_READONLY_INDEX_NOT_QUERYABLE") from ex

def original_freebase_eligibility(candidate=None)->dict:
    # F110 graph denial is immutable even if a caller fabricates fields.
    report=evaluate_manifest(candidate)
    need(report["status"]=="FREEBASE_GRAPH_SOURCE_NOT_QUALIFIED" and
         not report["admitted"] and report["real_graph_calls"]==0,
         "ORIGINAL_GRAPH_MUST_NEVER_ACTIVATE")
    return {
        "status":"PUBLISHER_SOURCE_LOCATED_ARCHIVE_BYTES_UNAVAILABLE",
        "publisher_repo_git_commit":ORIGINAL_UPSTREAM,
        "publisher_readme_git_blob":PUBLISHER_README_GIT_ID,
        "archive_bytes_downloaded":False,
        "original_archive_sha256_verified":False,
        "exact_original_edge_denominator_known":False,
        "original_edge_representation_authenticated":False,
        "original_edge_directions_authenticated":False,
        "full_publisher_graph_admitted":False,
        "source_graph_queries":0,
        "unresolved_custody_fields":report["missing_or_invalid_metadata_fields"],
    }

def run_diagnostic()->dict:
    sample=(b"film.a\tfilm.film.directed_by\tdirector.a\n"
            b"director.a\tpeople.person.parents\tparent.a\n"
            b"actor.a\tfilm.film.directed_by\tfilm.a\n"
            b"film.a\tfilm.film.directed_by\tdirector.b\n"
            b"director.b\tpeople.person.parents\tparent.b\n")
    with tempfile.TemporaryDirectory(prefix="f113o-synthetic-") as folder:
        base=Path(folder)
        src_dir=base/"source"
        idx_dir=base/"index"
        src_dir.mkdir();idx_dir.mkdir()
        src=src_dir/"synthetic.tsv"
        src.write_bytes(sample)
        dest=idx_dir/"synthetic.sqlite"
        proof=build_fixture(src,dest,digest_bytes(sample),len(sample),5)
        two_hop=resolve_fixture(dest,proof["source_sha256"],proof["sqlite_sha256"],
                                "film.a",[("film.film.directed_by","forward"),
                                          ("people.person.parents","forward")],AUTH)
        reverse=resolve_fixture(dest,proof["source_sha256"],proof["sqlite_sha256"],
                                "film.a",[("film.film.directed_by","reverse")],AUTH)
        need(two_hop==["parent.a","parent.b"] and reverse==["actor.a"],
             "SYNTHETIC_EXPLICIT_DIRECTION_TEST")
        graph=original_freebase_eligibility()
        return {
            "schema":SCHEMA,
            "status":STATUS,
            "source":graph,
            "synthetic_fixture_rows":proof["source_rows"],
            "synthetic_fixture_bytes":proof["source_bytes"],
            "synthetic_index_disk_bytes":proof["sqlite_file_bytes"],
            "synthetic_verified_two_hop_nodes":len(two_hop),
            "synthetic_verified_reverse_nodes":len(reverse),
            "index_bytes_written_from_original_freebase":0,
            "real_graph_queries":0,
            "real_qa_answers_scored":0,
            "reserved_dev_or_eval_bytes_read":False,
            "source_archive_downloaded":False,
            "independent_scientific_firstuse":False,
            "accepted_science":False,
            "accepted_ref_mutation":False,
            "dream_pareto_promotion":False,
            "thetaevolve_accepted_training":False,
            "science_dispatch":False,
            "codex_calls":0,"model_calls":0,"cloudflare_writes":0,
        }

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--out",required=True,type=Path)
    opts=p.parse_args()
    need(not opts.out.exists(),"OUTPUT_CANNOT_BE_OVERWRITTEN")
    payload=(json.dumps(run_diagnostic(),sort_keys=True,indent=2,
                        ensure_ascii=True)+"\n").encode("utf-8")
    with opts.out.open("xb") as f:f.write(payload)
    print("F113O_SYNTHETIC_DISK_INDEX_AND_EXPLICIT_DIRECTIONS=PASS")
    print("F113O_ORIGINAL_FREEBASE_ARCHIVE_PROVENANCE_AND_BLIND_SCIENCE=BLOCKED")

if __name__=="__main__":
    main()

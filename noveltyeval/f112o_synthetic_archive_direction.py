"""F112-O: bounded offline archive and directed-edge probes for SYNTHETIC fixtures.

Neither a successful synthetic probe nor a complete-looking user manifest
authorizes the original FreebaseQA graph, scientific first use, or QA scoring.
No network, no source download, no FreebaseQA split reading.
"""
from __future__ import annotations
from pathlib import Path, PurePosixPath
import hashlib
import re
import stat
import zipfile

MAX_FIXTURE_ARCHIVE=1024*1024
MAX_FIXTURE_UNPACKED=1024*1024
MAX_FIXTURE_MEMBERS=4
MAX_COMPRESSION_RATIO=100
CHUNK=65536
SHA256=re.compile(r"[0-9a-f]{64}\Z", re.ASCII)

class Denied(Exception):pass

def need(condition:bool,reason:str):
    if not condition:raise Denied("F112O_SYNTHETIC_ARCHIVE_DENIED_"+reason)

def hash_file(path:Path)->tuple[int,str]:
    h=hashlib.sha256()
    total=0
    with path.open("rb") as source:
        while True:
            chunk=source.read(CHUNK)
            if not chunk:break
            total+=len(chunk)
            need(total<=MAX_FIXTURE_ARCHIVE,"ARCHIVE_BYTE_CAP")
            h.update(chunk)
    return total,h.hexdigest()

def valid_member_name(name:str)->bool:
    if not isinstance(name,str) or not name or len(name)>255:
        return False
    if ("\\" in name or name.startswith("/") or ":" in name or
        any(ord(x)<32 or ord(x)==127 for x in name)):
        return False
    p=PurePosixPath(name)
    parts=name.split("/")
    return (not name.endswith("/") and len(parts)<=8 and
            all(part not in ("",".","..") for part in parts) and
            str(p)==name)

def verify_fixture_archive(path:Path,manifest:dict)->dict:
    """Check a tiny caller-provided test ZIP ONLY; never real Freebase custody."""
    need(isinstance(manifest,dict),"MANIFEST_TYPE")
    need(isinstance(path,Path),"PATH_TYPE")
    need(path.exists() and path.is_file() and not path.is_symlink(),
         "REGULAR_FILE_ONLY")
    need(isinstance(manifest.get("archive_bytes"),int) and
         not isinstance(manifest["archive_bytes"],bool) and
         0<manifest["archive_bytes"]<=MAX_FIXTURE_ARCHIVE,"ARCHIVE_DECLARED_BUDGET")
    need(isinstance(manifest.get("archive_sha256"),str) and
         SHA256.fullmatch(manifest["archive_sha256"]) is not None,
         "ARCHIVE_SHA256_FORMAT")
    members=manifest.get("members")
    need(isinstance(members,dict) and 0<len(members)<=MAX_FIXTURE_MEMBERS,
         "MEMBER_DECLARATIONS")
    for name,descriptor in members.items():
        need(valid_member_name(name) and isinstance(descriptor,dict),
             "MEMBER_NAME_OR_TYPE")
        need(isinstance(descriptor.get("bytes"),int) and
             not isinstance(descriptor["bytes"],bool) and
             0<descriptor["bytes"]<=MAX_FIXTURE_UNPACKED,
             "MEMBER_DECLARED_SIZE")
        need(isinstance(descriptor.get("sha256"),str) and
             SHA256.fullmatch(descriptor["sha256"]) is not None,
             "MEMBER_DECLARED_HASH")
    size,digest=hash_file(path)
    need(size==manifest["archive_bytes"] and digest==manifest["archive_sha256"],
         "ARCHIVE_BYTES_OR_HASH_MISMATCH")
    aggregate_size=0
    result={}
    try:
        with zipfile.ZipFile(path,"r") as archive:
            infos=archive.infolist()
            need(len(infos)==len(members) and len(infos)<=MAX_FIXTURE_MEMBERS,
                 "ARCHIVE_MEMBER_COUNT")
            seen=set()
            for info in infos:
                name=info.filename
                need(valid_member_name(name) and name not in seen and
                     name in members,"ARCHIVE_UNDECLARED_DUPLICATE_OR_TRAVERSAL")
                seen.add(name)
                unix_mode=(info.external_attr>>16)
                need(not info.is_dir() and
                     not stat.S_ISLNK(unix_mode),"ARCHIVE_LINK_OR_DIRECTORY")
                need(info.flag_bits & 1==0,"ARCHIVE_ENCRYPTED")
                need(info.compress_type in (zipfile.ZIP_STORED,zipfile.ZIP_DEFLATED),
                     "ARCHIVE_UNSUPPORTED_COMPRESSION")
                need(info.file_size>0 and
                     info.file_size<=MAX_FIXTURE_UNPACKED and
                     info.file_size==members[name]["bytes"],
                     "ARCHIVE_MEMBER_SIZE_MISMATCH")
                need(info.compress_size>0 and
                     info.file_size<=MAX_COMPRESSION_RATIO*info.compress_size,
                     "ARCHIVE_COMPRESSION_RATIO")
                aggregate_size+=info.file_size
                need(aggregate_size<=MAX_FIXTURE_UNPACKED,
                     "ARCHIVE_TOTAL_UNPACKED_BUDGET")
            for info in infos:
                checksum=hashlib.sha256()
                count=0
                with archive.open(info,"r") as stream:
                    while True:
                        chunk=stream.read(CHUNK)
                        if not chunk:break
                        count+=len(chunk)
                        need(count<=members[info.filename]["bytes"],
                             "ARCHIVE_STREAM_OVERRUN")
                        checksum.update(chunk)
                need(count==members[info.filename]["bytes"] and
                     checksum.hexdigest()==members[info.filename]["sha256"],
                     "ARCHIVE_MEMBER_HASH_MISMATCH")
                result[info.filename]=count
    except (zipfile.BadZipFile,RuntimeError,NotImplementedError,EOFError,OSError) as ex:
        raise Denied("F112O_SYNTHETIC_ARCHIVE_BAD_ZIP_OR_DECOMPRESSION") from ex
    return {
        "status":"SYNTHETIC_FIXTURE_BYTES_VERIFIED_ONLY",
        "archive_bytes_checked":size,
        "all_members_checked":len(result),
        "unpacked_bytes_checked":aggregate_size,
        "source_archive_authorized":False,
        "original_freebase_archive_verified":False,
        "freebase_graph_admitted":False,
        "graph_queries":0,
    }

def synthetic_direction_candidates(edges,anchor:str,predicate:str)->set[str]:
    """Fixture-only candidates, NOT a certificate of Freebase edge direction."""
    need(isinstance(edges,(tuple,list)) and len(edges)<=20,
         "ONLY_BOUNDED_SYNTHETIC_EDGES")
    need(isinstance(anchor,str) and isinstance(predicate,str) and anchor and predicate,
         "BOUND_SYNTHETIC_ROOT_ROLE")
    possible=set()
    for edge in edges:
        need(isinstance(edge,(tuple,list)) and len(edge)==3 and
             all(isinstance(s,str) and s for s in edge),
             "UNTRUSTED_SYNTHETIC_EDGE")
        subject,role,obj=edge
        if role==predicate:
            if subject==anchor:possible.add("forward")
            if obj==anchor:possible.add("reverse")
    return possible

def direction_disposition(edges,anchor,predicate)->dict:
    candidates=synthetic_direction_candidates(edges,anchor,predicate)
    return {
        "synthetic_candidate_count":len(candidates),
        "synthetic_direction_ambiguous":len(candidates)>1,
        "source_predicate_direction_certificate":False,
        "original_freebase_graph_directions_qualified":False,
        "original_freebase_graph_admission":False,
    }

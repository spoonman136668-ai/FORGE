"""L7 source: immutable E2E NLG challenge structured meanings and real human text.

E2E data © authors / CC BY-SA 4.0. Source files are never committed or
saved as workflow artifacts; public train/dev only, official test withheld.
Reject byte/commit drift before parsing. Public DEV is not blinded science.
"""
import csv
import hashlib
import io
import json
from pathlib import Path
import re
import urllib.request

REV="ab0d967dd5729ce455ef14ba9ffafc456a335264"
BASE="https://raw.githubusercontent.com/tuetschek/e2e-dataset/"+REV+"/"
FILES={
    "trainset.csv":(9340189,"fa3a5e1124d2aa0d768881e38f8ee73e63d5880d"),
    "devset.csv":(1161305,"c45950a0771c769d787a33fdf56439cb890005d7"),
}
ROLES=("L7_TRAIN","L7_SELECT","L7_DEV")
COUNTS={"L7_TRAIN":700,"L7_SELECT":80,"L7_DEV":100}
MR_RE=re.compile(r"([A-Za-z][A-Za-z ]*)\[([^\[\]]+)\]")


def canonical(obj):
    return json.dumps(obj,sort_keys=True,separators=(",",":"),
                      ensure_ascii=True,allow_nan=False).encode("ascii")


def verify(raw,name):
    if name not in FILES or type(raw) is not bytes:
        raise ValueError("L7_UNREGISTERED_EXTERNAL_SOURCE")
    size,expected=FILES[name]
    if len(raw)!=size:
        raise ValueError("L7_EXTERNAL_SOURCE_RAW_SIZE_DRIFT")
    digest=hashlib.sha1(
        b"blob "+str(len(raw)).encode("ascii")+b"\0"+raw).hexdigest()
    if digest!=expected:
        raise ValueError("L7_EXTERNAL_SOURCE_GIT_BLOB_DRIFT")
    return hashlib.sha256(raw).hexdigest()


def acquire(directory):
    dest=Path(directory)
    dest.mkdir(parents=True,exist_ok=True)
    identities={}
    for name,(size,_) in FILES.items():
        with urllib.request.urlopen(BASE+name,timeout=90) as f:
            raw=f.read(size+1)
        identities[name]=verify(raw,name)
        (dest/name).write_bytes(raw)
    return identities


def parse_mr(raw):
    if type(raw) is not str or not raw.strip():
        raise ValueError("L7_EMPTY_OR_MALFORMED_MEANING")
    values={}
    spans=[]
    for match in MR_RE.finditer(raw):
        key="".join(match.group(1).lower().split())
        value=match.group(2).strip()
        if not key or not value or key in values:
            raise ValueError("L7_DUPLICATE_OR_EMPTY_ATTRIBUTE")
        values[key]=value
        spans.append(match.span())
    remain=list(raw)
    for i,j in spans:
        remain[i:j]=" "*(j-i)
    if not values or "".join(remain).strip(" ,\t\n\r"):
        raise ValueError("L7_INVALID_MR_SYNTAX")
    return values


def identity(mr):
    return tuple(sorted((k,v.strip().lower()) for k,v in mr.items()))


def parse_csv(raw,name):
    verify(raw,name)
    data=io.StringIO(raw.decode("utf-8-sig"),newline="")
    reader=csv.DictReader(data)
    if not set(("mr","ref")).issubset(reader.fieldnames or []):
        raise ValueError("L7_UNEXPECTED_ORIGINAL_CSV_SCHEMA")
    for i,row in enumerate(reader):
        if not row["mr"] or not row["ref"] or len(row["ref"])>800:
            continue
        mr=parse_mr(row["mr"])
        yield {"mr":mr,"ref":row["ref"].strip(),"ordinal":i}


def cohorts(trainraw,devraw):
    train=[]
    seen=set()
    for row in parse_csv(trainraw,"trainset.csv"):
        key=identity(row["mr"])
        if key in seen:
            continue
        seen.add(key)
        train.append(row)
        if len(train)==COUNTS["L7_TRAIN"]:
            break
    devall=list(parse_csv(devraw,"devset.csv"))
    selected,dev=[],[]
    for row in devall:
        key=identity(row["mr"])
        if key in seen:
            continue
        seen.add(key)
        target=selected if len(selected)<COUNTS["L7_SELECT"] else dev
        target.append(row)
        if len(dev)==COUNTS["L7_DEV"]:
            break
    groups={"L7_TRAIN":tuple(train),"L7_SELECT":tuple(selected),
            "L7_DEV":tuple(dev)}
    for role,rows in groups.items():
        if len(rows)!=COUNTS[role]:
            raise ValueError("L7_FROZEN_DISTINCT_MR_ROLE_SHORTAGE_"+role)
    return groups


def load(directory):
    raw={n:(Path(directory)/n).read_bytes() for n in FILES}
    hashes={n:verify(data,n) for n,data in raw.items()}
    return hashes,cohorts(raw["trainset.csv"],raw["devset.csv"])


def digest(rows):
    return hashlib.sha256(canonical(rows)).hexdigest()

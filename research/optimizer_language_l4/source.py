"""L4 externally sourced public Shakespeare gap challenge; frozen custody.

Source is a pre-existing public corpus, NOT external blinded first use. Abort
on byte-count or Git object identity drift before reading any lexical data.
Physical line blocks are chronological and disjoint; no older L1-L3 data.
No source words, excerpts or full dataset are committed to FORGE.
"""
import hashlib
import json
from pathlib import Path
import re
import urllib.request

HERE=Path(__file__).resolve().parent
NAMESPACE="l4-20261023-realtext-gap-v1"
SOURCE_URL=("https://raw.githubusercontent.com/karpathy/char-rnn/"
 "6f9487a6fe5b420b7ca9afb0d7c078e37c1d1b4e/data/tinyshakespeare/input.txt")
EXPECTED_SIZE=1115394
EXPECTED_GIT_SHA1="7dcb3a2d4cc3b48b6283dd46870bfeb78f88aac9"
ROLES=("L4_REAL_TRAIN","L4_REAL_SELECT","L4_REAL_DEV")
COUNTS={"L4_REAL_TRAIN":1200,"L4_REAL_SELECT":300,"L4_REAL_DEV":300}
TOKEN=re.compile(r"[a-z]+(?:'[a-z]+)?")
# Pre-frozen physical-line blocks 70%, 15%, 15%, with one window/line.
PERCENT=(0.70,0.85)


def canonical(obj):
    return json.dumps(obj,sort_keys=True,ensure_ascii=True,allow_nan=False,
                      separators=(",",":")).encode("ascii")


def verify(data):
    if type(data) is not bytes or len(data)!=EXPECTED_SIZE:
        raise ValueError("L4_EXTERNAL_RAW_FILE_BYTE_CUSTODY_DRIFT")
    object_sha=hashlib.sha1(
        b"blob "+str(len(data)).encode("ascii")+b"\0"+data).hexdigest()
    if object_sha!=EXPECTED_GIT_SHA1:
        raise ValueError("L4_FROZEN_EXTERNAL_GIT_OBJECT_DRIFT")
    return hashlib.sha256(data).hexdigest()


def acquire(path):
    """Retrieval only on user-authorized GitHub-hosted CI; source never committed."""
    dest=Path(path)
    with urllib.request.urlopen(SOURCE_URL,timeout=45) as resp:
        raw=resp.read(EXPECTED_SIZE+1)
    sha=verify(raw)
    dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_bytes(raw)
    return sha


def examples_from_bytes(raw):
    verify(raw)
    physical_lines=raw.decode("utf-8").splitlines()
    n=len(physical_lines)
    limits=(int(n*PERCENT[0]),int(n*PERCENT[1]),n)
    starts=(0,limits[0],limits[1])
    roles={}
    used_examples=set()
    for role,lo,hi in zip(ROLES,starts,limits):
        items=[]
        for i in range(lo,hi):
            words=TOKEN.findall(physical_lines[i].lower())
            if not (9<=len(words)<=40):
                continue
            seed=hashlib.sha256(
                f"{NAMESPACE}:{i}".encode("ascii")).digest()
            gap=3+int.from_bytes(seed[:8],"big")%(len(words)-6)
            left=tuple(words[gap-3:gap])
            gold=tuple(words[gap:gap+2])
            right=tuple(words[gap+2:gap+5])
            if not(len(left)==3 and len(gold)==2 and len(right)==3):
                continue
            fingerprint=(left,gold,right)
            if fingerprint in used_examples:
                continue
            used_examples.add(fingerprint)
            items.append({
                "physical_line":i,
                "left":list(left),
                "gold":list(gold),
                "right":list(right),
            })
            if len(items)==COUNTS[role]:
                break
        if len(items)!=COUNTS[role]:
            raise ValueError("L4_FROZEN_PHYSICAL_CHRONOLOGY_ROLE_QUOTA_FAIL_"+role)
        roles[role]=tuple(items)
    return roles


def digest(episodes):
    return hashlib.sha256(canonical(episodes)).hexdigest()


def load_file(path):
    raw=Path(path).read_bytes()
    sha=verify(raw)
    roles=examples_from_bytes(raw)
    return sha,roles

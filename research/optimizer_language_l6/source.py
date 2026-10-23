"""L6 external Pride public source. Raw Git blob verified before text use.

Word-prefix + left/right context are the ONLY predictors' inputs.
Original physical line positions and gold full words are never provided
to any fit model at DEV inference.
"""
import hashlib
import json
from pathlib import Path
import re
import urllib.request

NAMESPACE="l6-20261023-pride-stem-affix-v1"
SOURCE_URL=("https://raw.githubusercontent.com/GITenberg/Pride-and-Prejudice_1342/"
            "81db45c9c48c592f0b77f01fc59e677ad0a5634e/1342-0.txt")
GIT_BLOB="20c3737a33af2501e4c0597285ad630ef42e8e46"
RAW_BYTES=724725
ROLES=("L6_TRAIN","L6_SELECT","L6_DEV")
COUNTS={"L6_TRAIN":900,"L6_SELECT":200,"L6_DEV":240}
TOKEN=re.compile(r"[a-z]+(?:'[a-z]+)?")


def canonical(obj):
    return json.dumps(obj,sort_keys=True,separators=(",",":"),
                      ensure_ascii=True,allow_nan=False).encode("ascii")


def verify(raw):
    if type(raw) is not bytes or len(raw)!=RAW_BYTES:
        raise ValueError("L6_RAW_EXTERNAL_LENGTH_DRIFT")
    blob=hashlib.sha1(
        b"blob "+str(len(raw)).encode("ascii")+b"\0"+raw).hexdigest()
    if blob!=GIT_BLOB:
        raise ValueError("L6_ORIGINAL_EXTERNAL_GIT_BLOB_DRIFT")
    return hashlib.sha256(raw).hexdigest()


def acquire(path):
    with urllib.request.urlopen(SOURCE_URL,timeout=45) as f:
        raw=f.read(RAW_BYTES+1)
    sha=verify(raw)
    dest=Path(path)
    dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_bytes(raw)
    return sha


def rows_from_raw(raw):
    verify(raw)
    lines=raw.decode("utf-8").splitlines()
    breaks=(0,int(.70*len(lines)),int(.85*len(lines)),len(lines))
    used=set()
    result={}
    for j,role in enumerate(ROLES):
        rows=[]
        for lineno in range(breaks[j],breaks[j+1]):
            toks=TOKEN.findall(lines[lineno].lower())
            if not (9<=len(toks)<=65):
                continue
            possible=[i for i in range(3,len(toks)-3)
                      if re.fullmatch(r"[a-z]{5,18}",toks[i])]
            if not possible:
                continue
            h=hashlib.sha256(
                f"{NAMESPACE}:{lineno}".encode("ascii")).digest()
            chosen=possible[int.from_bytes(h[:8],"big")%len(possible)]
            left=toks[chosen-3:chosen]
            right=toks[chosen+1:chosen+4]
            target=toks[chosen]
            fingerprint=canonical((left,target,right))
            if fingerprint in used:
                continue
            used.add(fingerprint)
            rows.append({"left":left,"right":right,"prefix":target[:3],
                         "gold":target,"line":lineno})
            if len(rows)==COUNTS[role]:
                break
        if len(rows)!=COUNTS[role]:
            raise ValueError("L6_FROZEN_SOURCE_ROLE_QUOTA_UNAVAILABLE_"+role)
        result[role]=tuple(rows)
    return result


def load(path):
    raw=Path(path).read_bytes()
    sha=verify(raw)
    return sha,rows_from_raw(raw)


def digest(rows):
    return hashlib.sha256(canonical(rows)).hexdigest()

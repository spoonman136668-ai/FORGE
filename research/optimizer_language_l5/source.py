"""L5 external public Alice word prefix source; immutable verified raw text.

Only 3-letter prefix and left/right three real words given at evaluation.
Gold full target revealed in TRAIN for fitting and DEV strictly for scoring.
Public well-known book; not independent blinded science.
"""
import hashlib
import json
from pathlib import Path
import re
import urllib.request

NAMESPACE="l5-20261023-alice-prefix-subword-v1"
URL=("https://raw.githubusercontent.com/GITenberg/Alice-s-Adventures-in-Wonderland_11/"
     "7f18748e114b994d5d9454d5793581bc0b9cf9d7/11-0.txt")
BLOB="0f25e9af379233267a09623e0c650472f9e463ea"
SIZE=173595
ROLES=("L5_TRAIN","L5_SELECT","L5_DEV")
COUNTS={"L5_TRAIN":750,"L5_SELECT":120,"L5_DEV":160}
TOKEN=re.compile(r"[a-z]+(?:'[a-z]+)?")


def canonical(obj):
    return json.dumps(obj,ensure_ascii=True,sort_keys=True,
                      separators=(",",":"),allow_nan=False).encode("ascii")


def verify(data):
    if type(data) is not bytes or len(data)!=SIZE:
        raise ValueError("L5_EXTERNAL_SOURCE_SIZE_DRIFT")
    actual=hashlib.sha1(
        b"blob "+str(SIZE).encode("ascii")+b"\0"+data).hexdigest()
    if actual!=BLOB:
        raise ValueError("L5_EXTERNAL_SOURCE_GIT_BLOB_DRIFT")
    return hashlib.sha256(data).hexdigest()


def acquire(filename):
    with urllib.request.urlopen(URL,timeout=45) as f:
        raw=f.read(SIZE+1)
    h=verify(raw)
    p=Path(filename)
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_bytes(raw)
    return h


def rows_from_bytes(data):
    verify(data)
    lines=data.decode("utf-8").splitlines()
    n=len(lines)
    cuts=(0,int(.70*n),int(.85*n),n)
    result={}
    fingerprints=set()
    for j,role in enumerate(ROLES):
        selected=[]
        for lineno in range(cuts[j],cuts[j+1]):
            words=TOKEN.findall(lines[lineno].lower())
            if not 9<=len(words)<=50:
                continue
            candidates=[k for k in range(3,len(words)-3)
                        if re.fullmatch("[a-z]{5,18}",words[k])]
            if not candidates:
                continue
            seed=hashlib.sha256(
                f"{NAMESPACE}:{lineno}".encode("ascii")).digest()
            index=candidates[int.from_bytes(seed[:8],"big")%len(candidates)]
            previous=words[index-3:index]
            following=words[index+1:index+4]
            target=words[index]
            r={"left":previous,"prefix":target[:3],
               "right":following,"gold":target,"line":lineno}
            fingerprint=canonical((previous,target,following))
            if fingerprint in fingerprints:
                continue
            fingerprints.add(fingerprint)
            selected.append(r)
            if len(selected)==COUNTS[role]:
                break
        if len(selected)!=COUNTS[role]:
            raise ValueError("L5_ROLE_QUOTA_UNACHIEVABLE_"+role)
        result[role]=tuple(selected)
    return result


def load(path):
    raw=Path(path).read_bytes()
    h=verify(raw)
    return h,rows_from_bytes(raw)


def digest(rows):
    return hashlib.sha256(canonical(rows)).hexdigest()

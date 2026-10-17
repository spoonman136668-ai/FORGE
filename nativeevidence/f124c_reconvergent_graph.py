"""F124-C source-only adversarial reconvergence generator, TRAIN admission only.

Freeze precedes implementation (Git blob 18d1c037d74224905a59c72f7e9fa2fcdbe73505).
No F123/F124 reserved confirmation case is constructed or inspected here.
Separate exact traversal is a reference oracle and NEVER a model feature.
"""
from __future__ import annotations
from collections import Counter
import hashlib
import json
from pathlib import Path
import random

ROOT=Path(__file__).resolve().parents[1]
FREEZE=ROOT/"reference/research-intake/f124c-compact-causal-composition-freeze.json"
FREEZE_BLOB="18d1c037d74224905a59c72f7e9fa2fcdbe73505"
SCHEMA="forge.research.f124c.frozen-compact-causal-composition-development.v1"
PARENT="bbdae44c217dba2234705d8327573476158fe1c1"
TRAIN={"Wingless":range(100000,100024),"Yggdrasil":range(110000,110024)}
RESERVED_CONFIRM={"Wingless":range(100100,100148),"Yggdrasil":range(110100,110148)}
FIELDS={"start","target","roles","edges"}
EDGE_FIELDS={"from","to","role","src_bits","dst_bits"}

class Quarantined(ValueError): pass
def require(ok, code):
    if not ok: raise Quarantined("F124C_"+code)

def git_blob(raw):
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

def frozen():
    raw=FREEZE.read_bytes().replace(b"\r\n",b"\n")
    require(git_blob(raw)==FREEZE_BLOB,"FROZEN_PROTOCOL_DRIFT")
    p=json.loads(raw)
    c=p["cohorts"]
    require(p["schema"]==SCHEMA and p["status"]=="PREIMPLEMENTATION_FREEZE"
            and p["parent_f123_audit_head"]==PARENT
            and p["qualified_f123_source_head"]=="7882849a59964f412a87589be653114e7bf64d52"
            and c["train_pair_seeds"]=={"Wingless":[100000,100023],"Yggdrasil":[110000,110023]}
            and c["confirm_pair_seeds"]=={"Wingless":[100100,100147],"Yggdrasil":[110100,110147]}
            and c["training_epochs"]==100 and c["trainable_parameter_max"]==768
            and c["training_hops"]==[3,4] and c["confirmation_hops"]==[7,9]
            and c["vectors_per_lane"]==2 and c["train_pairs_per_vector"]==24
            and all(p["authority"].values()),"FROZEN_CONTRACT_DRIFT")
    return hashlib.sha256(raw).hexdigest()

def validate(g):
    require(type(g) is dict and set(g)==FIELDS,"GRAPH_PRIVILEGE_OR_FIELD_DRIFT")
    require(type(g["start"]) is str and type(g["target"]) is str and
            g["start"]!=g["target"] and type(g["roles"]) is list and
            len(g["roles"]) in (3,4) and all(type(r) is str and r for r in g["roles"])
            and type(g["edges"]) is list and 4 <= len(g["edges"]) <= 128,
            "GRAPH_BOUNDS")
    for e in g["edges"]:
        require(type(e) is dict and set(e)==EDGE_FIELDS,
                "EDGE_PRIVILEGED_FIELD")
        require(all(type(e[k]) is str and e[k] for k in ("from","to","role")),
                "EDGE_ID_INVALID")
        for k in ("src_bits","dst_bits"):
            require(type(e[k]) is list and len(e[k])==16 and
                    all(type(v) is int and v in (0,1) for v in e[k]),
                    "RAW_TOKEN_BOUNDS")
    return g

def oracle(g,ignore_slots=False):
    """Pure public graph dynamic traversal; oracle is never given to learners."""
    validate(g)
    state=[(g["start"],None)]
    for role in g["roles"]:
        next_state=[]
        for node,prev in state:
            for e in g["edges"]:
                if e["from"]==node and e["role"]==role and (
                    ignore_slots or prev is None or prev==e["src_bits"]):
                    next_state.append((e["to"],e["dst_bits"]))
                    require(len(next_state)<=256,"PUBLIC_TRAVERSAL_BUDGET")
        state=next_state
    return sum(node==g["target"] for node,_ in state)

def pair_parity(a,b):
    validate(a);validate(b)
    require(a["start"]==b["start"] and a["target"]==b["target"] and
            a["roles"]==b["roles"],"QUERY_PARITY")
    def digest(g):
        return (Counter((e["from"],e["to"],e["role"]) for e in g["edges"]),
                Counter(tuple(bits) for e in g["edges"]
                        for bits in (e["src_bits"],e["dst_bits"])))
    require(digest(a)==digest(b),"TOPOLOGY_OR_RAW_TOKEN_MARGINAL_DRIFT")
    require(oracle(a)==1 and oracle(b)==0,"AMBIGUOUS_CAUSAL_TRUTH")
    require(oracle(a,True)>=3 and oracle(b,True)>=3,
            "ABSENT_RECONVERGENT_ROUTE_COLLISION")
    return True

def build(seed,vector,lane,phase="TRAIN"):
    frozen()
    require(phase=="TRAIN" and lane in TRAIN and
            type(seed) is int and seed in TRAIN[lane] and
            type(vector) is list and len(vector)==3 and
            all(type(v) is int and 0<=v<=3 for v in vector),
            "PROTECTED_OR_NONREGISTERED_SOURCE")
    hops=3+(seed%2)
    stratum=("alias","near_collision","parallel")[seed%3]
    source=f"f124c/{lane}/TRAIN/{seed}/{','.join(map(str,vector))}"
    rng=random.Random(int.from_bytes(hashlib.sha256(source.encode()).digest()[:8],"big"))
    def opaque(k):
        return hashlib.sha256((source+"/"+k).encode()).hexdigest()[:20]
    start,target,join=opaque("start"),opaque("target"),opaque("join-2")
    roles=[opaque("query-role-"+str(d)) for d in range(hops)]
    raw_used=set()
    def unique():
        for _ in range(1000):
            n=rng.randrange(1,65536)
            if n not in raw_used:
                raw_used.add(n);return n
        raise Quarantined("SALT_SPACE_EXHAUSTED")
    vals=[unique() for _ in range(hops+1)]
    token_by_val={}
    def bits(v):
        if v not in token_by_val: token_by_val[v]=[(v>>k)&1 for k in range(16)]
        return token_by_val[v]
    def edge(a,b,r,iv,ov):
        return {"from":a,"to":b,"role":r,"src_bits":bits(iv),"dst_bits":bits(ov)}
    nodes=[start,opaque("primary-1"),join]+[
        opaque("primary-"+str(i)) for i in range(3,hops)]+[target]
    require(len(nodes)==hops+1,"PRIMARY_LENGTH_DRIFT")
    positive=[edge(nodes[i],nodes[i+1],roles[i],vals[i],vals[i+1])
              for i in range(hops)]
    for branch in (1,2):
        mid=opaque("branch-"+str(branch)+"-1")
        begin=unique()
        carried=unique()
        arrival=unique()
        if branch==1 and stratum=="near_collision":
            arrival=vals[2]^(1<<(seed%16))
            require(arrival!=vals[2],"INVALID_NEAR_COLLISION")
        positive.extend([edge(start,mid,roles[0],begin,carried),
                         edge(mid,join,roles[1],carried,arrival)])
    junk_idx=len(positive)
    positive.append(edge(start,opaque("junk-"+stratum),opaque("off-role"),
                         unique(),unique()))
    if stratum=="alias":
        # This edge has a legitimate-looking slot alias but the wrong role.
        positive.append(edge(join,opaque("alias-end"),opaque("alias-role"),
                             vals[2],unique()))
    elif stratum=="parallel":
        # Parallel same-role public edge differs in both visible slot tokens.
        positive.append(edge(nodes[1],join,roles[1],unique(),unique()))
    for i in range(vector[0]%3):
        positive.append(edge(opaque(f"noise-{i}"),opaque(f"noise-to-{i}"),
                             opaque(f"noise-role-{i}"),unique(),unique()))
    # Paired intervention swaps only the publicly visible source-slot tokens.
    # Source/target, graph topology, role sequence and token histogram are fixed.
    negative=json.loads(json.dumps(positive))
    bridge=2
    negative[bridge]["src_bits"],negative[junk_idx]["src_bits"]=(
        negative[junk_idx]["src_bits"],negative[bridge]["src_bits"])
    rng.shuffle(positive)
    rng.shuffle(negative)
    a={"start":start,"target":target,"roles":roles,"edges":positive}
    b={"start":start,"target":target,"roles":roles,"edges":negative}
    pair_parity(a,b)
    return a,b

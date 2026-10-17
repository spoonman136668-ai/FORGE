"""F124-H newly salted key-value binding challenge; TRAIN-only admission.

The preimplementation freeze Git blob is checked before graph construction.
Exact raw-token public traversal is an admission reference, never a model input.
"""
from __future__ import annotations
from collections import Counter
import hashlib
import json
from pathlib import Path
import random

FREEZE=Path(__file__).resolve().parents[1]/"reference/research-intake/f124h-depth-invariant-evidence-freeze.json"
FREEZE_BLOB="5b3ca556f2cf55323b6317d506a62c6b2a4aab85"
TRAIN={"Wingless":range(180000,180024),"Yggdrasil":range(190000,190024)}
RESERVED_CONFIRM={"Wingless":range(180100,180148),"Yggdrasil":range(190100,190148)}
GRAPH_KEYS={"start","target","roles","edges"}
EDGE_KEYS={"from","to","role","src_bits","dst_bits"}
STRATA=("near_collision","wrong_role_alias","parallel_multiedge","repeated_key","late_cross_route")

class Invalid(ValueError):
    pass

def require(test,code):
    if not test: raise Invalid("F124H_"+code)

def git_blob(raw):
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

def frozen():
    raw=FREEZE.read_bytes().replace(b"\r\n",b"\n")
    require(git_blob(raw)==FREEZE_BLOB,"FROZEN_CONTRACT_DRIFT")
    p=json.loads(raw)
    require(p["schema"]=="forge.research.f124h.frozen-depth-invariant-competing-evidence.v1" and
            p["status"]=="PREIMPLEMENTATION_FREEZE" and
            p["parent_f124g_exact_head"]=="73bf69fea2a6d8932547c09a8c29741e95f983df" and
            p["cohorts"]["TRAIN"]=={"Wingless":[180000,180023],"Yggdrasil":[190000,190023]} and
            p["cohorts"]["RESERVED_CONFIRM"]=={"Wingless":[180100,180147],"Yggdrasil":[190100,190147]} and
            p["mechanisms"]["training"].startswith("100 fixed epochs") and
            all(p["authority"].values()),"INCOMPATIBLE_FROZEN_PROTOCOL")
    return hashlib.sha256(raw).hexdigest()

def validate(g):
    require(type(g) is dict and set(g)==GRAPH_KEYS,"INVALID_PUBLIC_GRAPH_KEYS")
    require(type(g["start"]) is str and type(g["target"]) is str and
            g["start"]!=g["target"] and type(g["roles"]) is list and
            len(g["roles"]) in (4,5) and
            all(type(x) is str and x for x in g["roles"]) and
            type(g["edges"]) is list and 8<=len(g["edges"])<=128,
            "GRAPH_TOPOLOGY_BUDGET")
    nodes={g["start"],g["target"]}
    for edge in g["edges"]:
        require(type(edge) is dict and set(edge)==EDGE_KEYS,"FORBIDDEN_EDGE_FEATURE")
        require(all(type(edge[x]) is str and edge[x] for x in ("from","to","role")),
                "GRAPH_ID_INVALID")
        nodes.update((edge["from"],edge["to"]))
        for field in ("src_bits","dst_bits"):
            require(type(edge[field]) is list and len(edge[field])==16 and
                    all(type(v) is int and v in (0,1) for v in edge[field]),
                    "RAW_TOKEN_OR_ORACLE_FEATURE")
    require(len(nodes)<=64,"NODE_BUDGET")
    return g

def public_routes(g,without_tokens=False):
    validate(g)
    frontier=[(g["start"],None)]
    for role in g["roles"]:
        following=[]
        for current,key in frontier:
            for edge in g["edges"]:
                if edge["from"]==current and edge["role"]==role and (
                    without_tokens or key is None or key==edge["src_bits"]):
                    following.append((edge["to"],edge["dst_bits"]))
                    require(len(following)<=256,"REFERENCE_FRONTIER_BUDGET")
        frontier=following
    return sum(node==g["target"] for node,_ in frontier)

def paired_admit(pos,neg):
    validate(pos);validate(neg)
    require(all(pos[k]==neg[k] for k in ("start","target","roles")),
            "PAIRED_QUERY_DRIFT")
    def inventory(x):
        return (Counter((e["from"],e["to"],e["role"]) for e in x["edges"]),
                Counter(tuple(e[k]) for e in x["edges"]
                        for k in ("src_bits","dst_bits")))
    require(inventory(pos)==inventory(neg),"PAIRED_TOPOLOGY_OR_TOKEN_LEAK")
    require(public_routes(pos)==1 and public_routes(neg)==0,
            "AMBIGUOUS_CAUSAL_IDENTITY")
    require(public_routes(pos,True)>=5 and public_routes(neg,True)>=5,
            "INSUFFICIENT_COMPETING_KEYS")
    return True

def build(seed,vector,lane,phase="TRAIN"):
    frozen()
    require(phase=="TRAIN" and lane in TRAIN and
            type(seed) is int and seed in TRAIN[lane] and
            type(vector) is list and len(vector)==3 and
            all(type(v) is int and 0<=v<=3 for v in vector),
            "RESERVED_OR_UNAUTHENTICATED_SOURCE")
    hops=4+(seed%2)
    family=STRATA[seed%len(STRATA)]
    salt=("forge/F124H/independent/depth-invariant-evidence/"+lane+"/TRAIN/"+str(seed)+"/"+
          ",".join(map(str,vector)))
    rng=random.Random(int.from_bytes(hashlib.sha256(salt.encode()).digest()[:12],"big"))
    def opaque(s):
        return hashlib.sha256((salt+"/"+s).encode()).hexdigest()[:22]
    roles=[opaque("role-"+str(i)) for i in range(hops)]
    points=[opaque("main-node-"+str(i)) for i in range(hops+1)]
    observed=set()
    def key():
        for _ in range(1024):
            v=rng.randrange(1,65536)
            if v not in observed:
                observed.add(v);return v
        raise Invalid("TOKEN_SPACE_EXHAUSTED")
    primary=[key() for _ in range(hops+1)]
    def bits(v):
        return [(v>>i)&1 for i in range(16)]
    def edge(a,b,r,x,y):
        return {"from":a,"to":b,"role":r,"src_bits":bits(x),"dst_bits":bits(y)}
    outgoing=[edge(points[i],points[i+1],roles[i],primary[i],primary[i+1])
              for i in range(hops)]
    # Two different incoming key/value records reach the FIRST shared node.
    arrivals=[]
    for i in range(2):
        mid=opaque("incoming-key-value-"+str(i))
        intermediate=key()
        arrival=key()
        if family=="near_collision" and i==0:
            alias=primary[2] ^ (1 << (seed%16))
            if alias not in observed:
                arrival=alias
                observed.add(alias)
        arrivals.append(arrival)
        outgoing.extend([edge(points[0],mid,roles[0],key(),intermediate),
                         edge(mid,points[2],roles[1],intermediate,arrival)])
    # Wrong-key second-stage exits converge at the later public node too.
    for i,arrival in enumerate(arrivals):
        if hops==4:
            bogus_dst=key()
            outgoing.append(edge(points[2],points[3],roles[2],arrival,bogus_dst))
        else:
            intermediate_node=opaque("second-stage-key-"+str(i))
            midvalue=key()
            outgoing.extend([edge(points[2],intermediate_node,roles[2],arrival,midvalue),
                             edge(intermediate_node,points[4],roles[3],midvalue,key())])
    if family=="wrong_role_alias":
        outgoing.append(edge(points[2],opaque("wrong-role-alias"),opaque("wrong-role"),
                             primary[2],key()))
    if family=="parallel_multiedge":
        outgoing.append(edge(points[1],points[2],roles[1],key(),key()))
    if family=="repeated_key":
        outgoing.append(edge(points[2],opaque("repeated-key"),opaque("off-role"),
                             arrivals[0],key()))
    if family=="late_cross_route":
        outgoing.append(edge(points[3],opaque("later-cross-route"),opaque("off-role"),
                             primary[3],key()))
    junk=len(outgoing)
    outgoing.append(edge(points[0],opaque("negative-swap-junk"),opaque("offrole-junk"),
                         key(),key()))
    for k in range(vector[0]%3):
        outgoing.append(edge(opaque("noise-"+str(k)),opaque("noise-dest-"+str(k)),
                             opaque("noise-role-"+str(k)),key(),key()))
    negative=json.loads(json.dumps(outgoing))
    negative[2]["src_bits"],negative[junk]["src_bits"]=(
        negative[junk]["src_bits"],negative[2]["src_bits"])
    rng.shuffle(outgoing)
    rng.shuffle(negative)
    pos={"start":points[0],"target":points[-1],"roles":roles,"edges":outgoing}
    neg={"start":points[0],"target":points[-1],"roles":roles,"edges":negative}
    paired_admit(pos,neg)
    return pos,neg

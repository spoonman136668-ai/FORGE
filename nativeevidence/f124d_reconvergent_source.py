"""F124-D TRAIN-only two-reconvergence raw-slot challenge generator.

The source and cohort contract was frozen first (Git blob
83dd63eb42e41c5583570d055b806b24f4ece5a6).
The reserved F124-D and earlier F123/F124-C confirmations are inaccessible.
Exact public symbolic reachability is an admission oracle, NOT a model feature.
"""
from __future__ import annotations
from collections import Counter
import hashlib
import json
from pathlib import Path
import random

ROOT=Path(__file__).resolve().parents[1]
FREEZE=ROOT/"reference/research-intake/f124d-mass-conserving-competition-freeze.json"
FREEZE_BLOB="83dd63eb42e41c5583570d055b806b24f4ece5a6"
PARENT="93b67755be286208adeafde01e5b0bd140df82a9"
SCHEMA="forge.research.f124d.frozen-competitive-causal-state.v1"
TRAIN={"Wingless":range(120000,120024),"Yggdrasil":range(130000,130024)}
RESERVED_CONFIRM={"Wingless":range(120100,120148),"Yggdrasil":range(130100,130148)}
GRAPH_FIELDS={"start","target","roles","edges"}
EDGE_FIELDS={"from","to","role","src_bits","dst_bits"}
STRATA=("early_rejoin","late_rejoin","alias_swap","near_collision","parallel_multiedge")

class Invalid(ValueError): pass

def require(ok,msg):
    if not ok: raise Invalid("F124D_"+msg)

def git_blob(raw):
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

def frozen():
    raw=FREEZE.read_bytes().replace(b"\r\n",b"\n")
    require(git_blob(raw)==FREEZE_BLOB,"FROZEN_SOURCE_CONTRACT_DRIFT")
    p=json.loads(raw)
    c=p["cohorts"]
    require(p["schema"]==SCHEMA and p["status"]=="PREIMPLEMENTATION_FREEZE"
            and p["parent_diagnostic_head"]==PARENT
            and c["train_seed_intervals"]=={"Wingless":[120000,120023],"Yggdrasil":[130000,130023]}
            and c["reserved_confirm_intervals"]=={"Wingless":[120100,120147],"Yggdrasil":[130100,130147]}
            and p["training"]["epochs"]==100 and p["training"]["slots_per_node"]==2
            and p["training"]["trainable_parameter_max"]==768
            and all(p["authority"].values()),"SOURCE_CONTRACT_INVALID")
    return hashlib.sha256(raw).hexdigest()

def validate(g):
    require(type(g) is dict and set(g)==GRAPH_FIELDS,"FORBIDDEN_OR_MISSING_GRAPH_FIELDS")
    require(type(g["start"]) is str and type(g["target"]) is str and
            g["start"]!=g["target"] and type(g["roles"]) is list and
            len(g["roles"]) in (4,5) and
            all(type(x) is str and x for x in g["roles"]) and
            type(g["edges"]) is list and 7<=len(g["edges"])<=128,
            "QUERY_OR_EDGE_BOUNDS")
    nodes={g["start"],g["target"]}
    for edge in g["edges"]:
        require(type(edge) is dict and set(edge)==EDGE_FIELDS,
                "FORBIDDEN_OR_MISSING_EDGE_FIELDS")
        require(all(type(edge[k]) is str and edge[k] for k in ("from","to","role")),
                "INVALID_PUBLIC_GRAPH_IDS")
        nodes.update((edge["from"],edge["to"]))
        for k in ("src_bits","dst_bits"):
            require(type(edge[k]) is list and len(edge[k])==16 and
                    all(type(bit) is int and bit in (0,1) for bit in edge[k]),
                    "RAW_TOKEN_CONTRACT")
    require(len(nodes)<=64,"NODE_BUDGET_EXCEEDED")
    return g

def routes(g,ignore_slots=False):
    validate(g)
    state=[(g["start"],None)]
    for role in g["roles"]:
        following=[]
        for at,carried in state:
            for edge in g["edges"]:
                if edge["from"]==at and edge["role"]==role and (
                    ignore_slots or carried is None or carried==edge["src_bits"]):
                    following.append((edge["to"],edge["dst_bits"]))
                    require(len(following)<=256,"REFERENCE_ORACLE_BUDGET")
        state=following
    return sum(node==g["target"] for node,_ in state)

def parity(positive,negative):
    validate(positive);validate(negative)
    require(all(positive[k]==negative[k] for k in ("start","target","roles")),
            "PAIR_QUERY_DRIFT")
    def inventory(g):
        return (Counter((e["from"],e["to"],e["role"]) for e in g["edges"]),
                Counter(tuple(e[k]) for e in g["edges"]
                        for k in ("src_bits","dst_bits")))
    require(inventory(positive)==inventory(negative),
            "COUNTERFACTUAL_TOPOLOGY_OR_TOKEN_HISTOGRAM_DRIFT")
    require(routes(positive)==1 and routes(negative)==0,
            "INVALID_UNAMBIGUOUS_PUBLIC_TRUTH")
    require(routes(positive,True)>=6 and routes(negative,True)>=6,
            "TOO_FEW_ROLE_COMPETING_ROUTES")
    return True

def build(seed,vector,lane,phase="TRAIN"):
    frozen()
    require(phase=="TRAIN" and lane in TRAIN and
            type(seed) is int and seed in TRAIN[lane] and
            type(vector) is list and len(vector)==3 and
            all(type(v) is int and v in (0,1,2,3) for v in vector),
            "RESERVED_OR_UNQUALIFIED_COHORT")
    hops=4+(seed%2)
    stratum=STRATA[seed%len(STRATA)]
    origin="f124d/independent-source-birth/"+lane+"/TRAIN/"+str(seed)+"/"+",".join(map(str,vector))
    rnd=random.Random(int.from_bytes(hashlib.sha256(origin.encode()).digest()[:16],"big"))
    def node(name):
        return hashlib.sha256((origin+"/NODE/"+name).encode()).hexdigest()[:22]
    roles=[node("ROLE-"+str(i)) for i in range(hops)]
    nodes=[node("primary-"+str(i)) for i in range(hops+1)]
    used=set()
    def token():
        for _ in range(2048):
            n=rnd.randrange(1,65536)
            if n not in used:
                used.add(n);return n
        raise Invalid("TOKEN_SPACE_EXHAUSTED")
    vals=[token() for _ in range(hops+1)]
    def raw(n):
        return [(n>>bit)&1 for bit in range(16)]
    def edge(a,b,role,left,right):
        return {"from":a,"to":b,"role":role,"src_bits":raw(left),"dst_bits":raw(right)}
    positive=[edge(nodes[i],nodes[i+1],roles[i],vals[i],vals[i+1])
              for i in range(hops)]
    # First true reconvergence: three+ public candidate routes merge at nodes[2].
    for i in range(2+(stratum=="early_rejoin")):
        mid=node("first-branch-"+str(i))
        carried=token()
        arrival=token()
        positive.extend([edge(nodes[0],mid,roles[0],token(),carried),
                         edge(mid,nodes[2],roles[1],carried,arrival)])
    # Second true reconvergence: three+ competing routes to nodes[hops-1].
    for i in range(2+(stratum=="late_rejoin")):
        before=token()
        arrival=token()
        if stratum=="near_collision" and i==0:
            near=vals[2]^(1<<(seed%16))
            if near!=vals[2] and near not in used:
                before=near;used.add(near)
        if hops==4:
            positive.append(edge(nodes[2],nodes[3],roles[2],before,arrival))
        else:
            mid=node("second-branch-"+str(i))
            carry=token()
            positive.extend([edge(nodes[2],mid,roles[2],before,carry),
                             edge(mid,nodes[4],roles[3],carry,arrival)])
    if stratum=="alias_swap":
        positive.append(edge(nodes[2],node("alias-end"),node("off-role-alias"),
                             vals[2],token()))
    if stratum=="parallel_multiedge":
        positive.append(edge(nodes[1],nodes[2],roles[1],token(),token()))
    # Unrelated off-role source token for balanced counterfactual intervention.
    junk_idx=len(positive)
    positive.append(edge(nodes[0],node("offroute-sink"),node("off-role-swap"),
                         token(),token()))
    for j in range(vector[0]%3):
        positive.append(edge(node("noise-"+str(j)),node("noise-dest-"+str(j)),
                             node("noise-role-"+str(j)),token(),token()))
    negative=json.loads(json.dumps(positive))
    # Break the one causal bridge, without changing public shape/token marginals.
    negative[2]["src_bits"],negative[junk_idx]["src_bits"]=(
        negative[junk_idx]["src_bits"],negative[2]["src_bits"])
    rnd.shuffle(positive)
    rnd.shuffle(negative)
    p={"start":nodes[0],"target":nodes[-1],"roles":roles,"edges":positive}
    n={"start":nodes[0],"target":nodes[-1],"roles":roles,"edges":negative}
    parity(p,n)
    return p,n

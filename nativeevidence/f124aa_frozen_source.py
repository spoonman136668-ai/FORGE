"""F124-AA pre-frozen novel public graph families; no oracle inside inference.

Each phase/lane has 48 pairs, 12 per family, four per 7/8/9-depth stratum.
Original Q generator bytecode is used with only new allowed seed identity.
Long-depth (10-12) graphs use a separately scoped validator so original
Q/Z source/model files are not modified.
"""
from __future__ import annotations
import hashlib, json, math, random, types
from pathlib import Path

import f124z_sparse_continuity as z
import f124q_fresh_source as q
import f124w_hop_trace_indexed as witness

FREEZE=Path(__file__).resolve().parents[1]/"reference/research-intake/f124aa-frozen-transfer-packed-state.json"
FREEZE_BLOB="44520db702ef71623d6bc17d1daa035b50095a3c"
PARENT_BLOB="94f2b157b685792d8aa30265b91f6de040f30de5"
COHORTS={
 "Wingless":{"FIT":range(1380000,1380024),"DEV":range(1380100,1380124)},
 "Yggdrasil":{"FIT":range(1390000,1390024),"DEV":range(1390100,1390124)}
}
VECTORS=z.VECTORS
FAMILIES=("permuted_bits","dense_distractors","extended_depth","one_bit_relaxed_keys")


def need(v,why):
    q.need(v,"F124AA_"+why)


def frozen():
    z.frozen()
    need(witness.blob(FREEZE)==FREEZE_BLOB,"PREIMPLEMENTATION_FREEZE_BLOB")
    p=json.loads(FREEZE.read_text(encoding="utf-8"))
    need(p["schema"]=="forge.research.f124aa.frozen-cross-family-transfer-and-packed-state.v1"
         and p["state"]=="PREIMPLEMENTATION_FROZEN"
         and p["lineage"]["qualified_parent"]==
             "62db833856e523c45c82cf11f3d76bf0f5d7c257"
         and p["lineage"]["parent_model_blob"]==PARENT_BLOB
         and p["source"]["FIT"]==
           {lane:[x["FIT"].start,x["FIT"].stop-1] for lane,x in COHORTS.items()}
         and p["source"]["DEV"]==
           {lane:[x["DEV"].start,x["DEV"].stop-1] for lane,x in COHORTS.items()}
         and p["source"]["four_families"]==list(FAMILIES),
         "FROZEN_FAMILY_AND_SOURCE")
    need(p["Wingless"]["new_architecture"].startswith("One retained packed")
         and p["Yggdrasil"]["new_hypothesis"].startswith("Transfer test")
         and all(v is False for v in p["authority"].values())
         and witness.blob(z.__file__)==PARENT_BLOB,
         "FROZEN_METHOD_OR_AUTHORITY")
    return p


def validate_extended(g):
    need(type(g) is dict and set(g)==q.GRAPH_KEYS,"PUBLIC_KEYS")
    need(type(g["start"]) is str and type(g["target"]) is str
         and g["start"]!=g["target"] and g["start"] and g["target"]
         and type(g["roles"]) is list and 7<=len(g["roles"])<=12
         and all(type(r) is str and r for r in g["roles"])
         and type(g["edges"]) is list and 12<=len(g["edges"])<=128,
         "EXTENDED_PUBLIC_BOUNDS")
    nodes={g["start"],g["target"]}
    for e in g["edges"]:
        need(type(e) is dict and set(e)==q.EDGE_KEYS
             and all(type(e[k]) is str and e[k] for k in ("from","to","role")),
             "PUBLIC_EDGE_FIELDS")
        nodes.update((e["from"],e["to"]))
        for k in ("src_bits","dst_bits"):
            need(type(e[k]) is list and len(e[k])==16
                 and all(type(b) is int and b in (0,1) for b in e[k]),
                 "PUBLIC_RAW_16_BITS")
    need(len(nodes)<=64,"PUBLIC_NODE_BOUND")
    return g


def routes(g,relaxed=False,role_only=False):
    """Admission oracle ONLY. Predictions must not call this."""
    validate_extended(g)
    frontier=[(g["start"],None)]
    for role in g["roles"]:
        after=[]
        for node,carry in frontier:
            for e in g["edges"]:
                if e["from"]!=node or e["role"]!=role:continue
                valid=(carry is None or role_only or
                       sum(a!=b for a,b in zip(carry,e["src_bits"]))<=
                            (1 if relaxed else 0))
                if valid:after.append((e["to"],tuple(e["dst_bits"])))
                need(len(after)<=256,"ORACLE_ONLY_FRONTIER_LIMIT")
        frontier=after
    return sum(node==g["target"] for node,_ in frontier)


def positive_route(g):
    """Generator/evaluator only, NOT model: unique raw-key matching route."""
    frontier=[(g["start"],None,[])]
    for role in g["roles"]:
        nxt=[]
        for node,carry,hist in frontier:
            for e in g["edges"]:
                if e["from"]==node and e["role"]==role and (
                  carry is None or carry==tuple(e["src_bits"])):
                    nxt.append((e["to"],tuple(e["dst_bits"]),hist+[e]))
                    need(len(nxt)<=256,"SOURCE_REFERENCE_LIMIT")
        frontier=nxt
    result=[h for node,_,h in frontier if node==g["target"]]
    need(len(result)==1,"ORIGINAL_POSITIVE_REFERENCE_UNIQUE")
    return result[0]


def build(lane,seed,vector,phase):
    need(lane in COHORTS and phase in ("FIT","DEV")
         and type(seed) is int and seed in COHORTS[lane][phase]
         and tuple(vector) in VECTORS
         and seed not in z.COHORTS[lane]["FIT"]
         and seed not in z.COHORTS[lane]["DEV"]
         and seed not in q.COHORTS[lane]["FIT"]
         and seed not in q.COHORTS[lane]["DEV"]
         and seed not in q.FORBIDDEN[lane],"FRESH_SOURCE_IDENTITY")
    env=dict(z.build.__globals__)
    env["COHORTS"]=COHORTS
    f=types.FunctionType(z.build.__code__,env,z.build.__name__,z.build.__defaults__)
    pos,neg=f(lane,seed,vector,phase)
    family=FAMILIES[(seed-COHORTS[lane][phase].start)%4]
    rng=random.Random(int.from_bytes(hashlib.sha256(
        ("F124AA/transform/v1/"+lane+"/"+phase+"/"+str(seed)+
         "/"+",".join(map(str,vector))).encode()).digest()[:12],"big"))
    p=json.loads(json.dumps(pos))
    n=json.loads(json.dumps(neg))
    def new_token(label):
        return hashlib.sha256(("F124AA/"+lane+"/"+phase+"/"+str(seed)+
                               "/"+",".join(map(str,vector))+"/"+label).encode()
                              ).hexdigest()[:22]
    def new_bits(label):
        v=hashlib.sha256((new_token(label)+"/raw").encode()).digest()
        return [((int.from_bytes(v[:2],"big")>>i)&1) for i in range(16)]
    if family=="permuted_bits":
        ix=list(range(16));rng.shuffle(ix)
        for g in (p,n):
            for edge in g["edges"]:
                for k in ("src_bits","dst_bits"):
                    b=edge[k];edge[k]=[b[j] for j in ix]
    elif family=="dense_distractors":
        path=positive_route(p)
        second_node=path[1]["to"]
        for j in range(4):
            mid=new_token("spur-node-"+str(j))
            first={"from":p["start"],"to":mid,"role":p["roles"][0],
                   "src_bits":new_bits("entry-"+str(j)),
                   "dst_bits":new_bits("internal-"+str(j))}
            second={"from":mid,"to":second_node,"role":p["roles"][1],
                    "src_bits":list(first["dst_bits"]),
                    "dst_bits":new_bits("exit-"+str(j))}
            for g in (p,n):
                g["edges"].append(json.loads(json.dumps(first)))
                g["edges"].append(json.loads(json.dumps(second)))
    elif family=="extended_depth":
        path=positive_route(p)
        endpoint=p["target"]
        carry=list(path[-1]["dst_bits"])
        for j in range(3):
            target=new_token("extension-node-"+str(j))
            role=new_token("extension-role-"+str(j))
            out=new_bits("extension-output-"+str(j))
            e={"from":endpoint,"to":target,"role":role,
               "src_bits":carry,"dst_bits":out}
            for g in (p,n):
                g["roles"].append(role)
                g["edges"].append(json.loads(json.dumps(e)))
                g["target"]=target
            endpoint=target;carry=out
    else:
        path=positive_route(p)
        selected=path[5]
        bit=rng.randrange(16)
        for g in (p,n):
            found=[e for e in g["edges"] if e["from"]==selected["from"]
                   and e["to"]==selected["to"] and e["role"]==selected["role"]]
            need(len(found)==1 and
                 found[0]["src_bits"]==selected["src_bits"],
                 "SYMMETRIC_RELAXED_KEY")
            found[0]["src_bits"][bit]^=1
    relax=family=="one_bit_relaxed_keys"
    need(routes(p,relaxed=relax)==1 and routes(n,relaxed=relax)==0,
         "FROZEN_ALTERNATIVE_SOURCE_CAUSAL_ADMISSION")
    need(routes(p,role_only=True)==routes(n,role_only=True)
         and routes(p,role_only=True)>=8,"ROLE_ONLY_NO_SHORTCUT")
    need(all(p[k]==n[k] for k in ("start","target","roles")),
         "PAIR_QUERY_DRIFT")
    def histogram(g):
        from collections import Counter
        return (Counter((e["from"],e["to"],e["role"]) for e in g["edges"]),
                Counter(tuple(e[k]) for e in g["edges"]
                        for k in ("src_bits","dst_bits")))
    need(histogram(p)==histogram(n),"PUBLIC_TOKEN_AND_TOPOLOGY_PARITY")
    return family,p,n


def pairs(lane,phase):
    result=[]
    for vector in VECTORS:
        for seed in COHORTS[lane][phase]:
            family,p,n=build(lane,seed,vector,phase)
            result.append((seed,tuple(vector),family,p,n))
    need(len(result)==48 and
         all(sum(x[2]==family for x in result)==12 for family in FAMILIES),
         "FAMILY_AND_DENOMINATOR")
    return result

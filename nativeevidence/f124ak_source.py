"""F124-AK independent braided public-graph source, source-only causal oracle.

Never imports older research graph generators. FIT and DEV sources are newly
born and fully disjoint; pair conservation includes all nodes, edges, roles,
and global raw16 source/destination token histograms.
"""
from __future__ import annotations
import hashlib,json,random
from collections import Counter
from pathlib import Path

PROTOCOL=Path(__file__).resolve().parents[1]/"reference/research-intake/f124ak-hop-supervision-freeze.json"
PROTOCOL_BLOB="53c7cd76e2a8fc44be05e186b989ef8b1a3ad86f"
FAMILIES=("near_weave","far_weave","role_weave")
SALTS={"near_weave":"forge/F124AK/learned-hop/near/v1",
       "far_weave":"forge/F124AK/learned-hop/far/v1",
       "role_weave":"forge/F124AK/learned-hop/reused/v1"}
HOPS={"near_weave":(2,4),"far_weave":(1,9),"role_weave":(3,8)}
VECTORS=((2,1,1),(1,2,1))
COHORTS={f:{"FIT":range(3290000,3290024),
            "DEV":range(3290100,3290124)} for f in FAMILIES}
FIELDS={"from","to","role","src_bits","dst_bits"}
class Quarantined(ValueError):pass
def need(test,code):
    if not test:raise Quarantined("F124AK_"+code)
def gitblob(b):
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
def frozen():
    data=PROTOCOL.read_bytes().replace(b"\r\n",b"\n")
    need(gitblob(data)==PROTOCOL_BLOB,"PREIMPLEMENTATION_BLOB_CHANGED")
    p=json.loads(data)
    need(p["schema"]=="forge.research.f124ak.intermediate-supervised-relation.v1"
       and p["stage"]=="PREIMPLEMENTATION_FROZEN"
       and p["qualified_parent"]["head"]=="9aa122181ce517f4e6967e752d8aff337c77d01c"
       and p["qualified_parent"]["run"]==39114981482
       and p["source"]["FIT_seed_interval"]==[3290000,3290023]
       and p["source"]["DEV_seed_interval"]==[3290100,3290123]
       and all(f["salt"]==SALTS[f["name"]] and
               f["error_hops"]==list(HOPS[f["name"]])
               for f in p["source"]["families"])
       and p["architecture"]["total_global_params"]==39
       and all(v is False for v in p["governance"].values()),
       "FROZEN_SOURCE_OR_GOVERNANCE_DRIFT")
    return hashlib.sha256(data).hexdigest()
def validate_public(g):
    need(type(g) is dict and set(g)=={"start","target","roles","edges"},
         "PUBLIC_GRAPH_SHAPE")
    need(type(g["start"]) is str and type(g["target"]) is str and
         g["start"]!=g["target"] and type(g["roles"]) is list
         and len(g["roles"]) in (10,11,12) and
         20<=len(g["edges"])<=128,"GRAPH_DEPTH_OR_EDGE_LIMIT")
    nodes={g["start"],g["target"]}
    for e in g["edges"]:
        need(type(e) is dict and set(e)==FIELDS,"EDGE_FIELDS")
        for k in ("from","to","role"):
            need(type(e[k]) is str and bool(e[k]),"BAD_EDGE_NODE_OR_ROLE")
        nodes.update((e["from"],e["to"]))
        for k in ("src_bits","dst_bits"):
            need(type(e[k]) is list and len(e[k])==16
              and all(type(v) is int and v in (0,1) for v in e[k]),
              "RAW16_SOURCE")
    need(len(nodes)<=64,"TOTAL_NODES_64")
    return g
def diff_bits(a,b):
    if a is None:return ()
    return tuple(i for i,(x,y) in enumerate(zip(a,b)) if x!=y)
def semantic_routes(g,rule="consistency"):
    """Source and post-prediction evaluator only. Never call in predictor."""
    validate_public(g)
    need(rule in ("consistency","tolerant","exact","role_only"),"RULE")
    state=[(g["start"],None,())]
    for role in g["roles"]:
        nxt=[]
        for node,carried,errors in state:
            for e in g["edges"]:
                if e["from"]!=node or e["role"]!=role:continue
                diff=diff_bits(carried,e["src_bits"])
                if rule=="exact" and diff:continue
                if rule in ("consistency","tolerant") and len(diff)>1:continue
                allerr=errors+diff
                if rule=="consistency" and (len(allerr)>2 or
                  (len(allerr)==2 and allerr[0]!=allerr[1])):continue
                nxt.append((e["to"],e["dst_bits"],allerr))
                need(len(nxt)<=128,"SEMANTIC_ROLE_FRONTIER_BOUND")
        state=nxt
    if rule=="consistency":
        return sum(node==g["target"] and len(err)==2 and err[0]==err[1]
                   for node,_,err in state)
    return sum(node==g["target"] for node,_,_ in state)
def admit(pos,neg):
    validate_public(pos);validate_public(neg)
    need(all(pos[k]==neg[k] for k in ("start","target","roles")),
         "PAIRED_QUERY_DRIFT")
    def histogram(g):
        return (Counter((e["from"],e["to"],e["role"]) for e in g["edges"]),
                Counter(tuple(e[k]) for e in g["edges"]
                        for k in ("src_bits","dst_bits")))
    need(histogram(pos)==histogram(neg),"PAIRED_TOKEN_HISTOGRAM_LEAK")
    need(semantic_routes(pos)==1 and semantic_routes(neg)==0,
         "NOT_TRUE_SEMANTIC_PAIR")
    need(semantic_routes(pos,"exact")==semantic_routes(neg,"exact")==0,
         "EXACT_TRIVIAL")
    need(semantic_routes(pos,"tolerant")==semantic_routes(neg,"tolerant")==1,
         "TOLERANT_NOT_AMBIGUOUS")
    need(semantic_routes(pos,"role_only")==semantic_routes(neg,"role_only")
         and semantic_routes(pos,"role_only")>=1,"ROLE_ONLY_DRIFT")
    return True
def build(family,seed,vector,phase):
    frozen()
    need(family in FAMILIES and phase in ("FIT","DEV") and
         seed in COHORTS[family][phase] and tuple(vector) in VECTORS,
         "SOURCE_BIRTH_NOT_AUTHORIZED")
    salt=SALTS[family]+"/"+phase+"/"+str(seed)+"/"+",".join(map(str,vector))
    rng=random.Random(int.from_bytes(hashlib.sha256(salt.encode()).digest()[:16],"big"))
    def name(k,i,j=0):
        return hashlib.sha256((salt+"/"+k+"/"+str(i)+"/"+str(j)).encode()).hexdigest()[:22]
    taken=set()
    def bits():
        for _ in range(500):
            v=rng.randrange(1,65536)
            if v not in taken:
                taken.add(v);return [(v>>i)&1 for i in range(16)]
        raise Quarantined("TOKEN_ALLOCATOR_EXHAUSTED")
    def flip(bit,k,other=None):
        out=list(bit);out[k%16]^=1
        if other is not None:out[other%16]^=1
        return out
    def e(frm,to,role,src,dst):
        return {"from":frm,"to":to,"role":role,
                "src_bits":list(src),"dst_bits":list(dst)}
    depth=10+seed%3
    roles=[name("public-role",i if family!="role_weave" else i%4)
           for i in range(depth)]
    main=[name("main",i) for i in range(depth+1)]
    side={(i,j):name("side",i,j)
          for i in range(1,depth+1) for j in range(2)}
    carried=[bits() for _ in range(depth+1)]
    sidecarried={(i,j):bits()
                 for i in range(1,depth+1) for j in range(2)}
    hops=HOPS[family]
    same_bit=rng.randrange(16)
    different_bit=(same_bit+1+rng.randrange(15))%16
    edges=[]
    for hop in range(depth):
        src=flip(carried[hop],same_bit) if hop in hops else carried[hop]
        edges.append(e(main[hop],main[hop+1],roles[hop],
                       src,carried[hop+1]))
        for j in range(2):
            branchsrc=flip(carried[hop],(same_bit+hop+j+3)%16)
            edges.append(e(main[hop],side[hop+1,j],roles[hop],
                           branchsrc,sidecarried[hop+1,j]))
            if hop:
                target_j=(j+int(hop%3==0))%2
                edges.append(e(side[hop,j],side[hop+1,target_j],
                         roles[hop],sidecarried[hop,j],
                         sidecarried[hop+1,target_j]))
    # Misleading role-valid terminal decoy, token-incompatible by TWO bits.
    edges.append(e(side[depth-1,1],main[-1],roles[-1],
        flip(sidecarried[depth-1,1],3,7),bits()))
    donorrole=name("nonquery-role",0)
    edges.append(e(main[0],name("nonquery-donor",0),donorrole,
                   flip(carried[hops[1]],different_bit),bits()))
    pos={"start":main[0],"target":main[-1],
         "roles":roles,"edges":json.loads(json.dumps(edges))}
    neg=json.loads(json.dumps(pos))
    target=[x for x in neg["edges"] if x["from"]==main[hops[1]]
            and x["to"]==main[hops[1]+1] and x["role"]==roles[hops[1]]]
    donor=[x for x in neg["edges"] if x["role"]==donorrole]
    need(len(target)==1 and len(donor)==1,"PAIR_SWAP_NOT_UNIQUE")
    target[0]["src_bits"],donor[0]["src_bits"]=(
      donor[0]["src_bits"],target[0]["src_bits"])
    rng.shuffle(pos["edges"]);rng.shuffle(neg["edges"])
    admit(pos,neg)
    return pos,neg
def protected(*args,**kwargs):
    raise Quarantined("ORIGINAL_PROTECTED_FIRST_USE_UNAVAILABLE")

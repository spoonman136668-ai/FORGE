"""F124-AJ new layered public-automata birth; entirely independent generator.

Only FIT labelled source may be read by training code. Semantic path checks
are SOURCE/EVALUATOR ONLY, NEVER callable from raw-neural inference.
"""
from __future__ import annotations
import hashlib,json,random
from pathlib import Path
from collections import Counter
ROOT=Path(__file__).resolve().parents[1]
PROTOCOL=ROOT/"reference/research-intake/f124aj-raw-operator-freeze.json"
PROTOCOL_BLOB="42d0a025bc2aba88032f28eecd58ef45bce8dfc5"
FAMILIES=("near_event","far_event","role_collision")
SALTS={"near_event":"forge/F124AJ/learn-operator/near-event/v1",
       "far_event":"forge/F124AJ/learn-operator/far-event/v1",
       "role_collision":"forge/F124AJ/learn-operator/role-collision/v1"}
HOPS={"near_event":(2,4),"far_event":(1,9),"role_collision":(3,8)}
COHORTS={fam:{"FIT":range(3190000,3190024),
              "DEV":range(3190100,3190124)} for fam in FAMILIES}
VECTORS=((2,1,1),(1,2,1))
EDGE_FIELDS={"from","to","role","src_bits","dst_bits"}
class Quarantined(ValueError):pass
def need(ok,message):
    if not ok:raise Quarantined("F124AJ_"+message)
def git_blob(b):
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
def frozen():
    raw=PROTOCOL.read_bytes().replace(b"\r\n",b"\n")
    need(git_blob(raw)==PROTOCOL_BLOB,"ORIGINAL_FREEZE_BLOB")
    p=json.loads(raw)
    need(p["schema"]=="forge.research.f124aj.raw-neural-operator.v1"
       and p["stage"]=="PREIMPLEMENTATION_FROZEN"
       and p["qualified_parent"]["head"]=="b39785756f7f587867930c34023986296455b077"
       and p["qualified_parent"]["run"]==39113708960
       and p["source"]["FIT_seeds"]==[3190000,3190023]
       and p["source"]["DEV_seeds"]==[3190100,3190123]
       and all(row["salt"]==SALTS[row["name"]]
               and row["noise_hops"]==list(HOPS[row["name"]])
               for row in p["source"]["families"])
       and p["architecture"]["model_params"]["total"]==50
       and all(v is False for v in p["governance"].values()),
       "PREREGISTRATION_CHANGED")
    return hashlib.sha256(raw).hexdigest()
def validate_public(g):
    need(type(g) is dict and set(g)=={"start","target","roles","edges"},
         "PUBLIC_GRAPH_FIELDS")
    need(type(g["start"]) is str and type(g["target"]) is str
         and g["start"]!=g["target"] and type(g["roles"]) is list
         and len(g["roles"]) in (10,11,12)
         and 20<=len(g["edges"])<=128,"PUBLIC_GRAPH_SHAPE")
    nodes={g["start"],g["target"]}
    for e in g["edges"]:
        need(type(e) is dict and set(e)==EDGE_FIELDS,"EDGE_FIELDS")
        for k in ("from","to","role"):
            need(type(e[k]) is str and bool(e[k]),"NODE_ROLE_SHAPE")
        nodes.update((e["from"],e["to"]))
        for k in ("src_bits","dst_bits"):
            need(type(e[k]) is list and len(e[k])==16 and
                 all(type(v) is int and v in (0,1) for v in e[k]),
                 "RAW_BIT16")
    need(len(nodes)<=64,"NODE_BOUND_64")
    return g
def bit_errors(a,b):
    if a is None:return ()
    return tuple(i for i in range(16) if a[i]!=b[i])
diff_bits=bit_errors  # compatibility with original unchanged fixed benchmark bytecode
def semantic_routes(g,mode="consistency"):
    """Source-only full semantic verifier, not exposed to learned model."""
    validate_public(g)
    need(mode in ("consistency","role_only","tolerant","exact"),"MODE")
    state=[(g["start"],None,())]
    for role in g["roles"]:
        newer=[]
        for node,carried,errors in state:
            for e in g["edges"]:
                if e["from"]!=node or e["role"]!=role:continue
                diff=bit_errors(carried,e["src_bits"])
                if mode=="exact" and diff:continue
                if mode in ("tolerant","consistency") and len(diff)>1:continue
                next_error=errors+diff
                if mode=="consistency" and (len(next_error)>2 or
                     (len(next_error)==2 and next_error[0]!=next_error[1])):
                    continue
                newer.append((e["to"],e["dst_bits"],next_error))
                need(len(newer)<=128,"SEMANTIC_FRONTIER_LIMIT")
        state=newer
    if mode=="consistency":
        return sum(n==g["target"] and len(err)==2 and err[0]==err[1]
                   for n,_,err in state)
    return sum(n==g["target"] for n,_,_ in state)
def paired_admit(p,n):
    validate_public(p);validate_public(n)
    need(all(p[k]==n[k] for k in ("start","target","roles")),
         "ROLE_TARGET_DRIFT")
    def inv(g):
        return (Counter((e["from"],e["to"],e["role"]) for e in g["edges"]),
                Counter(tuple(e[k]) for e in g["edges"]
                        for k in ("src_bits","dst_bits")))
    need(inv(p)==inv(n),"PAIR_PUBLIC_TOKEN_TOPOLOGY_LEAK")
    need(semantic_routes(p)==1 and semantic_routes(n)==0,
         "SEMANTIC_LABELS_WRONG")
    need(semantic_routes(p,"exact")==semantic_routes(n,"exact")==0,
         "EASY_EXACT_SOURCE")
    need(semantic_routes(p,"tolerant")==semantic_routes(n,"tolerant") and
         semantic_routes(p,"tolerant")>=1,"EASY_TOLERANT_SOURCE")
    need(semantic_routes(p,"role_only")==semantic_routes(n,"role_only"),
         "ROLE_REACHABILITY_LEAK")
    return True
def build(family,seed,vector,phase):
    frozen()
    need(family in FAMILIES and phase in ("FIT","DEV")
         and seed in COHORTS[family][phase]
         and tuple(vector) in VECTORS,"AUTHENTIC_SOURCE_COHORT")
    salt=SALTS[family]+"/"+phase+"/"+str(seed)+"/"+",".join(map(str,vector))
    rng=random.Random(int.from_bytes(hashlib.sha256(salt.encode()).digest()[:12],"big"))
    def name(kind,i,j=0):
        return hashlib.sha256((salt+"/"+kind+"/"+str(i)+"/"+str(j)).encode()).hexdigest()[:22]
    used=set()
    def bits():
        for _ in range(500):
            v=rng.randrange(1,65536)
            if v not in used:
                used.add(v)
                return [(v>>j)&1 for j in range(16)]
        raise Quarantined("TOKEN_POOL_EXHAUSTED")
    def flip(x,k,later=None):
        y=list(x);y[k%16]^=1
        if later is not None:y[later%16]^=1
        return y
    def edge(u,v,r,src,dst):
        return {"from":u,"to":v,"role":r,
                "src_bits":list(src),"dst_bits":list(dst)}
    depth=10+seed%3
    roles=[name("role",i if family!="role_collision" else i%4)
           for i in range(depth)]
    nodes=[name("main",i) for i in range(depth+1)]
    side={(i,j):name("branch",i,j) for i in range(1,depth+1) for j in range(2)}
    carry=[bits() for _ in range(depth+1)]
    sidebits={(i,j):bits() for i in range(1,depth+1) for j in range(2)}
    h0,h1=HOPS[family]
    first_bit=rng.randrange(16)
    other_bit=(first_bit+1+rng.randrange(15))%16
    edges=[]
    for hop in range(depth):
        main_src=flip(carry[hop],first_bit) if hop in (h0,h1) else carry[hop]
        edges.append(edge(nodes[hop],nodes[hop+1],roles[hop],
                          main_src,carry[hop+1]))
        for j in range(2):
            decoy=flip(carry[hop],(first_bit+hop+j+3)%16)
            edges.append(edge(nodes[hop],side[hop+1,j],
                     roles[hop],decoy,sidebits[hop+1,j]))
            if hop:
                edges.append(edge(side[hop,j],side[hop+1,j],
                        roles[hop],sidebits[hop,j],sidebits[hop+1,j]))
    edges.append(edge(side[depth-1,1],nodes[-1],roles[-1],
                      flip(sidebits[depth-1,1],3,7),bits()))
    off_role=name("offrole",0)
    edges.append(edge(nodes[0],name("donor",0),off_role,
                      flip(carry[h1],other_bit),bits()))
    positive={"start":nodes[0],"target":nodes[-1],
              "roles":roles,"edges":json.loads(json.dumps(edges))}
    negative=json.loads(json.dumps(positive))
    actual=[e for e in negative["edges"] if
             e["from"]==nodes[h1] and e["to"]==nodes[h1+1]
             and e["role"]==roles[h1]]
    donor=[e for e in negative["edges"] if e["role"]==off_role]
    need(len(actual)==len(donor)==1,"NEGATIVE_SWAP_UNIQUE")
    actual[0]["src_bits"],donor[0]["src_bits"]=(
        donor[0]["src_bits"],actual[0]["src_bits"])
    rng.shuffle(positive["edges"]);rng.shuffle(negative["edges"])
    paired_admit(positive,negative)
    return positive,negative
def protected(*args,**kwargs):
    raise Quarantined("PROTECTED_HK_FIRST_USE_UNAVAILABLE")

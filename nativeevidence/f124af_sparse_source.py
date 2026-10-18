"""F124-AF independent sparse-layer automata source, NOT historical F124AD stress.

No import of historical source constructors. Every graph is public
(start, target, roles, edges with 16-bit raw public tokens), two
paired labels share exact topology and 16-bit token histograms.
Protected science source is intentionally inaccessible.
"""
from __future__ import annotations
import hashlib,json,random
from pathlib import Path
from collections import Counter

ROOT=Path(__file__).resolve().parents[1]
PROTOCOL=ROOT/"reference/research-intake/f124af-structural-controls-freeze.json"
PROTOCOL_BLOB="c5656fcf328185ec6965cbe7bb2f42c0ea31523d"
FAMILIES=("sparse_diamond","role_reuse","terminal_decoy")
SALTS={"sparse_diamond":"forge/F124AF/structural/sparse-diamond/v1",
       "role_reuse":"forge/F124AF/structural/role-reuse/v1",
       "terminal_decoy":"forge/F124AF/structural/terminal-decoy/v1"}
VECTORS=((2,1,1),(1,2,1))
COHORTS={family:{"FIT":range(2790000,2790024),
                 "DEV":range(2790100,2790124)} for family in FAMILIES}

class Quarantined(ValueError):pass
def need(ok,label):
    if not ok:raise Quarantined("F124AF_"+label)
def git_blob(raw):
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()
def frozen():
    raw=PROTOCOL.read_bytes().replace(b"\r\n",b"\n")
    need(git_blob(raw)==PROTOCOL_BLOB,"PREIMPLEMENTATION_GIT_BLOB_DRIFT")
    p=json.loads(raw)
    need(p["schema"]=="forge.research.f124af.structurally-independent-bounded-controls.v1"
      and p["stage"]=="PREIMPLEMENTATION_FROZEN"
      and p["qualified_parent"]["head"]=="8eede780f027882c2c4e12b0452f78c99ebe0e64"
      and p["qualified_parent"]["actions"]==39109580026
      and [x["key"] for x in p["source"]["families"]]==list(FAMILIES)
      and all(row["salt"]==SALTS[row["key"]] for row in p["source"]["families"])
      and p["models"]["frozen_gamma"]==0.1
      and p["models"]["frozen_penalty"]==1.0
      and all(x is False for x in p["governance"].values()),
      "FROZEN_PROTOCOL_MISMATCH")
    return hashlib.sha256(raw).hexdigest()

GRAPH_KEYS={"start","target","roles","edges"}
EDGE_KEYS={"from","to","role","src_bits","dst_bits"}

def validate_public(g):
    need(type(g) is dict and set(g)==GRAPH_KEYS,"GRAPH_FIELDS")
    need(type(g["start"]) is str and type(g["target"]) is str
      and g["start"]!=g["target"] and type(g["roles"]) is list
      and len(g["roles"]) in (10,11,12)
      and 15<=len(g["edges"])<=128,"GRAPH_BOUNDS")
    nodes={g["start"],g["target"]}
    for e in g["edges"]:
        need(type(e) is dict and set(e)==EDGE_KEYS
         and all(type(e[k]) is str and e[k] for k in ("from","to","role")),
         "EDGE_SHAPE")
        nodes.add(e["from"]);nodes.add(e["to"])
        for key in ("src_bits","dst_bits"):
            need(type(e[key]) is list and len(e[key])==16
              and all(type(x) is int and x in (0,1) for x in e[key]),
              "RAW16_ONLY")
    need(len(nodes)<=64,"MAX64_NODES")
    return g

def routes(g,role_only=False):
    """Evaluator-side public oracle. NEVER imported into original prediction."""
    validate_public(g)
    frontier=[(g["start"],None)]
    for role in g["roles"]:
        new=[]
        for node,carried in frontier:
            for edge in g["edges"]:
                if edge["from"]==node and edge["role"]==role and (
                     role_only or carried is None or carried==edge["src_bits"]):
                    new.append((edge["to"],edge["dst_bits"]))
                    need(len(new)<=128,"ROLE_FRONTIER_ORIGINAL_FIXED_CAP")
        frontier=new
    return sum(node==g["target"] for node,_ in frontier)

def paired_admit(p,n):
    validate_public(p);validate_public(n)
    need(all(p[k]==n[k] for k in ("start","target","roles")),
         "PAIRED_QUERY_DRIFT")
    def inventory(g):
        return (Counter((e["from"],e["to"],e["role"]) for e in g["edges"]),
                Counter(tuple(e[b]) for e in g["edges"]
                        for b in ("src_bits","dst_bits")))
    need(inventory(p)==inventory(n),"PAIRED_TOKEN_HISTOGRAM_LEAK")
    need(routes(p)==1 and routes(n)==0,"TRUE_ROUTE_ADMISSION_FAILED")
    need(routes(p,True)==routes(n,True)
         and routes(p,True)>=1,"ROLE_ONLY_GRAPH_DRIFT")
    return True

def build(family,seed,vector,phase):
    frozen()
    need(family in FAMILIES and phase in ("FIT","DEV")
         and seed in COHORTS[family][phase]
         and tuple(vector) in VECTORS,"FAMILY_PHASE_SEED")
    salt=SALTS[family]+"/"+phase+"/"+str(seed)+"/"+",".join(map(str,vector))
    rng=random.Random(int.from_bytes(hashlib.sha256(salt.encode()).digest()[:12],"big"))
    def opaque(key):
        return hashlib.sha256((salt+"/"+key).encode()).hexdigest()[:22]
    used={0}
    def fresh_bits():
        for _ in range(1024):
            x=rng.randrange(1,65536)
            if x not in used:
                used.add(x)
                return [(x>>i)&1 for i in range(16)]
        raise Quarantined("TOKEN_SPACE_EXHAUSTED")
    def edge(frm,to,role,src,dst):
        return {"from":frm,"to":to,"role":role,
                "src_bits":list(src),"dst_bits":list(dst)}
    def flipped(x,i):
        out=list(x);out[i%16]^=1;return out
    depth=10+seed%3
    main=[opaque("main-"+str(i)) for i in range(depth+1)]
    decoy={(h,j):opaque("decoy-"+str(h)+"-"+str(j))
           for h in range(1,depth+1) for j in range(2)}
    roles=[opaque("role-"+str(i if family!="role_reuse" else i%4))
           for i in range(depth)]
    carried=[fresh_bits() for _ in range(depth+1)]
    decoy_carry={(h,j):fresh_bits() for h in range(1,depth+1) for j in range(2)}
    edges=[]
    for i in range(depth):
        edges.append(edge(main[i],main[i+1],roles[i],
                          carried[i],carried[i+1]))
        for j in range(2):
            # Branch starts from the true node, and is a 15/16 near match
            # to the correct public carried token. Some first-hop branches
            # remain exact-reachable but deliberately never reach target.
            edges.append(edge(main[i],decoy[i+1,j],roles[i],
                 flipped(carried[i],i+j+int(vector[0])),
                 decoy_carry[i+1,j]))
            if i:
                edges.append(edge(decoy[i,j],decoy[i+1,j],roles[i],
                     decoy_carry[i,j],decoy_carry[i+1,j]))
    if family=="terminal_decoy":
        # Near-terminal role-only alternative to the SAME public target,
        # using a deliberate 15/16 key mismatch to preserve a unique exact route.
        edges.append(edge(decoy[depth-1,1],main[depth],roles[-1],
            flipped(decoy_carry[depth-1,1],seed%16),
            decoy_carry[depth,1]))
    broken=(depth//2 if family=="sparse_diamond"
           else depth-2 if family=="role_reuse" else depth-1)
    main_entry=edges[broken*5] if broken else edges[0]
    # Exact main edge selection independent of list position and branch count.
    main_candidates=[e for e in edges
                     if e["from"]==main[broken] and e["to"]==main[broken+1]
                     and e["role"]==roles[broken]]
    need(len(main_candidates)==1,"UNIQUE_MAIN_LINK")
    edge_to_break=main_candidates[0]
    donor=edge(main[0],opaque("offrole-end"),opaque("offrole"),
               flipped(edge_to_break["src_bits"],seed%16),fresh_bits())
    edges.append(donor)
    p={"start":main[0],"target":main[-1],"roles":roles,
       "edges":json.loads(json.dumps(edges))}
    n={"start":main[0],"target":main[-1],"roles":list(roles),
       "edges":json.loads(json.dumps(edges))}
    target_edge=[e for e in n["edges"]
        if e["from"]==main[broken] and e["to"]==main[broken+1]
        and e["role"]==roles[broken]]
    offrole=[e for e in n["edges"] if e["role"]==donor["role"]]
    need(len(target_edge)==1 and len(offrole)==1,"NEGATIVE_SWAP_UNIQUE")
    target_edge[0]["src_bits"],offrole[0]["src_bits"]=(
        offrole[0]["src_bits"],target_edge[0]["src_bits"])
    rng.shuffle(p["edges"]);rng.shuffle(n["edges"])
    paired_admit(p,n)
    return p,n

def protected(*args,**kwargs):
    raise Quarantined("PROTECTED_FIRST_USE_UNAVAILABLE")

"""F124-AH new noisy causal-signature source, not derived from prior AF graphs.

Truth is a two-hop bit-flip consistency condition: exactly TWO transitions
whose public carried key differs from the next src token in ONE bit, and the
bit position must be the SAME at both transitions. Both positive and
negative have identical 1-bit-error counts and matched token inventories.
No target label or semantic reference may enter an inference function.
"""
from __future__ import annotations
import hashlib,json,random
from pathlib import Path
from collections import Counter

ROOT=Path(__file__).resolve().parents[1]
PROTOCOL=ROOT/"reference/research-intake/f124ah-learned-fingerprint-freeze.json"
PROTOCOL_BLOB="5e63d2b8f79e790e0fdd11690845f973a8edef92"
FAMILIES=("adjacent_noise","delayed_noise","reused_role_noise")
SALTS={"adjacent_noise":"forge/F124AH/new-fingerprint/adjacent/v1",
       "delayed_noise":"forge/F124AH/new-fingerprint/delayed/v1",
       "reused_role_noise":"forge/F124AH/new-fingerprint/roles/v1"}
PAIRS={"adjacent_noise":(4,5),"delayed_noise":(3,8),
       "reused_role_noise":(2,8)}
VECTORS=((2,1,1),(1,2,1))
COHORTS={family:{"FIT":range(2990000,2990024),
                 "DEV":range(2990100,2990124)} for family in FAMILIES}
GRAPH_KEYS={"start","target","roles","edges"}
EDGE_KEYS={"from","to","role","src_bits","dst_bits"}
class Quarantined(ValueError):pass
def need(ok,label):
    if not ok:raise Quarantined("F124AH_"+label)
def git_blob(b):
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
def frozen():
    raw=PROTOCOL.read_bytes().replace(b"\r\n",b"\n")
    need(git_blob(raw)==PROTOCOL_BLOB,"PREIMPLEMENTATION_GIT_BLOB_DRIFT")
    p=json.loads(raw)
    need(p["schema"]=="forge.research.f124ah.learned-pairwise-fingerprint.v1"
       and p["stage"]=="PREIMPLEMENTATION_FROZEN"
       and p["qualified_parent"]["head"]=="dad429047450b2b0dffbf61722d9fb9cef106e07"
       and p["qualified_parent"]["actions"]==39111665880
       and all(row["salt"]==SALTS[row["name"]]
         and row["hops"]==list(PAIRS[row["name"]])
         for row in p["source"]["families"])
       and p["source"]["FIT_seeds"]==[2990000,2990023]
       and p["source"]["DEV_seeds"]==[2990100,2990123]
       and p["models"]["sgd"]["epochs"]==100
       and p["models"]["train_and_eval_budget"]["max_total"]==16
       and all(x is False for x in p["governance"].values()),
       "PREIMPLEMENTATION_NOT_FROZEN")
    return hashlib.sha256(raw).hexdigest()

def validate_public(g):
    need(type(g) is dict and set(g)==GRAPH_KEYS,"PUBLIC_GRAPH_SCHEMA")
    need(type(g["start"]) is str and type(g["target"]) is str
         and g["start"]!=g["target"] and len(g["roles"]) in (10,11,12)
         and all(type(r) is str and r for r in g["roles"])
         and 20<=len(g["edges"])<=128,"PUBLIC_GRAPH_BOUNDS")
    nodes={g["start"],g["target"]}
    for e in g["edges"]:
        need(type(e) is dict and set(e)==EDGE_KEYS,"EDGE_FIELDS")
        for k in ("from","to","role"):
            need(type(e[k]) is str and bool(e[k]),"EDGE_PUBLIC_LABEL")
        nodes.add(e["from"]);nodes.add(e["to"])
        for k in ("src_bits","dst_bits"):
            need(type(e[k]) is list and len(e[k])==16
                and all(type(b) is int and b in (0,1) for b in e[k]),
                "EDGE_RAW16")
    need(len(nodes)<=64,"MAX_NODES")
    return g

def diff_bits(left,right):
    if left is None:return ()
    return tuple(i for i,(a,b) in enumerate(zip(left,right)) if a!=b)

def routes(g,rule="consistency"):
    """Evaluator-only bounded symbolic reference, never used in scoring."""
    validate_public(g)
    need(rule in ("consistency","tolerant15","exact16","role_only"),"RULE")
    frontier=[(g["start"],None,())]
    for role in g["roles"]:
        nxt=[]
        for node,carried,errors in frontier:
            for edge in g["edges"]:
                if edge["from"]!=node or edge["role"]!=role:continue
                diffs=diff_bits(carried,edge["src_bits"])
                if rule=="exact16" and diffs:continue
                if rule in ("tolerant15","consistency") and len(diffs)>1:continue
                next_errors=errors+diffs
                if rule=="consistency":
                    if len(next_errors)>2 or (
                        len(next_errors)==2 and
                        next_errors[0]!=next_errors[1]):continue
                nxt.append((edge["to"],edge["dst_bits"],next_errors))
                need(len(nxt)<=128,"128_ORIGINAL_SOURCE_BUDGET")
        frontier=nxt
    if rule=="consistency":
        return sum(node==g["target"] and len(errors)==2 and
                   errors[0]==errors[1] for node,_,errors in frontier)
    return sum(node==g["target"] for node,_,_ in frontier)

def paired_admit(p,n):
    validate_public(p);validate_public(n)
    need(all(p[k]==n[k] for k in ("start","target","roles")),
         "PAIR_QUERY_DRIFT")
    def inv(g):
        return (Counter((e["from"],e["to"],e["role"]) for e in g["edges"]),
                Counter(tuple(e[k]) for e in g["edges"]
                        for k in ("src_bits","dst_bits")))
    need(inv(p)==inv(n),"TOKEN_HISTOGRAM_OR_TOPOLOGY_LABEL_LEAK")
    need(routes(p,"consistency")==1 and routes(n,"consistency")==0,
         "COMPOSITIONAL_TRUTH_NOT_PAIRED")
    need(routes(p,"exact16")==0 and routes(n,"exact16")==0,
         "EXACT_FIXED_CONTROL_NOT_CHALLENGED")
    need(routes(p,"tolerant15")==1 and routes(n,"tolerant15")==1,
         "NAIVE_TOLERANT_CONTROL_NOT_AMBIGUOUS")
    need(routes(p,"role_only")==routes(n,"role_only") and
         routes(p,"role_only")>=1,"ROLE_ONLY_ROUTE_LEAK")
    return True

def build(family,seed,vector,phase):
    frozen()
    need(family in FAMILIES and phase in ("FIT","DEV")
         and seed in COHORTS[family][phase] and tuple(vector) in VECTORS,
         "SOURCE_SEED_AUTHORIZATION")
    salt=SALTS[family]+"/"+phase+"/"+str(seed)+"/"+",".join(map(str,vector))
    rng=random.Random(int.from_bytes(hashlib.sha256(salt.encode()).digest()[:12],"big"))
    def opaque(k):
        return hashlib.sha256((salt+"/"+k).encode()).hexdigest()[:22]
    taken=set()
    def raw16():
        for _ in range(300):
            v=rng.randrange(1,65536)
            if v not in taken:
                taken.add(v)
                return [(v>>i)&1 for i in range(16)]
        raise Quarantined("TOKEN_ALLOCATOR_EXHAUSTED")
    def flip(bits,j):
        out=list(bits);out[j%16]^=1;return out
    def edge(frm,to,role,src,dst):
        return {"from":frm,"to":to,"role":role,
                "src_bits":list(src),"dst_bits":list(dst)}
    depth=10+seed%3
    roles=[opaque("role-"+str(i if family!="reused_role_noise" else i%5))
           for i in range(depth)]
    main=[opaque("true-node-"+str(i)) for i in range(depth+1)]
    decoy={(hop,arm):opaque("decoy-"+str(hop)+"-"+str(arm))
           for hop in range(1,depth+1) for arm in range(2)}
    carried=[raw16() for _ in range(depth+1)]
    decoy_key={(hop,j):raw16() for hop in range(1,depth+1) for j in range(2)}
    first_noise,second_noise=PAIRS[family]
    signature=rng.randrange(0,16)
    altered=(signature+1+rng.randrange(15))%16
    edges=[]
    for hop in range(depth):
        src=(flip(carried[hop],signature)
             if hop in (first_noise,second_noise) else carried[hop])
        edges.append(edge(main[hop],main[hop+1],roles[hop],src,carried[hop+1]))
        for j in range(2):
            # Decoy branches are public near matches, never reach target.
            bits=flip(carried[hop],(signature+3+hop+j)%16)
            edges.append(edge(main[hop],decoy[hop+1,j],roles[hop],
                              bits,decoy_key[hop+1,j]))
            if hop:
                edges.append(edge(decoy[hop,j],decoy[hop+1,j],roles[hop],
                    decoy_key[hop,j],decoy_key[hop+1,j]))
    # Add one nonquery donor; its source key is exactly 1-bit away
    # at a DIFFERENT bit position for the second noisy role.
    donor=edge(main[0],opaque("offrole-node"),opaque("offrole-label"),
               flip(carried[second_noise],altered),raw16())
    edges.append(donor)
    p={"start":main[0],"target":main[-1],"roles":list(roles),
       "edges":json.loads(json.dumps(edges))}
    n={"start":main[0],"target":main[-1],"roles":list(roles),
       "edges":json.loads(json.dumps(edges))}
    candidates=[e for e in n["edges"]
                if e["from"]==main[second_noise] and
                   e["to"]==main[second_noise+1] and
                   e["role"]==roles[second_noise]]
    donors=[e for e in n["edges"] if e["role"]==donor["role"]]
    need(len(candidates)==1 and len(donors)==1,
         "NOISY_NEGATIVE_SWAP_IDENTITY")
    candidates[0]["src_bits"],donors[0]["src_bits"]=(
        donors[0]["src_bits"],candidates[0]["src_bits"])
    rng.shuffle(p["edges"]);rng.shuffle(n["edges"])
    paired_admit(p,n)
    return p,n

def protected(*args,**kwargs):
    raise Quarantined("PROTECTED_ORIGINAL_FIRST_USE_UNAVAILABLE")

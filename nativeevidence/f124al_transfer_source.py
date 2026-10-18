"""F124-AL: new independent operator-transfer public braided graph source.

Source/evaluator-only semantic verifier. No imports/calls of F124AK or prior
graph generators; no hidden oracle, labels or family in predictors.
"""
from __future__ import annotations
from collections import Counter
import hashlib,json,random
from pathlib import Path
PROTOCOL=Path(__file__).resolve().parents[1]/"reference/research-intake/f124al-operator-transfer-freeze.json"
PROTOCOL_BLOB="b88c8fbc01bc9cd1cceb6d9523e75cbc47dc2a9a"
FAMILIES=("double_bit","silent_slot","three_events")
SALTS={"double_bit":"forge/F124AL/multibit/v1",
       "silent_slot":"forge/F124AL/silent-evidence/v1",
       "three_events":"forge/F124AL/three-hops/v1"}
HOPS={"double_bit":(2,7),"silent_slot":(2,8),"three_events":(2,5,9)}
WIDTH={"double_bit":2,"silent_slot":1,"three_events":1}
COHORTS={f:{"FIT":range(3390000,3390024),
            "DEV":range(3390100,3390124)} for f in FAMILIES}
VECTORS=((2,1,1),(1,2,1))
EDGE_FIELDS={"from","to","role","src_bits","dst_bits"}
class Quarantined(ValueError):pass
def need(check,code):
    if not check:raise Quarantined("F124AL_"+code)
def gitblob(raw):
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()
def frozen():
    raw=PROTOCOL.read_bytes().replace(b"\r\n",b"\n")
    need(gitblob(raw)==PROTOCOL_BLOB,"ORIGINAL_PROTOCOL_BLOB")
    p=json.loads(raw)
    need(p["schema"]=="forge.research.f124al.operator-transfer.v1"
      and p["stage"]=="PREIMPLEMENTATION_FROZEN"
      and p["parent"]["qualified_head"]=="6b1e0dc9a9a8e971bdcc042ca54db4d88d8dfe0d"
      and p["parent"]["actions"]==39116272361
      and p["locked_model"]["fit_threshold"]==.1
      and p["locked_model"]["max_cells"]==16
      and all(row["salt"]==SALTS[row["name"]]
              and row["hops"]==list(HOPS[row["name"]])
              and row["width"]==WIDTH[row["name"]]
              for row in p["source"]["families"])
      and all(value is False for value in p["governance"].values()),
      "FROZEN_CONTRACT_DRIFT")
    return hashlib.sha256(raw).hexdigest()
def validate_public(g):
    need(type(g) is dict and set(g)=={"start","target","roles","edges"},
         "PUBLIC_GRAPH_SCHEMA")
    need(type(g["start"]) is str and type(g["target"]) is str and
         g["start"]!=g["target"] and type(g["roles"]) is list and
         len(g["roles"]) in (10,11,12) and
         20<=len(g["edges"])<=128,"GRAPH_BOUNDS")
    nodes={g["start"],g["target"]}
    for e in g["edges"]:
        need(type(e) is dict and set(e)==EDGE_FIELDS,"EDGE_FIELDS")
        for field in ("from","to","role"):
            need(type(e[field]) is str and e[field],"NAME")
        nodes.update((e["from"],e["to"]))
        for field in ("src_bits","dst_bits"):
            need(type(e[field]) is list and len(e[field])==16 and
                 all(type(k) is int and k in (0,1) for k in e[field]),
                 "PUBLIC_BITS")
    need(len(nodes)<=64,"MAX_NODES")
    return g
def diff_bits(a,b):
    if a is None:return ()
    return tuple(i for i,(x,y) in enumerate(zip(a,b)) if x!=y)
def mask_of(a,b):
    return sum(1<<i for i in diff_bits(a,b))
def semantic_routes(g,mode="generalized"):
    """Source-only semantic truth. NEVER callable from model inference."""
    validate_public(g)
    need(mode in ("generalized","role_only","exact","tolerant"),"SEMANTIC_MODE")
    state=[(g["start"],None,())]
    for role in g["roles"]:
        subsequent=[]
        for node,carried,events in state:
            for e in g["edges"]:
                if node!=e["from"] or role!=e["role"]:continue
                mask=mask_of(carried,e["src_bits"])
                if mode=="exact" and mask:continue
                if mode in ("tolerant","generalized") and mask.bit_count()>2:continue
                all_events=events+((mask,) if mask else ())
                if mode=="generalized" and (len(all_events)>3 or
                      (len(all_events)>=2 and
                       any(v!=all_events[0] for v in all_events[1:]))):
                    continue
                subsequent.append((e["to"],e["dst_bits"],all_events))
                need(len(subsequent)<=128,"SOURCE_ORACLE_FRONTIER")
        state=subsequent
    if mode=="generalized":
        return sum(node==g["target"] and len(ev)>=2 and
                   len(set(ev))==1 for node,_,ev in state)
    return sum(node==g["target"] for node,_,_ in state)
def admit(pos,neg):
    validate_public(pos);validate_public(neg)
    need(all(pos[k]==neg[k] for k in ("start","target","roles")),
         "QUERY_DRIFT")
    def witness(g):
        return (Counter((e["from"],e["to"],e["role"]) for e in g["edges"]),
                Counter(tuple(e[k]) for e in g["edges"]
                        for k in ("src_bits","dst_bits")))
    need(witness(pos)==witness(neg),"COMPLETE_PUBLIC_TOKEN_HISTOGRAM_LEAK")
    need(semantic_routes(pos)==1 and semantic_routes(neg)==0,
         "WRONG_GENERALIZED_CAUSAL_TRUTH")
    need(semantic_routes(pos,"exact")==semantic_routes(neg,"exact")==0,
         "EXACT_CONTINUATION_TOO_EASY")
    need(semantic_routes(pos,"tolerant")==semantic_routes(neg,"tolerant") and
         semantic_routes(pos,"tolerant")>=1,"TOLERANT_TRIVIAL_LEAK")
    need(semantic_routes(pos,"role_only")==semantic_routes(neg,"role_only"),
         "TOPOLOGY_LABEL_LEAK")
    return True
def build(family,seed,vector,phase):
    frozen()
    need(family in FAMILIES and phase in ("FIT","DEV") and
         seed in COHORTS[family][phase] and tuple(vector) in VECTORS,
         "SOURCE_COHORT_IDENTITY")
    salt=SALTS[family]+"/"+phase+"/"+str(seed)+"/"+",".join(map(str,vector))
    rng=random.Random(int.from_bytes(hashlib.sha256(salt.encode()).digest()[:16],"big"))
    def ident(tag,i,j=0):
        return hashlib.sha256((salt+"/"+tag+"/"+str(i)+"/"+str(j)).encode()).hexdigest()[:22]
    used=set()
    def token():
        for _ in range(500):
            n=rng.randrange(1,65536)
            if n not in used:
                used.add(n)
                return [(n>>i)&1 for i in range(16)]
        raise Quarantined("TOKEN_EXHAUSTED")
    def change(raw,indices):
        z=list(raw)
        for i in indices:z[i]^=1
        return z
    def edge(frm,to,role,src,dst):
        return {"from":frm,"to":to,"role":role,
                "src_bits":list(src),"dst_bits":list(dst)}
    depth=10+seed%3
    roles=[ident("role",i) for i in range(depth)]
    main=[ident("main",i) for i in range(depth+1)]
    side={(i,j):ident("side",i,j) for i in range(1,depth+1) for j in range(2)}
    main_bits=[token() for _ in range(depth+1)]
    side_bits={(i,j):token() for i in range(1,depth+1) for j in range(2)}
    width=WIDTH[family];hops=HOPS[family]
    mask=tuple(sorted(rng.sample(range(16),width)))
    alternate=tuple(sorted(rng.sample(
        [k for k in range(16) if k not in mask],width)))
    edges=[]
    for step in range(depth):
        src=change(main_bits[step],mask) if step in hops else main_bits[step]
        edges.append(edge(main[step],main[step+1],roles[step],
                          src,main_bits[step+1]))
        for j in range(2):
            decoy=change(main_bits[step],
                         ((mask[0]+3+step+j)%16,))
            edges.append(edge(main[step],side[step+1,j],
                              roles[step],decoy,side_bits[step+1,j]))
            if step:
                # Braided side continuity, never a valid route to target.
                destination=(j+int(step%3==0))%2
                edges.append(edge(side[step,j],side[step+1,destination],
                                  roles[step],side_bits[step,j],
                                  side_bits[step+1,destination]))
    edges.append(edge(side[depth-1,1],main[-1],roles[-1],
            change(side_bits[depth-1,1],(3,7,11)),token()))
    donor_role=ident("off-role",0)
    edges.append(edge(main[0],ident("off-role-target",0),donor_role,
            change(main_bits[hops[-1]],alternate),token()))
    pos={"start":main[0],"target":main[-1],
         "roles":roles,"edges":json.loads(json.dumps(edges))}
    neg=json.loads(json.dumps(pos))
    actual=[e for e in neg["edges"] if e["from"]==main[hops[-1]]
            and e["to"]==main[hops[-1]+1] and
            e["role"]==roles[hops[-1]]]
    donor=[e for e in neg["edges"] if e["role"]==donor_role]
    need(len(actual)==1 and len(donor)==1,"TOKEN_DONOR_PAIR")
    actual[0]["src_bits"],donor[0]["src_bits"]=(
        donor[0]["src_bits"],actual[0]["src_bits"])
    rng.shuffle(pos["edges"]);rng.shuffle(neg["edges"])
    admit(pos,neg)
    return pos,neg
def protected(*args,**kwargs):
    raise Quarantined("PROTECTED_SCIENTIFIC_SOURCE_UNAVAILABLE")

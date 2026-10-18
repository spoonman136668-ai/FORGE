"""F124-AM true public-bit unknown values: None in src_bits means unavailable.

New standalone source constructor; source-only semantic oracle uses ONLY
public known bits and explicitly unknown positions, never hidden true values.
No previous graph generator imported. Values erased in the returned graph
cannot be recovered from another out-of-band field or source seed.
"""
from __future__ import annotations
from collections import Counter
from itertools import combinations
from pathlib import Path
import hashlib,json,random
PROTOCOL=Path(__file__).resolve().parents[1]/"reference/research-intake/f124am-masked-recurrent-freeze.json"
PROTOCOL_BLOB="4675bdcebd9fcf99d3d5d9b539630c43cc5dbc95"
FAMILIES=("masked_middle","masked_first","variable_four")
SALTS={"masked_middle":"forge/F124AM/masked-middle/new/v1",
       "masked_first":"forge/F124AM/masked-first/new/v1",
       "variable_four":"forge/F124AM/variable-four/new/v1"}
HOPS={"masked_middle":(2,5,9),"masked_first":(2,6,9),
      "variable_four":(2,4,6,9)}
WIDTH={"masked_middle":2,"masked_first":1,"variable_four":2}
MASKED_HOP={"masked_middle":5,"masked_first":2,"variable_four":6}
COHORTS={x:{"FIT":range(3490000,3490024),
            "DEV":range(3490100,3490124)} for x in FAMILIES}
VECTORS=((2,1,1),(1,2,1))
EDGE_FIELDS={"from","to","role","src_bits","dst_bits"}
MASKS=tuple(m for m in range(1,65536) if m.bit_count() in (1,2))
MASK_ID={m:i for i,m in enumerate(MASKS)}
ALL_CANDIDATES=(1<<len(MASKS))-1
class Quarantined(ValueError):pass
def need(ok,code):
    if not ok:raise Quarantined("F124AM_"+code)
def gitblob(raw):
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()
def frozen():
    raw=PROTOCOL.read_bytes().replace(b"\r\n",b"\n")
    need(gitblob(raw)==PROTOCOL_BLOB,"FROZEN_PROTOCOL_CHANGED")
    p=json.loads(raw)
    need(p["schema"]=="forge.research.f124am.masked-recurrent.v1"
         and p["stage"]=="PREIMPLEMENTATION_FROZEN"
         and p["parent"]["head"]=="fd9760171f75052c546c0cb5f9f52bd635b9b3aa"
         and p["parent"]["actions"]==39117381114
         and p["source"]["FIT"]==[3490000,3490023]
         and p["source"]["DEV"]==[3490100,3490123]
         and all(row["salt"]==SALTS[row["name"]] and
                 row["hops"]==list(HOPS[row["name"]]) and
                 row["width"]==WIDTH[row["name"]]
                 for row in p["source"]["families"])
         and p["model"]["total_globals"]==7 and
         all(v is False for v in p["governance"].values()),
         "FROZEN_SOURCE_GOVERNANCE_DRIFT")
    return hashlib.sha256(raw).hexdigest()
def validate_public(g):
    need(type(g) is dict and set(g)=={"start","target","roles","edges"},
         "PUBLIC_GRAPH_FIELDS")
    need(type(g["start"]) is str and type(g["target"]) is str
         and g["start"]!=g["target"] and type(g["roles"]) is list
         and len(g["roles"]) in (10,11,12)
         and 20<=len(g["edges"])<=128,"GRAPH_DEPTH_OR_SIZE")
    nodes={g["start"],g["target"]}
    for e in g["edges"]:
        need(type(e) is dict and set(e)==EDGE_FIELDS,"EDGE_FIELDS")
        for key in ("from","to","role"):
            need(type(e[key]) is str and bool(e[key]),"PUBLIC_ROLE_OR_NODE")
        nodes.add(e["from"]);nodes.add(e["to"])
        need(type(e["src_bits"]) is list and len(e["src_bits"])==16
            and all(x is None or type(x) is int and x in (0,1)
                    for x in e["src_bits"]),"PUBLIC_MASKED_BITS")
        need(type(e["dst_bits"]) is list and len(e["dst_bits"])==16
            and all(type(x) is int and x in (0,1)
                    for x in e["dst_bits"]),"PUBLIC_KNOWN_DST")
    need(len(nodes)<=64,"NODES_EXCEED_64")
    return g
def allowed_masks(carried,observed):
    """Public-only possible NONZERO 1/2-bit change masks.

    Zero means exact edge, and is NOT an observable causal event.
    Unknown bits DO NOT imply equality; an opportunity with unknown bits
    may or may not have a true change. On the experimental masked hops,
    candidate widths 1/2 and nonzero are an explicitly engineered bias.
    """
    if carried is None:return 0
    definite=0;unknown=0
    for i,(a,b) in enumerate(zip(carried,observed)):
        if b is None:unknown|=1<<i
        elif a!=b:definite|=1<<i
    if not definite and not unknown:return 0
    possibles=0
    for m in MASKS:
        if m&definite==definite and m&~(definite|unknown)==0:
            possibles|=1<<MASK_ID[m]
    return possibles
def semantic_routes(g,mode="consistent"):
    """SOURCE-ONLY public existential relationship semantics, no hidden bit."""
    validate_public(g)
    need(mode in ("consistent","role_only","exact"),"SEMANTIC_MODE")
    paths=[(g["start"],None,0,0)]
    for role in g["roles"]:
        nxt=[]
        for node,carried,belief,events in paths:
            for edge in g["edges"]:
                if node!=edge["from"] or role!=edge["role"]:continue
                if carried is not None and sum(
                        a!=b for a,b in zip(carried,edge["src_bits"])
                        if b is not None)>2:continue
                candidate=allowed_masks(carried,edge["src_bits"])
                if mode=="exact" and candidate:continue
                if mode=="consistent" and carried is not None:
                    if not candidate and any(x is None for x in edge["src_bits"]):
                        # A masked observation may be genuinely ambiguous.
                        continue
                    if candidate:
                        now=(belief & candidate) if belief else candidate
                        if not now:continue
                        evt=events+1
                    else:now=belief;evt=events
                    if evt>4:continue
                else:now=belief;evt=events
                nxt.append((edge["to"],edge["dst_bits"],now,evt))
                need(len(nxt)<=128,"SOURCE_ORACLE_FRONTIER")
        paths=nxt
    if mode=="consistent":
        return sum(n==g["target"] and 2<=events<=4 and belief!=0
                   for n,_,belief,events in paths)
    return sum(n==g["target"] for n,_,_,_ in paths)
def admit(pos,neg):
    validate_public(pos);validate_public(neg)
    need(all(pos[k]==neg[k] for k in ("start","target","roles")),
         "PUBLIC_PAIR_QUERY_DRIFT")
    def inventory(g):
        return (Counter((e["from"],e["to"],e["role"]) for e in g["edges"]),
                Counter(tuple(e[field]) for e in g["edges"]
                        for field in ("src_bits","dst_bits")))
    need(inventory(pos)==inventory(neg),"PUBLIC_TOKEN_HISTOGRAM_LEAK")
    need(semantic_routes(pos)==1 and semantic_routes(neg)==0,
         "MASKED_SEMANTIC_SOURCE_NOT_SEPARABLE")
    need(semantic_routes(pos,"role_only")==semantic_routes(neg,"role_only"),
         "ROLE_ONLY_LABEL_LEAK")
    return True
def build(family,seed,vector,phase):
    frozen()
    need(family in FAMILIES and phase in ("FIT","DEV") and
         seed in COHORTS[family][phase] and tuple(vector) in VECTORS,
         "SOURCE_IDENTITY_NOT_FROZEN")
    tag=SALTS[family]+"/"+phase+"/"+str(seed)+"/"+",".join(map(str,vector))
    rng=random.Random(int.from_bytes(hashlib.sha256(tag.encode()).digest()[:16],"big"))
    def name(section,i,j=0):
        return hashlib.sha256((tag+"/"+section+"/"+str(i)+"/"+str(j)).encode()).hexdigest()[:22]
    used=set()
    def token():
        for _ in range(500):
            value=rng.randrange(1,65536)
            if value not in used:
                used.add(value);return [(value>>i)&1 for i in range(16)]
        raise Quarantined("TOKEN_ALLOCATION_EXHAUSTED")
    def flip(value,mask):
        v=list(value)
        for i in range(16):
            if mask&(1<<i):v[i]^=1
        return v
    def edge(u,v,r,src,dst):
        return {"from":u,"to":v,"role":r,
                "src_bits":list(src),"dst_bits":list(dst)}
    depth=10+seed%3
    roles=[name("role",i) for i in range(depth)]
    root=[name("main",i) for i in range(depth+1)]
    side={(i,j):name("branch",i,j) for i in range(1,depth+1) for j in range(2)}
    content=[token() for i in range(depth+1)]
    side_tokens={(i,j):token() for i in range(1,depth+1) for j in range(2)}
    width=WIDTH[family];hops=HOPS[family]
    anchor=tuple(sorted(rng.sample(range(16),width)))
    other=tuple(sorted(rng.sample([i for i in range(16) if i not in anchor],width)))
    def asmask(items):return sum(1<<k for k in items)
    edges=[]
    for hop in range(depth):
        sample=flip(content[hop],asmask(anchor)) if hop in hops else list(content[hop])
        if hop==MASKED_HOP[family]:
            # A TRUE value is removed; the visible edge carries only null.
            # No hidden fill/true bit appears elsewhere in the public graph.
            sample[anchor[-1]]=None
        edges.append(edge(root[hop],root[hop+1],roles[hop],sample,content[hop+1]))
        for j in range(2):
            mask=(1<<((anchor[0]+hop+j+4)%16))
            edges.append(edge(root[hop],side[hop+1,j],
                              roles[hop],flip(content[hop],mask),
                              side_tokens[hop+1,j]))
            if hop:
                dest_j=(j+int(hop%3==0))%2
                edges.append(edge(side[hop,j],side[hop+1,dest_j],roles[hop],
                          side_tokens[hop,j],side_tokens[hop+1,dest_j]))
    # Invalid 3-bit terminal shortcut cannot be mistaken for a valid route.
    terminalmask=sum(1<<i for i in (3,7,11))
    edges.append(edge(side[depth-1,1],root[-1],roles[-1],
                flip(side_tokens[depth-1,1],terminalmask),token()))
    donor_role=name("nonquery-role",0)
    edges.append(edge(root[0],name("nonquery-target",0),donor_role,
                flip(content[hops[-1]],asmask(other)),token()))
    pos={"start":root[0],"target":root[-1],
         "roles":roles,"edges":json.loads(json.dumps(edges))}
    neg=json.loads(json.dumps(pos))
    final=[e for e in neg["edges"] if e["from"]==root[hops[-1]]
           and e["to"]==root[hops[-1]+1] and e["role"]==roles[hops[-1]]]
    donor=[e for e in neg["edges"] if e["role"]==donor_role]
    need(len(final)==1 and len(donor)==1,"NEGATIVE_SWAPS")
    final[0]["src_bits"],donor[0]["src_bits"]=donor[0]["src_bits"],final[0]["src_bits"]
    rng.shuffle(pos["edges"]);rng.shuffle(neg["edges"])
    admit(pos,neg)
    return pos,neg
def protected(*args,**kwargs):
    raise Quarantined("PROTECTED_INDEPENDENT_FIRST_USE_UNAVAILABLE")

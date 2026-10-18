"""F124-AN source-born indistinguishable public worlds and resolvable masks.

Do not leak hidden-world labels or complete a None bit in model inference.
FIT and DEV independently salted. Ambiguous public graph appears as two
BYTE-FOR-BYTE identical observations with opposite latent validities.
"""
from __future__ import annotations
from pathlib import Path
from collections import Counter
import hashlib,json,random
PROTOCOL=Path(__file__).resolve().parents[1]/"reference/research-intake/f124an-identifiability-freeze.json"
PROTOCOL_BLOB="f204c96dc1adc6458d72df574d1e3baeabc03c18"
FAMILIES=("near_mask","distant_mask","role_repeat_mask")
SALTS={"near_mask":"forge/F124AN/observable/near/v1",
       "distant_mask":"forge/F124AN/observable/distant/v1",
       "role_repeat_mask":"forge/F124AN/observable/repeat/v1"}
HOPS={"near_mask":(2,5),"distant_mask":(1,9),"role_repeat_mask":(3,8)}
COHORTS={x:{"FIT":range(3590000,3590024),
            "DEV":range(3590100,3590124)} for x in FAMILIES}
VECTORS=((2,1,1),(1,2,1))
FIELDS={"from","to","role","src_bits","dst_bits"}
class Quarantined(ValueError):pass
def need(ok,label):
    if not ok:raise Quarantined("F124AN_"+label)
def gitblob(b):
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
def frozen():
    raw=PROTOCOL.read_bytes().replace(b"\r\n",b"\n")
    need(gitblob(raw)==PROTOCOL_BLOB,"ORIGINAL_PREIMPLEMENTATION_BLOB_DRIFT")
    p=json.loads(raw)
    need(p["schema"]=="forge.research.f124an.observable-identifiability.v1" and
      p["phase"]=="PREIMPLEMENTATION_FROZEN" and
      p["parent"]["head"]=="16af9d9175052856c54e20bd886aa49660c4b392" and
      p["parent"]["qualifying_actions"]==39118421276 and
      p["source"]["FIT_range"]==[3590000,3590023] and
      p["source"]["DEV_range"]==[3590100,3590123] and
      p["model"]["trained_head"].startswith("three-way softmax") and
      all(v is False for v in p["governance"].values()),
      "FROZEN_HYPOTHESIS_SOURCE_GOVERNANCE")
    return hashlib.sha256(raw).hexdigest()
def validate_public(g):
    need(type(g) is dict and set(g)=={"start","target","roles","edges"},
         "PUBLIC_FIELDS")
    need(type(g["start"]) is str and type(g["target"]) is str and
      len(g["roles"]) in (10,11,12) and type(g["roles"]) is list and
      20<=len(g["edges"])<=128,"PUBLIC_SIZE")
    nodes={g["start"],g["target"]}
    for e in g["edges"]:
        need(type(e) is dict and set(e)==FIELDS,"EDGE_FIELDS")
        for k in ("from","to","role"):
            need(type(e[k]) is str and bool(e[k]),"EDGE_NAMES")
        nodes.update((e["from"],e["to"]))
        need(type(e["src_bits"]) is list and len(e["src_bits"])==16
             and all(v is None or type(v) is int and v in (0,1)
                     for v in e["src_bits"]),"REAL_MASKED_PUBLIC_BITS")
        need(type(e["dst_bits"]) is list and len(e["dst_bits"])==16
             and all(type(v) is int and v in (0,1)
                     for v in e["dst_bits"]),"DST_RAW16")
    need(len(nodes)<=64,"NODE_CAP")
    return g
def public_bit_options(carried,observed):
    if carried is None:return (None,)
    definite=[i for i,(a,b) in enumerate(zip(carried,observed))
              if b is not None and a!=b]
    unknown=[i for i,b in enumerate(observed) if b is None]
    if len(definite)>1:return ()
    if definite:return (definite[0],)
    return (None,*unknown)
def witness(g):
    """Independent source-only public completions. NOT inference.

    Returns whether a complete 2-event target path can be valid and invalid.
    No hidden true values are used or reconstructed.
    """
    validate_public(g)
    rows=[(g["start"],None,())]
    for role in g["roles"]:
        nxt=[]
        for node,carried,events in rows:
            for e in g["edges"]:
                if e["from"]!=node or e["role"]!=role:continue
                for bit in public_bit_options(carried,e["src_bits"]):
                    if carried is not None and bit is not None:
                        new_events=events+(bit,)
                    else:new_events=events
                    if len(new_events)>2:continue
                    nxt.append((e["to"],e["dst_bits"],new_events))
                    need(len(nxt)<=192,"INDEPENDENT_SOURCE_ORACLE_FRONTIER")
        rows=nxt
    answers={len(events)==2 and events[0]==events[1]
             for node,_,events in rows
             if node==g["target"] and len(events)==2}
    return answers
def judgment(g):
    possibilities=witness(g)
    if possibilities=={True}:return "POS"
    if True not in possibilities:return "NEG"
    if possibilities=={True,False}:return "ABSTAIN"
    raise Quarantined("UNEXPECTED_PUBLIC_IDENTIFIABILITY")
def build(family,seed,vector,phase):
    frozen()
    need(family in FAMILIES and phase in ("FIT","DEV")
      and seed in COHORTS[family][phase] and tuple(vector) in VECTORS,
      "COHORT_NOT_FROZEN")
    salt=SALTS[family]+"/"+phase+"/"+str(seed)+"/"+",".join(map(str,vector))
    rng=random.Random(int.from_bytes(hashlib.sha256(salt.encode()).digest()[:16],"big"))
    def name(section,i,j=0):
        return hashlib.sha256((salt+"/"+section+"/"+str(i)+"/"+str(j)).encode()).hexdigest()[:22]
    used=set()
    def raw16():
        for _ in range(500):
            n=rng.randrange(1,65536)
            if n not in used:
                used.add(n);return [(n>>j)&1 for j in range(16)]
        raise Quarantined("TOKEN_EXHAUSTION")
    def flip(src,bit):
        z=list(src);z[bit]^=1;return z
    def edge(frm,to,role,src,dst):
        return {"from":frm,"to":to,"role":role,
                "src_bits":list(src),"dst_bits":list(dst)}
    depth=10+seed%3
    roles=[name("role",i if family!="role_repeat_mask" else i%4)
           for i in range(depth)]
    main=[name("main",i) for i in range(depth+1)]
    side={(i,j):name("side",i,j) for i in range(1,depth+1) for j in range(2)}
    main_content=[raw16() for _ in range(depth+1)]
    side_content={(i,j):raw16() for i in range(1,depth+1) for j in range(2)}
    first,last=HOPS[family]
    anchor=rng.randrange(16)
    wrong=(anchor+1+rng.randrange(15))%16
    nullable=next(i for i in range(16) if i not in (anchor,wrong))
    edges=[]
    for hop in range(depth):
        src=flip(main_content[hop],anchor) if hop in (first,last) else main_content[hop]
        edges.append(edge(main[hop],main[hop+1],roles[hop],src,main_content[hop+1]))
        for j in range(2):
            decoy=flip(main_content[hop],(anchor+hop+j+3)%16)
            edges.append(edge(main[hop],side[hop+1,j],roles[hop],
                              decoy,side_content[hop+1,j]))
            if hop:
                dest=(j+int(hop%3==0))%2
                edges.append(edge(side[hop,j],side[hop+1,dest],roles[hop],
                         side_content[hop,j],side_content[hop+1,dest]))
    # No viable side-to-target shortcut (three definite changed bits).
    bad=list(side_content[depth-1,1])
    for k in (3,7,11):bad[k]^=1
    edges.append(edge(side[depth-1,1],main[-1],roles[-1],
                      bad,raw16()))
    donor_role=name("non-query",0)
    edges.append(edge(main[0],name("donor",0),donor_role,
                      flip(main_content[last],wrong),raw16()))
    def base():
        return {"start":main[0],"target":main[-1],
                "roles":roles,"edges":json.loads(json.dumps(edges))}
    positive=base();negative=base()
    targetp=[e for e in positive["edges"] if e["from"]==main[last]
             and e["to"]==main[last+1] and e["role"]==roles[last]]
    targetn=[e for e in negative["edges"] if e["from"]==main[last]
             and e["to"]==main[last+1] and e["role"]==roles[last]]
    donorp=[e for e in positive["edges"] if e["role"]==donor_role]
    donorn=[e for e in negative["edges"] if e["role"]==donor_role]
    need(len(targetp)==len(targetn)==len(donorp)==len(donorn)==1,
         "DONOR_OR_TARGET_NONUNIQUE")
    # Genuine masked value in causal transition, but observed explicit
    # anchor/wrong mismatches still resolve POS/NEG under 1-bit cardinality.
    for row in (targetp[0],targetn[0],donorp[0],donorn[0]):
        row["src_bits"][nullable]=None
    targetn[0]["src_bits"],donorn[0]["src_bits"]=(
       donorn[0]["src_bits"],targetn[0]["src_bits"])
    ambiguous=base()
    tgt=[e for e in ambiguous["edges"] if e["from"]==main[last]
         and e["to"]==main[last+1] and e["role"]==roles[last]]
    need(len(tgt)==1,"AMBIGUOUS_TARGET_NONUNIQUE")
    # EXACT same PUBLIC graph permits two possible one-bit completions:
    # flip at anchor => TRUE causal continuation; flip at wrong => FALSE.
    tgt[0]["src_bits"][anchor]=None
    tgt[0]["src_bits"][wrong]=None
    rng.shuffle(positive["edges"]);rng.shuffle(negative["edges"])
    rng.shuffle(ambiguous["edges"])
    validate_public(positive);validate_public(negative)
    validate_public(ambiguous)
    def inventory(g):
        return (Counter((e["from"],e["to"],e["role"]) for e in g["edges"]),
                Counter(tuple(e[k]) for e in g["edges"]
                        for k in ("src_bits","dst_bits")))
    need(inventory(positive)==inventory(negative),"POS_NEG_TOKEN_OR_TOPOLOGY_LEAK")
    need(judgment(positive)=="POS" and judgment(negative)=="NEG"
         and judgment(ambiguous)=="ABSTAIN","SOURCE_PUBLIC_TRUTH_DRIFT")
    other=json.loads(json.dumps(ambiguous))
    need(json.dumps(other,sort_keys=True)==json.dumps(ambiguous,sort_keys=True),
         "OPPOSITE_LATENT_WORLD_OBSERVATION_IDENTITY")
    return {"positive":positive,"negative":negative,
            "ambiguous_public":ambiguous,"ambiguous_twin":other}
def protected(*a,**kw):
    raise Quarantined("SEALED_PROTECTED_FIRST_USE_NOT_ALLOWED")

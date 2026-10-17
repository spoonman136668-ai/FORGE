"""F124-K 7-9-hop independent source qualification with sealed first-use gate.

Only distinct NONRESERVED fixture seeds are executable. The frozen reserved
CONFIRM ranges are never evaluated, previewed, inferred, or unsealed here.
A separate independently authorized, independently reviewed single-use
adapter is required for the protected source-birth step.
"""
from __future__ import annotations
from collections import Counter
import hashlib
import inspect
import json
from pathlib import Path
import random

PROTOCOL=Path(__file__).resolve().parents[1]/"reference/research-intake/f124k-extended-confirm-source-freeze.json"
PROTOCOL_BLOB="8065de6263f45cea465ec0bda622d985c5488ef8"
FIXTURES={"Wingless":range(280000,280024),"Yggdrasil":range(290000,290024)}
RESERVED={"Wingless":range(180100,180148),"Yggdrasil":range(190100,190148)}
GRAPH_KEYS={"start","target","roles","edges"}
EDGE_KEYS={"from","to","role","src_bits","dst_bits"}
STRATA=("near_collision","wrong_role_alias","parallel_multiedge","repeated_key","late_cross_route")
AUTHORITY_STATUS="BLOCKED_PENDING_INDEPENDENT_FIRST_USE_AND_MODEL_INTERFACE"

class Invalid(ValueError):
    pass

def need(ok,code):
    if not ok: raise Invalid("F124K_"+code)

def git_blob(data):
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()

def frozen():
    raw=PROTOCOL.read_bytes().replace(b"\r\n",b"\n")
    need(git_blob(raw)==PROTOCOL_BLOB,"FREEZE_IDENTITY_DRIFT")
    p=json.loads(raw)
    need(p["schema"]=="forge.research.f124k.frozen-independent-confirm-source-v1"
         and p["status"]=="PREIMPLEMENTATION_FREEZE"
         and p["parent_f124j_head"]=="e4bb3850c0d45b195b30cefb4b6a86523370aff8"
         and p["fixtures"]["Wingless"]==[280000,280023]
         and p["fixtures"]["Yggdrasil"]==[290000,290023]
         and p["protected"]["Wingless"]==[180100,180147]
         and p["protected"]["Yggdrasil"]==[190100,190147]
         and p["expected_verdict"]==
               "SOURCE_FIXTURE_QUALIFIED__PROTECTED_FIRST_USE_BLOCKED"
         and all(p["authority"].values()),"FROZEN_CONTRACT_DRIFT")
    return hashlib.sha256(raw).hexdigest()

def validate_public(g):
    need(type(g) is dict and set(g)==GRAPH_KEYS,"FORBIDDEN_PUBLIC_FIELDS")
    need(type(g["start"]) is str and type(g["target"]) is str
         and g["start"] and g["target"] and g["start"]!=g["target"]
         and type(g["roles"]) is list and len(g["roles"]) in (7,8,9)
         and len(set(g["roles"]))==len(g["roles"])
         and all(type(x) is str and x for x in g["roles"])
         and type(g["edges"]) is list and 12<=len(g["edges"])<=128,
         "EXTENDED_SOURCE_SHAPE_INVALID")
    nodes={g["start"],g["target"]}
    for e in g["edges"]:
        need(type(e) is dict and set(e)==EDGE_KEYS,"FORBIDDEN_EDGE_FEATURE")
        need(all(type(e[x]) is str and e[x] for x in ("from","to","role")),
             "OPAQUE_GRAPH_ID_INVALID")
        nodes.update((e["from"],e["to"]))
        for field in ("src_bits","dst_bits"):
            need(type(e[field]) is list and len(e[field])==16 and
                 all(type(b) is int and b in (0,1) for b in e[field]),
                 "PUBLIC_RAW_BIT_ONLY")
    need(len(nodes)<=64,"SOURCE_NODE_BUDGET")
    return g

def symbolic_routes(g,role_only=False):
    """Independent *admission* reference; never passes true path to any model."""
    validate_public(g)
    frontier=[(g["start"],None)]
    for role in g["roles"]:
        next_states=[]
        for node,key in frontier:
            for e in g["edges"]:
                if e["from"]==node and e["role"]==role and (
                   role_only or key is None or key==e["src_bits"]):
                    next_states.append((e["to"],e["dst_bits"]))
                    need(len(next_states)<=256,"REFERENCE_FRONTIER_BUDGET")
        frontier=next_states
    return sum(node==g["target"] for node,_ in frontier)

def paired_admit(pos,neg):
    validate_public(pos);validate_public(neg)
    need(all(pos[k]==neg[k] for k in ("start","target","roles")),
         "PAIRED_QUERY_IDENTITY")
    def inventory(g):
        return (Counter((e["from"],e["to"],e["role"]) for e in g["edges"]),
                Counter(tuple(e[x]) for e in g["edges"]
                        for x in ("src_bits","dst_bits")))
    need(inventory(pos)==inventory(neg),"ROLE_TOPOLOGY_OR_TOKEN_HISTOGRAM_LEAK")
    need(symbolic_routes(pos)==1 and symbolic_routes(neg)==0,
         "CAUSAL_ROUTE_LABEL_AMBIGUITY")
    need(symbolic_routes(pos,True)>=5 and
         symbolic_routes(neg,True)==symbolic_routes(pos,True),
         "INSUFFICIENT_OR_CHANGED_COMPETING_PATHS")
    return True

def _assemble_fixture(seed,vector,lane):
    """Explicitly fixture-only; protected seed cannot satisfy the guard."""
    need(lane in FIXTURES and type(seed) is int and seed in FIXTURES[lane],
         "RESERVED_OR_UNAUTHORIZED_SOURCE")
    salt=("forge/F124K/FIXTURE/v1/"+lane+"/"+str(seed)+"/"+
          ",".join(map(str,vector)))
    rng=random.Random(int.from_bytes(hashlib.sha256(salt.encode()).digest()[:12],"big"))
    def opaque(s):
        return hashlib.sha256((salt+"/"+s).encode()).hexdigest()[:22]
    def bits(v):
        return [(v>>i)&1 for i in range(16)]
    def edge(a,b,role,src,dst):
        return {"from":a,"to":b,"role":role,
                "src_bits":bits(src),"dst_bits":bits(dst)}
    observed=set()
    def new_token():
        for _ in range(2048):
            value=rng.randrange(1,65536)
            if value not in observed:
                observed.add(value)
                return value
        raise Invalid("F124K_TOKEN_SPACE_EXHAUSTED")
    hops=7+seed%3
    roles=[opaque("role-"+str(i)) for i in range(hops)]
    points=[opaque("main-"+str(i)) for i in range(hops+1)]
    primary=[new_token() for _ in range(hops+1)]
    edges=[edge(points[i],points[i+1],roles[i],primary[i],primary[i+1])
           for i in range(hops)]
    family=STRATA[seed%len(STRATA)]
    previous_branch_keys=None
    stage_endkeys=[]
    # Three *distinct* successive join depths: 2, 4 and 6. Each stage has
    # two alternative 2-hop paths. Structurally 27 competing role-only paths.
    for stage in (2,4,6):
        start=points[stage-2]
        finish=points[stage]
        decoy_endkeys=[]
        for j in range(2):
            mid=opaque("decoy-stage-"+str(stage)+"-"+str(j))
            internal=new_token()
            dst=new_token()
            if stage==2 and family=="near_collision" and j==0:
                proposal=primary[2] ^ (1<<(seed%16))
                if proposal not in observed and proposal>0:
                    observed.discard(dst)
                    observed.add(proposal)
                    dst=proposal
            # At later joins, use a carried decoy key from the preceding
            # stage if available. The destination at the new join is still
            # deliberately incompatible with the main route.
            first_src=(previous_branch_keys[j] if previous_branch_keys is not None
                       else new_token())
            edges.extend((edge(start,mid,roles[stage-2],first_src,internal),
                          edge(mid,finish,roles[stage-1],internal,dst)))
            decoy_endkeys.append(dst)
        previous_branch_keys=decoy_endkeys
        stage_endkeys.append(decoy_endkeys)
    if family=="wrong_role_alias":
        edges.append(edge(points[4],opaque("wrong-role-alias"),
                          opaque("off-role-alias"),primary[4],new_token()))
    elif family=="parallel_multiedge":
        edges.append(edge(points[3],points[4],roles[3],new_token(),new_token()))
    elif family=="repeated_key":
        edges.append(edge(points[6],opaque("repeated-key-alias"),
                          opaque("off-role-repeat"),stage_endkeys[0][0],new_token()))
    elif family=="late_cross_route":
        edges.append(edge(points[7],opaque("late-cross-route"),
                          opaque("off-role-late"),primary[7],new_token()))
    swap_junk_index=len(edges)
    edges.append(edge(points[0],opaque("negative-swap-junk"),
                      opaque("offrole-swap"),new_token(),new_token()))
    for k in range(vector[0]%3):
        edges.append(edge(opaque("noise-src-"+str(k)),
                          opaque("noise-dst-"+str(k)),
                          opaque("noise-role-"+str(k)),new_token(),new_token()))
    neg=json.loads(json.dumps(edges))
    # Alter only the necessary main continuation at hop 3 by a globally
    # token-histogram-preserving exchange with an offrole edge.
    neg[2]["src_bits"],neg[swap_junk_index]["src_bits"]=(
        neg[swap_junk_index]["src_bits"],neg[2]["src_bits"])
    rng.shuffle(edges);rng.shuffle(neg)
    positive={"start":points[0],"target":points[-1],
              "roles":roles,"edges":edges}
    negative={"start":points[0],"target":points[-1],
              "roles":roles,"edges":neg}
    paired_admit(positive,negative)
    return positive,negative

def build_fixture(seed,vector,lane,phase="QUALIFICATION_FIXTURE"):
    frozen()
    need(phase=="QUALIFICATION_FIXTURE"
         and type(seed) is int and lane in FIXTURES and seed in FIXTURES[lane]
         and type(vector) is list and len(vector)==3
         and all(type(x) is int and 0<=x<=3 for x in vector),
         "PROTECTED_SOURCE_OR_INVALID_FIXTURE")
    return _assemble_fixture(seed,vector,lane)

def build_protected(*args,**kwargs):
    """Fail closed: no independent cryptographic first-use authority exists."""
    raise Invalid("F124K_FIRST_USE_BLOCKED_NO_INDEPENDENT_AUTHORIZATION")

def first_use_preflight():
    """Static state: no protected seed construction or model scoring."""
    frozen()
    import f124h_source as original
    original_raw=Path(original.__file__).read_bytes().replace(b"\r\n",b"\n")
    need(git_blob(original_raw)=="3feab91460f29ec169e1904479a134bb04691937",
         "ORIGINAL_MODEL_INPUT_SOURCE_DRIFT")
    original_validate_source=inspect.getsource(original.validate)
    need('len(g["roles"]) in (4,5)' in original_validate_source,
         "ORIGINAL_MODEL_INPUT_INTERFACE_DRIFT")
    need(all(not set(FIXTURES[l]) & set(RESERVED[l]) for l in FIXTURES),
         "RESERVED_FIXTURE_OVERLAP")
    return {
        "source_fixture_ready":True,
        "fixture_depths":[7,8,9],
        "fixture_cohorts_per_lane":24,
        "original_f124h_model_accepts_7_to_9_hops":False,
        "independent_first_use_receipt_verified":False,
        "protection":"BLOCKED_PENDING_INDEPENDENT_FIRST_USE_AND_MODEL_INTERFACE",
        "reserved_examples_built":0,
        "original_first_use_occurred":False,
        "next_steps":"review validation-only adapter without modifying original model, independent first-use signer, append-only one-shot admission"
    }

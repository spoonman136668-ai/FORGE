"""F124-AE: independent frozen 13-15 hop source and symmetric transfer domains.

Original AD source admission remains fail-closed. The only adapted component
of that generator is a new disjoint seed cohort. New longer paths are appended
identically to positive/negative AFTER prior legitimate pair admission.
Model sees only public graph; labels/oracles stay in admission/scoring.
"""
from __future__ import annotations
import hashlib,json,types
from collections import Counter
from pathlib import Path
import f124ad_frozen_source as previous
import f124aa_frozen_source as parent
import f124q_fresh_source as q
import f124w_hop_trace_indexed as guard

FREEZE=Path(__file__).resolve().parents[1]/"reference/research-intake/f124ae-frozen-extended-transfer-and-single-state.json"
FREEZE_BLOB="248666af8425bb786269a61f047f43c494be8a3e"
PARENT_SOURCE_BLOB="f2efa6566296e1ff406e5635c0cea2aa8593c7cb"
COHORTS={"Wingless":{"FIT":range(1780000,1780024),"DEV":range(1780100,1780124)},
         "Yggdrasil":{"FIT":range(1790000,1790024),"DEV":range(1790100,1790124)}}
VECTORS=previous.VECTORS
FAMILIES=("permuted_bits","long_dense_13_15","extended_13_15","one_bit_relaxed_keys")
BIAS=(-1.,-.5,-.25,0.,.25,.5,1.)

def need(ok,label):q.need(ok,"F124AE_"+label)

def frozen():
    previous.frozen()
    need(guard.blob(FREEZE)==FREEZE_BLOB
         and guard.blob(previous.__file__)==PARENT_SOURCE_BLOB,
         "ORIGINAL_SOURCE_AND_FREEZE")
    p=json.loads(FREEZE.read_text(encoding="utf-8"))
    need(p["schema"]=="forge.research.f124ae.frozen-extended-transfer-and-single-state-calibration.v1"
         and p["state"]=="PREIMPLEMENTATION_FROZEN"
         and p["lineage"]["parent_commit"]=="6d69e984ee5fb96e01f5067cb5ef9d4754d2a5fb"
         and p["source"]["Wingless"]==
           {k:[v.start,v.stop-1] for k,v in COHORTS["Wingless"].items()}
         and p["source"]["Yggdrasil"]==
           {k:[v.start,v.stop-1] for k,v in COHORTS["Yggdrasil"].items()}
         and p["source"]["families"]==list(FAMILIES)
         and p["Wingless"]["bias_grid"]==list(BIAS)
         and p["Yggdrasil"]["frozen_anchor"]==10
         and all(v is False for v in p["authority"].values()),
         "FROZEN_PARAMETERS_OR_SOURCE")
    return p

def validate_15(g):
    # Extend ONLY the structural shape bound, all exact raw-key constraints.
    need(type(g) is dict and set(g)==q.GRAPH_KEYS
         and type(g["roles"]) is list and 7<=len(g["roles"])<=15
         and type(g["start"]) is str and type(g["target"]) is str
         and g["start"] and g["target"] and g["start"]!=g["target"]
         and all(type(r) is str and r for r in g["roles"])
         and type(g["edges"]) is list and 12<=len(g["edges"])<=128,
         "PUBLIC_EXTENDED_SHAPE")
    nodes={g["start"],g["target"]}
    for e in g["edges"]:
        need(type(e) is dict and set(e)==q.EDGE_KEYS
             and all(type(e[k]) is str and e[k]
                     for k in ("from","to","role")),"PUBLIC_EDGE_FIELDS")
        nodes.update((e["from"],e["to"]))
        for name in ("src_bits","dst_bits"):
            bits=e[name]
            need(type(bits) is list and len(bits)==16
                 and all(type(b) is int and b in (0,1) for b in bits),
                 "PUBLIC_16BIT_KEYS")
    need(len(nodes)<=64,"PUBLIC_NODE_LIMIT")
    return g

def routes15(graph,relaxed=False,role_only=False):
    env=dict(parent.routes.__globals__)
    env["validate_extended"]=validate_15
    fn=types.FunctionType(parent.routes.__code__,env,
                          parent.routes.__name__,parent.routes.__defaults__)
    return fn(graph,relaxed,role_only)

def build(lane,requested_seed,vector,phase):
    need(lane in COHORTS and phase in ("FIT","DEV")
         and type(requested_seed) is int and
         requested_seed in COHORTS[lane][phase] and
         tuple(vector) in VECTORS,
         "ORIGINAL_SOURCE_NONRESERVED")
    env=dict(previous.build.__globals__)
    env["COHORTS"]=COHORTS
    generator=types.FunctionType(previous.build.__code__,env,
                     previous.build.__name__,previous.build.__defaults__)
    prior_family,pos,neg,chosen_seed=generator(lane,requested_seed,vector,phase)
    family=FAMILIES[(requested_seed-COHORTS[lane][phase].start)%4]
    need(prior_family==previous.FAMILIES[
        (requested_seed-COHORTS[lane][phase].start)%4],
        "UNCHANGED_PARENT_FAMILY")
    extra=6 if family=="long_dense_13_15" else (
          3 if family=="extended_13_15" else 0)
    if extra:
        terminal=parent.positive_route(pos)
        end=pos["target"];carry=list(terminal[-1]["dst_bits"])
        prefix="/".join(("F124AE",lane,phase,str(chosen_seed),
                         ",".join(map(str,vector)),family))
        def digest(label):
            return hashlib.sha256((prefix+"/"+label).encode()).digest()
        def token(label):
            return digest(label).hex()[:22]
        def bits(label):
            raw=digest(label)
            return [((int.from_bytes(raw[:2],"big")>>i)&1) for i in range(16)]
        for j in range(extra):
            target=token("target/"+str(j));role=token("role/"+str(j))
            out=bits("dst/"+str(j))
            edge={"from":end,"to":target,"role":role,
                  "src_bits":list(carry),"dst_bits":list(out)}
            for g in (pos,neg):
                g["roles"].append(role)
                g["edges"].append(json.loads(json.dumps(edge)))
                g["target"]=target
            end=target;carry=out
    relaxed=family=="one_bit_relaxed_keys"
    need(routes15(pos,relaxed)==1 and routes15(neg,relaxed)==0,
         "PUBLIC_CAUSAL_REFERENCE_NOT_ORACLE_IN_MODEL")
    need(routes15(pos,role_only=True)==routes15(neg,role_only=True)
         and routes15(pos,role_only=True)>=8,"ROLE_ONLY_NEGATIVE_CONTROL")
    need(all(pos[k]==neg[k] for k in ("start","target","roles")),
         "NO_PAIR_QUERY_LEAKAGE")
    def census(g):
        return (Counter((e["from"],e["to"],e["role"]) for e in g["edges"]),
                Counter(tuple(e[k]) for e in g["edges"]
                        for k in ("src_bits","dst_bits")))
    need(census(pos)==census(neg),"PAIR_IDENTICAL_PUBLIC_DISTRIBUTION")
    depth=len(pos["roles"])
    need((13<=depth<=15) if extra else (7<=depth<=9),
         "FROZEN_HOP_STRATUM")
    return family,pos,neg,chosen_seed

def pairs(lane,phase):
    cases=[]
    for vec in VECTORS:
        for requested in COHORTS[lane][phase]:
            fam,pos,neg,chosen=build(lane,requested,vec,phase)
            cases.append((chosen,tuple(vec),fam,pos,neg))
    need(len(cases)==48
         and all(sum(x[2]==fam for x in cases)==12 for fam in FAMILIES)
         and (phase!="FIT" or all(
            x[0]<COHORTS[lane]["DEV"].start for x in cases)),
         "COHORT_SEPARATION_AND_STRATA")
    return cases

"""F124-AD fresh independent identity-disjoint public composition source: DEVELOPMENT ONLY.

No protected constructor, no original or K fixture seed, no external dispatch.
Positive/negative pairing keeps role/topology/token inventories identical.
"""
from __future__ import annotations
from collections import Counter
import hashlib
import json
from pathlib import Path
import random

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "reference/research-intake/f124ad-intermediate-credit-freeze.json"
PROTOCOL_BLOB = "2941fdee92a866083a85fff795a118a933873a1a"
COHORTS = {
    "Wingless":{"FIT":range(1880000,1880024),"DEV":range(1880100,1880124)},
    "Yggdrasil":{"FIT":range(2290000,2290024),"DEV":range(2290100,2290124)},
    "YggdrasilStress":{"FIT":range(2290000,2290024),"DEV":range(2290100,2290124)},
    "YggdrasilCost":{"FIT":range(1990000,1990024),"DEV":range(1990100,1990124)}
}
SALTS={
    "Wingless":"f124ac/not-used/wing/",
    "Yggdrasil":"forge/F124AD/long-chain-causal-credit/v1/",
    "YggdrasilStress":"forge/F124AD/long-chain-causal-credit/v1/",
    "YggdrasilCost":"f124ac/not-used/cost/"
}
VECTORS = ((2, 1, 1), (1, 2, 1))
FORBIDDEN = {
    "Wingless": range(180100, 180148),
    "Yggdrasil": range(190100, 190148),
    "YggdrasilStress": range(190100, 190148),
    "YggdrasilCost": range(190100,190148),
}
GRAPH_KEYS = {"start", "target", "roles", "edges"}
EDGE_KEYS = {"from", "to", "role", "src_bits", "dst_bits"}


class Quarantined(ValueError):
    pass


def need(ok, code):
    if not ok:
        raise Quarantined("F124AD_" + code)


def git_blob(raw):
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def frozen():
    raw=PROTOCOL.read_bytes().replace(b"\r\n",b"\n")
    need(git_blob(raw)==PROTOCOL_BLOB,"PREIMPLEMENTATION_FREEZE_GIT_BLOB")
    p=json.loads(raw)
    need(p["schema"]=="forge.research.f124ad.intermediate-causal-evidence.v1"
         and p["stage"]=="PREIMPLEMENTATION_FROZEN"
         and p["parent"]["qualified_head"]=="8cefd03c798e944ae9aa0510c37066640e6bd0bb"
         and p["parent"]["run_id"]==39107491147
         and p["source"]["salt"]==SALTS["YggdrasilStress"]
         and p["source"]["fit"]==[2290000,2290023]
         and p["source"]["dev"]==[2290100,2290123]
         and p["original"]["cell_budget"]=={"active":7,"retained":9,"total":16}
         and p["hypotheses"]["grid"]==[0,0.1,0.25,0.5,1,2,4,8]
         and all(v is False for v in p["safety"].values()),
         "FROZEN_PROTOCOL_NOT_AUTHENTIC")
    return hashlib.sha256(raw).hexdigest()

def validate_public(g):
    need(type(g) is dict and set(g) == GRAPH_KEYS, "PUBLIC_GRAPH_FIELDS")
    need(type(g["start"]) is str and type(g["target"]) is str
         and g["start"] and g["target"] and g["start"] != g["target"]
         and type(g["roles"]) is list and len(g["roles"]) in (7, 8, 9, 10, 11, 12)
         and all(type(r) is str and r for r in g["roles"])
         and type(g["edges"]) is list and 12 <= len(g["edges"]) <= 128,
         "PUBLIC_GRAPH_SHAPE")
    nodes = {g["start"], g["target"]}
    for e in g["edges"]:
        need(type(e) is dict and set(e) == EDGE_KEYS
             and all(type(e[x]) is str and e[x] for x in ("from", "to", "role")),
             "NO_ORACLE_OR_HIDDEN_EDGE")
        nodes.update((e["from"], e["to"]))
        for k in ("src_bits", "dst_bits"):
            need(type(e[k]) is list and len(e[k]) == 16
                 and all(type(b) is int and b in (0, 1) for b in e[k]),
                 "RAW_16_BIT_ONLY")
    need(len(nodes) <= 64, "PUBLIC_NODE_BUDGET")
    return g


def public_routes(g, role_only=False):
    """Admission oracle, never passed into predictor or made into edge features."""
    validate_public(g)
    frontier = [(g["start"], None)]
    for role in g["roles"]:
        following = []
        for node, carried in frontier:
            for e in g["edges"]:
                if e["from"] == node and e["role"] == role and (
                    role_only or carried is None or carried == e["src_bits"]
                ):
                    following.append((e["to"], e["dst_bits"]))
                    need(len(following) <= 256, "REFERENCE_FRONTIER_BUDGET")
        frontier = following
    return sum(node == g["target"] for node, _ in frontier)


def paired_admit(pos, neg):
    validate_public(pos)
    validate_public(neg)
    need(all(pos[k] == neg[k] for k in ("start", "target", "roles")),
         "PAIR_QUERY_DRIFT")
    def inventory(g):
        return (Counter((e["from"], e["to"], e["role"]) for e in g["edges"]),
                Counter(tuple(e[k]) for e in g["edges"]
                        for k in ("src_bits", "dst_bits")))
    need(inventory(pos) == inventory(neg), "TOPOLOGY_TOKEN_HISTOGRAM_LEAK")
    need(public_routes(pos) == 1 and public_routes(neg) == 0,
         "EXACT_CAUSAL_LABEL_AMBIGUITY")
    rp, rn = public_routes(pos, True), public_routes(neg, True)
    need(rp >= 8 and rp == rn, "NONCAUSAL_TOPOLOGY_SHORTCUT")
    return True


def build(lane, seed, vector, phase):
    frozen()
    need(lane in COHORTS and phase in ("FIT", "DEV")
         and type(seed) is int and seed in COHORTS[lane][phase]
         and seed not in FORBIDDEN[lane]
         and type(vector) in (list, tuple) and tuple(vector) in VECTORS,
         "NONRESERVED_DEVELOPMENT_ONLY")
    salt = (SALTS[lane] + lane + "/" + phase + "/" +
            str(seed) + "/" + ",".join(map(str, vector)))
    rng = random.Random(int.from_bytes(hashlib.sha256(salt.encode()).digest()[:12], "big"))
    def opaque(label):
        return hashlib.sha256((salt + "/" + label).encode()).hexdigest()[:22]
    def bits(v):
        return [(v >> i) & 1 for i in range(16)]
    def edge(a, b, r, src, dst):
        return {"from": a, "to": b, "role": r,
                "src_bits": bits(src), "dst_bits": bits(dst)}
    used = {0}
    def key():
        for _ in range(1024):
            value = rng.randrange(1, 65536)
            if value not in used:
                used.add(value)
                return value
        raise Quarantined("F124AD_KEY_EXHAUSTION")
    n = 7 + seed % 3
    # Every even seed reuses the same public relation across nonadjacent hops.
    roles = [opaque("role-" + str(i % 3 if seed % 2 == 0 else i))
             for i in range(n)]
    nodes = [opaque("node-" + str(i)) for i in range(n+1)]
    carry = [key() for _ in range(n+1)]
    positive_edges = [edge(nodes[i], nodes[i+1], roles[i], carry[i], carry[i+1])
                      for i in range(n)]
    # Exactly three alternate two-hop joins; all are position/key-unreliable.
    # The second candidate at stage four has public partial observations
    # (zero-masked noncausal key fields), symmetrically across the pair.
    for stage in (2, 4, 6):
        for j in range(2):
            mid = opaque("join-" + str(stage) + "-" + str(j))
            entry = key()
            internal = key()
            exit_key = key()
            if stage == 4 and j == 1:
                entry = internal = exit_key = 0
            positive_edges.append(edge(nodes[stage-2], mid, roles[stage-2],
                                       entry, internal))
            positive_edges.append(edge(mid, nodes[stage], roles[stage-1],
                                       internal, exit_key))
    # Novel distractors, partly observed; no privileged path or truth metadata.
    for j in range(vector[0]):
        positive_edges.append(edge(opaque("noise-from-" + str(j)),
                                   opaque("noise-to-" + str(j)),
                                   opaque("noise-role-" + str(j)), 0, 0))
    offrole = len(positive_edges)
    positive_edges.append(edge(nodes[0], opaque("offrole-end"),
                               opaque("offrole"), key(), key()))
    negative_edges = json.loads(json.dumps(positive_edges))
    # This swap keeps complete public token histogram and topology fixed but
    # causally breaks the unique compatible main continuation at depth 3.
    negative_edges[2]["src_bits"], negative_edges[offrole]["src_bits"] = (
        negative_edges[offrole]["src_bits"], negative_edges[2]["src_bits"]
    )
    rng.shuffle(positive_edges)
    rng.shuffle(negative_edges)
    base = {"start": nodes[0], "target": nodes[-1], "roles": roles}
    pos = {**base, "edges": positive_edges}
    neg = {**base, "edges": negative_edges}
    paired_admit(pos, neg)
    return pos, neg


def protected(*args, **kwargs):
    raise Quarantined("F124AD_PROTECTED_FIRST_USE_UNAVAILABLE")


def stress_pair(seed,vector,phase,lane='YggdrasilStress'):
    """New independent stress source, no access to protected original data.

    Role-constrained matching-key distractor chains consume a measured >16
    candidate pool. They cannot reach target and preserve exact causal label.
    """
    need(lane in ("YggdrasilStress","YggdrasilCost") and seed in COHORTS[lane][phase],"STRESS_SEED")
    pos,neg=build(lane,seed,vector,phase)
    salt=SALTS[lane]+str(seed)+"/"+phase+"/"+str(tuple(vector))
    rng=random.Random(int.from_bytes(
        hashlib.sha256((salt+"/stress-shuffle").encode()).digest()[:12],"big"))
    n=len(pos["roles"])
    def node(h,j):
        return hashlib.sha256((salt+"/noise-node/"+str(h)+"/"+str(j)).encode()).hexdigest()[:22]
    def key(h):
        b=hashlib.sha256((salt+"/chain-key/"+str(h)).encode()).digest()
        return [int((b[i//8]>>(i%8))&1) for i in range(16)]
    # Four new decoy nodes on each of first six hop boundaries. Maintain
    # a bounded number of role-only paths (<=256), even for depth 9.
    main_first=pos["start"]
    base_edges=[]
    for h in range(min(n-1,6)):
        if h==0:
            for j in range(4):
                base_edges.append({"from":main_first,"to":node(h,j),
                    "role":pos["roles"][h],
                    "src_bits":key(h),"dst_bits":key(h+1)})
        else:
            for j in range(4):
                for k in (0,1):
                    nxt=(j+k+1)%4
                    base_edges.append({"from":node(h-1,j),
                        "to":node(h,nxt),"role":pos["roles"][h],
                        "src_bits":key(h),"dst_bits":key(h+1)})
    need(len(base_edges)>30,"NO_ACTUAL_GRAPH_SATURATION")
    for g in (pos,neg):
        g["edges"].extend(json.loads(json.dumps(base_edges)))
        rng.shuffle(g["edges"])
        validate_public(g)
    paired_admit(pos,neg)
    return pos,neg

def transfer_pair(seed,vector,phase,family):
    """New FIT/DEV source, all transformations fixed before implementation.

    Same graph paired labels and original public key/role inventory preserved;
    none of the transforms uses inference, fitted weights, or protected source.
    """
    need(family in ("rekey","rewire","long_depth"),"FAMILY_NOT_FROZEN")
    pos,neg=stress_pair(seed,vector,phase)
    salt=SALTS["YggdrasilStress"]+str(seed)+"/"+phase+"/"+family+"/"+str(tuple(vector))
    if family=="rekey":
        mask=0xA53C
        perm=[(i*5)%16 for i in range(16)]
        for g in (pos,neg):
            for e in g["edges"]:
                for k in ("src_bits","dst_bits"):
                    old=e[k]
                    e[k]=[old[perm[i]] ^ ((mask>>i)&1) for i in range(16)]
    elif family=="rewire":
        # Reroute only OFF-TARGET decoy edges. From/to inventory stays equal
        # between positive and negative, and true target remains unreachable
        # from those decoys. Changed topology is newly source-salted.
        n=len(pos["roles"])
        for g in (pos,neg):
            for e in g["edges"]:
                for h in range(1,min(n-1,6)):
                    for j in range(4):
                        nodeh=hashlib.sha256((
                            SALTS["YggdrasilStress"]+str(seed)+"/"+phase+"/"+str(tuple(vector))+
                            "/noise-node/"+str(h-1)+"/"+str(j)
                        ).encode()).hexdigest()[:22]
                        if e["from"]!=nodeh or e["role"]!=g["roles"][h]:
                            continue
                        # Deterministic, invertible alternate successor topology.
                        nxt=(j+2) % 4 if e["to"]==hashlib.sha256((
                            SALTS["YggdrasilStress"]+str(seed)+"/"+phase+"/"+str(tuple(vector))+
                            "/noise-node/"+str(h)+"/"+str((j+1)%4)
                        ).encode()).hexdigest()[:22] else j
                        e["to"]=hashlib.sha256((
                            SALTS["YggdrasilStress"]+str(seed)+"/"+phase+"/"+str(tuple(vector))+
                            "/noise-node/"+str(h)+"/"+str(nxt)
                        ).encode()).hexdigest()[:22]
    elif family=="long_depth":
        # Public relationship chain extended by 3 hops, not a new model rule.
        # The original source is 7–9 deep; extended source is 10–12.
        before=pos["target"]
        # Detach paired query roles before both independently append 3 hops.
        pos["roles"]=list(pos["roles"])
        neg["roles"]=list(neg["roles"])
        for g in (pos,neg):
            dst=before
            # Anchor first src key on original terminal edge's public dst bits.
            terminal=[e for e in g["edges"] if e["to"]==before and
                      e["role"]==g["roles"][-1]]
            need(len(terminal)>0,"LONG_DEPTH_TERMINAL_SOURCE")
            carried=list(terminal[0]["dst_bits"])
            for i in range(3):
                node=hashlib.sha256((salt+"/extension-node-"+str(i)).encode()).hexdigest()[:22]
                role=hashlib.sha256((salt+"/extension-role-"+str(i)).encode()).hexdigest()[:22]
                next_bits=[(int(i==j%3) ^ v) for j,v in enumerate(carried)]
                g["edges"].append({"from":dst,"to":node,"role":role,
                   "src_bits":list(carried),"dst_bits":next_bits})
                g["roles"].append(role)
                dst=node
                carried=next_bits
            g["target"]=dst
    paired_admit(pos,neg)
    if family=="long_depth":
        need(len(pos["roles"]) in (10,11,12),"LONG_DEPTH_NOT_CHALLENGING")
    return pos,neg

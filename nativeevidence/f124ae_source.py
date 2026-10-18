"""F124-AE fresh independent identity-disjoint public composition source: DEVELOPMENT ONLY.

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
PROTOCOL = ROOT / "reference/research-intake/f124ae-independent-transfer-freeze.json"
PROTOCOL_BLOB = "e2132d019d3cd9573250751fa466a60ad63d43ce"
FAMILIES=("rekey","rewire","near_break","late_break")
SEEDS={"rekey":2390000,"rewire":2490000,"near_break":2590000,"late_break":2690000}
COHORTS={
    "AE_"+family:{"FIT":range(start,start+24),
                  "DEV":range(start+100,start+124)}
    for family,start in SEEDS.items()
}
SALTS={
    "AE_"+family:"forge/F124AE/fresh-family/"+family.replace("_","-")+"/v1/"
    for family in FAMILIES
}
# Source family salt identity must match immutable preregistration,
# including the sole intentionally underscore-named source form.
SALTS["AE_near_break"]="forge/F124AE/fresh-family/near-break/v1/"
SALTS["AE_late_break"]="forge/F124AE/fresh-family/late-break/v1/"
FORBIDDEN={lane:range(180100,180148) for lane in COHORTS}
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
        raise Quarantined("F124AE_" + code)


def git_blob(raw):
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def frozen():
    raw=PROTOCOL.read_bytes().replace(b"\r\n",b"\n")
    need(git_blob(raw)==PROTOCOL_BLOB,"FREEZE_GIT_BLOB_MISMATCH")
    p=json.loads(raw)
    need(p["schema"]=="forge.research.f124ae.independent-transfer-resources.v1"
         and p["stage"]=="PREIMPLEMENTATION_FROZEN"
         and p["parent"]["exact_head"]=="64735ba011d235f4a040ef30135735f9008d896a"
         and p["parent"]["qualified_run"]==39108375190
         and [row["key"] for row in p["new_source"]["families"]]==list(FAMILIES)
         and all(row["salt"]==SALTS["AE_"+row["key"]] for row in p["new_source"]["families"])
         and all(row["fit"]==[SEEDS[row["key"]],SEEDS[row["key"]]+23]
                 and row["dev"]==[SEEDS[row["key"]]+100,SEEDS[row["key"]]+123]
                 for row in p["new_source"]["families"])
         and p["models"]["coefficients"]=={"gamma":0.1,"penalty":1}
         and p["models"]["persistent_cells"]=={"active":7,"retained":9,"total":16}
         and all(v is False for v in p["governance"].values()),
         "PREREGISTRATION_INVALID")
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
        raise Quarantined("F124AE_KEY_EXHAUSTION")
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
    raise Quarantined("F124AE_PROTECTED_FIRST_USE_UNAVAILABLE")


def stress_pair(seed,vector,phase,lane='YggdrasilStress'):
    """New independent stress source, no access to protected original data.

    Role-constrained matching-key distractor chains consume a measured >16
    candidate pool. They cannot reach target and preserve exact causal label.
    """
    need(lane in COHORTS and seed in COHORTS[lane][phase],"STRESS_SEED")
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

def original_true_edges(pos):
    """SOURCE-ONLY public exact-path oracle for controlled negative birth.

    The predictor never imports or invokes this function.
    """
    validate_public(pos)
    done=[]
    edges=pos["edges"]
    def walk(hop,node,carried,route):
        if hop==len(pos["roles"]):
            if node==pos["target"]:
                done.append(route)
                need(len(done)<=1,"TRUE_ROUTE_NOT_UNIQUE")
            return
        for edge in edges:
            if edge["from"]==node and edge["role"]==pos["roles"][hop] and (
                  carried is None or carried==edge["src_bits"]):
                walk(hop+1,edge["to"],edge["dst_bits"],route+[edge])
    walk(0,pos["start"],None,[])
    need(len(done)==1 and len(done[0])==len(pos["roles"]),"POSITIVE_PATH_NOT_UNIQUE")
    return done[0]


def transfer_pair(seed,vector,phase,family):
    """Independently born development-only transfer graph with public paired admission."""
    frozen()
    need(family in FAMILIES and seed in COHORTS["AE_"+family][phase],
         "FAMILY_AND_SEED_IDENTITY")
    pos,neg=stress_pair(seed,vector,phase,lane="AE_"+family)
    route=original_true_edges(pos)
    if family=="rekey":
        for graph in (pos,neg):
            for edge in graph["edges"]:
                for key in ("src_bits","dst_bits"):
                    old=edge[key]
                    edge[key]=[old[(i*5)%16]^((0xA53C>>i)&1) for i in range(16)]
    elif family=="rewire":
        main_nodes={pos["start"],pos["target"]}
        for edge in route:
            main_nodes.add(edge["from"])
            main_nodes.add(edge["to"])
        # Rewire only noncausal decoy-to-decoy edges at the same role stage.
        for role in pos["roles"][:6]:
            possible=sorted({edge["to"] for edge in pos["edges"]
                  if edge["role"]==role and edge["from"] not in main_nodes
                  and edge["to"] not in main_nodes})
            if len(possible)<4:continue
            targets={node:possible[(i+2)%len(possible)]
                     for i,node in enumerate(possible)}
            for graph in (pos,neg):
                for edge in graph["edges"]:
                    if (edge["role"]==role and edge["from"] not in main_nodes
                         and edge["to"] in targets):
                        edge["to"]=targets[edge["to"]]
    else:
        # Newly construct negative from positive at an independently selected
        # role-chain break, rather than inherit old fixed hop-3 negative.
        off=[e for e in pos["edges"]
             if e["from"]==pos["start"] and e["role"] not in pos["roles"]]
        need(len(off)==1,"UNIQUE_OFFROLE_SWAP_DONOR")
        target_hop=(len(route)//2 if family=="near_break" else len(route)-2)
        target_edge=route[target_hop]
        if family=="near_break":
            # One-bit hard negative source token, genuine 15/16 similarity.
            one_bit=list(target_edge["src_bits"])
            one_bit[(seed//3)%16]^=1
            off[0]["src_bits"]=one_bit
        neg={key:(json.loads(json.dumps(val)) if key=="edges" else list(val)
                 if key=="roles" else val) for key,val in pos.items()}
        matching=[edge for edge in neg["edges"] if edge==target_edge]
        donor=[edge for edge in neg["edges"]
               if edge["from"]==pos["start"] and edge["role"] not in pos["roles"]]
        need(len(matching)==1 and len(donor)==1 and matching[0] is not donor[0],
             "NEGATIVE_SWAP_DEGENERATE")
        matching[0]["src_bits"],donor[0]["src_bits"]=(
              donor[0]["src_bits"],matching[0]["src_bits"])
    paired_admit(pos,neg)
    need(len(pos["roles"]) in (10,11,12),"LONG_DEPTH_EXPECTED")
    return pos,neg

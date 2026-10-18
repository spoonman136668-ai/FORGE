"""F124-U fresh independent identity-disjoint public composition source: DEVELOPMENT ONLY.

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
PROTOCOL = ROOT / "reference/research-intake/f124u-microindex-causal-rank-freeze.json"
PROTOCOL_BLOB = "3f7150378a3b7e86006534843d4f1f41f6e783ef"
COHORTS = {
    "Wingless": {"FIT": range(880000, 880024), "DEV": range(880100, 880124)},
    "Yggdrasil": {"FIT": range(890000, 890024), "DEV": range(890100, 890124)},
}
VECTORS = ((2, 1, 1), (1, 2, 1))
FORBIDDEN = {
    "Wingless": range(180100, 180148),
    "Yggdrasil": range(190100, 190148),
}
GRAPH_KEYS = {"start", "target", "roles", "edges"}
EDGE_KEYS = {"from", "to", "role", "src_bits", "dst_bits"}


class Quarantined(ValueError):
    pass


def need(ok, code):
    if not ok:
        raise Quarantined("F124U_" + code)


def git_blob(raw):
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def frozen():
    raw=PROTOCOL.read_bytes().replace(b"\r\n",b"\n")
    need(git_blob(raw)==PROTOCOL_BLOB,"F124U_FROZEN_BLOB_DRIFT")
    p=json.loads(raw)
    need(p["schema"]=="forge.research.f124u.frozen-microindex-causal-rank-v1"
         and p["stage"]=="PREIMPLEMENTATION_FROZEN"
         and p["qualified_parent"]["head"]==
             "becf7829c7a5521b234a1c25b659b614570f1af7"
         and p["new_source"]["salt"]==
             "forge/F124U/nonprotected-new-structure/v1/"
         and p["new_source"]["FIT"]==
             {k:[v["FIT"].start,v["FIT"].stop-1] for k,v in COHORTS.items()}
         and p["new_source"]["DEV"]==
             {k:[v["DEV"].start,v["DEV"].stop-1] for k,v in COHORTS.items()}
         and p["new_source"]["vectors"]==[list(v) for v in VECTORS]
         and p["new_source"]["pairs_per_lane_per_cohort"]==48
         and all(x is False for x in p["authority"].values()),
         "FROZEN_PROTOCOL_DRIFT")
    return hashlib.sha256(raw).hexdigest()


def validate_public(g):
    need(type(g) is dict and set(g) == GRAPH_KEYS, "PUBLIC_GRAPH_FIELDS")
    need(type(g["start"]) is str and type(g["target"]) is str
         and g["start"] and g["target"] and g["start"] != g["target"]
         and type(g["roles"]) is list and len(g["roles"]) in (7, 8, 9)
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
    salt = ("forge/F124U/nonprotected-new-structure/v1/" + lane + "/" + phase + "/" +
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
        raise Quarantined("F124U_KEY_EXHAUSTION")
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
    raise Quarantined("F124U_PROTECTED_FIRST_USE_UNAVAILABLE")

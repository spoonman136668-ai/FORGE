"""F123 public synthetic multipath graph constructor and leakage guards.

Environment qualification only. No learned arms, training, confirmation scoring,
scientific first use, acceptance, dispatch, or promotion lives in this module.
Every model observation is a complete unordered graph with salted raw tokens:
no engineered route, equality feature, counterfactual coordinate, or label.
"""
from __future__ import annotations
from collections import Counter
import hashlib
import json
from pathlib import Path
import random

ROOT = Path(__file__).resolve().parents[1]
FREEZE = ROOT / "reference/research-intake/f123-learned-multipath-routing-freeze.json"
FREEZE_BLOB = "9663e453051642bd798f9647df9993c3470c8672"
SCHEMA = "forge.autonomy.f123.frozen-learned-multipath-routing-development.v1"
PARENT = "2e183a5c8d5df68f644a4a06f0ef689b88c9e223"
COHORTS = {
    "Wingless": {"TRAIN": range(96000, 96024), "CONFIRM": range(96100, 96148)},
    "Yggdrasil": {"TRAIN": range(97000, 97024), "CONFIRM": range(97100, 97148)},
}
FIELDS = {"start", "target", "roles", "edges"}
EDGE_FIELDS = {"from", "to", "role", "src_bits", "dst_bits"}

class Invalid(ValueError):
    pass

def require(condition, code):
    if not condition:
        raise Invalid("F123_" + code)

def frozen():
    raw = FREEZE.read_bytes().replace(b"\r\n", b"\n")
    blob = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
    require(blob == FREEZE_BLOB, "FROZEN_BLOB_DRIFT")
    p = json.loads(raw)
    c = p["cohorts"]
    require(p["schema"] == SCHEMA and p["parent_f122_head"] == PARENT
            and p["status"] == "PREIMPLEMENTATION_FREEZE"
            and c["training_epochs"] == 100
            and c["trainable_parameter_max"] == 768
            and c["train_pairs_per_candidate"] == 24
            and c["confirmation_pairs_per_candidate"] == 48
            and c["candidates_per_lane"] == 2
            and c["training_pair_seeds"] ==
            {"Wingless": [96000, 96023], "Yggdrasil": [97000, 97023]}
            and c["confirmation_pair_seeds"] ==
            {"Wingless": [96100, 96147], "Yggdrasil": [97100, 97147]}
            and all(p["authority"].values()), "CONTRACT_DRIFT")
    return hashlib.sha256(raw).hexdigest()

def validate_observation(o):
    require(type(o) is dict and set(o) == FIELDS, "PRIVILEGED_OR_MISSING_GRAPH_FIELD")
    require(type(o["start"]) is str and type(o["target"]) is str
            and o["start"] != o["target"]
            and type(o["roles"]) is list and 2 <= len(o["roles"]) <= 6
            and all(type(r) is str and r for r in o["roles"])
            and type(o["edges"]) is list and 2 <= len(o["edges"]) <= 128,
            "INVALID_PUBLIC_GRAPH")
    for edge in o["edges"]:
        require(type(edge) is dict and set(edge) == EDGE_FIELDS,
                "PRIVILEGED_OR_MISSING_EDGE_FIELD")
        require(all(type(edge[k]) is str and edge[k] for k in ("from", "to", "role")),
                "INVALID_EDGE_IDENTITY")
        for k in ("src_bits", "dst_bits"):
            require(type(edge[k]) is list and len(edge[k]) == 16
                    and all(type(v) is int and v in (0, 1) for v in edge[k]),
                    "INVALID_RAW_TOKEN")

def symbolic_routes(observation, role_only=False):
    """Independent reference traversal over model-visible fields only."""
    validate_observation(observation)
    states = [(observation["start"], None)]
    for role in observation["roles"]:
        successors = []
        for node, value in states:
            for edge in observation["edges"]:
                if edge["from"] != node or edge["role"] != role:
                    continue
                if not role_only and value is not None and value != edge["src_bits"]:
                    continue
                successors.append((edge["to"], edge["dst_bits"]))
        states = successors
    return sum(node == observation["target"] for node, _ in states)

def build(seed, vector, lane, phase):
    require(lane in COHORTS and phase in ("TRAIN", "CONFIRM")
            and type(seed) is int and seed in COHORTS[lane][phase]
            and type(vector) is list and len(vector) == 3
            and all(type(v) is int and 0 <= v <= 3 for v in vector),
            "SOURCE_NOT_FROZEN")
    rng = random.Random(seed * 4099 + vector[0] * 101 + vector[1] * 23 + vector[2])
    hops = (2 if seed % 2 == 0 else 3) if phase == "TRAIN" else (5 if seed % 2 == 0 else 6)
    paths = 2 if phase == "TRAIN" else 3 + (vector[1] % 2)
    context = f"f123/{lane}/{phase}/{seed}/{','.join(map(str, vector))}/"
    def opaque(kind):
        return hashlib.sha256((context + kind).encode()).hexdigest()[:20]
    source, target = opaque("begin"), opaque("end")
    roles = [opaque(f"role-{i}") for i in range(hops)]
    route_nodes = [[source] + [opaque(f"route-{p}-depth-{i}") for i in range(1, hops)] + [target]
                   for p in range(paths)]
    # Actual shared-prefix and shared-suffix branch collisions, never route labels.
    route_nodes[1][1] = route_nodes[0][1]
    if paths > 2:
        route_nodes[2][-2] = route_nodes[0][-2]
    used_values = set()
    def unique():
        while True:
            val = rng.randrange(1000, 65000)
            if val not in used_values:
                used_values.add(val)
                return val
    primary_values = [unique() for _ in range(hops + 1)]
    primary = [(route_nodes[0][i], route_nodes[0][i + 1], roles[i],
                primary_values[i], primary_values[i + 1]) for i in range(hops)]
    positive = list(primary)
    for p in range(1, paths):
        for i in range(hops):
            # Shared actual edge, not a duplicate that announces the right route.
            if (p == 1 and i == 0) or (p == 2 and i == hops - 1):
                continue
            positive.append((route_nodes[p][i], route_nodes[p][i + 1], roles[i],
                             unique(), unique()))
    # Wrong-role decoys provide the controlled off-route counterfactual slot.
    decoy_index = len(positive)
    positive.append((source, opaque("junk-middle"), opaque("junk-role"), unique(), unique()))
    # Repeated aliases in off-route distractors must not trivially mark a label.
    alias = primary_values[0]
    positive.append((opaque("junk-middle"), opaque("junk-end"), opaque("junk-role-2"),
                     alias, unique()))
    intervention = max(1, hops // 2)
    negative = list(positive)
    source_edge = list(negative[intervention])
    off_edge = list(negative[decoy_index])
    source_edge[3], off_edge[3] = off_edge[3], source_edge[3]
    negative[intervention], negative[decoy_index] = tuple(source_edge), tuple(off_edge)
    rng.shuffle(positive)
    rng.shuffle(negative)
    def parity(edges):
        return (Counter(e[:3] for e in edges), Counter(v for e in edges for v in e[3:]))
    require(parity(positive) == parity(negative), "COUNTERFACTUAL_MARGINAL_DRIFT")
    # Salt is selected from public joint token vocabulary, never based on label.
    values = sorted({v for es in (positive, negative) for e in es for v in e[3:]})
    lookup = None
    for retry in range(64):
        salt = context + f"raw-salt/{retry}"
        proposed = {}
        for val in values:
            digest = hashlib.sha256((salt + "/" + str(val)).encode()).digest()
            token = int.from_bytes(digest[:2], "big")
            proposed[val] = [(token >> bit) & 1 for bit in range(16)]
        if len({tuple(x) for x in proposed.values()}) == len(values):
            lookup = proposed
            break
    require(lookup is not None, "RAW_TOKEN_COLLISION_QUARANTINE")
    def observe(edges):
        o = {"start": source, "target": target, "roles": list(roles),
             "edges": [{"from": e[0], "to": e[1], "role": e[2],
                        "src_bits": lookup[e[3]], "dst_bits": lookup[e[4]]} for e in edges]}
        validate_observation(o)
        return o
    pair = (observe(positive), observe(negative))
    admit(*pair, required_routes=paths)
    return pair

def admit(positive, negative, required_routes=2):
    validate_observation(positive)
    validate_observation(negative)
    def parity(o):
        return (Counter((e["from"], e["to"], e["role"]) for e in o["edges"]),
                Counter(tuple(v) for e in o["edges"] for v in (e["src_bits"], e["dst_bits"])))
    require(positive["start"] == negative["start"]
            and positive["target"] == negative["target"]
            and positive["roles"] == negative["roles"]
            and parity(positive) == parity(negative), "PAIR_PUBLIC_INFORMATION_DRIFT")
    require(symbolic_routes(positive, role_only=True) >= required_routes
            and symbolic_routes(negative, role_only=True) >= required_routes,
            "INSUFFICIENT_COMPETING_PATHS")
    require(symbolic_routes(positive) == 1 and symbolic_routes(negative) == 0,
            "AMBIGUOUS_OR_INCORRECT_TRUTH_QUARANTINED")
    return True

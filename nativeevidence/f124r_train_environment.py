"""F124-R new synthetic TRAIN graph family; never admits protected CONFIRM.

Public observations only. Source labels and the exact symbolic oracle are
construction/admission checks and never model inputs or predictors.
"""
from __future__ import annotations
from collections import Counter
import hashlib
import json
import random

import f124r_freeze_admission as freeze

FIELDS = frozenset(("start", "target", "roles", "edges"))
EDGE_FIELDS = frozenset(("from", "to", "role", "src_bits", "dst_bits"))
TRAIN = {"Wingless": range(98100, 98132), "Yggdrasil": range(99100, 99132)}
MAX_EDGES = 128
BIT_WIDTH = 16
class Invalid(ValueError):
    pass

def require(ok, code):
    if not ok:
        raise Invalid("F124R_" + code)

def validate(obs):
    require(type(obs) is dict and set(obs) == FIELDS,
            "PUBLIC_OBSERVATION_FIELDS")
    require(type(obs["start"]) is str and type(obs["target"]) is str
            and obs["start"] != obs["target"]
            and type(obs["roles"]) is list and 3 <= len(obs["roles"]) <= 4
            and all(type(s) is str and len(s) > 0 for s in obs["roles"])
            and type(obs["edges"]) is list and
            2 <= len(obs["edges"]) <= MAX_EDGES, "PUBLIC_GRAPH_SHAPE")
    for edge in obs["edges"]:
        require(type(edge) is dict and set(edge) == EDGE_FIELDS and
                all(type(edge[k]) is str and edge[k] for k in ("from", "to", "role")) and
                all(type(edge[k]) is list and len(edge[k]) == BIT_WIDTH and
                    all(type(v) is int and v in (0, 1) for v in edge[k])
                    for k in ("src_bits", "dst_bits")),
                "PUBLIC_EDGE_CONTRACT")

def symbolic_count(obs, role_only=False):
    """Independent exact-public-label audit, never passed to learner."""
    validate(obs)
    states = [(obs["start"], None)]
    for role in obs["roles"]:
        successors = []
        for node, last in states:
            for edge in obs["edges"]:
                if edge["from"] != node or edge["role"] != role:
                    continue
                if last is not None and not role_only and last != edge["src_bits"]:
                    continue
                successors.append((edge["to"], edge["dst_bits"]))
                require(len(successors) <= 4096, "ORACLE_STATE_BUDGET")
        states = successors
    return sum(node == obs["target"] for node, _ in states)

def marginals(obs):
    validate(obs)
    return (Counter((e["from"], e["to"], e["role"]) for e in obs["edges"]),
            Counter(tuple(bits) for e in obs["edges"]
                    for bits in (e["src_bits"], e["dst_bits"])))

def pair_admit(positive, negative, paths):
    validate(positive)
    validate(negative)
    require(positive["start"] == negative["start"] and
            positive["target"] == negative["target"] and
            positive["roles"] == negative["roles"] and
            marginals(positive) == marginals(negative),
            "COUNTERFACTUAL_MARGINAL_DRIFT")
    require(symbolic_count(positive, role_only=True) >= paths and
            symbolic_count(negative, role_only=True) >= paths,
            "COMPETING_ROUTES_ABSENT")
    require(symbolic_count(positive) == 1 and symbolic_count(negative) == 0,
            "AMBIGUITY_OR_LABEL_ERROR")
    return True

def build(seed, vector, lane):
    """Construct exactly one paired public TRAIN case; no phase argument."""
    require(lane in TRAIN and type(seed) is int and seed in TRAIN[lane] and
            type(vector) is list and len(vector) == 3 and
            all(type(v) is int and 0 <= v <= 3 for v in vector),
            "SOURCE_OUTSIDE_IMMUTABLE_TRAIN")
    cfg, _ = freeze.frozen()
    require(cfg["cohorts"][lane]["TRAIN"] == [TRAIN[lane].start, TRAIN[lane].stop - 1]
            and cfg["cohorts"]["confirm_is_reserved"] is True and
            cfg["environment"]["train_path_count"] == [4, 6] and
            cfg["environment"]["train_hops"] == [3, 4],
            "FROZEN_ENVIRONMENT_DRIFT")
    context = "F124R/NEW/FAMILY/TRAIN/" + lane + "/" + str(seed) + "/" + str(vector)
    rng = random.Random(int(hashlib.sha256(context.encode()).hexdigest()[:16], 16))
    hops = 3 if seed % 2 == 0 else 4
    path_count = 4 + ((seed + vector[0]) % 3)
    def node(tag):
        return hashlib.sha256((context + "/node/" + tag).encode()).hexdigest()[:24]
    start, target = node("start"), node("target")
    roles = [node("q-role-" + str(i)) for i in range(hops)]
    route_nodes = [[start] + [node("path-" + str(p) + "-level-" + str(i))
                       for i in range(1, hops)] + [target]
                   for p in range(path_count)]
    route_nodes[1][1] = route_nodes[0][1]   # shared-prefix collision
    route_nodes[2][-2] = route_nodes[0][-2]  # shared-suffix collision
    values = set()
    def unique():
        while True:
            x = rng.randrange(4096, 64000)
            if x not in values:
                values.add(x)
                return x
    main_values = [unique() for _ in range(hops + 1)]
    edges = [(route_nodes[0][i], route_nodes[0][i + 1], roles[i],
              main_values[i], main_values[i + 1]) for i in range(hops)]
    for p in range(1, path_count):
        for i in range(hops):
            if (p == 1 and i == 0) or (p == 2 and i == hops - 1):
                continue
            edges.append((route_nodes[p][i], route_nodes[p][i + 1], roles[i],
                          unique(), unique()))
    # Wrong-role decoys balance syntactic information and supply a null slot.
    off = len(edges)
    edges.append((start, node("offpath"), node("off-role"), unique(), unique()))
    edges.append((node("offpath"), node("offpath-2"), node("off-role-2"),
                  main_values[0], unique()))
    edges.append((node("offpath-2"), target, node("off-role-3"), unique(), unique()))
    negative = list(edges)
    intervention = max(1, hops // 2)
    chosen, unused = list(negative[intervention]), list(negative[off])
    chosen[3], unused[3] = unused[3], chosen[3]
    negative[intervention], negative[off] = tuple(chosen), tuple(unused)
    rng.shuffle(edges)
    rng.shuffle(negative)
    assert all(type(e) is tuple for e in edges + negative)
    present_values = sorted({v for row in (edges, negative) for e in row for v in e[3:]})
    tokens = None
    for k in range(128):
        # Graph-local salt; independent of F123's context and seed families.
        salt = context + "/v124r-salt/" + str(k)
        trial = {}
        for val in present_values:
            d = hashlib.sha256((salt + "/" + str(val)).encode()).digest()
            n = int.from_bytes(d[:2], "big")
            trial[val] = [(n >> b) & 1 for b in range(BIT_WIDTH)]
        if len({tuple(x) for x in trial.values()}) == len(trial):
            tokens = trial
            break
    require(tokens is not None, "RAW_16_BIT_COLLISION_QUARANTINE")
    def observation(rows):
        obs = {"start": start, "target": target, "roles": list(roles),
               "edges": [{"from": a, "to": b, "role": r,
                          "src_bits": tokens[x], "dst_bits": tokens[y]}
                         for a, b, r, x, y in rows]}
        validate(obs)
        return obs
    positive, counterfactual = observation(edges), observation(negative)
    pair_admit(positive, counterfactual, path_count)
    return positive, counterfactual

def train_rows(lane, vectors):
    require(lane in TRAIN and type(vectors) is list and len(vectors) == 2
            and vectors[0] != vectors[1], "TRAIN_TWO_DISTINCT_SOURCE_VECTORS")
    all_rows = []
    for v in vectors:
        for seed in TRAIN[lane]:
            p, n = build(seed, v, lane)
            all_rows.extend(((p, 1), (n, 0)))
    require(len(all_rows) == 128, "TRAIN_PAIR_COUNT")
    return all_rows

"""F124-AR prospective source-only TRAIN adapter; DEV must remain inaccessible.

Reuse the immutable F124-AQ first-admitted source construction by exact source
identity. Change only the separately frozen cohort/operator identifiers.
Evaluator/source inverse and partner labels are never inputs to inference.
"""
from __future__ import annotations
from collections import Counter
from pathlib import Path
import json
import types

import f124aq_train_source as parent
import f124w_hop_trace_indexed as witness

FREEZE = Path(__file__).resolve().parents[1] / (
    "reference/research-intake/"
    "f124ar-frozen-meta-relational-and-packed-causality.json"
)
FREEZE_BLOB = "235b8094e8c61222ffea409f2f58fd083eb00c08"
PARENT_BLOB = "7899ce9c63f040823fec73657154e5245feb7899"
PARENT_HEAD = "cb2d4ff16e8054e790a0f1dfb4e558b97ebcb3a1"

COHORTS = {
    "Yggdrasil": {"TRAIN": range(3000000, 3000024),
                   "DEV": range(3000100, 3000124)},
    "Wingless": {"TRAIN": range(3010000, 3010024),
                 "DEV": range(3010100, 3010124)},
}
OPERATORS = {
    "TRAIN": ("affine_AX199", "feistel_K199",
              "affine_AX211", "feistel_K211"),
    "DEV": ("affine_AX223", "feistel_K223",
            "affine_AX227", "feistel_K227"),
}
FAMILIES = parent.FAMILIES
VECTORS = parent.VECTORS

def need(ok, tag):
    parent.need(ok, "F124AR_" + tag)

def frozen():
    parent.frozen()
    need(witness.blob(FREEZE) == FREEZE_BLOB, "ORIGINAL_FREEZE_BLOB")
    need(witness.blob(parent.__file__) == PARENT_BLOB, "ORIGINAL_SOURCE_BLOB")
    data = json.loads(FREEZE.read_text(encoding="utf-8"))
    src = data["new_source"]
    need(data["schema"] ==
         "forge.research.f124ar.frozen-meta-relational-and-packed-causality.v1"
         and data["status"] == "PREIMPLEMENTATION_FROZEN"
         and data["lineage"]["qualified_parent_head"] == PARENT_HEAD,
         "FROZEN_IDENTITY")
    need(src["operators"]["TRAIN"] == list(OPERATORS["TRAIN"]) and
         src["operators"]["DEV"] == list(OPERATORS["DEV"]) and
         all(src["cohorts"][lane] ==
             {phase: [group.start, group.stop - 1]
              for phase, group in COHORTS[lane].items()}
             for lane in COHORTS), "SOURCE_COHORT_DRIFT")
    need(src["pairs_per_split_per_lane"] == 48 and
         src["public_demonstrations"] == 24 and
         src["corrupted_public_output_bits"] == 3 and
         set(OPERATORS["TRAIN"]).isdisjoint(OPERATORS["DEV"]) and
         all(not value for value in
             data["qualification"]["authority"].values()), "SAFETY_CONTRACT")
    for lane in COHORTS:
        need(set(COHORTS[lane]["TRAIN"]).isdisjoint(
             COHORTS[lane]["DEV"]), "NO_SPLIT_REUSE")
    return data

_RELATION_ENV = dict(parent.RELATION.__globals__, OPERATORS=OPERATORS)
_RELATION = types.FunctionType(
    parent.RELATION.__code__, _RELATION_ENV,
    parent.RELATION.__name__, parent.RELATION.__defaults__)
_PLAIN_ENV = dict(parent.PLAIN.__globals__, relation=_RELATION)
_PLAIN = types.FunctionType(
    parent.PLAIN.__code__, _PLAIN_ENV,
    parent.PLAIN.__name__, parent.PLAIN.__defaults__)

def relation(bits, operator, inverse=False):
    return _RELATION(bits, operator, inverse)

def plain(graph, operator, nonce):
    return _PLAIN(graph, operator, nonce)

def build(lane, seed, vector, phase):
    need(phase == "TRAIN" and lane in COHORTS and
         type(seed) is int and seed in COHORTS[lane]["TRAIN"] and
         tuple(vector) in VECTORS, "NO_DEV_FIRST_USE")
    env = dict(parent.build.__globals__)
    env.update(COHORTS=COHORTS, OPERATORS=OPERATORS,
               relation=relation, plain=plain)
    fn = types.FunctionType(
        parent.build.__code__, env,
        parent.build.__name__, parent.build.__defaults__)
    family, operator, nonce, positive, negative, selected = (
        fn(lane, seed, vector, phase)
    )
    demos = positive["demos"]
    need(demos == negative["demos"] and len(demos) == 24 and
         sum(relation(d["input_bits"], operator) != d["output_bits"]
             for d in demos) == 3, "AUTHENTIC_SYMMETRIC_NOISE")
    return family, operator, nonce, positive, negative, selected

def pairs(lane, phase):
    need(lane in COHORTS and phase == "TRAIN",
         "DEV_SOURCE_CONSTRUCTION_FORBIDDEN")
    rows = []
    for vector in VECTORS:
        for seed in COHORTS[lane]["TRAIN"]:
            family, operator, nonce, positive, negative, selected = (
                build(lane, seed, vector, phase)
            )
            rows.append((selected, tuple(vector), family, operator,
                         nonce, positive, negative))
    need(len(rows) == 48 and
         Counter(row[2] for row in rows) ==
         Counter({family: 12 for family in FAMILIES}),
         "FROZEN_TRAIN_FAMILY_DENOMINATOR")
    return rows

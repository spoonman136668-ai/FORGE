"""F124-AX source-only NEW TRAIN cohort. DEV identities are frozen, never built here.

Implements the immutable F124-AO graph birth with newly precommitted source IDs.
Operator names, ground truth and inverses belong only to this source module,
never to any source-blind learner. Exact AX protocol Git blob is pinned.
"""
from __future__ import annotations
import json
import types
from collections import Counter
from pathlib import Path

import f124ao_frozen_source as birth
import f124av_train_source as av
import f124w_hop_trace_indexed as witness

FREEZE = Path(__file__).resolve().parents[1] / "reference/research-intake/f124ax-frozen-equal-information-transfer.json"
FREEZE_BLOB = "9c853649d498af8d264271851417070ab5ee0450"
PARENT_HEAD = "a0173ff8ab3093dbb24d1b517c416c03502570e1"
BIRTH_BLOB = "6c6bd9b685b8ad6b1b3685f95959947c4940f2ff"
TRAIN = range(4500000, 4500024)
RESERVED_DEV = range(4500100, 4500124)
OPERATORS = {
    "TRAIN": ("affine_AX401", "feistel_K401", "affine_AX409", "feistel_K409"),
    "DEV": ("affine_AX419", "feistel_K419", "affine_AX421", "feistel_K421"),
}
VECTORS = av.VECTORS
FAMILIES = av.FAMILIES
COHORTS = {"Yggdrasil": {"TRAIN": TRAIN, "DEV": RESERVED_DEV}}

def need(ok, tag):
    av.need(ok, "AX_" + tag)

def frozen():
    av.frozen()
    need(witness.blob(FREEZE) == FREEZE_BLOB and
         witness.blob(birth.__file__) == BIRTH_BLOB, "IMMUTABLE_FREEZE_AND_SOURCE")
    p = json.loads(FREEZE.read_text(encoding="utf-8"))
    src = p["source"]
    need(p["schema"] == "forge.research.f124ax.equal-information-nonlinear-transfer-prereg.v1"
         and p["status"] == "PREIMPLEMENTATION_FROZEN"
         and p["lineage"]["parent_qualified_head"] == PARENT_HEAD
         and src["TRAIN"] == [TRAIN.start, TRAIN.stop - 1]
         and src["unused_DEV"] == [RESERVED_DEV.start, RESERVED_DEV.stop - 1]
         and src["TRAIN_operators"] == list(OPERATORS["TRAIN"])
         and src["unused_DEV_operators"] == list(OPERATORS["DEV"])
         and src["TRAIN_total_paired"] == 48
         and src["FIT_paired"] == 24
         and src["SCREEN_paired"] == 24
         and src["all_48_public_answers"] == 48
         and src["original_corrupted_outputs"] == 3
         and src["extra_corrupted_outputs"] == 3
         and not src["DEV_constructed"] and not src["DEV_consumed"]
         and all(value is False for value in p["authority"].values()),
         "SOURCE_IDENTITY_OR_AUTHORITY_DRIFT")
    need(set(OPERATORS["TRAIN"]).isdisjoint(OPERATORS["DEV"]) and
         set(TRAIN).isdisjoint(RESERVED_DEV), "TRAIN_DEV_SEPARATION")
    return p

RENV = dict(birth.RELATION.__globals__, OPERATORS=OPERATORS)
RELATION = types.FunctionType(birth.RELATION.__code__, RENV,
                              birth.RELATION.__name__, birth.RELATION.__defaults__)
PENV = dict(birth.PLAIN.__globals__, relation=RELATION)
PLAIN = types.FunctionType(birth.PLAIN.__code__, PENV,
                           birth.PLAIN.__name__, birth.PLAIN.__defaults__)

def relation(bits, op, inverse=False):
    return RELATION(bits, op, inverse)

def plain(graph, op, nonce):
    return PLAIN(graph, op, nonce)

def build_train(seed, vector):
    need(type(seed) is int and seed in TRAIN and tuple(vector) in VECTORS,
         "NO_DEV_BIRTH")
    env = dict(birth.build.__globals__)
    env.update(COHORTS=COHORTS, OPERATORS=OPERATORS, relation=relation, plain=plain)
    fn = types.FunctionType(birth.build.__code__, env,
                            birth.build.__name__, birth.build.__defaults__)
    family, op, nonce, pos, neg, _ = fn("Yggdrasil", seed, vector, "TRAIN")
    need(pos["demos"] == neg["demos"] and len(pos["demos"]) == 24 and
         sum(relation(row["input_bits"], op) != row["output_bits"]
             for row in pos["demos"]) == 3,
         "EXACT_PAIRED_PUBLIC_NOISE")
    return family, op, nonce, pos, neg

def train_rows(stage):
    frozen()
    need(stage in ("FIT", "SCREEN"), "TRAIN_STAGE_ONLY")
    seeds = range(TRAIN.start, TRAIN.start+12) if stage == "FIT" else range(TRAIN.start+12, TRAIN.stop)
    rows = []
    for vector in VECTORS:
        for seed in seeds:
            family, op, nonce, pos, neg = build_train(seed, vector)
            rows.append((seed, tuple(vector), family, op, nonce, pos, neg))
    need(len(rows) == 24 and
         Counter(row[2] for row in rows) == Counter({f: 6 for f in FAMILIES}),
         "FROZEN_FOUR_FAMILIES_PER_SPLIT")
    return rows

def public_48(seed, vector, op, condition, original):
    need(seed in TRAIN and tuple(vector) in VECTORS and
         op in OPERATORS["TRAIN"] and
         condition in ("balanced_basis48", "random48"),
         "NEW_TRAIN_PUBLIC_ONLY")
    env = dict(av.active_public_demos.__globals__)
    env.update(COHORTS=COHORTS, relation=relation)
    fn = types.FunctionType(av.active_public_demos.__code__, env,
                            av.active_public_demos.__name__,
                            av.active_public_demos.__defaults__)
    result = fn(seed, vector, op, condition, original)
    need(len(result) == 48 and
         sum(relation(row["input_bits"], op) != row["output_bits"]
             for row in result) == 6, "EQUAL_PUBLIC_INFORMATION")
    return result

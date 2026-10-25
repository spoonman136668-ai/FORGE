#!/usr/bin/env python3
"""L10-B11 development-only semantic parity, NOT a prospective-source adapter.

Original TextWorld predicate signatures were read from pinned original .twl
files; TextWorld itself is NOT imported or executed. NLTK local installation
is NOT qualified as the pinned GitHub original-owner evaluator.
"""
from __future__ import annotations

from collections import Counter
import re

from nltk.sem import Assignment, Model, Valuation

NAMES = ("Aster", "Boreal", "Cora", "Dana")
RELATIONS = ("located_in", "owns", "parent_of")
ROLE = "L10_SYNTHETIC_DEV"
SOURCE_STATUS = "TEXTWORLD_L10_FULL_RELATION_SOURCE_COMPATIBILITY_NO_GO"
PAIR_TYPES = ("o", "r")
POSITIVE_COVERAGE = ("located_in",)
DENOMINATOR = 36


def require(ok: bool, message: str) -> None:
    if not ok:
        raise ValueError("L10_B11_SOURCE_SEMANTICS_DENIED:" + message)


def map_textworld_positive(predicate, args, types):
    """Map only an original typed at(o,r) PUBLIC positive into L10 location.

    in(o,I) means *carried in inventory*, not legal ownership.
    Missing TextWorld facts never imply closed-world L10 negatives.
    """
    require(type(predicate) is str and type(args) is tuple
            and type(types) is tuple and len(args) == len(types) == 2,
            "TW_PUBLIC_TYPED_PREDICATE_SCHEMA")
    require(predicate == "at" and types == PAIR_TYPES, "TW_TO_L10_UNSUPPORTED_MEANING")
    s, o = args
    require(type(s) is str and type(o) is str
            and s in NAMES and o in NAMES and s != o,
            "TW_TO_L10_DEVELOPMENT_PUBLIC_NAMES")
    return (s, "located_in", o, 1)


def source_eligibility():
    return {
        "role": ROLE,
        "supported_positive_relation": "located_in",
        "owns_supported_from_original_TextWorld": False,
        "parent_of_supported_from_original_TextWorld": False,
        "closed_world_negative_claims_from_missing_TextWorld_facts": False,
        "full_L10_source_admission": False,
        "disposition": SOURCE_STATUS,
    }


def _facts(values, label):
    require(type(values) in (tuple, list) and len(values) == DENOMINATOR,
            label + "_DENOMINATOR")
    seen = set()
    out = {}
    for v in values:
        require(type(v) is tuple and len(v) == 4, label + "_FACT_SCHEMA")
        s, r, o, p = v
        require(type(s) is str and type(r) is str and type(o) is str
                and s in NAMES and r in RELATIONS and o in NAMES and o != s
                and type(p) is int and p in (-1, 1),
                label + "_SEMANTIC_TYPE")
        require((s, r, o) not in seen, label + "_DUPLICATE")
        seen.add((s, r, o))
        out[(s, r, o)] = p
    all_facts = {(s, r, o) for s in NAMES for r in RELATIONS
                 for o in NAMES if o != s}
    require(set(out) == all_facts, label + "_ALL_FACTS")
    for s in NAMES:
        for r in RELATIONS:
            require(sum(out[s, r, o] == 1 for o in NAMES if o != s) == 1,
                    label + "_UNIQUE_POSITIVE")
    return out


def check_all_signed_with_nltk(source_truth, proposed):
    """NLTK evaluates EVERY signed fact using the public DEV truth model.

    source_truth must be the independently known OPEN DEVELOPMENT graph, not
    a protected source or future generator. This cannot attest source birth.
    """
    truth = _facts(source_truth, "TRUTH")
    got = _facts(proposed, "PROPOSED")
    individual = {e: e.lower() for e in NAMES}
    valuation = Valuation(
        [(individual[e], e) for e in NAMES] +
        [(r, {(s, o) for (s, rel, o), p in truth.items()
              if rel == r and p == 1}) for r in RELATIONS]
    )
    model = Model(valuation.domain, valuation)
    assignment = Assignment(valuation.domain)
    passed = []
    for (s, relation, o), sign in sorted(got.items()):
        atom = f"{relation}({individual[s]},{individual[o]})"
        formula = atom if sign == 1 else "-" + atom
        result = model.evaluate(formula, assignment)
        require(type(result) is bool, "NLTK_NONBOOLEAN_EVALUATION")
        passed.append(result)
    return {
        "status": "L10_B11_DEVELOPMENT_NLTK_FULL_SIGNED_GRAPH_EXACT"
        if all(passed) else "L10_B11_DEVELOPMENT_NLTK_SEMANTIC_MISMATCH",
        "source_role": ROLE,
        "full_signed_denominator": DENOMINATOR,
        "NLTK_correct_signed_claims": sum(passed),
        "exact": all(passed),
        "original_TextWorld_source_executed": False,
        "pinned_original_NLTK_git_blob_executed": False,
        "independent_owner_scorer_acceptance": False,
        "prospective_examples_consumed": 0,
        "scientific_go": False,
    }


if __name__ == "__main__":
    raise SystemExit("L10_B11_NO_PROSPECTIVE_OR_SOURCE_EXECUTION")

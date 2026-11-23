"""Agent-free, source-only FORGE RSI-R3 custody and two-generation rehearsal.

This module is inert: no runner, checkout, imports of owner code, Git writes,
scientific first-use, or deployment. Its tiny fixed grammar changes the code
of its *own* candidate proposer, rather than only changing policy parameters.
A successful rehearsal is NOT a measured autonomous FORGE RSI improvement.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json

SCHEMA = "forge.f139.rsi-r3.self-source-development.v1"
TARGET = "f139/rsi_r3_source_cycle.py"
# A fixed, reviewable source grammar: candidates cannot supply Python text.
# Each branch is executable Python source, and G1's branch is used to choose G2.
RANK_EXPRESSIONS = (
    "row[0]",                         # Original: maximize apparent correct solutions
    "row[0] - row[1]",                # Resource-adjusted correct solutions
    "row[0] + row[2] - row[1]",       # Robustness-adjusted correct solutions
    "row[0] + row[3] - row[1]",       # Distinct correct solutions
)
SOURCE_TEMPLATE = '''# FORGE_RSI_R3_BOUNDED_GENERATED_SOURCE
# This is untrusted for science or deployment even after compilation.
def rank(row):
    return {expression}

def propose(training_rows):
    return max(training_rows, key=lambda entry: (rank(entry[1]), -entry[0]))[0]
'''
SEED_OPERATOR = 0
MAX_GENERATIONS = 2


class R3Denied(ValueError):
    pass


def require(ok: bool, reason: str) -> None:
    if not ok:
        raise R3Denied("FORGE_RSI_R3_" + reason)


def fingerprint(value: bytes) -> str:
    return sha256(value).hexdigest()


def source_for(operator: int) -> bytes:
    require(type(operator) is int and 0 <= operator < len(RANK_EXPRESSIONS),
            "OPERATOR_NOT_IN_FROZEN_GRAMMAR")
    return SOURCE_TEMPLATE.format(expression=RANK_EXPRESSIONS[operator]).encode("ascii")


def _operator_for(source: bytes) -> int:
    require(type(source) is bytes and len(source) < 2048, "UNTRUSTED_PARENT_SOURCE")
    matches = [i for i in range(len(RANK_EXPRESSIONS)) if source == source_for(i)]
    require(len(matches) == 1, "UNREGISTERED_OR_TAMPERED_SOURCE")
    return matches[0]


def _validate_feedback(rows, exclude: frozenset[int]) -> tuple:
    require(type(rows) in (list, tuple) and len(rows) > 0, "FEEDBACK_MISSING")
    checked, seen = [], set()
    for entry in rows:
        require(type(entry) in (tuple, list) and len(entry) == 2,
                "FEEDBACK_ROW_SHAPE")
        operation, metrics = entry
        require(type(operation) is int and operation in range(len(RANK_EXPRESSIONS))
                and operation not in seen and operation not in exclude,
                "FEEDBACK_OPERATOR_IDENTITY")
        require(type(metrics) in (tuple, list) and len(metrics) == 4
                and all(type(x) is int and 0 <= x <= 10000 for x in metrics),
                "FEEDBACK_NONNEGATIVE_BOUNDED_METRICS")
        seen.add(operation)
        checked.append((operation, tuple(metrics)))
    return tuple(sorted(checked))


def _run_verified_parent(source: bytes, training_rows: tuple) -> int:
    """Only the exact finite grammar may be executed in the *test process*.

    No arbitrary source or imports can reach exec, and builtins are limited to
    max. This is a development readout, not a general-purpose Python sandbox.
    """
    _operator_for(source)  # Exact byte equality BEFORE compiling or executing.
    env = {"__builtins__": {"max": max}}
    exec(compile(source, "<f139-rsi-r3-reviewed-grammar>", "exec"), env)
    return env["propose"](training_rows)


@dataclass(frozen=True)
class Generation:
    schema: str
    generation: int
    parent_sha256: str
    source_sha256: str
    operator: int
    feedback_sha256: str
    source: bytes
    parent_source: bytes
    observed_training: tuple


def generate(*, parent_source: bytes, generation: int, feedback,
             used_operators: frozenset[int]) -> Generation:
    require(type(generation) is int and 1 <= generation <= MAX_GENERATIONS,
            "GENERATION_BUDGET")
    parent_operator = _operator_for(parent_source)
    require(type(used_operators) is frozenset
            and all(type(i) is int and i in range(len(RANK_EXPRESSIONS))
                    for i in used_operators)
            and parent_operator in used_operators,
            "PARENT_LINEAGE_UNVERIFIED")
    observations = _validate_feedback(feedback, used_operators)
    selected = _run_verified_parent(parent_source, observations)
    require(selected not in used_operators
            and selected in (r[0] for r in observations), "SELECTOR_INVALID")
    child = source_for(selected)
    require(child != parent_source, "UNCHANGED_SOURCE_REJECTED")
    frozen_bytes = json.dumps(observations, separators=(",", ":"),
                              sort_keys=True).encode("ascii")
    return Generation(SCHEMA, generation, fingerprint(parent_source),
                      fingerprint(child), selected, fingerprint(frozen_bytes),
                      child, parent_source, observations)


def verify(generations: tuple[Generation, ...]) -> bool:
    require(type(generations) is tuple and 1 <= len(generations) <= MAX_GENERATIONS,
            "INVALID_GENERATION_COUNT")
    previous = source_for(SEED_OPERATOR)
    used = frozenset({SEED_OPERATOR})
    for expected, row in enumerate(generations, 1):
        require(type(row) is Generation and row.schema == SCHEMA
                and row.generation == expected
                and row.parent_source == previous
                and row.parent_sha256 == fingerprint(previous)
                and row.source_sha256 == fingerprint(row.source)
                and row.operator not in used,
                "SOURCE_CUSTODY_OR_LINEAGE_DRIFT")
        independent = generate(parent_source=previous, generation=expected,
                               feedback=row.observed_training,
                               used_operators=used)
        require(independent == row, "SOURCE_NOT_GENERATED_BY_PARENT")
        previous, used = row.source, used | {row.operator}
    return True


def rehearsal(g1_training, g2_training) -> tuple[Generation, Generation]:
    """Development-only demonstration of real G0 -> G1 -> G2 source lineage.

    No heldout, speed threshold, independent owner, or qualification is used.
    RSI_PASS cannot be inferred from its successful return value.
    """
    first = generate(parent_source=source_for(SEED_OPERATOR), generation=1,
                     feedback=g1_training, used_operators=frozenset({0}))
    second = generate(parent_source=first.source, generation=2,
                      feedback=g2_training, used_operators=frozenset({0, first.operator}))
    assert verify((first, second))
    return first, second

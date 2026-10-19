"""F124-CM learned quadratic GF(2) online causal-state transition candidate.

ENGINEERING ONLY. A new sequential public FIT/CHECK interface is required;
prior E2/F2 isolated 16-bit transform pairs cannot train this model.
No hidden source, prospective cases, graph oracle or held-out labels are
used by fit. A transition has (event, current, lagged, next), each an
unsigned nibble. 25 transition features are learned from 40 public FIT
transitions; eight separate CHECK transitions are veto only.
No scientific generalization or equal-resource claim.
"""
from __future__ import annotations
from typing import NamedTuple
import hashlib
import json

FIT_COUNT = 40
CHECK_COUNT = 8
STATE_BITS = 4
FEATURE_BITS = 25
COEFFICIENT_BITS = FEATURE_BITS * STATE_BITS
HISTORY_BITS = 2 * STATE_BITS


class OnlineState(NamedTuple):
    current: int
    lagged: int


class LearnedModel(NamedTuple):
    weights: tuple[int, int, int, int]


def require(ok: bool, reason: str) -> None:
    if not ok:
        raise ValueError("F124CM_" + reason)


def nibble(v: int) -> bool:
    return type(v) is int and 0 <= v < 16


def features(event: int, current: int, lagged: int) -> int:
    """25 fixed source-independent nonlinear binary features."""
    require(all(nibble(x) for x in (event, current, lagged)), "NIBBLE")
    a = [(event >> i) & 1 for i in range(4)]
    b = [(current >> i) & 1 for i in range(4)]
    c = [(lagged >> i) & 1 for i in range(4)]
    values = [1] + a + b + c
    values += [a[i] & b[i] for i in range(4)]
    values += [a[i] & c[i] for i in range(4)]
    values += [b[i] & c[i] for i in range(4)]
    require(len(values) == FEATURE_BITS, "FEATURE_CONTRACT")
    return sum(bit << idx for idx, bit in enumerate(values))


def predict(model: LearnedModel, event: int, state: OnlineState) -> OnlineState:
    require(isinstance(model, LearnedModel) and len(model.weights) == 4
            and all(type(w) is int and 0 <= w < (1 << FEATURE_BITS)
                    for w in model.weights), "MODEL_BOUNDED")
    require(isinstance(state, OnlineState) and all(nibble(x) for x in state),
            "STATE_BOUNDED")
    x = features(event, state.current, state.lagged)
    target = sum(((w & x).bit_count() & 1) << bit
                 for bit, w in enumerate(model.weights))
    return OnlineState(target, state.current)


def validate(rows: object, size: int) -> list[tuple[int, int, int, int]]:
    require(type(rows) in (tuple, list) and len(rows) == size,
            "FROZEN_ROW_COUNT")
    require(all(type(r) in (tuple, list) and len(r) == 4
                and all(nibble(v) for v in r) for r in rows),
            "PUBLIC_SEQUENTIAL_TRANSITIONS_ONLY")
    return [tuple(r) for r in rows]


def fit(fit_rows: object, check_rows: object):
    """Learn 25x4 GF(2) map on FIT only; CHECK is veto, not training.

    Full rank and exact public FIT are admission requirements. If a source
    exceeds this representation, retain a negative instead of post-hoc
    parameter adjustment or fitting CHECK.
    """
    fit_data = validate(fit_rows, FIT_COUNT)
    check_data = validate(check_rows, CHECK_COUNT)
    require(len({tuple(row[:3]) for row in fit_data + check_data}) == 48,
            "DUPLICATE_TRANSITION_INPUT")
    pivot: dict[int, tuple[int, int]] = {}
    for event, current, lag, target in fit_data:
        x, y = features(event, current, lag), target
        while x:
            bit = x.bit_length() - 1
            if bit in pivot:
                px, py = pivot[bit]
                x ^= px
                y ^= py
            else:
                pivot[bit] = (x, y)
                break
        if x == 0:
            require(y == 0, "INCONSISTENT_FIT")
    rank = len(pivot)
    full_rank = rank == FEATURE_BITS
    weights = [0, 0, 0, 0]
    if full_rank:
        for col in sorted(pivot):
            x, y = pivot[col]
            for output_bit in range(4):
                residual = (y >> output_bit) & 1
                residual ^= (weights[output_bit] & (x ^ (1 << col))).bit_count() & 1
                weights[output_bit] |= residual << col
    candidate = LearnedModel(tuple(weights)) if full_rank else None
    fit_errors = (sum(predict(candidate, row[0], OnlineState(row[1], row[2])).current
                      != row[3] for row in fit_data) if candidate else None)
    check_errors = (sum(predict(candidate, row[0], OnlineState(row[1], row[2])).current
                        != row[3] for row in check_data) if candidate else None)
    accepted = bool(full_rank and fit_errors == 0 and check_errors == 0)
    return (candidate if accepted else None), {
        "schema": "mass.f124cm.learned-online-causal-state-engineering.v1",
        "FIT_sha256": hashlib.sha256(json.dumps(fit_data,
            separators=(",", ":")).encode()).hexdigest(),
        "fit_only_parameters": True, "CHECK_veto_only": True,
        "FIT_rows": FIT_COUNT, "CHECK_rows": CHECK_COUNT,
        "rank": rank, "identifiable": full_rank,
        "FIT_mismatches": fit_errors, "CHECK_mismatches": check_errors,
        "coefficient_bits": COEFFICIENT_BITS, "online_history_bits": HISTORY_BITS,
        "source_or_oracle_access": False, "prior_E2F2_source_reused": False,
        "scientific_accepted": False, "model_admitted_on_public_check": accepted,
    }


if __name__ == "__main__":
    raise SystemExit("ENGINEERING_ONLY_NO_FIRST_USE")

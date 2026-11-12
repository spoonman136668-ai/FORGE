"""R36/F3 Yggdrasil development-only read-plan candidates.

This is a bounded method layer, not a scientific original or a simulator result.
Only explicitly reserved development seeds may train or be scored here.
"""
from __future__ import annotations
from dataclasses import dataclass
import math

DEV = frozenset(range(67200, 67208))
SEALED = frozenset(range(67240, 67256))
READS = 10
COORDS = 16
METHODS = ("YF3-C1", "YF3-C2", "YF3-C3", "YF3-C4")

@dataclass(frozen=True)
class DevelopmentTrial:
    seed: int
    before: tuple[float, ...]
    previous: tuple[float, ...]
    after: tuple[float, ...]
    onset_coordinate: int

def _validate(trials: tuple[DevelopmentTrial, ...]) -> None:
    if not trials:
        raise ValueError("F3_EMPTY_DEVELOPMENT")
    seen = set()
    for t in trials:
        if type(t.seed) is not int or t.seed not in DEV or t.seed in seen:
            raise ValueError("F3_NON_DEVELOPMENT_OR_DUPLICATE_SEED")
        seen.add(t.seed)
        if type(t.onset_coordinate) is not int or not 0 <= t.onset_coordinate < COORDS:
            raise ValueError("F3_ONSET_LABEL")
        for values in (t.before, t.previous, t.after):
            if len(values) != COORDS or any(type(v) not in (int, float) or not math.isfinite(v) for v in values):
                raise ValueError("F3_INVALID_OBSERVATIONS")

def _rank(scores: list[float]) -> tuple[int, ...]:
    if len(scores) != COORDS or any(not math.isfinite(x) for x in scores):
        raise ValueError("F3_SCORE_DRIFT")
    result = tuple(sorted(range(COORDS), key=lambda i: (-scores[i], i))[:READS])
    if len(result) != READS or len(set(result)) != READS:
        raise ValueError("F3_READ_BUDGET")
    return result

def fit_candidate(method: str, trials: tuple[DevelopmentTrial, ...]) -> tuple[int, ...]:
    """Returns an immutable ten-coordinate read order; no heldout access or I/O."""
    if method not in METHODS:
        raise ValueError("F3_UNKNOWN_CANDIDATE")
    _validate(trials)
    n = len(trials)
    label = [sum(t.onset_coordinate == i for t in trials) / n for i in range(COORDS)]
    change = [sum(abs(t.after[i] - t.before[i]) for t in trials) / n for i in range(COORDS)]
    trend = [sum(abs(t.before[i] - t.previous[i]) for t in trials) / n for i in range(COORDS)]
    if method == "YF3-C1":
        # Train-only observed detection frequency: learned fixed permutation.
        scores = label
    elif method == "YF3-C2":
        # Retained-state trend changes prioritize coordinates before onset.
        scores = [label[i] + trend[i] for i in range(COORDS)]
    elif method == "YF3-C3":
        # Two-step paired change-point evidence; no new public reads.
        scores = [label[i] + max(0.0, change[i] - trend[i]) for i in range(COORDS)]
    else:
        # Sparsity-aware fixed-quota read allocation.
        scores = [label[i] + change[i] / (1.0 + trend[i]) for i in range(COORDS)]
    return _rank(scores)

def development_detection_misses(plan: tuple[int, ...], trials: tuple[DevelopmentTrial, ...]) -> int:
    """Illustrative development proxy, NOT a scientific onset-mismatch metric."""
    _validate(trials)
    if len(plan) != READS or len(set(plan)) != READS or any(type(i) is not int or not 0 <= i < COORDS for i in plan):
        raise ValueError("F3_PLAN_BUDGET_OR_DRIFT")
    return sum(t.onset_coordinate not in plan for t in trials)

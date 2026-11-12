"""ACC-98 equal-information adaptive counting control, development only.

EMA rates are the frozen ACC-94 grid. No source rule ID, switch cue, protected
TEST cohort, per-step evaluator truth, or hidden lattice state enters this learner.
"""
from __future__ import annotations
import hashlib
import json
from switching import SCHEMA, TOTAL_STEPS, PRE_STEPS, ADAPT_STEPS

RATES = (0.02, 0.1, 0.3, 0.7)
CONTROL_SCHEMA = "forge.acc98.u24.ewma-control.v1"

def _index(bits):
    if len(bits) != 3 or any(type(bit) is not int or bit not in (0, 1) for bit in bits):
        raise ValueError("INVALID_NEIGHBORHOOD")
    return (bits[0] << 2) | (bits[1] << 1) | bits[2]

class EWMATable:
    def __init__(self, rate):
        if type(rate) is not float or rate not in RATES:
            raise ValueError("RATE_OUTSIDE_FROZEN_GRID")
        self.rate = rate
        self.means = [0.5] * 8
        self.counts = [0] * 8

    def predict(self, bits):
        return int(self.means[_index(bits)] > 0.5)

    def observe(self, visible):
        for bits, target in visible:
            if type(target) is not int or target not in (0, 1):
                raise ValueError("INVALID_TARGET")
            i = _index(bits)
            self.means[i] = (1.0 - self.rate) * self.means[i] + self.rate * target
            self.counts[i] += 1

    def snapshot(self):
        return json.dumps({"rate": self.rate, "means": self.means, "counts": self.counts},
                          allow_nan=False, sort_keys=True, separators=(",", ":"))

    @classmethod
    def restore(cls, encoded):
        obj = json.loads(encoded)
        if set(obj) != {"rate", "means", "counts"}:
            raise ValueError("INVALID_STATE")
        state = cls(obj["rate"])
        means, counts = obj["means"], obj["counts"]
        if (not isinstance(means, list) or len(means) != 8 or
            any(type(m) is not float or not 0 <= m <= 1 for m in means) or
            not isinstance(counts, list) or len(counts) != 8 or
            any(type(n) is not int or n < 0 for n in counts)):
            raise ValueError("INVALID_STATE")
        state.means, state.counts = means, counts
        return state

def evaluate_ewma(trace, rate):
    if (trace.get("schema") != SCHEMA or trace.get("split") not in ("FIT", "DEV") or
        trace.get("reserved_test_used") is not False or
        len(trace.get("records", [])) != TOTAL_STEPS):
        raise ValueError("UNQUALIFIED_TRACE")
    model = EWMATable(rate)
    correct, total = [0, 0, 0], [0, 0, 0]
    restored = False
    for step, row in enumerate(trace["records"]):
        if row.get("step") != step:
            raise ValueError("TRACE_ORDER_DRIFT")
        phase = 0 if step < PRE_STEPS else (1 if step < PRE_STEPS + ADAPT_STEPS else 2)
        for bits, target in row["queries"]:
            correct[phase] += model.predict(bits) == target
            total[phase] += 1
        model.observe(row["visible"])
        if step == PRE_STEPS + ADAPT_STEPS - 1:
            before = model.snapshot()
            model = EWMATable.restore(before)
            restored = model.snapshot() == before
    return {"schema": CONTROL_SCHEMA, "rate": rate, "phase_accuracy":
            [a / b for a, b in zip(correct, total)], "phase_queries": total,
            "adapt_error": total[1] - correct[1],
            "cold_restore_exact": restored,
            "state_sha256": hashlib.sha256(model.snapshot().encode()).hexdigest(),
            "scientific_acceptance": "NOT_GRANTED", "resources_qualified": False}

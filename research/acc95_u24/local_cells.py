"""ACC-99 bounded local-plasticity candidate; source-free FIT/DEV only.

Eight independent neighborhood cells update from their own observations.
There is no rule identity, switch signal, global gradient, pooling or oracle.
This is an intentionally narrow mechanistic candidate, NOT an implementation
or qualification of native Yggdrasil and not a claim of advantage.
"""
from __future__ import annotations
import hashlib
import json
from switching import SCHEMA, TOTAL_STEPS, PRE_STEPS, ADAPT_STEPS
from ewma import RATES

MODEL_SCHEMA = "forge.acc99.u24.independent-local-cells.v1"

def neighborhood_index(bits):
    if (not isinstance(bits, (list, tuple)) or len(bits) != 3 or
        any(type(x) is not int or x not in (0, 1) for x in bits)):
        raise ValueError("INVALID_NEIGHBORHOOD")
    return (bits[0] << 2) | (bits[1] << 1) | bits[2]

class LocalCells:
    """No cross-cell communication; nonlinear bounded eligibility memory."""
    def __init__(self, rate=0.1):
        if type(rate) is not float or rate not in RATES:
            raise ValueError("RATE_OUTSIDE_FROZEN_GRID")
        self.rate = rate
        self.state = [0.0] * 8
        self.count = [0] * 8

    def predict(self, bits):
        return int(self.state[neighborhood_index(bits)] > 0.0)

    def observe(self, visible):
        for bits, target in visible:
            if type(target) is not int or target not in (0, 1):
                raise ValueError("INVALID_TARGET")
            i = neighborhood_index(bits)
            # A bounded leaky local plasticity update; each cell sees its own
            # input/target and state only. This is not a novel neural learner.
            self.state[i] = (1.0 - self.rate) * self.state[i] + self.rate * (2 * target - 1)
            self.count[i] += 1

    def snapshot(self):
        return json.dumps({"schema": MODEL_SCHEMA, "rate": self.rate,
                           "state": self.state, "count": self.count},
                          sort_keys=True, separators=(",", ":"), allow_nan=False)

    @classmethod
    def restore(cls, encoded):
        obj = json.loads(encoded)
        if not isinstance(obj, dict) or set(obj) != {"schema", "rate", "state", "count"} or obj["schema"] != MODEL_SCHEMA:
            raise ValueError("INVALID_SNAPSHOT")
        model = cls(obj["rate"])
        states, counts = obj["state"], obj["count"]
        if (not isinstance(states, list) or len(states) != 8 or
            any(type(v) is not float or not -1.0 <= v <= 1.0 for v in states) or
            not isinstance(counts, list) or len(counts) != 8 or
            any(type(v) is not int or v < 0 for v in counts)):
            raise ValueError("INVALID_SNAPSHOT")
        model.state, model.count = states, counts
        return model

def evaluate_local(trace, *, rate=0.1):
    if (not isinstance(trace, dict) or trace.get("schema") != SCHEMA or
        trace.get("split") not in ("FIT", "DEV") or
        trace.get("reserved_test_used") is not False or
        len(trace.get("records", [])) != TOTAL_STEPS):
        raise ValueError("UNQUALIFIED_TRACE")
    model = LocalCells(rate)
    correct, total = [0, 0, 0], [0, 0, 0]
    restored = False
    for step, row in enumerate(trace["records"]):
        if row.get("step") != step:
            raise ValueError("TRACE_ORDER_DRIFT")
        phase = 0 if step < PRE_STEPS else (1 if step < PRE_STEPS + ADAPT_STEPS else 2)
        # Never expose a query label to learning.
        for bits, target in row["queries"]:
            correct[phase] += model.predict(bits) == target
            total[phase] += 1
        model.observe(row["visible"])
        if step == PRE_STEPS + ADAPT_STEPS - 1:
            snapshot = model.snapshot()
            model = LocalCells.restore(snapshot)
            restored = model.snapshot() == snapshot
    return {"schema": MODEL_SCHEMA, "rate": rate,
            "phase_accuracy": [a / b for a, b in zip(correct, total)],
            "phase_queries": total, "adapt_error": total[1] - correct[1],
            "cold_restore_exact": restored,
            "state_sha256": hashlib.sha256(model.snapshot().encode()).hexdigest(),
            "no_communication": True, "resources_qualified": False,
            "scientific_acceptance": "NOT_GRANTED",
            "limitation": "Mathematically affine to eight-cell EWMA; not independent evidence of superiority."}

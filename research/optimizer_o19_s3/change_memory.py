"""O19-S3: source-only, public-sensor two-timescale occupancy memory.

No MiniGrid imports; does not identify walls/balls. An observed occupancy flip
establishes change, not a globally learned law or source-private truth.
"""
from __future__ import annotations
from dataclasses import dataclass
import hashlib
import json
import math

SCHEMA = "optimizer.o19-s3.public-front-change-memory.v1"
MAX_CELLS = 64


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def _cell(coord):
    if (type(coord) is not tuple or len(coord) != 2 or
        any(type(v) is not int or not 0 <= v < 256 for v in coord)):
        raise ValueError("O19_PUBLIC_COORDINATE_INVALID")
    return f"{coord[0]},{coord[1]}"


def _tick(t):
    if type(t) is not int or not 0 <= t <= 1000000:
        raise ValueError("O19_PUBLIC_TICK_INVALID")


@dataclass
class Cell:
    slow: float
    fast: float
    last_tick: int
    last_value: bool
    observations: int
    observed_flips: int


class TwoTimescaleMemory:
    """Hand-specified, outcome-updated slow/fast LOCAL state. Not native Ygg R3.

    The estimator predicts a subsequent direct-front sensor observation. A
    legal action veto is deliberately IDENTICAL to the conventional guard.
    """
    def __init__(self, capacity=MAX_CELLS):
        if type(capacity) is not int or not 1 <= capacity <= MAX_CELLS:
            raise ValueError("O19_CAPACITY_INVALID")
        self.capacity = capacity
        self.cells: dict[str, Cell] = {}
        self.last_tick = -1
        self.predict_calls = 0
        self.update_calls = 0

    def predict(self, t, coord):
        _tick(t)
        key = _cell(coord)
        c = self.cells.get(key)
        if c is None:
            self.predict_calls += 1
            return 0.5
        if t <= c.last_tick:
            raise ValueError("O19_NONFUTURE_PREDICTION")
        self.predict_calls += 1
        gap = t - c.last_tick
        # Recent evidence decays rapidly once observed occupancy has flipped;
        # accumulated slow evidence is retained separately but never treated
        # as proof of permanent geometry.
        decay = 0.58 if c.observed_flips else 0.22
        fast = c.fast * math.exp(-decay * (gap - 1))
        return max(0.01, min(0.99, 0.5 + 0.46 * (0.42 * c.slow + 0.58 * fast)))

    def observe(self, t, coord, blocked):
        """Record a CURRENT public FrontBlocked; no hidden grid or oracle.

        Fail closed without partial state mutation on invalid time/value/capacity.
        """
        _tick(t)
        key = _cell(coord)
        if type(blocked) is not bool:
            raise ValueError("O19_FRONT_SENSOR_NOT_BOOLEAN")
        if t <= self.last_tick:
            raise ValueError("O19_NONMONOTONIC_PUBLIC_CLOCK")
        if key not in self.cells and len(self.cells) >= self.capacity:
            raise ValueError("O19_MEMORY_CAPACITY_REACHED")
        value = 1.0 if blocked else -1.0
        prev = self.cells.get(key)
        if prev is None:
            self.cells[key] = Cell(.08 * value, .75 * value, t, blocked, 1, 0)
        else:
            flips = prev.observed_flips + int(prev.last_value != blocked)
            self.cells[key] = Cell(
                .92 * prev.slow + .08 * value,
                .25 * prev.fast + .75 * value,
                t, blocked, prev.observations + 1, flips)
        self.last_tick = t
        self.update_calls += 1

    def change_status(self, coord):
        key = _cell(coord)
        c = self.cells.get(key)
        if c is None:
            return "UNOBSERVED"
        return "OBSERVED_VARIABLE_OCCUPANCY" if c.observed_flips else "STATIC_OR_UNOBSERVED_CHANGE_UNIDENTIFIABLE"

    @staticmethod
    def guarded_action(proposed, current_front_blocked):
        if type(proposed) is not int or proposed not in (0, 1, 2):
            raise ValueError("O19_ACTION_INVALID")
        if type(current_front_blocked) is not bool:
            raise ValueError("O19_GUARD_SENSOR_INVALID")
        return 0 if proposed == 2 and current_front_blocked else proposed

    def snapshot(self):
        payload = {"schema": SCHEMA, "capacity": self.capacity,
                   "last_tick": self.last_tick,
                   "cells": {k: vars(c) for k, c in sorted(self.cells.items())},
                   "predict_calls": self.predict_calls,
                   "update_calls": self.update_calls}
        raw = canonical(payload)
        return canonical({"payload": payload, "sha256": hashlib.sha256(raw).hexdigest()})

    @classmethod
    def restore(cls, data):
        if type(data) is not bytes or not 0 < len(data) < 40000:
            raise ValueError("O19_CHECKPOINT_SIZE_OR_TYPE_INVALID")
        try:
            envelope = json.loads(data)
            if type(envelope) is not dict or set(envelope) != {"payload", "sha256"}:
                raise ValueError("O19_CHECKPOINT_SCHEMA")
            p = envelope["payload"]
            if (type(p) is not dict or
                set(p) != {"schema", "capacity", "last_tick", "cells", "predict_calls", "update_calls"} or
                p["schema"] != SCHEMA or
                hashlib.sha256(canonical(p)).hexdigest() != envelope["sha256"]):
                raise ValueError("O19_CHECKPOINT_INTEGRITY")
            q = cls(p["capacity"])
            _tick(p["last_tick"]) if p["last_tick"] != -1 else None
            if any(type(p[n]) is not int or p[n] < 0 for n in ("predict_calls", "update_calls")):
                raise ValueError("O19_CHECKPOINT_COUNTERS")
            q.last_tick = p["last_tick"]
            q.predict_calls = p["predict_calls"]
            q.update_calls = p["update_calls"]
            if type(p["cells"]) is not dict or len(p["cells"]) > q.capacity:
                raise ValueError("O19_CHECKPOINT_CAPACITY")
            max_seen = -1
            for key, value in p["cells"].items():
                s = key.split(",")
                if len(s) != 2 or any(not z.isascii() or not z.isdigit() for z in s):
                    raise ValueError("O19_CHECKPOINT_CELL_KEY")
                if _cell((int(s[0]), int(s[1]))) != key:
                    raise ValueError("O19_CHECKPOINT_CELL_KEY_NONCANONICAL")
                if type(value) is not dict or set(value) != set(Cell.__dataclass_fields__):
                    raise ValueError("O19_CHECKPOINT_CELL_SCHEMA")
                c = Cell(**value)
                if (type(c.last_tick) is not int or not 0 <= c.last_tick <= q.last_tick or
                    type(c.last_value) is not bool or
                    type(c.observations) is not int or c.observations < 1 or
                    type(c.observed_flips) is not int or not 0 <= c.observed_flips < c.observations or
                    any(type(v) not in (int, float) or not math.isfinite(v) or abs(v) > 1
                        for v in (c.slow, c.fast))):
                    raise ValueError("O19_CHECKPOINT_CELL_STATE")
                q.cells[key] = c
                max_seen = max(max_seen, c.last_tick)
            if (max_seen != q.last_tick or q.update_calls < len(q.cells) or
                (not q.cells and q.last_tick != -1)):
                raise ValueError("O19_CHECKPOINT_TIME_INVARIANT")
            return q
        except (ValueError, TypeError, KeyError, OverflowError, AttributeError) as exc:
            raise ValueError("O19_CHECKPOINT_INVALID") from exc

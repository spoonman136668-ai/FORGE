"""Optimizer O2: bounded public-only learned retention / replay diagnostics.

The selected replay policy is HAND-DESIGNED. Fast and slow predictive values
ARE learned from public observed outcomes. No simulation, scientific cohort
birth, FSA admission, hidden roles or source selection occurs in this module.
"""
from __future__ import annotations

import hashlib
import json
import math

SCHEMA = "forge.optimizer.o2.replay-public-state.v1"
POLICIES = ("SURPRISE_REPLAY", "FIFO_REPLAY", "FIXED_RANDOM_REPLAY",
            "FULL_HISTORY_COUNTS_DIAGNOSTIC")
CUES = ("u", "v")
MAX_EVENTS = 48
BUFFER_CAP = 12
REPLAY_STEPS = 4


class InvalidPublicExperience(ValueError):
    pass


def require(ok, name):
    if not ok:
        raise InvalidPublicExperience("O2_" + name)


def canonical(obj):
    return json.dumps(obj, allow_nan=False, sort_keys=True,
                      separators=(",", ":"), ensure_ascii=True).encode("ascii")


def _random_key(*values):
    data = ":".join(str(x) for x in (7,) + values).encode("ascii")
    return hashlib.sha256(data).digest()


class PublicLearner:
    """One source-only model with an immutable replay policy and bounded state."""

    def __init__(self, policy):
        require(type(policy) is str and policy in POLICIES, "POLICY")
        self.policy = policy
        self.observations = 0
        self.consolidations = 0
        self.replay_updates = 0
        self.fast = {c: 0.5 for c in CUES}
        self.slow = {c: 0.5 for c in CUES}
        self.counts = {c: [0, 0] for c in CUES}
        self.buffer = []

    def predict(self, cue):
        require(type(cue) is str and cue in CUES, "PREDICT_CUE")
        if self.policy == "FULL_HISTORY_COUNTS_DIAGNOSTIC":
            neg, pos = self.counts[cue]
            return (pos + 1) / (neg + pos + 2)
        return 0.75 * self.slow[cue] + 0.25 * self.fast[cue]

    def _store(self, item):
        if len(self.buffer) < BUFFER_CAP:
            self.buffer.append(item)
            return
        if self.policy == "FIFO_REPLAY":
            self.buffer.pop(0)
            self.buffer.append(item)
        elif self.policy == "FIXED_RANDOM_REPLAY":
            # Deterministic control-only reservoir replacement, not study RNG.
            index = int.from_bytes(
                _random_key("store", self.observations)[:8], "big"
            ) % (self.observations + 1)
            if index < BUFFER_CAP:
                self.buffer[index] = item
        elif self.policy == "SURPRISE_REPLAY":
            lowest = min(range(len(self.buffer)),
                         key=lambda i: (self.buffer[i]["surprise"],
                                        self.buffer[i]["seq"]))
            if item["surprise"] > self.buffer[lowest]["surprise"]:
                self.buffer[lowest] = item

    def observe(self, experience):
        """Every arm receives precisely the same public (cue,outcome) fields."""
        require(type(experience) is dict and
                set(experience) == {"cue", "outcome"}, "PUBLIC_FIELDS")
        cue, outcome = experience["cue"], experience["outcome"]
        require(type(cue) is str and cue in CUES, "PUBLIC_CUE")
        require(type(outcome) is int and outcome in (0, 1),
                "PUBLIC_OUTCOME")
        require(self.observations < MAX_EVENTS, "OBSERVATION_BUDGET")
        before = self.predict(cue)
        if self.policy == "FULL_HISTORY_COUNTS_DIAGNOSTIC":
            self.counts[cue][outcome] += 1
        else:
            self.fast[cue] += 0.5 * (outcome - self.fast[cue])
            self.slow[cue] += 0.1 * (outcome - self.slow[cue])
            self._store({"seq": self.observations,
                         "cue": cue, "outcome": outcome,
                         "surprise": abs(outcome - before)})
        self.observations += 1
        return before

    def consolidate(self):
        """Replay equal numbers of retained public observations for 3 policies."""
        if self.policy == "FULL_HISTORY_COUNTS_DIAGNOSTIC":
            return []
        require(self.observations > 0, "NO_OBSERVATIONS")
        if self.policy == "SURPRISE_REPLAY":
            selected = sorted(self.buffer,
                              key=lambda r: (-r["surprise"], r["seq"]))
        elif self.policy == "FIFO_REPLAY":
            selected = sorted(self.buffer, key=lambda r: r["seq"])
        else:
            selected = sorted(self.buffer,
                              key=lambda r: _random_key(
                                  "replay", self.consolidations, r["seq"]))
        selected = selected[:min(REPLAY_STEPS, len(selected))]
        for event in selected:
            cue, y = event["cue"], event["outcome"]
            self.slow[cue] += 0.1 * (y - self.slow[cue])
        self.replay_updates += len(selected)
        self.consolidations += 1
        return [r["seq"] for r in selected]

    def checkpoint(self):
        state = {
            "schema": SCHEMA, "policy": self.policy,
            "observations": self.observations,
            "consolidations": self.consolidations,
            "replay_updates": self.replay_updates,
            "fast": self.fast, "slow": self.slow, "counts": self.counts,
            "buffer": self.buffer,
        }
        return canonical({"state": state,
                          "sha256": hashlib.sha256(canonical(state)).hexdigest()})

    @classmethod
    def restore(cls, data):
        require(type(data) is bytes and len(data) <= 16384, "CHECKPOINT_SIZE")
        try:
            obj = json.loads(data)
        except (ValueError, UnicodeError) as exc:
            raise InvalidPublicExperience("O2_CHECKPOINT_JSON") from exc
        require(type(obj) is dict and set(obj) == {"state", "sha256"},
                "CHECKPOINT_FIELDS")
        s = obj["state"]
        require(type(s) is dict and set(s) == {
            "schema", "policy", "observations", "consolidations",
            "replay_updates", "fast", "slow", "counts", "buffer",
        }, "STATE_FIELDS")
        require(s["schema"] == SCHEMA and type(obj["sha256"]) is str and
                hashlib.sha256(canonical(s)).hexdigest() == obj["sha256"],
                "CHECKPOINT_IDENTITY")
        r = cls(s["policy"])
        for name in ("observations", "consolidations", "replay_updates"):
            v = s[name]
            require(type(v) is int and v >= 0, "CHECKPOINT_COUNTER")
            setattr(r, name, v)
        require(r.observations <= MAX_EVENTS and
                r.consolidations <= MAX_EVENTS and
                r.replay_updates <= r.consolidations * REPLAY_STEPS,
                "CHECKPOINT_BUDGET")
        for field in ("fast", "slow"):
            v = s[field]
            require(type(v) is dict and set(v) == set(CUES) and
                    all(type(a) in (float, int) and math.isfinite(a)
                        and 0.0 <= a <= 1.0 for a in v.values()),
                    "CHECKPOINT_PREDICTOR")
            setattr(r, field, v)
        c = s["counts"]
        require(type(c) is dict and set(c) == set(CUES) and
                all(type(v) is list and len(v) == 2 and
                    all(type(a) is int and 0 <= a <= r.observations for a in v)
                    for v in c.values()), "CHECKPOINT_COUNTS")
        r.counts = c
        if r.policy == "FULL_HISTORY_COUNTS_DIAGNOSTIC":
            require(sum(sum(v) for v in c.values()) == r.observations and
                    s["buffer"] == [] and r.replay_updates == 0 and
                    r.consolidations == 0, "BASELINE_STATE_COHERENCE")
        else:
            require(all(sum(v) == 0 for v in c.values()),
                    "LEARNED_COUNTS_FORBIDDEN")
        rows = s["buffer"]
        require(type(rows) is list and len(rows) <= BUFFER_CAP,
                "CHECKPOINT_BUFFER")
        seen = set()
        for item in rows:
            require(type(item) is dict and set(item) ==
                    {"seq", "cue", "outcome", "surprise"}, "CHECKPOINT_ROW")
            t = item["seq"]
            require(type(t) is int and 0 <= t < r.observations and
                    t not in seen, "CHECKPOINT_ROW_SEQUENCE")
            seen.add(t)
            require(type(item["cue"]) is str and item["cue"] in CUES and
                    type(item["outcome"]) is int and item["outcome"] in (0, 1)
                    and type(item["surprise"]) in (int, float)
                    and math.isfinite(item["surprise"])
                    and 0 <= item["surprise"] <= 1,
                    "CHECKPOINT_ROW_PUBLIC")
        r.buffer = rows
        return r


def public_nll(outcome, prediction):
    require(type(outcome) is int and outcome in (0, 1),
            "EVAL_OUTCOME")
    require(type(prediction) in (float, int) and
            math.isfinite(prediction) and 0 <= prediction <= 1,
            "EVAL_PREDICTION")
    p = min(1 - 1e-12, max(1e-12, prediction))
    return -math.log(p if outcome == 1 else 1-p)

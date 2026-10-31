"""ACC-95 source-free FIT/DEV harness; does not run reserved TEST or claim science."""
from __future__ import annotations
import hashlib
import json
import random
from dataclasses import dataclass

FIT_RULES = (90, 110, 30, 184)
DEV_RULES = (54, 150)
FIT_SEEDS = (601, 607, 613, 617)
DEV_SEEDS = (701, 709)
ALLOWED = {"FIT": (FIT_RULES, FIT_SEEDS), "DEV": (DEV_RULES, DEV_SEEDS)}
DOMAIN = b"forge.acc95.u24.sourcefree.v1"
SCHEMA = "forge.acc95.u24.fitdev.v1"

def seed_for(split: str, rule: int, seed: int, episode: int) -> int:
    if split not in ALLOWED or rule not in ALLOWED[split][0] or seed not in ALLOWED[split][1]:
        raise ValueError("RESERVED_OR_UNKNOWN_SOURCE_BLOCKED")
    if episode not in (0, 1):
        raise ValueError("EPISODE_NOT_FROZEN")
    payload = DOMAIN + b"|" + f"{split}:{rule}:{seed}:{episode}".encode("ascii")
    return int.from_bytes(hashlib.sha256(payload).digest(), "big")

def next_bit(rule: int, l: int, c: int, r: int) -> int:
    if not (0 <= rule <= 255 and l in (0, 1) and c in (0, 1) and r in (0, 1)):
        raise ValueError("INVALID_NEIGHBORHOOD")
    return (rule >> ((l << 2) | (c << 1) | r)) & 1

def transitions(split: str, rule: int, seed: int, *, width: int, episode: int = 0,
                steps: int = 128) -> dict:
    if width not in (25, 63, 127) or steps not in (64, 128):
        raise ValueError("PROTOCOL_DRIFT")
    rng = random.Random(seed_for(split, rule, seed, episode))
    cells = [rng.randrange(2) for _ in range(width)]
    records = []
    for step in range(steps):
        before = [(cells[(i-1) % width], cells[i], cells[(i+1) % width]) for i in range(width)]
        following = [next_bit(rule, *x) for x in before]
        # Sampling is independent of learner predictions; exactly 25% rounded down.
        visible = sorted(rng.sample(range(width), width // 4))
        records.append({"step": step,
                        "visible": [(before[i], following[i]) for i in visible],
                        "queries": [(before[i], following[i]) for i in range(width) if i not in visible]})
        cells = following
    return {"split": split, "width": width, "steps": steps, "records": records,
            "trace_sha256": hashlib.sha256(json.dumps(records, sort_keys=True,
                separators=(",", ":")).encode()).hexdigest()}

@dataclass
class CountTable:
    positive: list
    negative: list

    @classmethod
    def fresh(cls):
        return cls([0] * 8, [0] * 8)

    def observe(self, observations):
        for neighborhood, target in observations:
            idx = (neighborhood[0] << 2) | (neighborhood[1] << 1) | neighborhood[2]
            self.positive[idx] += target
            self.negative[idx] += 1 - target

    def predict(self, neighborhood):
        idx = (neighborhood[0] << 2) | (neighborhood[1] << 1) | neighborhood[2]
        return int(self.positive[idx] > self.negative[idx])

    def snapshot(self):
        return json.dumps({"positive": self.positive, "negative": self.negative},
                          sort_keys=True, separators=(",", ":"))

    @classmethod
    def restore(cls, payload):
        obj = json.loads(payload)
        if set(obj) != {"positive", "negative"}:
            raise ValueError("INVALID_SNAPSHOT")
        arrays = [obj["positive"], obj["negative"]]
        if any(not isinstance(a, list) or len(a) != 8 or
               any(type(v) is not int or v < 0 for v in a) for a in arrays):
            raise ValueError("INVALID_SNAPSHOT")
        return cls(*arrays)

def baseline_screen(split: str, rule: int, seed: int, *, width: int = 25):
    """Non-admission engineering diagnostic; no reserved TEST rules or observations."""
    trace = transitions(split, rule, seed, width=width)
    table = CountTable.fresh()
    correct, total = 0, 0
    for record in trace["records"]:
        # Predict only held-out cells, before consuming the current step's visible labels.
        for neighborhood, target in record["queries"]:
            correct += table.predict(neighborhood) == target
            total += 1
        table.observe(record["visible"])
    return {"schema": SCHEMA, "split": split, "source_sha256": trace["trace_sha256"],
            "accuracy": correct / total, "queries": total, "table_state": table.snapshot(),
            "science_accepted": False, "test_split_accessed": False,
            "resources_qualified": False, "classification": "DEVELOPMENT_DIAGNOSTIC_ONLY"}

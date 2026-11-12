"""ITD-01/O1 public-intervention causal state: SOURCE-ONLY HANDWRITTEN TOYS.

This learns signed direct links from paired, externally supplied public observations.
Composition is a disclosed generic graph search, not a learned reasoning operator.
No simulator, seed generator, cohort access, hidden-state input or science dispatcher.
"""
from __future__ import annotations

import hashlib
import json
import re
from collections import deque

SCHEMA = "forge.optimizer.itd01-o1.public-causal-memory.v1"
ENTITY = re.compile(r"[A-Za-z][A-Za-z0-9_-]{0,31}\Z")
MIN_SUPPORT = 2
MAX_ENTITIES = 8
MAX_TRIALS = 48


class Refused(ValueError):
    pass


def require(condition: bool, reason: str) -> None:
    if not condition:
        raise Refused("ITD01_O1_" + reason)


def canonical(obj: object) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode("ascii")


class CausalMemory:
    """A bounded learner of signed one-step effects from matched public interventions.

    A trial exposes an intervened source and the resulting *public* 0/1 readings
    under treatment and matched control. It cannot inspect a simulator's latent
    causal law; a caller must separately ensure trials really are controlled.
    """

    def __init__(self, entities: tuple[str, ...]):
        require(type(entities) is tuple and 2 <= len(entities) <= MAX_ENTITIES,
                "ENTITY_COUNT")
        require(all(type(x) is str and ENTITY.fullmatch(x) for x in entities)
                and len(set(entities)) == len(entities), "ENTITY_ID")
        self.entities = tuple(sorted(entities))
        self._counts: dict[tuple[str, str], list[int]] = {}
        self.trials = 0

    def _readings(self, readings: dict[str, int]) -> None:
        require(type(readings) is dict and set(readings) == set(self.entities),
                "PUBLIC_READING_KEYS")
        require(all(type(v) is int and v in (0, 1) for v in readings.values()),
                "PUBLIC_READING_VALUES")

    def observe(self, source: str, control: dict[str, int],
                intervention: dict[str, int]) -> None:
        """Consume one matched public intervention/control pair, never a role cohort."""
        require(type(source) is str and source in self.entities, "SOURCE")
        self._readings(control)
        self._readings(intervention)
        require(control[source] == 0 and intervention[source] == 1,
                "INTERVENTION_WAS_NOT_APPLIED")
        require(self.trials < MAX_TRIALS, "TRIAL_BUDGET")
        for target in self.entities:
            if target == source:
                continue
            delta = intervention[target] - control[target]
            pair = (source, target)
            counts = self._counts.setdefault(pair, [0, 0, 0])
            counts[delta + 1] += 1
        self.trials += 1

    def direct_effect(self, source: str, target: str) -> int | None:
        self._query_guard(source, target)
        neg, zero, pos = self._counts.get((source, target), [0, 0, 0])
        if pos >= MIN_SUPPORT and neg == 0:
            return 1
        if neg >= MIN_SUPPORT and pos == 0:
            return -1
        return None

    def _query_guard(self, source: str, target: str) -> None:
        require(type(source) is str and type(target) is str and
                source in self.entities and target in self.entities and
                source != target, "QUERY")

    def compose(self, source: str, target: str, max_hops: int = 2) -> dict | None:
        """Generic, explicitly hand-coded graph composition of *learned* links."""
        self._query_guard(source, target)
        require(type(max_hops) is int and max_hops == 2, "HOP_BUDGET")
        q = deque([(source, (source,), 1)])
        while q:
            node, path, sign = q.popleft()
            if len(path) - 1 >= max_hops:
                continue
            for next_node in self.entities:
                if next_node in path:
                    continue
                edge = self.direct_effect(node, next_node)
                if edge is None:
                    continue
                next_path = path + (next_node,)
                next_sign = sign * edge
                if next_node == target:
                    return {"path": list(next_path), "sign": next_sign,
                            "hops": len(next_path) - 1}
                q.append((next_node, next_path, next_sign))
        return None

    def checkpoint(self) -> bytes:
        """Canonical content-checked public-evidence persistence; not trusted signature."""
        state = {"schema": SCHEMA, "entities": list(self.entities),
                 "trials": self.trials,
                 "counts": [{"source": s, "target": t, "hist": list(hist)}
                            for (s, t), hist in sorted(self._counts.items())]}
        digest = hashlib.sha256(canonical(state)).hexdigest()
        return canonical({"state": state, "sha256": digest})

    @classmethod
    def restore(cls, data: bytes) -> "CausalMemory":
        require(type(data) is bytes and len(data) <= 16384,
                "CHECKPOINT_SIZE")
        try:
            payload = json.loads(data)
        except (TypeError, ValueError, UnicodeError) as exc:
            raise Refused("ITD01_O1_CHECKPOINT_ENCODING") from exc
        require(type(payload) is dict and set(payload) == {"state", "sha256"},
                "CHECKPOINT_FIELDS")
        state, checksum = payload["state"], payload["sha256"]
        require(type(state) is dict and set(state) ==
                {"schema", "entities", "trials", "counts"}, "STATE_FIELDS")
        require(type(checksum) is str and
                checksum == hashlib.sha256(canonical(state)).hexdigest(),
                "CHECKPOINT_HASH")
        require(state["schema"] == SCHEMA and type(state["entities"]) is list,
                "STATE_SCHEMA")
        result = cls(tuple(state["entities"]))
        require(list(result.entities) == state["entities"], "ENTITY_ORDER")
        require(type(state["trials"]) is int and
                0 <= state["trials"] <= MAX_TRIALS, "RESTORED_BUDGET")
        rows = state["counts"]
        require(type(rows) is list and len(rows) <= MAX_ENTITIES * (MAX_ENTITIES - 1),
                "COUNT_ROWS")
        for row in rows:
            require(type(row) is dict and set(row) == {"source", "target", "hist"},
                    "COUNT_ROW_FIELDS")
            s, t, hist = row["source"], row["target"], row["hist"]
            require(type(s) is str and type(t) is str and s in result.entities
                    and t in result.entities and s != t and (s, t) not in result._counts,
                    "COUNT_PAIR")
            require(type(hist) is list and len(hist) == 3 and
                    all(type(v) is int and v >= 0 for v in hist) and
                    sum(hist) > 0 and sum(hist) <= state["trials"],
                    "COUNT_VALUES")
            result._counts[(s, t)] = list(hist)
        require(rows == [{"source": s, "target": t, "hist": list(h)}
                         for (s, t), h in sorted(result._counts.items())],
                "COUNT_ORDER")
        # Every trial updates every off-diagonal target for exactly one source.
        per_source = {s: None for s in result.entities}
        for s in result.entities:
            frequencies = [sum(result._counts.get((s, t), [0, 0, 0]))
                           for t in result.entities if t != s]
            require(len(set(frequencies)) == 1, "COUNT_COHERENCE")
            per_source[s] = frequencies[0]
        require(sum(per_source.values()) == state["trials"], "TRIAL_COHERENCE")
        result.trials = state["trials"]
        return result

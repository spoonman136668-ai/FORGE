"""ITD-01 developer-only, public-action interactive contract.

This is a **transparent, public synthetic fixture**, NOT a protected H1/H2
world or scientific first use. Agents receive ONLY observation dictionaries
through the API. Do not give an agent a reference to the environment object
or load this code into a protected evaluator. No controller/queue/issuer route.
"""
from __future__ import annotations

import hashlib
import json
import random
import re

OBS_SCHEMA = "itd01.observe.v1"
ACTION_SCHEMA = "itd01.act.v1"
STEP_SCHEMA = "itd01.step.v1"
GENESIS = hashlib.sha256(b"ITD01_PUBLIC_DEV_GENESIS_V1").hexdigest()
MAX_OBSERVATION = 16384
MAX_INVESTIGATION = 24
MAX_EXECUTION = 16
MAX_INTERACTIONS = 40
PUBLIC_FAMILIES = ("A_delayed_relay_repair", "B_threshold_resource_flow")
ACTION_KEYS = frozenset(("schema", "verb", "target", "value"))
VALID_VERBS = frozenset(("inspect", "intervene", "wait", "commit"))
DEV_EPISODE = re.compile(r"DEV-[A-Za-z0-9_-]{1,60}\Z")


def canonical(data: object) -> bytes:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
                      allow_nan=False).encode("ascii")


class ContractViolation(ValueError):
    pass


def _need(valid: bool, why: str) -> None:
    if not valid:
        raise ContractViolation("ITD01_" + why)


def action(verb: str, target: str | None = None,
           value: str | None = None) -> dict:
    return {"schema": ACTION_SCHEMA, "verb": verb, "target": target, "value": value}


class PublicDevWorld:
    """Two distinct *public-development* dynamics behind one action interface.

    Hidden causal roles are private Python attributes of this mock evaluator,
    which is why a real agent must be invoked with observation dictionaries
    only. A shared-process Python mock is NOT an isolation/security boundary.
    """

    def __init__(self, family: str, episode_id: str, seed: int):
        _need(family in PUBLIC_FAMILIES, "NONPUBLIC_FAMILY_DENIED")
        _need(isinstance(episode_id, str) and
              DEV_EPISODE.fullmatch(episode_id) is not None,
              "DEV_EPISODE_ID_REQUIRED")
        _need(type(seed) is int and 0 <= seed < 2**31, "SEED_INVALID")
        self._family = family
        self._episode = episode_id
        self._rng = random.Random(seed)
        self._required = frozenset(self._rng.sample(range(4), 2))
        labels = [f"node{n}" for n in range(4)]
        self._rng.shuffle(labels)
        self._labels = tuple(labels)
        self._lookup = {label: i for i, label in enumerate(labels)}
        self._states = [False] * 4
        self._confirmed = [False] * 4
        self._pending: list[tuple[int, int, bool]] = []
        self._tick = 0
        self._turn = 0
        self._investigation = 0
        self._execution = 0
        self._done = False
        self._trace_head = GENESIS
        self._trace_records: list[dict] = []
        self._last_event: list[dict] = []
        self._last_signal: list[dict] = []

    def reset(self) -> dict:
        _need(self._turn == 0 and not getattr(self, "_reset_used", False),
              "RESET_ALREADY_USED")
        self._reset_used = True
        return self._observation()

    def _observation(self) -> dict:
        values = ["activate", "deactivate"] if self._family == PUBLIC_FAMILIES[0] else ["fill", "drain"]
        obs = {
            "schema": OBS_SCHEMA, "episode_id": self._episode, "turn": self._turn,
            "entities": [{"id": name, "legal_values": values} for name in self._labels],
            "observations": list(self._last_signal),
            "delayed_events": list(self._last_event),
            "public_goal": "stabilize relay output" if self._family == PUBLIC_FAMILIES[0]
                           else "sustain balanced resource delivery",
            "interaction_budget_remaining": max(0, MAX_INTERACTIONS - self._turn),
        }
        _need(len(canonical(obs)) <= MAX_OBSERVATION, "OBSERVATION_TOO_LARGE")
        return obs

    def _advance(self) -> None:
        self._tick += 1
        arrived = [(idx, state) for tick, idx, state in self._pending if tick <= self._tick]
        self._pending = [event for event in self._pending if event[0] > self._tick]
        self._last_event = []
        for idx, state in arrived:
            self._confirmed[idx] = state
            self._last_event.append({
                "kind": "relay_settled" if self._family == PUBLIC_FAMILIES[0]
                        else "resource_delivered",
                "entity": self._labels[idx], "status": "settled",
            })

    def _success(self) -> bool:
        return (not self._pending and
                all(self._states[i] and self._confirmed[i] for i in self._required) and
                not any(self._states[i] for i in range(4) if i not in self._required))

    def _validate(self, proposed: object) -> tuple[str, str | None, str | None]:
        _need(type(proposed) is dict and set(proposed) == ACTION_KEYS,
              "ACTION_FIELDS_INVALID")
        _need(proposed["schema"] == ACTION_SCHEMA, "ACTION_SCHEMA_INVALID")
        verb, target, value = proposed["verb"], proposed["target"], proposed["value"]
        _need(type(verb) is str and verb in VALID_VERBS, "ACTION_VERB_INVALID")
        _need(self._turn < MAX_INTERACTIONS or verb == "commit",
              "TURN_BUDGET_EXCEEDED")
        if verb in ("inspect", "wait"):
            _need(self._investigation < MAX_INVESTIGATION,
                  "INVESTIGATION_BUDGET_EXCEEDED")
        if verb == "intervene":
            _need(self._execution < MAX_EXECUTION, "EXECUTION_BUDGET_EXCEEDED")
        if verb in ("wait", "commit"):
            _need(target is None and value is None, "NULL_FIELDS_REQUIRED")
        else:
            _need(type(target) is str and target in self._lookup, "TARGET_INVALID")
            if verb == "inspect":
                _need(value is None, "INSPECTION_VALUE_FORBIDDEN")
            else:
                legal = ("activate", "deactivate") if self._family == PUBLIC_FAMILIES[0] else ("fill", "drain")
                _need(type(value) is str and value in legal, "INTERVENTION_VALUE_INVALID")
        return verb, target, value

    def step(self, proposed: object) -> dict:
        _need(getattr(self, "_reset_used", False), "RESET_REQUIRED")
        _need(not self._done, "ALREADY_TERMINAL_NO_RETRY")
        self._last_signal = []
        self._last_event = []
        violation = False
        try:
            verb, target, value = self._validate(proposed)
        except ContractViolation:
            violation = True
            verb, target, value = "invalid", None, None
        reward = 0
        if violation:
            self._done = True
            self._last_signal = [{"kind": "invalid_action", "status": "rejected"}]
        elif verb == "commit":
            reward = int(self._success())
            self._done = True
        else:
            if verb in ("inspect", "wait"):
                self._investigation += 1
            else:
                self._execution += 1
            if verb == "inspect":
                idx = self._lookup[target]
                positive = idx in self._required
                if self._rng.random() < 0.10:
                    positive = not positive
                self._last_signal = [{"kind": "public_diagnostic",
                                      "entity": target,
                                      "signal": "responsive" if positive else "idle"}]
            elif verb == "intervene":
                idx = self._lookup[target]
                turn_on = value in ("activate", "fill")
                self._states[idx] = turn_on
                lag = 2 if self._family == PUBLIC_FAMILIES[0] else 3
                self._pending.append((self._tick + lag + 1, idx, turn_on))
            self._advance()
        self._turn += 1
        public = self._observation()
        result = {"schema": STEP_SCHEMA, "observation": public,
                  "reward": reward, "done": self._done}
        # Only public bytes are part of this DEV receipt. No hidden-target output.
        # Snapshot public bytes now: caller mutation cannot rewrite custody.
        record = {"action": json.loads(canonical(proposed)) if not violation else "INVALID",
                  "result": json.loads(canonical(result)),
                  "prior_sha256": self._trace_head}
        self._trace_head = hashlib.sha256(canonical(record)).hexdigest()
        self._trace_records.append({"record_sha256": self._trace_head, **record})
        return result

    def public_trace_receipt(self) -> dict:
        """Engineering fixture receipt; no signature, accepted source or science."""
        return {"schema": "itd01.public-dev-trace.v1", "episode_id": self._episode,
                "trace_head_sha256": self._trace_head,
                "steps": self._turn, "done": self._done,
                "scientific_first_use": False, "source_birth_attested": False,
                "authority": "NONE_PUBLIC_DEV_ONLY"}

    def public_trace_records(self) -> list[dict]:
        return json.loads(canonical(self._trace_records))

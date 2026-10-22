"""ITD-01 R3 public-only interactive causal development worlds.

R3 A and B are NEW training/development mock mechanisms, not H1/H2.
Both require discovering upstream causation through interventions,
waiting for delayed consequences, and subsequently controlling a different
downstream entity. Public inspections alone carry NO causal-role answer.
A shared-process Python mock is NOT a secure first-use source custodian.
"""
from __future__ import annotations

import hashlib
import random
from public_dev import (PUBLIC_FAMILIES, ContractViolation, PublicDevWorld,
                        action, canonical, MAX_INTERACTIONS)


class PublicCausalDevWorld(PublicDevWorld):
    """Preserves ITD-01 external action/observation contract, changes dynamics."""

    def __init__(self, family: str, episode_id: str, seed: int):
        super().__init__(family, episode_id, seed)
        self._upstream, self._downstream = self._rng.sample(range(4), 2)
        # Deliberately remove easy direct readout of the relevant pair:
        # public inspections are noisy *device health* observations, not truth.
        self._required = frozenset()
        self._ready = False
        self._reservoir_units = 0
        self._completed = False
        self._target_armed_at_action = False
        self._public_interventions = 0

    def _advance(self) -> None:
        self._tick += 1
        arrived = [(idx, state) for due, idx, state in self._pending if due <= self._tick]
        self._pending = [event for event in self._pending if event[0] > self._tick]
        self._last_event = []
        for idx, state in arrived:
            self._confirmed[idx] = state
            if not state:
                if idx == self._upstream:
                    self._ready = False
                    self._reservoir_units = 0
                    self._completed = False
                if idx == self._downstream:
                    self._completed = False
            elif idx == self._upstream:
                # A: one upstream pulse activates a downstream relay.
                # B: a reservoir needs TWO independently delayed deliveries.
                if self._family == PUBLIC_FAMILIES[0]:
                    self._ready = True
                else:
                    self._reservoir_units += 1
                    self._ready = self._reservoir_units >= 2
                self._last_event.append({
                    "kind": "relay_pulse" if self._family == PUBLIC_FAMILIES[0]
                            else "inflow_arrived",
                    "entity": self._labels[self._downstream],
                    "status": "ready" if self._ready else "partial",
                })
            elif (idx == self._downstream and self._target_armed_at_action
                  and self._ready and self._states[self._upstream]):
                self._completed = True
                self._last_event.append({
                    "kind": "relay_stable" if self._family == PUBLIC_FAMILIES[0]
                            else "reservoir_balanced",
                    "entity": self._labels[self._downstream], "status": "confirmed",
                })

    def _success(self) -> bool:
        return (self._completed and self._ready and
                self._states[self._upstream] and self._states[self._downstream] and
                not any(self._states[i] for i in range(4)
                        if i not in (self._upstream, self._downstream)) and
                not self._pending)

    def step(self, proposed: object) -> dict:
        # Enforcement and immutable public hash-chain remain in the qualified
        # R1 parent. No private metadata are returned or serialized.
        if (type(proposed) is dict and proposed.get("verb") == "intervene"
                and proposed.get("target") == self._labels[self._downstream]):
            # Critical causal ordering: authorization is evaluated when the
            # agent ACTS, not when a previously scheduled consequence arrives.
            self._target_armed_at_action = bool(
                self._ready and self._states[self._upstream] and
                proposed.get("value") in ("activate", "fill"))
        result = super().step(proposed)
        if type(proposed) is dict and proposed.get("verb") == "intervene":
            self._public_interventions += 1
        return result


def solve_from_public_only(world: PublicCausalDevWorld) -> dict:
    """Diagnostic PUBLIC-information oracle; NEVER use world private fields.

    A fixed exhaustive exploration policy: try each publicly listed upstream
    candidate; wait for any delayed downstream causal event; undo candidates
    without effect; follow confirmed causal event. This is an explicit-knowledge
    ceiling/control, never scored as a trained nonprivileged comparator.
    """
    obs = world.reset()
    names = sorted(entity["id"] for entity in obs["entities"])
    put = obs["entities"][0]["legal_values"][0]
    undo = obs["entities"][0]["legal_values"][1]
    if put not in ("activate", "fill") or len(names) != 4:
        raise RuntimeError("ITD01_R3_PUBLIC_ORACLE_BAD_OBSERVATION")
    discovered_downstream = None
    discovered_upstream = None
    for name in names:
        transition = world.step(action("intervene", name, put))
        if transition["done"]:
            return transition
        for _ in range(3):
            transition = world.step(action("wait"))
            candidates = [
                e["entity"] for e in transition["observation"]["delayed_events"]
                if e["kind"] in ("relay_pulse", "inflow_arrived")
            ]
            if candidates:
                discovered_upstream, discovered_downstream = name, candidates[0]
        if discovered_upstream is not None:
            break
        transition = world.step(action("intervene", name, undo))
        if transition["done"]:
            return transition

    if discovered_downstream is None:
        return world.step(action("commit"))
    if discovered_upstream == discovered_downstream:
        raise AssertionError("PUBLIC_CAUSAL_GRAPH_SELF_EDGE")
    if put == "fill":
        # Public feedback on B says first delivery was partial; acquire a
        # second delayed delivery before trying the downstream receiver.
        transition = world.step(action("intervene", discovered_upstream, put))
        for _ in range(3):
            transition = world.step(action("wait"))
        if not any(e["kind"] == "inflow_arrived" and e["status"] == "ready"
                   for e in transition["observation"]["delayed_events"]):
            raise RuntimeError("ITD01_R3_RESOURCE_DELIVERY_NOT_CONFIRMED")
    transition = world.step(action("intervene", discovered_downstream, put))
    for _ in range(3):
        transition = world.step(action("wait"))
    return world.step(action("commit"))


def fixed_public_control(world: PublicCausalDevWorld) -> dict:
    """Prespecified blind fixed two-action control, not learned."""
    obs = world.reset()
    names = sorted(entity["id"] for entity in obs["entities"])
    value = obs["entities"][0]["legal_values"][0]
    for name in names[:2]:
        world.step(action("intervene", name, value))
    for _ in range(3):
        world.step(action("wait"))
    return world.step(action("commit"))


def public_episode_summary(seed: int, family: str, policy: str) -> dict:
    if policy not in ("public_oracle", "fixed"):
        raise ValueError("ITD01_R3_POLICY_UNAUTHORIZED")
    episode = f"DEV-R3-{policy}-{seed}"
    world = PublicCausalDevWorld(family, episode, seed)
    transition = (solve_from_public_only(world) if policy == "public_oracle"
                  else fixed_public_control(world))
    receipt = world.public_trace_receipt()
    if not receipt["done"] or receipt["steps"] > MAX_INTERACTIONS:
        raise AssertionError("ITD01_R3_PUBLIC_BUDGET")
    return {"success": transition["reward"], "steps": receipt["steps"],
            "trace_sha256": receipt["trace_head_sha256"],
            "scientific_first_use": receipt["scientific_first_use"]}


def development_calibration(n: int = 120, seed_start: int = 80000) -> dict:
    """Fresh public DEV-only calibration. Not real held H1/H2 birth."""
    result = {}
    for family_id, family in enumerate(PUBLIC_FAMILIES):
        batch = {}
        for policy in ("public_oracle", "fixed"):
            outcomes = [public_episode_summary(seed_start + family_id * 100000 + i,
                                               family, policy) for i in range(n)]
            batch[policy] = {
                "n": len(outcomes),
                "success_rate": sum(r["success"] for r in outcomes) / n,
                "mean_actions": sum(r["steps"] for r in outcomes) / n,
                "public_receipts_sha256": hashlib.sha256(canonical(outcomes)).hexdigest(),
            }
        result[family] = batch
    return {"schema": "itd01.r3.public-causal-dev-calibration.v1",
            "status": "DEVELOPER_PUBLIC_ONLY_NOT_ITD01_HELD_FIRST_USE",
            "scientific_first_use": False,
            "source_birth_attested": False,
            "family_results": result}

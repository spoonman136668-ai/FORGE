"""Private original Shuttle event producer, NOT an admitted execution lane.

The source owner alone holds the original hidden state, transition/observation
matrices and random generator. Only public observations, actions, observed
rewards, and terminal status can leave the owner. This module deliberately
does not issue its own scientific authority or attest its own receipts.

A real FORGE admission verifier and durable intent/result writer are REQUIRED
before any source-world reset or step. No CLI, no default grants, no fallback.
"""
import hashlib
import json
import math
import random

from shuttle_source_contract import (
    ACTIONS, OBSERVATIONS, SOURCE_GIT_BLOB, parse_original_source,
    PublicEventGuard,
)


class NotAdmitted(RuntimeError):
    pass


def _draw(weights, rng):
    # Exact categorical sampling from upstream parsed probability rows.
    value = rng.random()
    total = 0.0
    for index, probability in enumerate(weights):
        total += probability
        if value < total:
            return index
    # No invalid probabilities survive source-law parsing.
    return len(weights) - 1


class OriginalShuttlePrivateOwner:
    """Owner-private state; NEVER pass this instance to candidate learners.

    The owner must provide an external admission object implementing
    verify_open(metadata) -> grant, and a durable journal implementing
    write_intent(record) / write_terminal(record). The grant must be
    independently authenticated by that external service. This code does
    not implement that service and cannot replace its authority.
    """

    def __init__(self, original_source, *, admission=None, journal=None):
        self._law = parse_original_source(original_source)
        self._admission = admission
        self._journal = journal
        self._state = None
        self._rng = None
        self._grant = None
        self._guard = PublicEventGuard()
        self._step = 0
        self._max_steps = None
        self._open = False
        self._faulted = False

    def _require_external_authority(self):
        if (self._admission is None or self._journal is None or
                not callable(getattr(self._admission, "verify_open", None)) or
                not callable(getattr(self._journal, "write_intent", None)) or
                not callable(getattr(self._journal, "write_terminal", None))):
            raise NotAdmitted("FORGE_INDEPENDENT_ADMISSION_AND_DURABLE_JOURNAL_REQUIRED")
        # IMPORTANT: injected Python objects and a nonempty receipt string are
        # not an authenticated FORGE grant or a durable external witness.
        # FORGE nativefirstuse.AuthorizeLiveOriginal is currently an explicit
        # DENY; fsaintent.Append is in-memory; signed checkpoint is not a
        # first-use permit. Until a separately qualified real FORGE adapter
        # replaces this explicit interlock, NO original RNG may be drawn.
        raise NotAdmitted("FORGE_LIVE_SCIENTIFIC_AUTHORITY_UNPROVISIONED")

    def open(self, *, prereg_id, cohort_id, episode_id, seed, max_steps):
        if self._open or self._faulted:
            raise NotAdmitted("SHUTTLE_OWNER_ALREADY_OPEN_OR_FAULTED")
        self._require_external_authority()
        if (any(type(x) is not str or not x or len(x) > 128
                for x in (prereg_id, cohort_id, episode_id)) or
                type(seed) is not int or not 0 <= seed < 2**64 or
                type(max_steps) is not int or not 1 <= max_steps <= 10000):
            raise ValueError("INVALID_FROZEN_COHORT_OR_BUDGET")
        meta = {"source_git_blob": SOURCE_GIT_BLOB,
                "prereg_id": prereg_id, "cohort_id": cohort_id,
                "episode_id": episode_id, "seed": seed,
                "max_steps": max_steps}
        # Verification MUST be external, independently authenticated, durable,
        # cohort-exclusive and one-shot; local caller assertions are not enough.
        grant = self._admission.verify_open(dict(meta))
        if (type(grant) is not dict or grant.get("source_git_blob") != SOURCE_GIT_BLOB
                or grant.get("prereg_id") != prereg_id
                or grant.get("cohort_id") != cohort_id
                or grant.get("episode_id") != episode_id
                or grant.get("seed") != seed
                or grant.get("max_steps") != max_steps
                or type(grant.get("authority_receipt")) is not str
                or not grant["authority_receipt"]):
            raise NotAdmitted("FORGE_AUTHENTICATED_GRANT_MISMATCH")
        # Durable intent is written BEFORE first source RNG draw.
        # Any write error leaves this owner permanently faulted.
        self._faulted = True
        self._journal.write_intent({
            "kind": "SHUTTLE_OPEN_INTENT", **meta,
            "authority_receipt": grant["authority_receipt"]})
        self._grant = grant
        self._rng = random.Random(seed)
        self._state = _draw(self._law.start, self._rng)
        obs = OBSERVATIONS[_draw(self._law.observation[self._state], self._rng)]
        self._max_steps = max_steps
        self._open = True
        self._step = 0
        self._journal.write_terminal({
            "kind": "SHUTTLE_OPEN_COMMITTED", "episode_id": episode_id,
            "source_git_blob": SOURCE_GIT_BLOB, "initial_public_observation": obs})
        self._guard.begin(obs)
        self._faulted = False
        return obs

    def step(self, action):
        if not self._open or self._faulted or self._grant is None:
            raise NotAdmitted("SHUTTLE_OWNER_NOT_ADMITTED_OR_FAULTED")
        if type(action) is not str or action not in ACTIONS:
            raise ValueError("SHUTTLE_INVALID_PUBLIC_ACTION")
        if self._step >= self._max_steps:
            raise ValueError("SHUTTLE_FROZEN_STEP_BUDGET_EXHAUSTED")
        # Fail closed on uncertain start. Never continue after an indeterminate
        # intent or terminal receipt: a new owner must reconcile externally.
        self._faulted = True
        action_index = ACTIONS.index(action)
        self._journal.write_intent({
            "kind": "SHUTTLE_STEP_INTENT",
            "episode_id": self._grant["episode_id"], "step": self._step,
            "action": action, "source_git_blob": SOURCE_GIT_BLOB})
        successor = _draw(self._law.transition[action_index][self._state], self._rng)
        observation = OBSERVATIONS[_draw(self._law.observation[successor], self._rng)]
        reward = 0
        for a, prior, next_state, amount in self._law.reward_rows:
            if (a, prior, next_state) == (action_index, self._state, successor):
                reward = amount
                break
        terminal = self._step + 1 >= self._max_steps
        # No source-private state, transition probability, RNG state or law
        # enters the public journal result or learner-facing event.
        result = self._guard.accept(
            action=action, next_observation=observation,
            reward=reward, terminal=terminal)
        self._journal.write_terminal({
            "kind": "SHUTTLE_STEP_COMMITTED",
            "episode_id": self._grant["episode_id"],
            "step": self._step, "source_git_blob": SOURCE_GIT_BLOB,
            **result})
        self._state = successor
        self._step += 1
        self._open = not terminal
        if not terminal:
            self._guard.begin(observation)
        self._faulted = False
        return result

    def public_metadata(self):
        return {"source_git_blob": SOURCE_GIT_BLOB,
                "open": self._open, "steps": self._step,
                "admitted": self._grant is not None,
                "faulted": self._faulted}


"""FORGE-owned original Shuttle source identity and public-event contract.

Source-only engineering: this module does NOT instantiate or step the original
POMDP, expose a hidden-state oracle to a learner, or authorize scientific first use.
The private parsed law stays on the FORGE side; the public wire carries only
observations, selected actions, actual owner-supplied rewards, and terminal flags.
"""
from dataclasses import dataclass
import hashlib
import math
import re

UPSTREAM_REPO = "mhahsler/pomdp"
UPSTREAM_COMMIT = "05db0c69396128e6960f54d41503dca1e90e221c"
UPSTREAM_PATH = "inst/examples/shuttle_95.POMDP"
SOURCE_GIT_BLOB = "fb8612d67e43112e210a252b29b49f8bdba37863"
ACTIONS = ("TurnAround", "GoForward", "Backup")
OBSERVATIONS = ("LRV", "MRV", "docked_MRV", "Nothing", "docked_LRV")
SOURCE_REWARDS = (-3, 0, 10)
MAX_SOURCE_BYTES = 16384


def git_blob_id(raw):
    if type(raw) is not bytes:
        raise ValueError("SOURCE_MUST_BE_BYTES")
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def _vector(line, count):
    parts = line.split()
    if len(parts) != count:
        raise ValueError("SHUTTLE_MATRIX_WIDTH")
    try:
        values = tuple(float(p) for p in parts)
    except ValueError as exc:
        raise ValueError("SHUTTLE_MATRIX_NUMBER") from exc
    if any(not math.isfinite(x) or x < 0 or x > 1 for x in values):
        raise ValueError("SHUTTLE_MATRIX_PROBABILITY")
    if abs(sum(values) - 1) > 1e-12:
        raise ValueError("SHUTTLE_MATRIX_ROW_SUM")
    return values


@dataclass(frozen=True)
class PrivateSourceLaw:
    # Never serialize this object into a candidate-learner public event.
    transition: tuple
    observation: tuple
    start: tuple
    reward_rows: tuple


def parse_original_source(raw, *, expected_blob=SOURCE_GIT_BLOB):
    if type(raw) is not bytes or not 0 < len(raw) <= MAX_SOURCE_BYTES:
        raise ValueError("SHUTTLE_SOURCE_SIZE")
    if type(expected_blob) is not str or not re.fullmatch(r"[0-9a-f]{40}", expected_blob):
        raise ValueError("SHUTTLE_INVALID_EXPECTED_BLOB")
    if git_blob_id(raw) != expected_blob:
        raise ValueError("SHUTTLE_SOURCE_IDENTITY_DRIFT")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("SHUTTLE_SOURCE_ENCODING") from exc
    lines = [line.strip() for line in text.splitlines()
             if line.strip() and not line.lstrip().startswith("#")]
    def header(name):
        found = [line[len(name) + 1:].strip() for line in lines
                 if line.startswith(name + ":")]
        if len(found) != 1:
            raise ValueError("SHUTTLE_HEADER_CARDINALITY_" + name)
        return found[0]
    if header("states").split() != [
            "Docked_LRV", "At_MRV_facing_station", "Space_facing_LRV",
            "At_LRV_back_to_station", "At_MRV_back_to_station",
            "Space_facing_MRV", "At_LRV_facing_station", "Docked_MRV"]:
        raise ValueError("SHUTTLE_STATE_IDENTITY_DRIFT")
    if tuple(header("actions").split()) != ACTIONS:
        raise ValueError("SHUTTLE_ACTION_IDENTITY_DRIFT")
    if tuple(header("observations").split()) != OBSERVATIONS:
        raise ValueError("SHUTTLE_OBSERVATION_IDENTITY_DRIFT")
    if header("values") != "reward" or float(header("discount")) != .95:
        raise ValueError("SHUTTLE_OBJECTIVE_IDENTITY_DRIFT")
    if lines.count("start:") != 1:
        raise ValueError("SHUTTLE_START_CARDINALITY")
    start_index = lines.index("start:")
    start = _vector(lines[start_index + 1], 8)
    if start != (0., 0., 0., 0., 0., 0., 0., 1.):
        raise ValueError("SHUTTLE_START_IDENTITY_DRIFT")
    transitions = []
    for action in ACTIONS:
        key = "T: " + action
        if lines.count(key) != 1:
            raise ValueError("SHUTTLE_TRANSITION_CARDINALITY")
        at = lines.index(key)
        transitions.append(tuple(_vector(row, 8) for row in lines[at + 1:at + 9]))
        if len(transitions[-1]) != 8:
            raise ValueError("SHUTTLE_TRANSITION_HEIGHT")
    if lines.count("O: *") != 1:
        raise ValueError("SHUTTLE_OBSERVATION_CARDINALITY")
    at = lines.index("O: *")
    observation = tuple(_vector(row, 5) for row in lines[at + 1:at + 9])
    if len(observation) != 8:
        raise ValueError("SHUTTLE_OBSERVATION_HEIGHT")
    reward_rows = []
    for line in lines:
        if not line.startswith("R:"):
            continue
        match = re.fullmatch(
            r"R:\s+(TurnAround|GoForward|Backup)\s+:\s+(\d+)\s+:\s+(\d+)\s+:\s+\*\s+(-?\d+)",
            line)
        if not match:
            raise ValueError("SHUTTLE_REWARD_SYNTAX")
        action, state, successor, reward = match.groups()
        reward_rows.append((ACTIONS.index(action), int(state), int(successor), int(reward)))
    # The author's commented alternate reward row is not an active rule.
    if tuple(reward_rows) != ((1, 1, 1, -3), (1, 6, 6, -3), (2, 3, 0, 10)):
        raise ValueError("SHUTTLE_ACTIVE_REWARD_IDENTITY_DRIFT")
    if any(len(t) != 8 for t in transitions):
        raise ValueError("SHUTTLE_TRANSITION_HEIGHT")
    return PrivateSourceLaw(tuple(transitions), observation, start, tuple(reward_rows))


def public_source_receipt(raw):
    """Public metadata only. No hidden states, matrices or reward law."""
    parse_original_source(raw)
    return {"source_git_blob": SOURCE_GIT_BLOB,
            "source_commit": UPSTREAM_COMMIT,
            "public_actions": ACTIONS,
            "public_observations": OBSERVATIONS,
            "source_only": True,
            "original_episodes": 0}


class PublicEventGuard:
    """Strict public event seam; owner must separately attest actual transitions.

    The guard validates public shape and pending custody. It CANNOT authenticate
    that a supplied reward came from an original world. FORGE admission, source
    execution and signed receipts remain separate mandatory responsibilities.
    """
    def __init__(self):
        self.pending = False
        self.transitions = 0
        self._observation = None

    def begin(self, observation):
        if self.pending:
            raise ValueError("SHUTTLE_PUBLIC_PENDING_ACTION")
        if type(observation) is not str or observation not in OBSERVATIONS:
            raise ValueError("SHUTTLE_PUBLIC_INVALID_OBSERVATION")
        self._observation = observation
        self.pending = True

    def accept(self, *, action, next_observation, reward, terminal):
        if not self.pending:
            raise ValueError("SHUTTLE_PUBLIC_NO_PENDING_ACTION")
        if type(action) is not str or action not in ACTIONS:
            raise ValueError("SHUTTLE_PUBLIC_INVALID_ACTION")
        if type(next_observation) is not str or next_observation not in OBSERVATIONS:
            raise ValueError("SHUTTLE_PUBLIC_INVALID_SUCCESSOR")
        if type(reward) is not int or reward not in SOURCE_REWARDS:
            raise ValueError("SHUTTLE_PUBLIC_INVALID_REWARD")
        if type(terminal) is not bool:
            raise ValueError("SHUTTLE_PUBLIC_INVALID_TERMINAL")
        event = {"observation": self._observation, "action": action,
                 "next_observation": next_observation, "reward": reward,
                 "terminal": terminal}
        self.pending = False
        self._observation = None
        self.transitions += 1
        return event

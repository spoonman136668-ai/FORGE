"""O7 prospective public-only, three-family source; no protected roles.

Source law is used to emit public (o_t,a_t,o_{t+1}) only; latent state and
the family/role are NEVER learner features. No O2-O6 role seeds are reused.
"""
from __future__ import annotations
import hashlib
import json
import random

NAMESPACE = "o7-new-public-v1"
FAMILIES = ("A_PUBLIC_FEEDBACK_LATCH", "B_THREE_STATE_ROTATOR",
            "NULL_PUBLIC_IID")
ROLES = ("O7_TRAIN", "O7_SELECT", "O7_DEV")
ROLE_COUNTS = {"O7_TRAIN":96, "O7_SELECT":32, "O7_DEV":48}
STEPS = 32


class PublicSourceRefused(ValueError):
    pass


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=True,
                      allow_nan=False, separators=(",", ":")).encode("ascii")


def seed(role, family, index):
    if not (type(role) is str and role in ROLES and
            type(family) is str and family in FAMILIES and
            type(index) is int and 0 <= index < ROLE_COUNTS[role]):
        raise PublicSourceRefused("O7_PROTECTED_OR_UNREGISTERED_ROLE")
    x = f"{NAMESPACE}:{role}:{family}:{index}".encode("ascii")
    return int.from_bytes(hashlib.sha256(x).digest()[:8], "big")


def episode(role, family, index):
    rng = random.Random(seed(role, family, index))
    if family == "NULL_PUBLIC_IID":
        obs = rng.randrange(2)
        rows = []
        for _ in range(STEPS):
            action, nxt = rng.randrange(2), rng.randrange(2)
            rows.append((obs, action, nxt))
            obs = nxt
        return tuple(rows)

    if family == "A_PUBLIC_FEEDBACK_LATCH":
        hidden = rng.randrange(2)
        previous_action = rng.randrange(2)
        accuracy = 0.88
        def emitted():
            return hidden if rng.random() < accuracy else hidden ^ 1
        obs = emitted()
        rows = []
        for _ in range(STEPS):
            action = rng.randrange(2)
            hidden ^= action & previous_action
            nxt = emitted()
            rows.append((obs, action, nxt))
            obs, previous_action = nxt, action
        return tuple(rows)

    hidden = rng.randrange(3)
    accuracy = 0.88
    def emitted_rotator():
        value = int(hidden == 2)
        return value if rng.random() < accuracy else value ^ 1
    obs = emitted_rotator()
    rows = []
    for _ in range(STEPS):
        action = rng.randrange(2)
        hidden = (hidden + (1 if action == 0 else 2)) % 3
        nxt = emitted_rotator()
        rows.append((obs, action, nxt))
        obs = nxt
    return tuple(rows)


def episodes(role, family):
    if role not in ROLES or family not in FAMILIES:
        raise PublicSourceRefused("O7_PROTECTED_OR_UNREGISTERED_ROLE")
    return tuple(episode(role, family, i) for i in range(ROLE_COUNTS[role]))


def digest(rows):
    return hashlib.sha256(canonical(rows)).hexdigest()


def public_examples(episodes):
    """Deterministic public six-bit history features, no next-bit feature leak."""
    examples = []
    for episode in episodes:
        prev_o, prev_a, older_o, older_a = 0, 0, 0, 0
        for current_o, action, next_o in episode:
            x = (current_o, action, prev_o, prev_a, older_o, older_a)
            examples.append((x, next_o))
            older_o, older_a = prev_o, prev_a
            prev_o, prev_a = current_o, action
    return tuple(examples)

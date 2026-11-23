"""Q21 bounded prequalification seam: source-free experience and public-history controls.

No protected Q20 cohorts or original science are imported. This file is a
source-only candidate, not an authorization to execute Q21 development cohorts.
"""
from __future__ import annotations

import hashlib
import json
import math
import random
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROTOCOL_BLOB = "d7c35c10f80b36a758b78e0deedf36d74bf5767d"
SCHEMA = "forge.nci04.q21.information_budget_prereg.v1"
ROLES = {"FIT_TRAIN", "FIT_VALID", "DEV"}
FAMILIES = ("A_PERSISTENT_ACTION_FLIP", "B_DELAYED_ACTION_CHANGE", "NULL_ACTION_INDEPENDENT")
PUBLIC_EPISODE_FIELDS = ("family", "observations", "actions")
ROLE_COUNTS = {"FIT_TRAIN": 256, "FIT_VALID": 64, "DEV": 128}
SMOOTH = 0.5
EPS = 1e-12


def require(condition: bool, name: str) -> None:
    if not condition:
        raise ValueError("Q21_" + name)


def protocol() -> dict:
    data = (HERE / "FROZEN_PROTOCOL.json").read_bytes()
    actual = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
    require(actual == PROTOCOL_BLOB, "PROTOCOL_GIT_BLOB_IDENTITY_DRIFT")
    doc = json.loads(data)
    require(doc["schema"] == SCHEMA and doc["state"] == "FROZEN_DESIGN_ONLY_NOT_EXECUTED",
            "SCHEMA_OR_FROZEN_STATE_DRIFT")
    require(tuple(x["id"] for x in doc["source_free_families"]) == FAMILIES,
            "FROZEN_FAMILY_ORDER_DRIFT")
    require(doc["role_separation"]["train_episodes_per_family"] == ROLE_COUNTS["FIT_TRAIN"]
            and doc["role_separation"]["fit_validation_episodes_per_family"] == ROLE_COUNTS["FIT_VALID"]
            and doc["role_separation"]["development_episodes_per_family"] == ROLE_COUNTS["DEV"],
            "ROLE_COUNT_DRIFT")
    return doc


def initial_seed(role: str, family: str, index: int) -> int:
    require(role in ROLES, "UNKNOWN_OR_PROTECTED_ROLE")
    require(family in FAMILIES, "UNKNOWN_FAMILY")
    require(type(index) is int and index >= 0 and index < ROLE_COUNTS[role],
            "EPISODE_INDEX_OUTSIDE_FROZEN_ROLE")
    material = "forge-q21-v1:" + role + ":" + family + ":" + str(index)
    return int.from_bytes(hashlib.sha256(material.encode("utf-8")).digest()[:8], "big")


def fraction(value: str) -> float:
    numerator, denominator = value.split("/")
    return int(numerator) / int(denominator)


def public_episode(family: str, observations: list, actions: list) -> tuple:
    require(family in FAMILIES, "FAMILY_NOT_AUTHENTIC")
    require(len(observations) == len(actions) + 1, "ACTION_OBSERVATION_MISMATCH")
    require(all(len(x) == 2 and set(x).issubset({0, 1}) for x in observations),
            "INVALID_PUBLIC_OBSERVATION")
    require(set(actions).issubset({0, 1}), "INVALID_PUBLIC_ACTION")
    return family, tuple(map(tuple, observations)), tuple(actions)


def generate(role: str, family: str, index: int, doc: dict) -> tuple:
    """Explicit development-only operation. Return public data and sealed oracle metadata.

    The caller must supply an admitted Q21 execution environment; tests do
    not invoke this function. No 'held' or 'original' role exists.
    """
    rng = random.Random(initial_seed(role, family, index))
    f = next(x["fixed_generator"] for x in doc["source_free_families"] if x["id"] == family)
    length = f["episode_observations"]
    count = f["actions"]
    require(length == 33 and count == 32, "EPISODE_LENGTH_DRIFT")
    actions = [rng.randrange(2) for _ in range(count)]
    if family == "NULL_ACTION_INDEPENDENT":
        observations = [(rng.randrange(2), rng.randrange(2)) for _ in range(length)]
        secret = {"privileged": True, "family": family, "null": True}
    else:
        slot = rng.randrange(2)
        z = rng.randrange(2)
        noise = fraction(f["noise"])
        obs = []
        for t in range(length):
            observed_z = z ^ int(rng.random() < noise)
            distractor = rng.randrange(2)
            obs.append((observed_z, distractor) if slot == 0 else (distractor, observed_z))
            if t < count:
                a = actions[t]
                if family == "A_PERSISTENT_ACTION_FLIP":
                    pflip = fraction(f["flip_if_a1"] if a else f["flip_if_a0"])
                else:
                    toggle = bool(a and t and actions[t-1])
                    spontaneous = fraction(f["spontaneous_flip"])
                    pflip = (1 - spontaneous) if toggle else spontaneous
                z ^= int(rng.random() < pflip)
        observations = obs
        secret = {"privileged": True, "family": family, "responsive_slot": slot,
                  "initial_latent_private": True}
    return public_episode(family, observations, actions), secret


def public_rows(episodes: list) -> list:
    """Fail closed if private metadata is passed to any empirical learner."""
    rows = []
    for row in episodes:
        require(type(row) is tuple and len(row) == 3, "PRIVATE_FIELDS_IN_EMPIRICAL_ROWS")
        family, obs, actions = row
        rows.append(public_episode(family, obs, actions))
    return rows


def symbol(observation: tuple) -> int:
    return 2 * observation[0] + observation[1]


def context(row: tuple, t: int, history: bool) -> tuple:
    _, observations, actions = row
    require(0 <= t < len(actions), "FUTURE_OR_INVALID_TIME_INDEX")
    base = (symbol(observations[t]), actions[t], actions[t-1] if t else 0)
    if history:
        return base + (symbol(observations[t-1]) if t else 4,)
    return base


def fit_counts(train: list, history: bool) -> dict:
    """Joint categorical empirical estimator fitted on public training data only."""
    tables = {}
    for row in public_rows(train):
        _, obs, actions = row
        for t in range(len(actions)):
            key = context(row, t, history)
            if key not in tables:
                tables[key] = [SMOOTH] * 4
            tables[key][symbol(obs[t+1])] += 1
    return {key: tuple(value / sum(counts) for value in counts)
            for key, counts in tables.items() for value in [counts]}


def forecast_counts(model: dict, row: tuple, history: bool) -> list:
    public_rows([row])
    scores = []
    for t in range(len(row[2])):
        p = model.get(context(row, t, history), (.25,) * 4)
        scores.append((p[2] + p[3], p[1] + p[3]))
    return scores


def _transition(family: str, action: int, previous_action: int, doc: dict) -> float:
    f = next(x["fixed_generator"] for x in doc["source_free_families"] if x["id"] == family)
    if family == FAMILIES[0]:
        return fraction(f["flip_if_a1"] if action else f["flip_if_a0"])
    if family == FAMILIES[1]:
        s = fraction(f["spontaneous_flip"])
        return 1 - s if action and previous_action else s
    require(False, "ORACLE_TRANSITION_FOR_NULL")
    return 0.0


def marginalized_public_oracle(row: tuple, doc: dict) -> list:
    """Privileged true-law benchmark; integrates, rather than reveals, hidden sensor slot.

    This diagnostics-only oracle has access to generator family parameters.
    It is not a fit-trained, equally informed empirical comparator.
    """
    family, observations, actions = public_rows([row])[0]
    if family == FAMILIES[2]:
        return [(.5, .5)] * len(actions)
    f = next(x["fixed_generator"] for x in doc["source_free_families"] if x["id"] == family)
    noise = fraction(f["noise"])

    def emission(slot, latent, observation):
        likelihood = (1 - noise) if observation[slot] == latent else noise
        return likelihood * .5  # other sensor remains an uninformative fair bit

    mass = {(slot, latent): .25 * emission(slot, latent, observations[0])
            for slot in range(2) for latent in range(2)}

    def normalize(m):
        total = sum(m.values())
        require(total > 0, "ORACLE_IMPOSSIBLE_OBSERVATION")
        return {key: val / total for key, val in m.items()}

    mass = normalize(mass)
    result = []
    for t, action in enumerate(actions):
        pflip = _transition(family, action, actions[t-1] if t else 0, doc)
        prior = {}
        for slot in range(2):
            for latent_next in range(2):
                prior[(slot, latent_next)] = sum(
                    mass[(slot, latent)] *
                    ((1 - pflip) if latent_next == latent else pflip)
                    for latent in range(2))
        pair = []
        for sensor in range(2):
            pair.append(sum(prob * ((noise + (1-2*noise) * latent)
                                   if slot == sensor else .5)
                            for (slot, latent), prob in prior.items()))
        result.append(tuple(pair))
        mass = normalize({key: val * emission(key[0], key[1], observations[t+1])
                          for key, val in prior.items()})
    return result


def nll(row: tuple, predictions: list) -> float:
    require(len(predictions) == len(row[2]), "FORECAST_COUNT_DRIFT")
    total = 0.
    for t, pair in enumerate(predictions):
        for j, p in enumerate(pair):
            require(math.isfinite(p) and 0 <= p <= 1, "FORECAST_NONFINITE")
            p = min(1 - EPS, max(EPS, p))
            y = row[1][t+1][j]
            total -= y * math.log(p) + (1-y) * math.log1p(-p)
    return total / (2 * len(predictions))


def preflight() -> dict:
    doc = protocol()
    for name in ("HELD_NEW_SENSOR_FAMILY", "HELD_LONG_HORIZON_TRANSFER", "scientific", "original", "held"):
        try:
            initial_seed(name, FAMILIES[0], 0)
        except ValueError as err:
            require("UNKNOWN_OR_PROTECTED_ROLE" in str(err), "PROTECTED_ROLE_GUARD_DRIFT")
        else:
            raise RuntimeError("Q21_HELD_ORIGINAL_BYPASS")
    # Self-test uses handcrafted PUBLIC observations, not an actual Q21 cohort.
    toy = public_episode(FAMILIES[0], [(0, 0), (0, 1), (1, 1), (1, 0)], [0, 1, 0])
    fit = fit_counts([toy], False)
    hist = fit_counts([toy], True)
    for label, probabilities in (
        ("current", forecast_counts(fit, toy, False)),
        ("history", forecast_counts(hist, toy, True)),
        ("privileged_oracle", marginalized_public_oracle(toy, doc))
    ):
        require(all(0 < p < 1 for pair in probabilities for p in pair),
                "TOY_" + label.upper() + "_FORECAST_INVALID")
        require(math.isfinite(nll(toy, probabilities)), "TOY_NONFINITE_LOSS")
    require(len(toy) == 3, "PUBLIC_SHAPE_DRIFT")
    return {"status": "Q21_SOURCE_ONLY_PREFLIGHT_PASS",
            "sourcefree_q21_development_cohorts_generated": 0,
            "protected_sources_used": False,
            "empirical_controls_present": ["current_public_counts", "history_public_counts"],
            "full_Q21_dev_and_scientific_qualification": "NOT_RUN"}


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["preflight"], required=True)
    args = parser.parse_args()
    if args.mode == "preflight":
        print(json.dumps(preflight(), sort_keys=True))

"""Evidence-Driven Adaptive Blueprint Mutator & Breeder for FORGE F139 (Gate 21).

Takes surviving/winning open-ended architecture & training blueprints, mutates
their numeric, categorical, or structural parameters (and crossbreeds pairs of
winners), avoids repeating any already-tested blueprint SHA-256, and generates
the next wave of experimental configurations deterministically with zero paid
API calls.
"""
from __future__ import annotations

import copy
import random

from f139.nci04_native_contract import canonical, digest

MUTATOR_SCHEMA = "forge.f139.adaptive-blueprint-wave.v1"


class MutatorDenied(ValueError):
    """Fail-closed denial for invalid mutator inputs or search space."""


def need(ok: bool, reason: str) -> None:
    if not ok:
        raise MutatorDenied("F139_MUTATOR_" + reason)


def blueprint_digest(blueprint: dict) -> str:
    """Canonical SHA-256 identity of a blueprint's structural & training config."""
    core = {k: v for k, v in blueprint.items() if k not in ("blueprint_id", "blueprint_sha256", "parent_ids")}
    return digest(canonical(core))


def _mutate_value(val, spec: dict, rng: random.Random):
    kind = spec.get("type")
    if kind == "choice":
        choices = spec["values"]
        need(type(choices) is list and len(choices) >= 1, "EMPTY_CHOICE_SPACE")
        return rng.choice(choices)
    if kind == "float":
        lo, hi = float(spec["min"]), float(spec["max"])
        need(lo < hi, "FLOAT_BOUNDS_INVALID")
        if type(val) in (int, float) and rng.random() < 0.7:
            # Local Gaussian perturbation around surviving value
            span = (hi - lo) * 0.20
            nv = float(val) + rng.gauss(0.0, span)
        else:
            nv = rng.uniform(lo, hi)
        return round(max(lo, min(hi, nv)), 6)
    if kind == "int":
        lo, hi = int(spec["min"]), int(spec["max"])
        need(lo < hi, "INT_BOUNDS_INVALID")
        if type(val) is int and rng.random() < 0.7:
            delta = max(1, (hi - lo) // 5)
            nv = val + rng.randint(-delta, delta)
        else:
            nv = rng.randint(lo, hi)
        return max(lo, min(hi, nv))
    need(False, "UNKNOWN_PARAM_SPACE_TYPE")
    return val


def generate_next_blueprint_wave(
    *,
    parents: list[dict],
    search_space: dict[str, dict],
    wave_size: int = 8,
    seen_digests: set[str] | None = None,
    seed: int = 20261125,
    wave_prefix: str = "wave",
) -> dict:
    """Mutate and crossbreed surviving blueprints into a deduplicated next wave.

    - `parents`: list of surviving blueprint dicts (each containing a `hyperparams`
      dict and/or top-level mutable keys matching `search_space`).
    - `search_space`: open-ended dict mapping parameter names to
      `{"type": "float"|"int", "min": ..., "max": ...}` or
      `{"type": "choice", "values": [...]}`.
    """
    need(type(parents) is list and len(parents) >= 1, "EMPTY_PARENTS")
    need(type(search_space) is dict and len(search_space) >= 1, "EMPTY_SEARCH_SPACE")
    need(type(wave_size) is int and 1 <= wave_size <= 64, "WAVE_SIZE_INVALID")

    rng = random.Random(seed)
    seen = set(seen_digests or set())
    for p in parents:
        seen.add(blueprint_digest(p))

    children: list[dict] = []
    attempts = 0
    max_attempts = wave_size * 25
    keys = sorted(search_space.keys())

    while len(children) < wave_size and attempts < max_attempts:
        attempts += 1
        p1 = rng.choice(parents)
        child = copy.deepcopy(p1)
        parent_ids = [p1.get("blueprint_id", "parent")]

        # Optional crossover with a second surviving parent
        if len(parents) >= 2 and rng.random() < 0.45:
            p2 = rng.choice(parents)
            if p2 is not p1:
                parent_ids.append(p2.get("blueprint_id", "parent2"))
                hp1 = child.setdefault("hyperparams", {})
                hp2 = p2.get("hyperparams", {})
                for k in keys:
                    if k in hp2 and rng.random() < 0.5:
                        hp1[k] = copy.deepcopy(hp2[k])

        # Mutate 1 to 3 parameters from the open search space
        hp = child.setdefault("hyperparams", {})
        n_mut = rng.randint(1, min(3, len(keys)))
        for k in rng.sample(keys, n_mut):
            hp[k] = _mutate_value(hp.get(k), search_space[k], rng)

        b_sha = blueprint_digest(child)
        if b_sha in seen:
            continue
        seen.add(b_sha)
        child["blueprint_id"] = f"{wave_prefix}-{len(children) + 1:02d}-{b_sha[:8]}"
        child["parent_ids"] = parent_ids
        child["blueprint_sha256"] = b_sha
        children.append(child)

    report = {
        "schema": MUTATOR_SCHEMA,
        "wave_prefix": wave_prefix,
        "seed": seed,
        "requested_wave_size": wave_size,
        "generated_count": len(children),
        "blueprints": children,
        "paid_model_calls": 0,
    }
    report["wave_sha256"] = digest(canonical(report))
    return report

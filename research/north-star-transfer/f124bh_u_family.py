"""F124-BH U: independent SPN source grammar, never a model feature.

Source-born *after* immutable BH preregistration. Only the negative synthetic
fixture -940 can be realized. Registered 902000..902127 stay inaccessible.
This module deliberately never imports a candidate, baseline or evaluator.
"""
from __future__ import annotations
import hashlib
import random

FAMILY = "SPN_NIBBLE_COMPOSITION"
FIXTURE_ID = -940
PROSPECTIVE = range(902000, 902128)


def need(ok: bool, code: str) -> None:
    if not ok:
        raise ValueError("F124BH_U_" + code)


def rol16(x: int, n: int) -> int:
    return ((x << n) | (x >> (16 - n))) & 65535


def ror16(x: int, n: int) -> int:
    return ((x >> n) | (x << (16 - n))) & 65535


def rol8(x: int, n: int) -> int:
    return ((x << n) | (x >> (8 - n))) & 255


def _recipe(seed: int):
    need(type(seed) is int and seed == FIXTURE_ID,
         "REGISTERED_FIRST_USE_DENIED")
    entropy = hashlib.sha256(b"F124BH-SPN-UNSEEN-U-SYNTHETIC-FIXTURE-v1").digest()
    rng = random.Random(int.from_bytes(entropy, "big"))
    rounds = []
    for _ in range(4):
        boxes = []
        for __ in range(4):
            p = list(range(16))
            rng.shuffle(p)
            boxes.append(tuple(p))
        places = list(range(4))
        rng.shuffle(places)
        rounds.append((tuple(boxes), tuple(places), rng.randint(1, 7)))
    return tuple(rounds)


def forward(value: int, recipe) -> int:
    need(type(value) is int and 0 <= value <= 65535, "VALUE")
    x = value
    for boxes, positions, spin in recipe:
        nib = [boxes[j][(x >> (4 * j)) & 15] for j in range(4)]
        nib = [nib[j] for j in positions]
        y = sum(v << (4 * j) for j, v in enumerate(nib))
        a, b = y & 255, y >> 8
        x = rol16(((a + rol8(b, 3)) & 255) | (b << 8), spin)
    return x


def inverse(value: int, recipe) -> int:
    need(type(value) is int and 0 <= value <= 65535, "VALUE")
    x = value
    for boxes, positions, spin in reversed(recipe):
        y = ror16(x, spin)
        b = y >> 8
        a = ((y & 255) - rol8(b, 3)) & 255
        nib = [(a | (b << 8)) >> (4 * j) & 15 for j in range(4)]
        restored = [0] * 4
        for dest, src in enumerate(positions):
            restored[src] = nib[dest]
        original = [boxes[j].index(restored[j]) for j in range(4)]
        x = sum(v << (4 * j) for j, v in enumerate(original))
    return x


def fixture(seed: int):
    recipe = _recipe(seed)
    rng = random.Random(int.from_bytes(hashlib.sha256(
        b"F124BH-U-PUBLIC-ONLY-NEGATIVE-940").digest(), "big"))
    ins = rng.sample(range(65536), 48)
    corrupt = set(rng.sample(range(48), 6))
    public = [(x, forward(x, recipe) ^ (1 if i in corrupt else 0))
              for i, x in enumerate(ins)]
    need(len(public) == 48 and len(set(ins)) == 48
         and len(corrupt) == 6, "PUBLIC_40_8_SIX_NOISE")
    return {"FIT": public[:40], "CHECK": public[40:],
            "source_family_sent_to_model": False}, {
                "family_private": FAMILY, "source_recipe_private": recipe,
                "noise_positions_private": tuple(sorted(corrupt))}


def source_birth_descriptor():
    return {"family": FAMILY, "registered_range": [902000, 902127],
            "only_synthetic_fixture": FIXTURE_ID,
            "source_grammar": "4-stage keyed nibble S-box SPN with reversible byte coupling",
            "independent_provenance_witnessed": False,
            "registered_source_generated": 0,
            "scientific_first_use": False}

"""F124-BH R: independent noncommuting reversible causal-word graph source.

No import from U or learned kernel; realization restricted to negative fixture
-939. Registered 903000..903127 remains strictly denied until separately
authenticated first-use authorization. Every edge has a local inverse.
"""
from __future__ import annotations
import hashlib
import random

FAMILY = "NONCOMMUTING_WORD_GRAPH"
FIXTURE_ID = -939
PROSPECTIVE = range(903000, 903128)


def need(ok: bool, code: str) -> None:
    if not ok:
        raise ValueError("F124BH_R_" + code)


def rol16(x: int, n: int) -> int:
    return ((x << n) | (x >> (16 - n))) & 65535


def ror16(x: int, n: int) -> int:
    return ((x >> n) | (x << (16 - n))) & 65535


def rol8(x: int, n: int) -> int:
    return ((x << n) | (x >> (8 - n))) & 255


def _recipe(seed: int):
    need(type(seed) is int and seed == FIXTURE_ID,
         "REGISTERED_FIRST_USE_DENIED")
    entropy = hashlib.sha256(b"F124BH-CAUSAL-WORD-R-INDEPENDENT-FIXTURE-v1").digest()
    rng = random.Random(int.from_bytes(entropy, "big"))
    depth = 6
    # Distinct graph path orders alternate additive carry propagation and XOR
    # feedback, interleaved with independently keyed invertible whole-word maps.
    return tuple((2 * rng.randrange(32768) + 1,
                  rng.randrange(65536), rng.randint(1, 15),
                  rng.randrange(65536), rng.randrange(256),
                  rng.randrange(256), i & 1) for i in range(depth))


def forward(value: int, recipe) -> int:
    need(type(value) is int and 0 <= value <= 65535, "VALUE")
    x = value
    for odd, add, shift, salt, k1, k2, direction in recipe:
        y = rol16((odd * x + add) & 65535, shift) ^ salt
        a, b = y & 255, y >> 8
        if direction == 0:
            a = (a + (rol8(b, 3) ^ k1)) & 255
            b ^= rol8(a, 5) & k2
        else:
            b ^= rol8(a, 5) & k2
            a = (a + (rol8(b, 3) ^ k1)) & 255
        x = a | (b << 8)
    return x


def inverse(value: int, recipe) -> int:
    need(type(value) is int and 0 <= value <= 65535, "VALUE")
    x = value
    for odd, add, shift, salt, k1, k2, direction in reversed(recipe):
        a, b = x & 255, x >> 8
        if direction == 0:
            b ^= rol8(a, 5) & k2
            a = (a - (rol8(b, 3) ^ k1)) & 255
        else:
            a = (a - (rol8(b, 3) ^ k1)) & 255
            b ^= rol8(a, 5) & k2
        y = ror16((a | (b << 8)) ^ salt, shift)
        x = ((y - add) * pow(odd, -1, 65536)) & 65535
    return x


def fixture(seed: int):
    recipe = _recipe(seed)
    rng = random.Random(int.from_bytes(hashlib.sha256(
        b"F124BH-R-PUBLIC-ONLY-NEGATIVE-939").digest(), "big"))
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
    return {"family": FAMILY, "registered_range": [903000, 903127],
            "only_synthetic_fixture": FIXTURE_ID,
            "source_grammar": "6-stage odd-modular affine, rotations, noncommuting causal-byte feedback",
            "independent_provenance_witnessed": False,
            "registered_source_generated": 0,
            "scientific_first_use": False}

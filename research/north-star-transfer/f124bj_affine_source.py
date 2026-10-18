"""F124-BJ independent affine TRAIN source birth; never imports a learner.

Frozen prereg: 900000..900095 only. Synthetic negative -950 exists exclusively
for pre-first-use adversarial checks. No other case can be generated here.
"""
from __future__ import annotations
import hashlib
import random

TRAIN = range(900000, 900096)
SYNTHETIC = -950
SALT = b"BJ-AFFINE-TRAIN-v1"


def make(task):
    if type(task) is not int or (task not in TRAIN and task != SYNTHETIC):
        raise ValueError("BJ_AFFINE_UNREGISTERED_CASE_REFUSED")
    seed = hashlib.sha256(SALT + b":" + str(task).encode("ascii")).digest()
    rng = random.Random(int.from_bytes(seed, "big"))
    multiplier = 2 * rng.randrange(32768) + 1
    offset = rng.randrange(65536)
    ins = rng.sample(range(65536), 48)
    corruption = tuple(sorted(rng.sample(range(48), 6)))
    corruption_set = set(corruption)
    public = [(x, (((multiplier * x + offset) & 65535) ^
                   (1 if idx in corruption_set else 0)))
              for idx, x in enumerate(ins)]
    if len(set(ins)) != 48 or len(corruption) != 6:
        raise RuntimeError("BJ_AFFINE_PUBLIC_IDENTITY")
    # Family tag/true coefficients/corrupt positions never enter learner input.
    return (public[:40], public[40:]), {
        "task_private": task, "operator_private": (multiplier, offset),
        "corruption_private": corruption
    }

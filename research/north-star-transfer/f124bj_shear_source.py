"""F124-BJ independent nonlinear two-shear TRAIN source birth.

Separate public relation grammar from affine source, learned model and U/R.
Preregistered 900096..900191 only; negative fixture -951 allowed for preflight.
"""
from __future__ import annotations
import hashlib
import random

TRAIN = range(900096, 900192)
SYNTHETIC = -951
SALT = b"BJ-SHEAR-TRAIN-v1"


def rol8(x, n):
    return ((x << n) | (x >> (8 - n))) & 255


def shear(x, p, q):
    return (rol8(x, 1) & p) ^ ((rol8(x, 3) & rol8(x, 5)) & q)


def relation(x, params):
    a, b = x & 255, x >> 8
    p, q, r, s = params
    b ^= shear(a, p, q)
    a ^= shear(b, r, s)
    return a | (b << 8)


def make(task):
    if type(task) is not int or (task not in TRAIN and task != SYNTHETIC):
        raise ValueError("BJ_SHEAR_UNREGISTERED_CASE_REFUSED")
    seed = hashlib.sha256(SALT + b":" + str(task).encode("ascii")).digest()
    rng = random.Random(int.from_bytes(seed, "big"))
    params = tuple(rng.randrange(256) for _ in range(4))
    ins = rng.sample(range(65536), 48)
    corruption = tuple(sorted(rng.sample(range(48), 6)))
    corruption_set = set(corruption)
    public = [(x, relation(x, params) ^ (1 if idx in corruption_set else 0))
              for idx, x in enumerate(ins)]
    if len(set(ins)) != 48 or len(corruption) != 6:
        raise RuntimeError("BJ_SHEAR_PUBLIC_IDENTITY")
    return (public[:40], public[40:]), {
        "task_private": task, "operator_private": params,
        "corruption_private": corruption,
    }

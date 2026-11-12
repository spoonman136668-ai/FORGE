"""L1 additive synthetic meaning-to-language PUBLIC source, no science admission.

This module is an *oracle for source creation only*, NOT a permissible learner
feature extractor or inference-time dictionary. Tokens and five semantic field
IDs are PUBLIC training examples; all oracle lexeme arrays must be learned
from L1_FIT_TRAIN tokens. The source's fixed canonical word order is a major
limitation and forbids general-language or cognitive advancement claims.

FIT_TRAIN/SELECT never contain any held-out complete five-field combination.
L1_PUBLIC_DEV_COMPOSE contains ONLY prospectively held-out combinations.
L1_PUBLIC_NULL pairs semantics with deliberately corrupted text; null is a
source-leakage diagnostic and NOT a target for natural-language quality claims.
"""
from __future__ import annotations

import hashlib
import itertools
import json
import random

NAMESPACE = "l1-20261023-additive-meaning-realization-v1"
ROLES = ("L1_FIT_TRAIN", "L1_FIT_SELECT",
         "L1_PUBLIC_DEV_COMPOSE", "L1_PUBLIC_NULL")
COUNTS = {
    "L1_FIT_TRAIN": 192,
    "L1_FIT_SELECT": 48,
    "L1_PUBLIC_DEV_COMPOSE": 64,
    "L1_PUBLIC_NULL": 64,
}
ACTORS = ("mason", "pilot", "gardener", "artist", "doctor", "baker")
VERBS = ("find", "carry", "inspect", "repair", "follow", "observe")
OBJECTS = ("parcel", "lantern", "bridge", "vessel", "engine", "portrait")
MODIFIERS = ("today", "carefully", "quietly", "outside", "soon")
SEMANTIC_WIDTH = 5

# Full 6 * 6 * 6 * 5 * 2 semantic product. Fixed holdout chosen by public
# arithmetic, not discovered or tuned from L1_PUBLIC_DEV.
_UNIVERSE = tuple(itertools.product(
    range(6), range(6), range(6), range(5), range(2)
))


class SourceCustodyDenied(ValueError):
    pass


def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(",",":"),
                      allow_nan=False,ensure_ascii=True).encode("ascii")


def semantic_holdout(semantic):
    actor,verb,obj,mod,neg=semantic
    return (actor+2*verb+3*obj+mod+neg)%7==0


# The fitted-role split is determined BEFORE role-specific selection.
# Distinct FIT role pools guarantee zero train-to-selection tuple identity.
_NONHOLDOUT = tuple(s for s in _UNIVERSE if not semantic_holdout(s))
_HOLDOUT = tuple(s for s in _UNIVERSE if semantic_holdout(s))
_FIT_POOL = tuple(sorted(
    _NONHOLDOUT,
    key=lambda s: hashlib.sha256(
        canonical((NAMESPACE,"FIT_PARTITION",s))).hexdigest()
))
_POOLS = {
    "L1_FIT_TRAIN":_FIT_POOL[:1200],
    "L1_FIT_SELECT":_FIT_POOL[1200:],
    "L1_PUBLIC_DEV_COMPOSE":_HOLDOUT,
    "L1_PUBLIC_NULL":_HOLDOUT,
}


def seed(role,index):
    if not (type(role) is str and role in ROLES
            and type(index) is int and 0 <= index < COUNTS[role]):
        raise SourceCustodyDenied("L1_UNKNOWN_OR_PROTECTED_SOURCE_ROLE")
    data=f"{NAMESPACE}:{role}:{index}".encode("ascii")
    return int.from_bytes(hashlib.sha256(data).digest()[:8],"big")


def semantics(role,index):
    """Deterministic per-record seeded sampling without replacement.

    Replay the short role-local prefix so independent index calls cannot
    collide and selection is invariant under request order or machine OS.
    """
    seed(role,index)
    pool=_POOLS[role]
    taken=set()
    chosen=None
    for i in range(index+1):
        rng=random.Random(seed(role,i))
        offset=rng.randrange(len(pool))
        while offset in taken:
            offset=(offset+1)%len(pool)
        taken.add(offset)
        chosen=pool[offset]
    return chosen


def realize(semantic,corrupt=False):
    if not (type(semantic) in (tuple,list) and len(semantic)==5
            and all(type(x) is int for x in semantic)):
        raise ValueError("L1_PUBLIC_SEMANTIC_VECTOR_INVALID")
    a,v,o,m,neg=semantic
    if not (0<=a<6 and 0<=v<6 and 0<=o<6
            and 0<=m<5 and neg in (0,1)):
        raise ValueError("L1_SEMANTIC_FIELD_RANGE")
    if corrupt:
        a=(a+1)%6
        v=(v+2)%6
        o=(o+3)%6
    return (
        ("<bos>","the",ACTORS[a],"will")
        + (("not",) if neg else ())
        + (VERBS[v],"the",OBJECTS[o],MODIFIERS[m],".","<eos>")
    )


def public_record(role,index):
    s=semantics(role,index)
    # Never export source oracle names or semantic decomposition metadata
    # beyond the public IDs and training-target tokens.
    return (s,realize(s,corrupt=(role=="L1_PUBLIC_NULL")))


def public_role(role):
    if type(role) is not str or role not in ROLES:
        raise SourceCustodyDenied("L1_PUBLIC_ROLE_NOT_AUTHORIZED")
    return tuple(public_record(role,i) for i in range(COUNTS[role]))


def digest(role):
    return hashlib.sha256(canonical(public_role(role))).hexdigest()

"""L2 prospectively frozen synthetic PUBLIC dependent-phrase grammar.

Only export public semantic inputs (6 integer IDs) and aligned target chunks.
Source parity, role labels and source gold may never be supplied to learners
at inference. All roles are distinct complete semantic tuples. Synthetic
codes should NOT be interpreted as natural language intelligence.
"""
import hashlib
import itertools
import json

NAMESPACE="l2-20261023-conditional-phrase-dependence-v1"
ROLES=("L2_TRAIN","L2_SELECT","L2_DEV_COMPOSE","L2_NULL_CORRUPTION")
COUNTS={"L2_TRAIN":700,"L2_SELECT":150,
        "L2_DEV_COMPOSE":160,"L2_NULL_CORRUPTION":80}
FIELD_SIZES=(5,4,4,3,2,3)
FIELDS=("actor","verb","object","tense","negative","manner")
SLOTS=("article","subject-code","dependent-verb","article2",
       "object","manner","punctuation","end")


class RoleCustodyError(ValueError):
    pass


def canonical(x):
    return json.dumps(x,sort_keys=True,ensure_ascii=True,
                      allow_nan=False,separators=(",",":")).encode("ascii")


def holdout(s):
    a,v,o,t,negative,m=s
    return (a+2*v+3*o+t+negative+m)%5==0


def ordered_universe():
    universe=tuple(itertools.product(*(range(k) for k in FIELD_SIZES)))
    def rank(s):
        return hashlib.sha256(NAMESPACE.encode("ascii")+b":"+
                              canonical(s)).digest()
    ordinary=sorted((s for s in universe if not holdout(s)),key=rank)
    held=sorted((s for s in universe if holdout(s)),key=rank)
    if len(ordinary)<850 or len(held)<240:
        raise ValueError("L2_INSUFFICIENT_NOVEL_COMBINATIONS")
    return {
        "L2_TRAIN":tuple(ordinary[:700]),
        "L2_SELECT":tuple(ordinary[700:850]),
        "L2_DEV_COMPOSE":tuple(held[:160]),
        "L2_NULL_CORRUPTION":tuple(held[160:240]),
    }


PARTITION=ordered_universe()


def source_tokens(meaning,corrupt=False):
    if not (type(meaning) in (tuple,list) and len(meaning)==6
            and all(type(v) is int and 0<=v<FIELD_SIZES[i]
                    for i,v in enumerate(meaning))):
        raise ValueError("L2_SOURCE_SEMANTIC_INPUT_INVALID")
    a,v,o,t,negative,m=meaning
    parity=(3*a+5*v+7*t+11*negative)%2
    if corrupt:
        parity^=1
    return ("the",f"s{a}_{t}_{negative}",
            f"v{v}_{parity}","the",f"o{o}",f"m{m}",
            ".","<eos>")


def render(chunks):
    if len(chunks)!=8:
        raise ValueError("L2_BAD_SURFACE_CHUNK_COUNT")
    return " ".join(chunks[:6])+" . <eos>"


def record(role,index):
    if type(role) is not str or role not in ROLES or \
       type(index) is not int or index<0 or index>=COUNTS[role]:
        raise RoleCustodyError("L2_UNREGISTERED_OR_PROTECTED_SOURCE")
    meaning=PARTITION[role][index]
    return {
        "meaning":list(meaning),
        "slots":list(source_tokens(meaning,role=="L2_NULL_CORRUPTION")),
    }


def dataset(role):
    if type(role) is not str or role not in ROLES:
        raise RoleCustodyError("L2_ROLE_NOT_REGISTERED")
    return tuple(record(role,i) for i in range(COUNTS[role]))


def digest(role):
    return hashlib.sha256(canonical(dataset(role))).hexdigest()

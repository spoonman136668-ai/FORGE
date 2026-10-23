"""L3 new public synthetic aligned semantics-to-language, source-law custody only.

Every candidate gets meaning IDs and FIT target chunks, NOT generator lexeme
arrays or hidden partition role. DEV gold is used solely after frozen fitting.
This small fixture is not natural language or independent external science.
"""
import hashlib
import itertools
import json

NAMESPACE="l3-20261023-new-semantic-surface-v1"
ROLES=("L3_TRAIN","L3_SELECT","L3_COMPOSITION_DEV",
       "L3_UNFAMILIAR_PAIR_DEV","L3_NULL_CORRUPT")
COUNTS={"L3_TRAIN":768,"L3_SELECT":160,
        "L3_COMPOSITION_DEV":128,"L3_UNFAMILIAR_PAIR_DEV":64,
        "L3_NULL_CORRUPT":64}
SIZES=(5,5,5,3,2,3)
ACTORS=("adrian","blair","casey","dana","emery")
VERBS=("open","close","carry","inspect","move")
OBJECTS=("gate","box","book","lamp","door")
MANNERS=("quickly","slowly","carefully")
FIELDS=("actor","verb","object","tense","negative","manner")
SLOTS=("subject","auxiliary","negative","verb","determiner","object","manner","punctuation")


class SourceRoleDenied(ValueError):
    pass


def canonical(x):
    return json.dumps(x,sort_keys=True,separators=(",",":"),
                      allow_nan=False,ensure_ascii=True).encode("ascii")


def _holdout(s):
    a,v,o,t,n,m=s
    return (a+2*v+3*o+t+n+m)%7==0


def _rank(s):
    return hashlib.sha256(NAMESPACE.encode("ascii")+b":"+canonical(s)).digest()


def _partition():
    all_meaning=itertools.product(*(range(n) for n in SIZES))
    fit=[]
    comp=[]
    pair=[]
    for s in all_meaning:
        if s[0]==4 and s[2]==4:
            pair.append(s)
        elif _holdout(s):
            comp.append(s)
        else:
            fit.append(s)
    fit.sort(key=_rank)
    comp.sort(key=_rank)
    pair.sort(key=_rank)
    if min(len(fit)-928,len(comp)-192,len(pair)-64)<0:
        raise ValueError("L3_INSUFFICIENT_DISJOINT_SEMANTIC_UNIVERSE")
    return {
        "L3_TRAIN":tuple(fit[:768]),
        "L3_SELECT":tuple(fit[768:928]),
        "L3_COMPOSITION_DEV":tuple(comp[:128]),
        "L3_UNFAMILIAR_PAIR_DEV":tuple(pair[:64]),
        "L3_NULL_CORRUPT":tuple(comp[128:192]),
    }


PARTITIONS=_partition()


def surface(meaning,corrupted=False):
    if not (type(meaning) in (list,tuple) and len(meaning)==6 and
            all(type(x) is int and 0<=x<SIZES[i]
                for i,x in enumerate(meaning))):
        raise ValueError("L3_INVALID_PUBLIC_MEANING")
    a,v,o,t,negative,m=meaning
    neg=negative^int(corrupted)
    verb=VERBS[v]
    if t==0 and neg:
        aux,form="does",verb
    elif t==0:
        aux,form="",(verb[:-1]+"ies" if verb.endswith("y")
                      else verb+"s")
    elif t==1 and neg:
        aux,form="did",verb
    elif t==1:
        aux,form="",(verb[:-1]+"ied" if verb.endswith("y")
                      else verb+"d" if verb.endswith("e") else verb+"ed")
    else:
        aux,form="will",verb
    return (ACTORS[a],aux,"not" if neg else "",form,
            "the",OBJECTS[o],MANNERS[m],".")


def row(role,index):
    if not (type(role) is str and role in ROLES and
            type(index) is int and 0<=index<COUNTS[role]):
        raise SourceRoleDenied("L3_ROLE_OR_INDEX_REFUSED")
    m=PARTITIONS[role][index]
    return {"meaning":list(m),"slots":list(surface(m,role=="L3_NULL_CORRUPT"))}


def dataset(role):
    if type(role) is not str or role not in ROLES:
        raise SourceRoleDenied("L3_PROTECTED_OR_OLD_SOURCE_ROLE")
    return tuple(row(role,i) for i in range(COUNTS[role]))


def sha(role):
    return hashlib.sha256(canonical(dataset(role))).hexdigest()

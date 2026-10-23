"""L1 fresh aligned PUBLIC meaning-to-utterance development corpus.

All learners get the same 512 FIT + 96 SELECT aligned sentence slots and
meaning tuples; there is NO hidden natural-language benchmark and NO
internally acquired cognitive meaning representation. Heldout actor-object
pair never appears during fitting or selection. Deterministic full-source
rankings exclude duplicate meanings across four roles.
"""
import hashlib
import itertools
import json

NAMESPACE="ol1-20261023-language-synthetic-v1"
AGENTS=("ava","ben","cyra","drew","eli")
VERBS=("open","close","move","inspect","lift","carry")
OBJECTS=("gate","box","book","lamp","door")
TENSES=("present","past","future")
NEGATIVE=(0,1)
MANNERS=("quickly","slowly","carefully")
FIELDS=("agent","verb","object","tense","negative","manner")
SLOTS=("subject","aux","negation","verb","determiner","object","adverb","punctuation")
ROLES=("L1_TRAIN","L1_SELECT","L1_INDOMAIN_DEV","L1_NOVEL_COMPOSITION_DEV")
COUNTS={"L1_TRAIN":512,"L1_SELECT":96,
        "L1_INDOMAIN_DEV":128,"L1_NOVEL_COMPOSITION_DEV":80}


class NotPublicRole(ValueError):
    pass


def canonical(x):
    return json.dumps(x,sort_keys=True,ensure_ascii=True,
                      allow_nan=False,separators=(",",":")).encode("ascii")


def _present(verb):
    return verb[:-1]+"ies" if verb.endswith("y") else verb+"s"


def _past(verb):
    return verb[:-1]+"ied" if verb.endswith("y") else (
        verb+"d" if verb.endswith("e") else verb+"ed"
    )


def surface_slots(meaning):
    if not (type(meaning) is tuple and len(meaning)==6 and
            meaning[0] in AGENTS and meaning[1] in VERBS and
            meaning[2] in OBJECTS and meaning[3] in TENSES and
            type(meaning[4]) is int and meaning[4] in NEGATIVE and
            meaning[5] in MANNERS):
        raise ValueError("L1_INVALID_PUBLIC_MEANING")
    agent,verb,obj,tense,neg,manner=meaning
    if tense=="present" and neg:
        aux,verb_form="does",verb
    elif tense=="present":
        aux,verb_form="",_present(verb)
    elif tense=="past" and neg:
        aux,verb_form="did",verb
    elif tense=="past":
        aux,verb_form="",_past(verb)
    else:
        aux,verb_form="will",verb
    return (agent,aux,"not" if neg else "",verb_form,
            "the",obj,manner,".")


def render(slots):
    if len(slots)!=8:
        raise ValueError("L1_SURFACE_SLOT_COUNT")
    return " ".join(x for x in slots[:-1] if x)+str(slots[-1])


def _partition():
    full=itertools.product(AGENTS,VERBS,OBJECTS,TENSES,NEGATIVE,MANNERS)
    def rank(item):
        return hashlib.sha256(NAMESPACE.encode("ascii")+b":"+
                              canonical(item)).digest()
    ordinary=[]
    held=[]
    for meaning in full:
        (held if meaning[0]=="eli" and meaning[2]=="door"
         else ordinary).append(meaning)
    ordinary.sort(key=lambda x:(rank(x),x))
    held.sort(key=lambda x:(rank(x),x))
    result={}
    pos=0
    for role in ROLES[:-1]:
        size=COUNTS[role]
        result[role]=tuple(ordinary[pos:pos+size])
        pos+=size
    result["L1_NOVEL_COMPOSITION_DEV"]=tuple(held[:COUNTS["L1_NOVEL_COMPOSITION_DEV"]])
    if any(len(result[k])!=COUNTS[k] for k in ROLES):
        raise ValueError("L1_INSUFFICIENT_DISJOINT_SOURCE")
    return result


PARTITION=_partition()


def dataset(role):
    if type(role) is not str or role not in ROLES:
        raise NotPublicRole("L1_PROTECTED_OR_UNREGISTERED_SOURCE")
    return tuple({"meaning":list(m),"slots":list(surface_slots(m))}
                 for m in PARTITION[role])


def role_hash(role):
    return hashlib.sha256(canonical(dataset(role))).hexdigest()

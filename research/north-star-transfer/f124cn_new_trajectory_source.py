"""F124-CN novel internally originated trajectory laws — source-only, no learner.

Not F124-CM model code, not a scorer and NOT executed before authorized birth.
Two distinct hidden laws are deliberately not defined using the candidate's
or competitor's learned feature parameterizations. Both track separately
bound entity-role contexts across delayed interventions and branch changes.
Source seeds must come from a one-time separate OS entropy birth job.
"""
from __future__ import annotations
import copy
import hashlib
import json
import random

FAMILY_BASE = {"G": 932000, "H": 933000}
FROZEN_DEV_CASES = 12
FIT = 40
CHECK = 8
ROLES = ("A", "B")

def need(ok, why):
    if not ok:
        raise ValueError("F124CN_SOURCE_" + why)

def rot4(v, n):
    return ((v << n) | (v >> (4 - n))) & 15

def law(family, event, current, lagged, key):
    """Unseen delayed interventional laws. No model architecture is imported."""
    need(family in FAMILY_BASE and all(type(v) is int and 0 <= v < 16
         for v in (event, current, lagged, *key)) and len(key) == 4,
         "BOUNDED_HIDDEN_RELATION")
    k0, k1, k2, k3 = key
    if family == "G":
        lead = (rot4(current, 1) + 3 * (event ^ k0) +
                (lagged ^ k1)) & 15
        branch = rot4(lagged + k2 & 15, 2) if event & 1 else (current ^ k3)
        return (lead ^ branch ^ ((current * lagged) & 15)) & 15
    branch = (lagged + k3) & 15 if (current ^ event ^ k0) & 4 else event ^ k2
    mixed = ((current ^ rot4(lagged, 2)) +
             (event * event & 15) + k1) & 15
    return (mixed ^ rot4(branch, 1) ^ (lagged * event & 15)) & 15

def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()

def truth(trajectory, family, key):
    states = {role: list(value) for role, value in trajectory["initial"].items()}
    ok = True
    for e in trajectory["events"]:
        current, lagged = states[e["role"]]
        expected = law(family, e["event"], current, lagged, key)
        ok = bool(ok and expected == e["observed"])
        states[e["role"]] = [expected, current]
    return ok

def task(family, ordinal, seed):
    """Only an authorized source-only birth process may call this function."""
    need(family in FAMILY_BASE and type(ordinal) is int
         and 0 <= ordinal < FROZEN_DEV_CASES
         and type(seed) is int and seed > 0, "NEW_ORIGIN_ID")
    rng = random.Random(seed)
    key = [rng.randrange(16) for _ in range(4)]
    inputs = rng.sample(range(4096), 48)
    def decode(x):
        return (x & 15, (x >> 4) & 15, (x >> 8) & 15)
    pairs = [list(decode(x)) + [law(family, *decode(x), key)] for x in inputs]
    count = 8 + 2 * (ordinal % 2)
    initial = {role: [rng.randrange(16), rng.randrange(16)] for role in ROLES}
    active = copy.deepcopy(initial)
    events = []
    for i in range(count):
        role = ROLES[i % 2]
        event = rng.randrange(16)
        current, lagged = active[role]
        output = law(family, event, current, lagged, key)
        events.append({"role": role, "event": event, "observed": output})
        active[role] = [output, current]
    positive = {"initial": initial, "events": events}
    negative = copy.deepcopy(positive)
    # Deterministically select earliest distinct opposite-role observed values;
    # never search over model outcomes or trial scores.
    swaps = next(((i,j) for i in range(count) for j in range(i+1,count)
                  if events[i]["role"] != events[j]["role"]
                  and events[i]["observed"] != events[j]["observed"]), None)
    need(swaps is not None, "HARD_NEGATIVE_DISTINCT_ROLE_OUTPUTS")
    i, j = swaps
    negative["events"][i]["observed"], negative["events"][j]["observed"] = (
        negative["events"][j]["observed"],negative["events"][i]["observed"])
    need(truth(positive, family, key) and not truth(negative, family, key),
         "SYMBOLIC_CAUSAL_GROUND_TRUTH")
    for name in ("role", "event"):
        need([e[name] for e in positive["events"]] ==
             [e[name] for e in negative["events"]], "EVENT_TOPOLOGY_SAME")
    need(sorted(e["observed"] for e in positive["events"]) ==
         sorted(e["observed"] for e in negative["events"]),
         "IDENTICAL_NEXT_STATE_TOKEN_INVENTORY")
    index = FAMILY_BASE[family] + ordinal
    public = {"case_id": index, "FIT": pairs[:FIT], "CHECK": pairs[FIT:],
              "positive": positive, "hard_negative": negative}
    return {"schema": "mass.f124cn.internal-source-born.v1",
            "case_id": index, "private_family": family,
            "private_seed": str(seed), "private_law_key": key,
            "source_origin": "INTERNAL_NO_EXTERNAL_AUTHOR_CLAIM",
            "oracle": {"positive": True, "hard_negative": False},
            "public_task": public,
            "public_sha256": hashlib.sha256(canonical(public)).hexdigest(),
            "old_924_931_sources_used": False,
            "protected_cohort_opened": False}

if __name__ == "__main__":
    raise SystemExit("SOURCE_ONLY_NO_PREBIRTH_CASE_CREATION")

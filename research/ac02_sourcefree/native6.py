"""AC-02 native six proposed mechanisms: deterministic counterexample probes only.

No native model modified and no original scientific outcomes are represented here.
"""
import itertools
import json
from collections import defaultdict

def causal_output(state):
    return state["a"]*state["b"] + state["c"]

def dependencies_near(state):
    """A deliberately incomplete one-at-a-time sensitivity heuristic."""
    start = causal_output(state)
    detected = set()
    for name in sorted(state):
        candidate = dict(state)
        candidate[name] += 1
        if causal_output(candidate) != start:
            detected.add(name)
    return detected

def delta_update(previous, current, cached, dependencies):
    changed = {key for key in previous if previous[key] != current[key]}
    if not changed.intersection(dependencies):
        return cached, False
    return causal_output(current), True

def certified_choice(bounds):
    for candidate,(low,_) in bounds.items():
        if all(candidate == other or low > other_high
               for other,(_,other_high) in bounds.items()):
            return candidate
    return None

class PredictiveFusion:
    def __init__(self):
        self.records = {}
    def observe(self, history, probe, outcome):
        self.records.setdefault(history,{})[probe] = outcome
    def groups(self):
        groups=defaultdict(list)
        for history, observations in self.records.items():
            groups[tuple(sorted(observations.items()))].append(history)
        return tuple(tuple(sorted(g)) for g in groups.values())

def fit_table(experiences):
    memory={}
    for context,action,outcome in experiences:
        key=(context,action)
        if key not in memory:
            memory[key]=outcome
        elif memory[key]!=outcome:
            memory[key]=None
    return memory

def local_updates(eligibilities, reward):
    return tuple(reward*e for e in eligibilities)

def typed_isomorphic(n,edges_a,edges_b):
    if not isinstance(n,int) or n<1 or n>6:
        raise ValueError("bounded source-free graph n=1..6")
    if len(edges_a)!=len(edges_b):
        return False
    a,b=set(edges_a),set(edges_b)
    if len(a)!=len(edges_a) or len(b)!=len(edges_b):
        raise ValueError("duplicate edge")
    if any(x<0 or y<0 or x>=n or y>=n for x,_,y in a|b):
        raise ValueError("node out of range")
    return any({(perm[x],role,perm[y]) for x,role,y in a}==b
               for perm in itertools.permutations(range(n)))

def run():
    base={"a":0,"b":0,"c":0}
    modified={"a":1,"b":1,"c":0}
    cached=causal_output(base)
    deps=dependencies_near(base)
    unsafe,skipped=delta_update(base,modified,cached,deps)
    d1=(unsafe!=causal_output(modified) and skipped is False)
    d2=(certified_choice({"left":(9,10),"right":(2,8)})=="left"
        and certified_choice({"left":(5,10),"right":(6,11)}) is None)
    fusion=PredictiveFusion()
    fusion.observe("A","early","same")
    fusion.observe("B","early","same")
    merged=len(fusion.groups())==1
    fusion.observe("A","later","up")
    fusion.observe("B","later","down")
    d3=merged and len(fusion.groups())==2 and len(fusion.records)==2
    table=fit_table([("x","act","up"),("x","act","down")])
    d4=(table[("x","act")] is None and table.get(("unknown","act")) is None)
    values=local_updates((1,0,1,0),3)
    d5=(values==(3,0,3,0) and values[2]!=0)
    chain=((0,"r",1),(1,"r",2),(2,"r",3))
    renamed=((3,"r",0),(0,"r",2),(2,"r",1))
    fork=((0,"r",1),(0,"r",2),(2,"r",3))
    d6=typed_isomorphic(4,chain,renamed) and not typed_isomorphic(4,chain,fork)
    checks={"AC-D1":d1,"AC-D2":d2,"AC-D3":d3,
            "AC-D4":d4,"AC-D5":d5,"AC-D6":d6}
    assert all(checks.values())
    return {"schema":"forge.ac02.native6.sourcefree.v1",
            "scientific_admission":False,
            "original_first_use":False,
            "observed_development_checks":checks,
            "diagnosis":{
                "AC-D1":"LOCAL_SENSITIVITY_MISSES_INTERACTION; REQUIRES CONSERVATIVE FALLBACK",
                "AC-D2":"BOUND_VALIDITY_AND_FUTURE_VALUE_UNPROVEN",
                "AC-D3":"SPLIT_WORKS_BUT_FULL_HISTORY_RETENTION_MEANS_NO_MEMORY_SAVING",
                "AC-D4":"EVIDENCE_TABLE_ABSTAINS; NO_UNFAMILIAR_TRANSFER",
                "AC-D5":"NONCAUSAL_ELIGIBLE_CELL_GETS_CREDIT",
                "AC-D6":"RENAMING_NOT_STRUCTURAL_NOVELTY; ONLY SMALL_GRAPHS"
            }}
if __name__=="__main__":
    print(json.dumps(run(),sort_keys=True,indent=2))

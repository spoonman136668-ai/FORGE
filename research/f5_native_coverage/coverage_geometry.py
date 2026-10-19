"""F5 public-sensor coverage geometry, independent of scientific data.

Optimize the worst possible observable-swap coverage over ALL 91 unordered
pairs from 14 non-anchor physical cells, across ALL 14 public rotation
start states. No seed, family, true pair, hidden outcome, trial or heldout
enters this module.

Candidate geometry: exactly four distinct sensor offsets sampled in two
late episodes. Normalize the first offset to zero because simultaneous
rotation doesn't change the objective. Maximize the minimum number of the
14 start states in which either swapped cell would be observed, then the
total exposure across all pairs, then lexical offsets for determinism.

This is engineering combinatorics, not a scientific finding or admission.
"""
from itertools import combinations

N=14
K=4
BASELINE_OFFSETS=(0,1,5,10)

def pairs():
    return tuple(combinations(range(N),2))

def rotation_exposures(offsets):
    if type(offsets) is not tuple or len(offsets)!=K or offsets[0]!=0 or (
            any(type(x) is not int or x<0 or x>=N for x in offsets)) or len(set(offsets))!=K:
        raise ValueError("F5_GEOMETRY_INVALID_OFFSETS")
    counts={}
    for a,b in pairs():
        hits=0
        for start in range(N):
            sensors={(start+offset)%N for offset in offsets}
            if a in sensors or b in sensors:
                hits+=1
        counts[f"{a+2}_{b+2}"]=hits
    return counts

def evaluate(offsets):
    exposures=rotation_exposures(offsets)
    return {"worst_pair_exposure":min(exposures.values()),
            "best_pair_exposure":max(exposures.values()),
            "pair_count":len(exposures),
            "start_state_count":N,
            "sum_pair_exposure":sum(exposures.values()),
            "pair_exposure_histogram":{str(x):list(exposures.values()).count(x)
                                        for x in sorted(set(exposures.values()))}}

def optimize():
    ranked=[]
    for other in combinations(range(1,N),K-1):
        offsets=(0,)+other
        score=evaluate(offsets)
        ranked.append((score["worst_pair_exposure"],
                       score["sum_pair_exposure"],offsets))
    optimal_worst=max(v[0] for v in ranked)
    contenders=[v for v in ranked if v[0]==optimal_worst]
    optimal_total=max(v[1] for v in contenders)
    winner=min(v[2] for v in contenders if v[1]==optimal_total)
    baseline=evaluate(BASELINE_OFFSETS)
    best=evaluate(winner)
    if len(ranked)!=286 or len(pairs())!=91:
        raise ValueError("F5_GEOMETRY_ENUMERATION_DRIFT")
    if winner!=(0,1,4,6) or best["worst_pair_exposure"]!=7 or (
            baseline["worst_pair_exposure"]!=5):
        raise ValueError("F5_GEOMETRY_OPTIMUM_DRIFT")
    return {
        "schema":"forge.f5.public-coverage-geometry.v1",
        "status":"SOURCE_ONLY_NO_NEW_SCIENTIFIC_DATA",
        "objective":"Maximize worst exposure across all 91 nonanchor pairs and 14 public start states",
        "enumerated_offset_patterns":len(ranked),
        "nonanchor_pair_count":len(pairs()),
        "rotation_starts":N,
        "baseline_offsets":list(BASELINE_OFFSETS),
        "baseline":baseline,
        "optimal_offsets":list(winner),
        "optimal":best,
        "new_development_cohorts_accessed":0,
        "new_sealed_cohorts_accessed":0,
        "new_first_use_claims":0,
        "scientific_winner_selected":False,
        "prospective_scientific_execution_authorized":False,
    }

if __name__=="__main__":
    import json
    print(json.dumps(optimize(),sort_keys=True,indent=2))

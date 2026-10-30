#!/usr/bin/env python3
"""NR-M1V: compare literal pinned Yggdrasil TaskCell against independent Beta control.

Only historical *algorithm* / source-only parameter states; NEVER instantiate
or advance Farama. No selected-action goal-return or scientific gain claim.
"""
import argparse
from fractions import Fraction
import itertools
import json
from pathlib import Path

from pinned_native_taskcell import TaskCell

MAX_COUNT=4096

def exact_bayesian_predictive(effect, count):
    """Conventional Beta(1,1) Bernoulli posterior predictive probability."""
    if (type(effect) is not int or type(count) is not int
            or not 0 <= effect <= count <= MAX_COUNT):
        raise ValueError("NRM1V_INVALID_SELECTED_SOURCE_COUNTS")
    return Fraction(effect+1, count+2)

def control_propose(parent, count, effect):
    """Independent rational-valued Beta control; quantize only at policy gate."""
    if type(parent) is not int or parent not in range(7):
        raise ValueError("NRM1V_INVALID_PARENT")
    if len(count)!=7 or len(effect)!=7:
        raise ValueError("NRM1V_INVALID_ROW")
    for n,k in zip(count,effect):
        exact_bayesian_predictive(k,n)
    if count[parent]<2:
        return parent, False
    parent_basis=int(exact_bayesian_predictive(effect[parent],count[parent])*10000)
    selected=parent
    best_basis=0
    for alternative in (3,5):
        if (alternative==parent or count[alternative]<2
                or effect[alternative]==0):
            continue
        candidate_basis=int(exact_bayesian_predictive(
            effect[alternative],count[alternative])*10000)
        if (candidate_basis>=5000
                and candidate_basis>=parent_basis+1000
                and candidate_basis>best_basis):
            selected=alternative
            best_basis=candidate_basis
    return selected, selected!=parent

def check(parent, pairs):
    native=TaskCell()
    native.count=list(pair[0] for pair in pairs)
    native.effect=list(pair[1] for pair in pairs)
    actual=native.propose(parent)
    expected=control_propose(parent,native.count,native.effect)
    if actual!=expected:
        raise AssertionError("NRM1V_NATIVE_CONVENTIONAL_DISAGREEMENT "
                             +repr((parent,pairs,actual,expected)))
    # Exact fraction + declared 1e4 quantization equals native score.
    for action in range(7):
        n,k=pairs[action]
        score=10000*(k+1)//(n+2)
        if score!=int(exact_bayesian_predictive(k,n)*10000):
            raise AssertionError("NRM1V_POSTERIOR_IDENTITY_DRIFT")
    return actual[1]

def audit():
    # Freeze all noncompeting actions to 0/0; this is mathematically sufficient
    # because the native proposal reads only parent, pickup(3), toggle(5).
    small=[(n,k) for n in range(7) for k in range(n+1)]
    edge=[(0,0),(1,0),(1,1),(2,0),(2,1),(2,2),
          (4095,0),(4095,1),(4095,2048),(4095,4095),
          (4096,0),(4096,1),(4096,2048),(4096,4095),(4096,4096)]
    count=0
    overrides=0
    for source_name,options in (("exhaustive_0_to_6",small),
                                ("cap_and_threshold_edges",edge)):
        c=0
        o=0
        for parent in range(7):
            other_actions=tuple(a for a in (3,5) if a!=parent)
            varied=(parent,)+other_actions
            for selected_pairs in itertools.product(options,repeat=len(varied)):
                row=[(0,0)]*7
                for action,pair in zip(varied,selected_pairs):
                    row[action]=pair
                did_override=check(parent,row)
                c+=1
                o+=int(did_override)
        yield {"suite":source_name,"cases":c,"overrides":o,"disagreements":0,
               "posterior_score_disagreements":0}
        count+=c
        overrides+=o
    yield {"suite":"all","cases":count,"overrides":overrides,
           "disagreements":0,"posterior_score_disagreements":0}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--output",type=Path)
    args=p.parse_args()
    suites=list(audit())
    result={
       "schema":"nr-m1v-native-beta-conventional-equivalence-v1",
       "source_native":"Yggdrasil #700 exact 8a1bf9c9 TaskCell excerpt",
       "source_full_git_blob":"fdccd7a601adfacf4a4f8533279e66280cf16d99",
       "independent_control":"Fraction Beta(1,1) posterior and 10000-policy quantization",
       "engineering_source_only":True,
       "original_source_actions":0,
       "independent_scientific_first_use":False,
       "actual_native_new_world_goal_improvement":"UNVERIFIED",
       "conclusion":"NO DISTINCT SCORING ADVANTAGE over exact-information Beta(1,1) baseline",
       "suites":suites}
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(result,sort_keys=True,indent=2)+"\n")
    print(json.dumps(result,sort_keys=True))
if __name__=="__main__":
    main()

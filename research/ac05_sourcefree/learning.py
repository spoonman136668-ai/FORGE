"""AC-05 bounded synthetic learning falsification screen (no protected science).

All algorithms operate on generated development data with no repository-native
Wingless/Yggdrasil execution. Controls intentionally include strong simple
fitted alternatives; no result constitutes scientific superiority or admission.
Python >=3.11 standard library only.
"""
from __future__ import annotations
from collections import defaultdict
import hashlib
import json
import random
import time
import tracemalloc

SCHEMA = "forge.ac05.learned-mechanisms.sourcefree.v1"
SEED = 23051

def world(state):
    """Synthetic independent outcome generator, inaccessible to learners."""
    return state[2]*state[8] + 3*state[13]

def fit_dependencies(states, n=20):
    """Learn influence from paired, FIT-only interventions, not known graph."""
    deps=set()
    probes=0
    for state in states:
        reference=world(state)
        for i in range(n):
            altered=state.copy()
            altered[i]=(altered[i]+1)%3
            probes+=1
            if world(altered)!=reference:
                deps.add(i)
    return deps, probes

def delta_experiment():
    rng=random.Random(SEED)
    fit=[[rng.randrange(3) for _ in range(20)] for _ in range(16)]
    deps, fit_queries=fit_dependencies(fit)
    state=[rng.randrange(3) for _ in range(20)]
    last=world(state)
    full=0; selective=0; errors=0; total=0
    for _ in range(240):
        i=rng.randrange(20)
        state[i]=(state[i]+1)%3
        total+=1; full+=1
        if i in deps:
            last=world(state)
            selective+=1
        if last!=world(state):
            errors+=1
    poor_deps,_=fit_dependencies([[0]*20])
    blind=[0]*20
    guessed=world(blind)
    for i in (2,8):
        blind[i]=1
        if i in poor_deps:
            guessed=world(blind)
    unseen_error=guessed!=world(blind)
    return {"learned_dependency_count":len(deps),
            "fit_outcome_queries":fit_queries,
            "evaluation_events":total,
            "full_outcome_computations":full,
            "incremental_outcome_computations":selective,
            "observed_incremental_errors":errors,
            "undercovered_fit_dependencies":len(poor_deps),
            "undercovered_fit_unseen_interaction_failure":unseen_error,
            "cost_caveat":"Fit needs 320 intervention pairs; not net faster by short horizon alone."}

def decision_experiment():
    # A simple fitted deterministic multi-arm control; confidence intervals
    # are only valid under the assumption of unchanged deterministic rewards.
    rewards=[3,8,5,1,2,6,4,7]
    trained={i:[rewards[i]]*3 for i in range(8)}
    intervals={i:(min(v),max(v)) for i,v in trained.items()}
    best=next((i for i,(lo,_) in intervals.items()
               if all(i==j or lo>hi for j,(_,hi) in intervals.items())),None)
    full=max(range(8),key=lambda i:sum(trained[i])/len(trained[i]))
    changed=list(rewards)
    changed[2]=30
    return {"fit_reward_observations":24,
            "certified_action":best,"full_fitted_action":full,
            "fit_action_parity":best==full,
            "observed_stationarity_shift_failure":best!=max(range(8),key=lambda i:changed[i]),
            "assumption":"Deterministic/stationary rewards, unlike unknown real causal dynamics."}

def fusion_experiment():
    # Learn equivalence from FIT observations, then reveal a delayed
    # distinction. Same early outcome does not guarantee future equivalence.
    items={f"h{i:03}":{"early":0} for i in range(200)}
    def grouping(rows):
        g=defaultdict(list)
        for ident,history in sorted(rows.items()):
            g[tuple(sorted(history.items()))].append(ident)
        return dict(g)
    early=grouping(items)
    before_bytes=len(json.dumps(items,sort_keys=True))
    summary=lambda groups: [{"signature":list(key),"identities":identities}
                            for key,identities in groups.items()]
    early_bytes=len(json.dumps(summary(early),sort_keys=True))
    # Before future labels become observable, a merged memory has no basis
    # to distinguish members. Use an explicitly declared default-zero
    # prediction; measure errors from withheld synthetic outcomes below.
    default_future_prediction=0
    for i in range(200):
        items[f"h{i:03}"]["delayed"] = 0 if i<100 else 1
    mistaken_prediction_count=sum(default_future_prediction!=record["delayed"]
                                   for record in items.values())
    split=grouping(items)
    later_bytes=len(json.dumps(summary(split),sort_keys=True))
    roundtrip=json.loads(json.dumps(items,sort_keys=True))
    return {"fit_history_count":200,"fit_group_count":len(early),
            "fit_full_serialized_bytes":before_bytes,
            "fit_group_serialized_bytes":early_bytes,
            "unobserved_future_error_count":mistaken_prediction_count,
            "future_prediction_policy":"default_zero_for_unobserved_outcome",
            "post_counterexample_groups":len(split),
            "post_counterexample_group_bytes":later_bytes,
            "cold_restart_history_roundtrip":roundtrip==items,
            "caveat":"Identity retention remains; future unobserved distinctions caused failures."}

def program_experiment():
    fit=[(0,2),(1,5),(2,8)]
    tested=0
    candidates=[]
    for slope in range(-6,7):
        for intercept in range(-10,11):
            tested+=1
            if all(slope*x+intercept==y for x,y in fit):
                candidates.append((slope,intercept))
    if not candidates:
        raise AssertionError("NO_FITTED_RULE")
    rule=min(candidates,key=lambda pair:(abs(pair[0])+abs(pair[1]),pair))
    # Properly fitted linear control has identical behavior, so no advantage.
    conventional=(round((fit[-1][1]-fit[0][1])/(fit[-1][0]-fit[0][0])),
                  fit[0][1])
    transfer=[(x,3*x+2) for x in (9,11,17)]
    rule_ok=sum(rule[0]*x+rule[1]==y for x,y in transfer)
    control_ok=sum(conventional[0]*x+conventional[1]==y for x,y in transfer)
    return {"candidate_count_evaluated":tested,
            "fitted_rule":list(rule),"fitted_linear_control":list(conventional),
            "unfamiliar_input_correct":rule_ok,
            "fully_fitted_linear_control_correct":control_ok,
            "advantage_over_fitted_control":rule_ok>control_ok,
            "caveat":"Within-family extrapolation, not unfamiliar causal-family transfer."}

def credit_experiment():
    # Distinct local cells can update using selected-action feedback.
    # No privileged hidden answers enter the local estimates, but no genuine
    # independently executed native Yggdrasil cell runtime exists here.
    rewards=[1,0,4,3,2,5,0,2]
    trace=[0.0]*8
    count=[0]*8
    reward_updates=0
    for round_idx in range(4):
        for a in (0,2,4,6,1,3,5,7):
            observed=rewards[a]
            count[a]+=1
            trace[a]+= (observed-trace[a])/count[a]
            reward_updates+=1
    ema=trace[:] # a fully fitted per-action EMA equals the proposed learner.
    train_accuracy=sum(abs(trace[i]-rewards[i])<1e-9 for i in range(8))
    shifted=rewards[::-1]
    shift_accuracy=sum(abs(trace[i]-shifted[i])<1e-9 for i in range(8))
    # A deliberately naive shared-eligibility update gives a coactivated
    # but causally unrelated cell credit for the selected action reward.
    # It is a negative control, not an intrinsic failure of the local estimator.
    naive_credit=[0.0]*8
    for a in range(8):
        if rewards[a]:
            naive_credit[(a+1)%8] += rewards[a]
    spurious_credit=any(naive_credit[i]>0 for i in range(8) if rewards[i]==0)
    return {"fit_updates":reward_updates,"fit_action_reward_exact":train_accuracy,
            "matched_fitted_ema_parity":ema==trace,
            "shifted_family_action_reward_exact":shift_accuracy,
            "confounded_noncausal_credit_risk":spurious_credit,
            "local_messages":0,
            "caveat":"Synthetic per-action table; no actual local-cell learning or causal attribution validation."}

def transfer_experiment():
    # Learned FIT structures are directed role-labelled graphs; a heldout
    # new shape has no same-shape analogy and forces abstention.
    fit=[
        ((0,"r",1),(1,"r",2),(2,"r",3)),
        ((0,"r",1),(0,"r",2),(2,"r",3))
    ]
    unknown=((0,"r",1),(1,"r",2),(2,"r",0),(2,"r",3))
    def signature(edges):
        degrees=defaultdict(lambda:[0,0])
        for a,role,b in edges:
            degrees[a][1]+=1;degrees[b][0]+=1
        return (len(edges),tuple(sorted(map(tuple,degrees.values()))))
    learned={signature(graph) for graph in fit}
    unseen_new=signature(unknown) not in learned
    rename=((3,"r",0),(0,"r",2),(2,"r",1))
    renamed_known=signature(rename) in learned
    # A strong typed-reachability control can answer a bounded path query.
    current={0}
    for _ in range(2):
        current={b for a,role,b in unknown if a in current and role=="r"}
    control_reaches_2=2 in current
    return {"fit_graph_families":len(fit),
            "renamed_familiar_classified_as_known":renamed_known,
            "unfamiliar_graph_abstained":unseen_new,
            "typed_graph_control_two_step_success":control_reaches_2,
            "verified_unfamiliar_transfer":False,
            "caveat":"A topological signature is no learned transfer operator; no first-use success."}

def run():
    functions={
        "AC-D1":delta_experiment,
        "AC-D2":decision_experiment,
        "AC-D3":fusion_experiment,
        "AC-D4":program_experiment,
        "AC-D5":credit_experiment,
        "AC-D6":transfer_experiment
    }
    tracemalloc.start()
    begin=time.perf_counter_ns()
    results={}
    for key,function in functions.items():
        start=time.perf_counter_ns()
        results[key]=dict(function())
        results[key]["development_wall_ns"]=time.perf_counter_ns()-start
    wall=time.perf_counter_ns()-begin
    peak=tracemalloc.get_traced_memory()[1]
    tracemalloc.stop()
    assert set(results)=={"AC-D"+str(i) for i in range(1,7)}
    assert results["AC-D1"]["observed_incremental_errors"]==0
    assert results["AC-D1"]["undercovered_fit_unseen_interaction_failure"]
    assert results["AC-D2"]["fit_action_parity"]
    assert results["AC-D2"]["observed_stationarity_shift_failure"]
    assert results["AC-D3"]["post_counterexample_groups"]==2
    assert not results["AC-D4"]["advantage_over_fitted_control"]
    assert results["AC-D5"]["matched_fitted_ema_parity"]
    assert not results["AC-D6"]["verified_unfamiliar_transfer"]
    return {"schema":SCHEMA,"seed":SEED,
        "scope":"SYNTHETIC_DEVELOPMENT_ONLY",
        "all_36_ideas_retained_in_portfolio":True,
        "scientific_first_use":False,
        "independent_consequence_source_verified":False,
        "native_model_changed":False,
        "accepted_science":False,
        "new_controller_or_scheduler":False,
        "source_free_mechanism_count":6,
        "measurement":{"total_wall_ns":wall,"python_peak_bytes":peak},
        "results":results}

if __name__=="__main__":
    print(json.dumps(run(),sort_keys=True,indent=2))

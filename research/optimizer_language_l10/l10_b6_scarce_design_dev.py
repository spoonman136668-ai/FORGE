#!/usr/bin/env python3
"""L10-B6: scarce DEV-only probe design with exact Bayesian permutation control.

All evaluations use existing 12 DEV_FIT + 12 DEV_CHECK synthetic cases.
The world adapter alone owns true mapping. Policies see only code counts,
DEV_FIT graph code sets, public bijective hypothesis class, and consequences.
A complete exact graph is scored zero if even one code remains ambiguous.
"""
from __future__ import annotations
from collections import Counter
from hashlib import sha256
from itertools import permutations
import math
import time
import tracemalloc

import l10_dev_source_custody as src
import l10_b4_effect_local_learning as b4
import l10_b5_delayed_probe_dev as b5
import l10_semantic_dev_oracle as oracle

SCHEMA="forge.optimizer.language.l10.b6-scarce-probe-dev-v1"
ROLE=src.DEV_ROLE
BUDGETS=(1,2)
CONDITIONS=b5.REGIMES
METHODS=("local-uncertainty","classical-frequency","exact-bayesian-design",
         "round-robin","fixed-random","no-query")
CODES=src.PREDICATE_CODES
EFFECTS=b4.EFFECTS
ALL_MAPS=tuple(dict(zip(CODES,values)) for values in permutations(EFFECTS))

def require(value,reason):
    if not value:raise ValueError("L10_B6_SCARCE_CUSTODY_BLOCKED:"+reason)

def hypotheses(counts:Counter):
    require(isinstance(counts,Counter),"learner state")
    direct={}
    for (code,effect),count in counts.items():
        require(code in CODES and effect in EFFECTS
                and type(count) is int and count>0,"invalid effect counts")
        if code in direct and direct[code]!=effect:
            # Conflicting effects do not earn a mapped meaning.
            return ()
        direct[code]=effect
    return tuple(h for h in ALL_MAPS if all(h[c]==e for c,e in direct.items()))

def determined(counts):
    possible=hypotheses(counts)
    if not possible:return {}
    return {c:possible[0][c] for c in CODES
            if all(h[c]==possible[0][c] for h in possible)}

def infer_with_posterior(inp,counts):
    known=determined(counts)
    return b4.translate(inp,lambda code:known.get(code))

def _fit_shapes(fit):
    require(type(fit) in (list,tuple) and len(fit)==12,"fit source cardinality")
    shapes=[]
    counts=Counter()
    seen=set()
    for f in fit:
        src.validate_fixture(f)
        require(f.split=="DEV_FIT" and f.input.information_regime=="WITHHELD_MAPPING"
                and f.role==ROLE and f.fixture_sha256 not in seen,"fit role/exposure")
        seen.add(f.fixture_sha256)
        shape=frozenset(edge.relation_code for edge in src.public_input(f).observed)
        require(shape and shape.issubset(CODES),"invalid relation-code composition")
        shapes.append(shape)
        counts.update(edge.relation_code for edge in f.input.observed)
    require(all(counts[c]>0 for c in CODES),"missing learnable code")
    return tuple(shapes),counts

def exact_expected_utility(action,counts,fit_shapes):
    require(action in CODES,"illegal proposed intervention")
    possible=hypotheses(counts)
    if not possible:return -1.0
    # Exact finite prior: each hypothesis maps the proposed code to one
    # outcome. Credit a graph only if *every* mapping remaining after that
    # hypothetical observation determines each relation in its code-set.
    utility=0.
    for hypothesis in possible:
        virtual=Counter(counts)
        virtual[(action,hypothesis[action])]+=1
        closure=set(determined(virtual))
        utility+=sum(shape.issubset(closure) for shape in fit_shapes)/len(fit_shapes)
    return utility/len(possible)

def pick(policy,counts,fit_shapes,code_counts,index):
    require(policy in METHODS and type(index) is int and index>=0,"invalid method")
    if policy=="no-query":return None
    require(hypotheses(counts),"contradictory observation posterior")
    # Only unresolved codes are eligible: repeating an already determined
    # mapping is allowed neither credit nor action-budget waste.
    unresolved=[c for c in CODES if c not in determined(counts)]
    if not unresolved:return None
    if policy=="local-uncertainty":
        # Original local uncertainty preference: least prior exposure.
        return min(unresolved,key=lambda c:(code_counts[c],CODES.index(c)))
    if policy=="classical-frequency":
        return max(unresolved,key=lambda c:(code_counts[c],-CODES.index(c)))
    if policy=="exact-bayesian-design":
        return max(unresolved,key=lambda c:(exact_expected_utility(c,counts,fit_shapes),
                                            -CODES.index(c)))
    if policy=="round-robin":
        return min(unresolved,key=lambda c:(CODES.index(c)-index)%len(CODES))
    if policy=="fixed-random":
        return next(c for c in ("P2","P0","P1") if c in unresolved)
    raise ValueError("unrecognized policy")

def execute(fit,check,condition,policy,budget):
    require(condition in CONDITIONS and policy in METHODS and budget in BUDGETS,
            "unregistered experiment conditions")
    shapes,frequencies=_fit_shapes(fit)
    require(type(check) in (tuple,list) and len(check)==12,"check size")
    seen_check=set()
    for f in check:
        src.validate_fixture(f)
        require(f.split=="DEV_CHECK" and f.role==ROLE and
                f.input.information_regime=="WITHHELD_MAPPING"
                and f.fixture_sha256 not in seen_check,"protected/check source drift")
        seen_check.add(f.fixture_sha256)
    require(not seen_check.intersection(f.fixture_sha256 for f in fit),"train/check overlap")
    world=b5.World(fit,condition)
    require(dict(world.fit_code_frequencies)==dict(frequencies),"public fit freq custody")
    mem=b4.LocalMemory()
    selected=[]
    delay_tickets=[]
    ledger=set()
    restart_sha=None
    start=time.perf_counter();start_cpu=time.process_time()
    tracemalloc.start()
    for i in range(0 if policy=="no-query" else budget):
        choice=pick(policy,mem.counts,shapes,frequencies,i)
        if choice is None:break
        # Action occurs before observation. B5 World seals effect privately.
        ticket=world.request(choice,world.clock)
        delay_tickets.append(ticket)
        selected.append(choice)
        require(ticket.release_tick==ticket.action_tick+3,"feedback delay identity")
        while world.clock<ticket.release_tick:
            world.advance()
            require(ticket.ticket_sha256 not in world.claimed,"early-feedback side channel")
        consequence=world.release(ticket,world.clock)
        require(consequence.ticket_sha256==ticket.ticket_sha256
                and consequence.release_tick>=ticket.action_tick+3
                and consequence.ticket_sha256 not in ledger,"forged/early feedback")
        ledger.add(consequence.ticket_sha256)
        mem.update(b4.Observation(consequence.code,consequence.effect_channel))
        # Persist model and world-independent tickets+receipt ledger after
        # first feedback. No hidden mapping or DEV_CHECK content serialized.
        if restart_sha is None:
            snap=b5.snapshot_public_state(mem,[],ledger,world.clock)
            restart_sha=sha256(snap).hexdigest()
            mem,pending,ledger,clock=b5.restore_public_state(snap)
            require(not pending and clock==world.clock,"resume drift")
    require(len(world.claimed)==len(selected)==len(ledger),"lost consequence")
    # All options consume no more than the exact equal-budget allowance.
    require(len(selected)<=budget,"overspent action allowance")
    learning_wall=time.perf_counter()-start
    learning_cpu=time.process_time()-start_cpu
    check_start=time.perf_counter();check_cpu=time.process_time()
    byfam={f:Counter() for f in src.FAMILIES}
    for f in check:
        input_only=src.public_input(f)
        result=(infer_with_posterior(input_only,mem.counts)
                if policy=="exact-bayesian-design" else
                b4.translate(input_only,lambda code:b4._winner(mem.counts,code)))
        score=oracle.evaluate_one(f.target,result)
        byfam[f.family].update(score)
        byfam[f.family]["cases"]+=1
    eval_wall=time.perf_counter()-check_start
    eval_cpu=time.process_time()-check_cpu
    peak=tracemalloc.get_traced_memory()[1]
    tracemalloc.stop()
    rows=[]
    for family in src.FAMILIES:
        values=byfam[family]
        require(values["cases"]==4,"source family omission")
        rows.append({
            "family_sha256":sha256(family.encode()).hexdigest(),
            "cases":4,"exact":values["exact_semantic_graph_success"],
            "abstentions":values["abstentions"],
            "supported":values["supported_claims"],"missing":values["missing_claims"],
            "extra":values["extra_claims"],
            "contradictions":values["contradictory_claims"]})
    return dict(method=policy,condition=condition,budget=budget,
       source_role=ROLE,source_fit_world_sha256=world.world_source_sha,
       query_count=len(selected),
       selected_code_sequence=selected,
       delivered_ticket_count=len(ledger),
       delayed_delivery_verified=all(t.ticket_sha256 in ledger and t.release_tick>=t.action_tick+3
              for t in delay_tickets),
       recovered_restart_sha256=restart_sha,
       learned_state_sha256=mem.digest(),
       learned_state_bytes=len(mem.snapshot()),
       permutation_posterior_size=len(hypotheses(mem.counts)),
       fully_determined_relation_count=len(determined(mem.counts)),
       outcomes=rows,micro_exact=sum(x["exact"] for x in rows)/12,
       macro_exact=sum(x["exact"]/x["cases"] for x in rows)/3,
       micro_abstention=sum(x["abstentions"] for x in rows)/12,
       fit_wall_seconds=round(learning_wall,9),
       fit_cpu_seconds=round(learning_cpu,9),
       inference_wall_seconds=round(eval_wall,9),
       inference_cpu_seconds=round(eval_cpu,9),
       peak_python_traced_bytes=peak,
       energy="NOT_MEASURED",flops="NOT_MEASURED",
       prospective_source_consumed=False,scientific_go=False)

def benchmark(fit,check):
    shapes,frequency=_fit_shapes(fit)
    require(len(shapes)==12 and len(frequency)==3,"information source grid")
    rows=[execute(fit,check,cond,policy,budget)
          for budget in BUDGETS for cond in CONDITIONS for policy in METHODS]
    require(len(rows)==len(BUDGETS)*len(CONDITIONS)*len(METHODS),"partial comparison grid")
    for budget in BUDGETS:
        for condition in CONDITIONS:
            arms=[r for r in rows if r["budget"]==budget and r["condition"]==condition]
            require(len(arms)==len(METHODS) and [x["method"] for x in arms]==list(METHODS),
                    "arm order or missing comparator")
            require(len({x["source_fit_world_sha256"] for x in arms})==1,
                    "source/information mismatch")
            require(all(r["query_count"]==budget for r in arms[:-1])
                    and arms[-1]["query_count"]==0,"unequal action allocation")
            if condition=="DELAYED_NO_FEEDBACK":
                require(all(r["micro_exact"]==0 and r["micro_abstention"]==1 for r in arms),
                        "information-free false claim")
            if condition=="DELAYED_CLEAN" and budget==2:
                require(arms[2]["micro_exact"]==1.,
                        "exact bijective posterior should resolve third code")
    return dict(schema=SCHEMA,status="SYNTHETIC_DEV_SCARCE_INFORMATION_ONLY",
       development_fit_count=12,development_check_count=12,independent_test_families=False,
       information_structure="uniform-unknown-3-code-permutation",
       budgets=list(BUDGETS),conditions=list(CONDITIONS),methods=list(METHODS),
       outcomes=rows,
       prospectively_protected_examples_generated=0,l9_audit_reused=False,
       native_causal_world_model_demonstrated=False,scientific_go=False)

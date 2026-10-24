#!/usr/bin/env python3
"""L10-B5 DEV-only active probes with delayed consequences and restart custody.

This is a *stationary code-to-effect association world*, not proof of
counterfactual reasoning. Feedback semantics are publicly specified.
Every policy has same training-code frequencies, glossary and probe budget.
Original L9/WebNLG and protected L10 sources are never imported.
"""
from __future__ import annotations
from collections import Counter
from dataclasses import dataclass
from hashlib import sha256
import json
import math
import time
import tracemalloc

import l10_dev_source_custody as src
import l10_b4_effect_local_learning as b4
import l10_semantic_dev_oracle as oracle

SCHEMA="forge.optimizer.language.l10.b5-delayed-active-probe-dev-v1"
REGIMES=("DELAYED_CLEAN","DELAYED_NO_FEEDBACK","DELAYED_PERMUTED")
POLICIES=("local-uncertainty","classical-coverage-greedy",
          "bayesian-information-gain","fixed-round-robin",
          "deterministic-random","no-query-abstention")
BUDGET=3
DELAY_TICKS=2
ROLE=src.DEV_ROLE

@dataclass(frozen=True)
class Ticket:
    ticket_sha256:str
    code:str
    action_tick:int
    release_tick:int

@dataclass(frozen=True)
class Consequence:
    ticket_sha256:str
    code:str
    effect_channel:str
    release_tick:int

def require(ok,reason):
    if not ok:raise ValueError("L10_B5_DEFERRED_CUSTODY_BLOCKED:"+reason)

def _sha(obj):
    return sha256(src.canonical_bytes(obj)).hexdigest()

def _map_from_fit(fit):
    require(type(fit) in (list,tuple) and len(fit)==12,"missing DEV_FIT")
    # Access to hidden fitting relations occurs *only* in this world factory.
    outcomes=b4.make_fit_events(fit,"FEEDBACK_OBSERVED")
    counts=Counter(e.relation_code for e in outcomes)
    groups={}
    for e in outcomes:
        if e.relation_code in groups:
            require(groups[e.relation_code]==e.effect_channel,"nonstationary hidden world")
        groups[e.relation_code]=e.effect_channel
    require(set(groups)==set(src.PREDICATE_CODES),"incomplete effect world")
    return groups,counts,_sha([e.event_sha256 for e in outcomes])

class World:
    def __init__(self,fit,regime):
        require(regime in REGIMES,"unknown consequence condition")
        original,counts,world_source_sha=_map_from_fit(fit)
        self.hidden={
            code:(b4.EMPTY if regime=="DELAYED_NO_FEEDBACK" else
                  b4.EFFECTS[(b4.EFFECTS.index(effect)+1)%3]
                  if regime=="DELAYED_PERMUTED" else effect)
            for code,effect in original.items()}
        self.regime=regime
        self.fit_code_frequencies=tuple((code,counts[code]) for code in src.PREDICATE_CODES)
        self.world_source_sha=world_source_sha
        self.issued={}
        self.claimed=set()
    def _ticket_id(self,code,tick):
        return _sha([SCHEMA,self.world_source_sha,self.regime,code,tick])
    def request(self,code,tick):
        require(code in src.PREDICATE_CODES and type(tick) is int and tick>=0
                and tick not in self.issued,"duplicate/invalid action dispatch")
        ticket=Ticket(self._ticket_id(code,tick),code,tick,tick+DELAY_TICKS+1)
        self.issued[tick]=ticket
        # NOT a consequence. Merely an opaque delayed-action receipt.
        return ticket
    def release(self,ticket:Ticket,now:int):
        require(type(ticket) is Ticket and type(now) is int,"invalid delayed message")
        stored=self.issued.get(ticket.action_tick)
        require(stored==ticket and stored.ticket_sha256==self._ticket_id(ticket.code,ticket.action_tick),
                "substituted action ticket")
        require(now>=ticket.release_tick,"future consequence read blocked")
        require(ticket.ticket_sha256 not in self.claimed,"duplicate consequence delivery")
        self.claimed.add(ticket.ticket_sha256)
        return Consequence(ticket.ticket_sha256,ticket.code,self.hidden[ticket.code],now)

def _ticket_body(t:Ticket):
    return [t.ticket_sha256,t.code,t.action_tick,t.release_tick]

def snapshot_public_state(memory:b4.LocalMemory,pending:list[Ticket],seen:set[str],next_tick:int):
    require(type(memory) is b4.LocalMemory and type(pending) is list
            and type(seen) is set and type(next_tick) is int and next_tick>=0,
            "restart contract mismatch")
    require(all(type(t) is Ticket and t.action_tick<next_tick
                and t.release_tick==t.action_tick+DELAY_TICKS+1
                for t in pending),"pending receipt drift")
    require(len({t.ticket_sha256 for t in pending})==len(pending)
            and not any(t.ticket_sha256 in seen for t in pending),"pending duplicates")
    body=dict(schema="forge.optimizer.language.l10.b5-restart-state-v1",
       memory_sha256=memory.digest(),
       memory_snapshot=json.loads(memory.snapshot()),
       pending=[_ticket_body(t) for t in pending],
       delivered_ticket_sha256=sorted(seen),
       next_tick=next_tick)
    return src.canonical_bytes(body)

def restore_public_state(raw:bytes):
    require(type(raw) is bytes and 0<len(raw)<10000,"bad process state")
    body=json.loads(raw)
    require(type(body) is dict and set(body)=={
       "schema","memory_sha256","memory_snapshot","pending",
       "delivered_ticket_sha256","next_tick"},"corrupt restart fields")
    require(body["schema"]=="forge.optimizer.language.l10.b5-restart-state-v1","state version")
    mem=b4.LocalMemory.restore(src.canonical_bytes(body["memory_snapshot"]))
    require(mem.digest()==body["memory_sha256"],"memory hash drift")
    require(type(body["pending"]) is list,"pending type")
    pending=[]
    for v in body["pending"]:
        require(type(v) is list and len(v)==4 and type(v[0]) is str
                and type(v[1]) is str and type(v[2]) is int and type(v[3]) is int
                and len(v[0])==64,"pending ticket malformed")
        pending.append(Ticket(*v))
    delivered=body["delivered_ticket_sha256"]
    require(type(delivered) is list and
            len(delivered)==len(set(delivered)) and delivered==sorted(delivered)
            and all(type(x) is str and len(x)==64 for x in delivered),"delivery ledger drift")
    seen=set(delivered)
    require(snapshot_public_state(mem,pending,seen,body["next_tick"])==raw,
            "noncanonical or altered process snapshot")
    return mem,pending,seen,body["next_tick"]

def _choose(policy:str,code_counts:dict,counts:Counter,pending:list[Ticket],tick:int):
    require(policy in POLICIES,"unknown query policy")
    if policy=="no-query-abstention":return None
    considered=Counter(t.code for t in pending)
    def observed(c):
        return sum(v for (k,_),v in counts.items() if k==c)
    options=list(src.PREDICATE_CODES)
    if policy=="fixed-round-robin":
        return options[tick%len(options)]
    if policy=="deterministic-random":
        # Frozen non-data-dependent (balanced but reordered) schedule.
        return (options[2],options[0],options[1])[tick%3]
    if policy=="local-uncertainty":
        return min(options,key=lambda c:(observed(c)+considered[c],
                        -code_counts[c],options.index(c)))
    if policy=="classical-coverage-greedy":
        return min(options,key=lambda c:(observed(c)+considered[c]>0,
                        -code_counts[c],options.index(c)))
    if policy=="bayesian-information-gain":
        # Symmetric Dirichlet(1/2) posterior; the expected information
        # proxy is preference for unobserved and non-pending relation codes.
        return max(options,key=lambda c:(code_counts[c]/(1+observed(c)+considered[c]),
                                         -options.index(c)))
    raise ValueError("unknown policy")

def execute(fit,check,regime,policy):
    require(regime in REGIMES and policy in POLICIES
            and type(fit) in (list,tuple) and len(fit)==12
            and type(check) in (list,tuple) and len(check)==12,"experiment identity")
    for f in check:
        src.validate_fixture(f)
        require(f.split=="DEV_CHECK" and f.role==ROLE
                and f.input.information_regime=="WITHHELD_MAPPING",
                "check/truth leakage")
    world=World(fit,regime)
    code_counts=dict(world.fit_code_frequencies)
    learner=b4.LocalMemory()
    pending=[]
    seen=set()
    tick=0
    queried=[]
    release_ticks=[]
    first_restart_sha=None
    action_count=0
    start=time.perf_counter()
    start_cpu=time.process_time()
    tracemalloc.start()
    limit=BUDGET if policy!="no-query-abstention" else 0
    # Fixed action phase: each choice occurs before the next release.
    while action_count<limit:
        choice=_choose(policy,code_counts,learner.counts,pending,tick)
        require(choice is not None,"unexpected abstention")
        receipt=world.request(choice,tick)
        pending.append(receipt)
        queried.append(choice)
        action_count+=1
        tick+=1
        delivered=[]
        for t in pending:
            if t.release_tick<=tick:
                result=world.release(t,tick)
                require(result.release_tick>=t.action_tick+DELAY_TICKS+1,
                        "premature feedback")
                require(result.ticket_sha256==t.ticket_sha256,"feedback binding")
                learner.update(b4.Observation(result.code,result.effect_channel))
                require(t.ticket_sha256 not in seen,"duplicate receipt")
                seen.add(t.ticket_sha256)
                release_ticks.append((t.action_tick,result.release_tick))
                delivered.append(t)
        pending=[t for t in pending if t not in delivered]
        if delivered and first_restart_sha is None:
            # Rehydrate the *public learner and pending-action state*.
            # World semantic mapping remains private to the environment.
            state=snapshot_public_state(learner,pending,seen,tick)
            first_restart_sha=sha256(state).hexdigest()
            learner,pending,seen,tick=restore_public_state(state)
    # Allow outstanding already-purchased consequences to mature.
    while pending:
        tick+=1
        delivered=[]
        for t in pending:
            if t.release_tick<=tick:
                result=world.release(t,tick)
                learner.update(b4.Observation(result.code,result.effect_channel))
                require(t.ticket_sha256 not in seen,"duplicate delivered")
                seen.add(t.ticket_sha256)
                release_ticks.append((t.action_tick,result.release_tick))
                delivered.append(t)
        pending=[t for t in pending if t not in delivered]
        require(tick<=BUDGET+DELAY_TICKS+1,"unbounded delayed queue")
    require(len(seen)==limit==len(world.claimed),"unaccounted action/consequence")
    if limit:
        require(first_restart_sha is not None,"never recovered persisted state")
    state=learner.snapshot()
    fit_wall=time.perf_counter()-start
    fit_cpu=time.process_time()-start_cpu
    # Only after fitting/restart complete can the scorer inspect DEV_CHECK.
    families={f:Counter() for f in src.FAMILIES}
    evaluation_start=time.perf_counter()
    evaluation_cpu_start=time.process_time()
    for f in check:
        inp=src.public_input(f)
        text=b4.translate(inp,lambda code:b4._winner(learner.counts,code))
        measures=oracle.evaluate_one(f.target,text)
        families[f.family].update(measures)
        families[f.family]["examples"]+=1
    eval_wall=time.perf_counter()-evaluation_start
    eval_cpu=time.process_time()-evaluation_cpu_start
    peak=tracemalloc.get_traced_memory()[1]
    tracemalloc.stop()
    result=[]
    for family,c in sorted(families.items()):
        require(c["examples"]==4,"partial family")
        result.append(dict(family_sha256=sha256(family.encode()).hexdigest(),
              examples=c["examples"],exact_graph_success=c["exact_semantic_graph_success"],
              abstentions=c["abstentions"],missing_claims=c["missing_claims"],
              unsupported_claims=c["extra_claims"],
              contradictory_claims=c["contradictory_claims"]))
    micro=sum(x["exact_graph_success"] for x in result)
    return dict(policy=policy,regime=regime,source_role=ROLE,
       source_custody_sha256=world.world_source_sha,
       action_budget=BUDGET,actual_probes=action_count,
       released_feedback=len(seen),
       selected_code_sequence=queried,
       actual_delays=[released-action for action,released in release_ticks],
       learned_state_sha256=sha256(state).hexdigest(),
       learned_state_bytes=len(state),
       restart_state_sha256=first_restart_sha,
       restart_executed=first_restart_sha is not None,
       family_metrics=result,
       micro_exact=micro/12,macro_exact=sum(x["exact_graph_success"]/4 for x in result)/3,
       micro_abstention=sum(x["abstentions"] for x in result)/12,
       fit_wall_seconds=round(fit_wall,9),fit_cpu_seconds=round(fit_cpu,9),
       inference_wall_seconds=round(eval_wall,9),
       inference_cpu_seconds=round(eval_cpu,9),
       python_traced_peak_bytes=peak,
       flops="NOT_MEASURED",energy="NOT_MEASURED",
       protected_samples_read=0,scientific_go=False)

def benchmark(fit,check):
    require(type(fit) in (list,tuple) and len(fit)==12
            and type(check) in (list,tuple) and len(check)==12,"missing source")
    rows=[]
    for regime in REGIMES:
        for policy in POLICIES:
            rows.append(execute(fit,check,regime,policy))
    require(len(rows)==18 and len({(x["regime"],x["policy"]) for x in rows})==18,
            "incomplete policy grid")
    for reg in REGIMES:
        in_reg=[x for x in rows if x["regime"]==reg]
        require(len({x["source_custody_sha256"] for x in in_reg})==1,
                "inconsistent matched-world source")
        require(all(x["actual_probes"]==3 for x in in_reg[:-1])
                and in_reg[-1]["actual_probes"]==0,"unmatched query budget")
        require(all(all(delay>=DELAY_TICKS+1 for delay in x["actual_delays"])
                for x in in_reg),"hidden future reference")
        if reg=="DELAYED_NO_FEEDBACK":
            require(all(x["micro_exact"]==0 and x["micro_abstention"]==1
                    for x in in_reg),"no-information false success")
        if reg=="DELAYED_CLEAN":
            require(in_reg[0]["micro_exact"]<=max(x["micro_exact"] for x in in_reg[1:]),
                    "novelty can only be established independently")
    return {"schema":SCHEMA,"status":"DEV_ONLY_DELAYED_ACTIVE_INFORMATION_MECHANISM_SCREEN",
       "policy_count":len(POLICIES),"regimes":list(REGIMES),
       "source_families":3,"fit_cases":12,"check_cases":12,
       "action_budget":BUDGET,"feedback_delay_ticks":DELAY_TICKS,
       "outcomes":rows,"prospective_examples_generated_or_used":0,
       "original_l9_webnlg_reused":False,
       "native_causal_representation_demonstrated":False,
       "scientific_go":False}

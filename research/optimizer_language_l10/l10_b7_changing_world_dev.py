#!/usr/bin/env python3
"""L10-B7 state-dependent development episodes with delayed observations.

Nonbijective code/effect relation; P2 changes the next hidden state; a
possibly unannounced switch at CHECK step 6 changes it again. Oracle-private
state is accessible ONLY in World. All policies see identical training
consequences, checking actions, delayed checking consequences and structural
hypotheses. No L9/WebNLG or prospective examples.
"""
from __future__ import annotations
from dataclasses import dataclass
from hashlib import sha256
import json
import math
import time
import tracemalloc

import l10_dev_source_custody as custody

SCHEMA="forge.optimizer.language.l10.b7-changing-state-dev-v1"
ROLE="L10_SYNTHETIC_DEV"
FAMILIES=("world-phase","world-switch","world-interference")
SPLITS=("FIT","CHECK")
ACTIONS=("P0","P1","P2")
METHODS=("local-phase-adapter","exact-bayesian-change-point",
         "per-code-last-effect","no-feedback-abstain")
REGIMES=("CLEAN","WITHHELD","INVERTED_FEEDBACK")
EFFECT_BASE={"P0":0,"P1":1,"P2":0}
FLIP_ACTION="P2"
INTERFERENCE_STEP=6
DELAY=3
N=12
SEED=b"L10-B7-Original-Synthetic-Development-Episodes-20261024"

def require(ok,why):
    if not ok:raise ValueError("L10_B7_FAIL_CLOSED:"+why)

def canonical(v):
    return custody.canonical_bytes(v)

def sha(v):
    return sha256(canonical(v)).hexdigest()

@dataclass(frozen=True)
class Episode:
    family:str
    split:str
    role:str
    identity:str
    actions:tuple[str,...]
    start_phase:int
    hidden_switch:int

@dataclass(frozen=True)
class Feedback:
    identity:str
    step:int
    action:str
    bit:int
    available_at:int
    event_sha256:str

def create_dev_episode(family,split):
    require(family in FAMILIES and split in SPLITS,"no protected family/role generator")
    base=("P0","P1","P2","P0","P2","P1","P1","P0","P2","P0","P1","P2")
    rotation=(FAMILIES.index(family)+int(split=="CHECK"))%N
    actions=tuple(base[(i+rotation)%N] for i in range(N))
    phase=sha256(SEED+b"|"+family.encode()+b"|"+split.encode()+b"|phase").digest()[0]%2
    # Private change/no-change values are NOT conveyed to policy methods.
    switch=int(split=="CHECK" and family in ("world-switch","world-interference"))
    identity=sha([SCHEMA,ROLE,family,split,list(actions),phase,switch])
    e=Episode(family,split,ROLE,identity,actions,phase,switch)
    validate_episode(e)
    return e

def validate_episode(e):
    require(type(e) is Episode and e.family in FAMILIES and e.split in SPLITS
            and e.role==ROLE and e.start_phase in (0,1)
            and e.hidden_switch in (0,1)
            and len(e.actions)==N and set(e.actions)==set(ACTIONS),"development episode identity")
    require(e.identity==sha([SCHEMA,ROLE,e.family,e.split,list(e.actions),e.start_phase,e.hidden_switch]),
            "source identity change")
    # Exact original invented-source identity, not caller-modifiable hidden bits.
    original=create_identity_only(e.family,e.split)
    require(e.identity==original,"generated source does not match original development grid")
    return True

def create_identity_only(family,split):
    base=("P0","P1","P2","P0","P2","P1","P1","P0","P2","P0","P1","P2")
    rotation=(FAMILIES.index(family)+int(split=="CHECK"))%N
    actions=tuple(base[(i+rotation)%N] for i in range(N))
    phase=sha256(SEED+b"|"+family.encode()+b"|"+split.encode()+b"|phase").digest()[0]%2
    switch=int(split=="CHECK" and family in ("world-switch","world-interference"))
    return sha([SCHEMA,ROLE,family,split,list(actions),phase,switch])

def parity_before(actions,step):
    require(0<=step<=len(actions) and all(x in ACTIONS for x in actions),"action history invalid")
    return sum(x==FLIP_ACTION for x in actions[:step])%2

def truth_bit(e,step):
    validate_episode(e)
    require(type(step) is int and 0<=step<N,"time bound")
    phase=e.start_phase ^ parity_before(e.actions,step)
    if e.split=="CHECK" and step>=INTERFERENCE_STEP:
        phase^=e.hidden_switch
    return EFFECT_BASE[e.actions[step]] ^ phase

class World:
    def __init__(self,e:Episode,regime:str):
        validate_episode(e)
        require(regime in REGIMES,"unknown information regime")
        self._e=e
        self.regime=regime
        self.current_tick=0
        self.pending=[]
        self.delivered=set()
        self.issued=set()
    def deliver(self):
        # Called BEFORE the current prediction; cannot expose current action.
        ready=[f for f in self.pending if f.available_at<=self.current_tick]
        self.pending=[f for f in self.pending if f.available_at>self.current_tick]
        output=[]
        for f in ready:
            require(f.available_at==f.step+DELAY and
                    f.available_at<=self.current_tick and f.step in self.issued
                    and f.event_sha256 not in self.delivered,"late/early/duplicate feedback")
            self.delivered.add(f.event_sha256)
            if self.regime!="WITHHELD":
                output.append(f)
        return tuple(output)
    def act(self,step:int,action:str):
        require(type(step) is int and step==self.current_tick
                and 0<=step<N and action==self._e.actions[step]
                and step not in self.issued,"wrong/duplicated action")
        bit=truth_bit(self._e,step)
        if self.regime=="INVERTED_FEEDBACK":bit^=1
        digest=sha([SCHEMA,self._e.identity,self.regime,step,action,bit,step+DELAY])
        feedback=Feedback(self._e.identity,step,action,bit,step+DELAY,digest)
        self.issued.add(step)
        self.pending.append(feedback)
        self.current_tick+=1
        return feedback.event_sha256
    def flush_fit(self):
        require(self._e.split=="FIT" and len(self.issued)==N,"fit cannot flush incomplete run")
        result=[]
        while self.pending:
            result.extend(self.deliver())
            if self.pending:self.current_tick+=1
        require(len(self.delivered)==N,"lost fit consequences")
        return result

def fit(e,regime):
    require(e.split=="FIT" and regime in REGIMES,"no CHECK source model fit")
    world=World(e,regime)
    results=[]
    for step,code in enumerate(e.actions):
        results.extend(world.deliver())
        world.act(step,code)
    results.extend(world.flush_fit())
    require(len(results)==(0 if regime=="WITHHELD" else N),"missing fit sensory evidence")
    adjusted={}
    raw={}
    for f in results:
        require(f.identity==e.identity and f.action==e.actions[f.step]
                and f.available_at==f.step+DELAY,"fit event custody")
        value=f.bit ^ parity_before(e.actions,f.step)
        if f.action in adjusted:
            require(adjusted[f.action]==value,"unexpected nonstationary FIT source")
        adjusted[f.action]=value
        raw[f.action]=f.bit
    if regime=="WITHHELD":
        require(not adjusted,"labels generated despite information veto")
        relative={}
    else:
        require(set(adjusted)==set(ACTIONS),"fit failed code coverage")
        relative={code:adjusted[code]^adjusted["P0"] for code in ACTIONS}
        require(relative["P0"]==0,"global phase invariance")
    model=dict(schema="forge.optimizer.language.l10.b7-fit-state-v1",
               role=ROLE,fit_episode_identity=e.identity,
               regime=regime,relative=relative,last_by_code=raw,
               received_fit_effects=len(results),
               public_flip_action=FLIP_ACTION)
    return model

def _phase_candidates(model,received,actions):
    # Posterior over check episode start bit and unannounced step-6 change.
    rel=model["relative"]
    if not rel:return ()
    hypotheses=[]
    for phase in (0,1):
        for switch in (0,1):
            valid=True
            for f in received:
                if f.action not in rel:continue
                pred=rel[f.action] ^ phase ^ parity_before(actions,f.step)
                if f.step>=INTERFERENCE_STEP:pred^=switch
                if pred!=f.bit:
                    valid=False
                    break
            if valid:hypotheses.append((phase,switch))
    return tuple(hypotheses)

def predict(method,model,received,actions,step):
    require(method in METHODS and model["role"]==ROLE and model["regime"] in REGIMES
            and type(step) is int and 0<=step<N
            and all(type(f) is Feedback and f.available_at<=step and
                    f.action==actions[f.step] for f in received),
            "model shown future information")
    code=actions[step]
    if method=="no-feedback-abstain" or not model["relative"]:
        return None
    if method=="per-code-last-effect":
        recent={**model["last_by_code"]}
        for f in received:recent[f.action]=f.bit
        return recent.get(code)
    if method=="exact-bayesian-change-point":
        hyps=_phase_candidates(model,received,actions)
        vals={model["relative"][code] ^ phase ^ parity_before(actions,step) ^
              (int(step>=INTERFERENCE_STEP)*switch) for phase,switch in hyps}
        return next(iter(vals)) if len(vals)==1 else None
    if method=="local-phase-adapter":
        # Local "latest consequence" estimator; can confidently mispredict
        # during a delayed hidden switch. Unlike the Bayesian controller it
        # does not model change-point uncertainty.
        if not received:return None
        newest=received[-1]
        phase=newest.bit ^ model["relative"][newest.action] ^ parity_before(actions,newest.step)
        return model["relative"][code] ^ phase ^ parity_before(actions,step)
    raise ValueError("unrecognized method")

def snapshot(model,received):
    # Development-only public learner state. No future effects or hidden flags.
    return canonical({"schema":"forge.optimizer.language.l10.b7-restart-v1",
        "model":model,"received":[[x.identity,x.step,x.action,x.bit,x.available_at,x.event_sha256]
                                    for x in received]})

def restore(raw):
    require(type(raw) is bytes and 0<len(raw)<12000,"restart length")
    d=json.loads(raw)
    require(type(d) is dict and set(d)=={"schema","model","received"} and
            d["schema"]=="forge.optimizer.language.l10.b7-restart-v1","restart schema")
    received=tuple(Feedback(*row) for row in d["received"])
    require(snapshot(d["model"],received)==raw,"noncanonical restart drift")
    return d["model"],received

def benchmark_family(family,regime,method):
    require(family in FAMILIES and regime in REGIMES and method in METHODS,"identity boundary")
    tr=create_dev_episode(family,"FIT")
    check=create_dev_episode(family,"CHECK")
    started=time.perf_counter();cpu=time.process_time()
    tracemalloc.start()
    model=fit(tr,regime)
    fit_wall=time.perf_counter()-started
    fit_cpu=time.process_time()-cpu
    world=World(check,regime)
    received=[]
    good=0;abstentions=0;before_good=0;after_good=0
    first_release=None
    restarts=0
    e_start=time.perf_counter();e_cpu=time.process_time()
    for step,action in enumerate(check.actions):
        delivered=world.deliver()
        for f in delivered:
            require(f.step<=step-DELAY,"future sensory information")
            received.append(f)
            if f.step>=INTERFERENCE_STEP and first_release is None:
                first_release=step
        # Restart only after at least one valid delivered check consequence.
        if step==4:
            raw=snapshot(model,received)
            model,recovered=restore(raw)
            require(list(recovered)==received and sha256(raw).hexdigest()==sha256(snapshot(model,recovered)).hexdigest(),
                    "restart retention failure")
            restarts+=1
        answer=predict(method,model,received,check.actions,step)
        truth=truth_bit(check,step)
        score=int(answer is not None and answer==truth)
        good+=score
        abstentions+=int(answer is None)
        if step<INTERFERENCE_STEP:before_good+=score
        else:after_good+=score
        world.act(step,action)
    require(len(world.issued)==N and restarts==1 and
            (first_release is None or first_release>=INTERFERENCE_STEP+DELAY),
            "incomplete check or premature intervention evidence")
    eval_wall=time.perf_counter()-e_start
    eval_cpu=time.process_time()-e_cpu
    peak=tracemalloc.get_traced_memory()[1];tracemalloc.stop()
    return dict(family_sha256=sha256(family.encode()).hexdigest(),
       fit_source_sha256=tr.identity,check_source_sha256=check.identity,
       regime=regime,method=method,
       episode_steps=N,correct=good,abstentions=abstentions,
       pre_switch_correct=before_good,post_switch_correct=after_good,
       first_interference_feedback_tick=first_release,
       fitted_state_sha256=sha(model),
       fit_state_bytes=len(canonical(model)),
       recovered_model_state=True,simulated_restarts=restarts,
       train_fit_wall_seconds=round(fit_wall,9),
       train_fit_cpu_seconds=round(fit_cpu,9),
       check_wall_seconds=round(eval_wall,9),
       check_cpu_seconds=round(eval_cpu,9),peak_python_traced_bytes=peak)

def benchmark():
    results=[benchmark_family(family,regime,method)
             for regime in REGIMES for method in METHODS for family in FAMILIES]
    require(len(results)==36,"missing comparison")
    out=[]
    for regime in REGIMES:
        for method in METHODS:
            rows=[x for x in results if x["regime"]==regime and x["method"]==method]
            require(len(rows)==3 and len({x["check_source_sha256"] for x in rows})==3,
                    "development case custody")
            out.append({"regime":regime,"method":method,
                "correct":sum(x["correct"] for x in rows),
                "decisions":N*3,
                "abstentions":sum(x["abstentions"] for x in rows),
                "pre_switch_correct":sum(x["pre_switch_correct"] for x in rows),
                "post_switch_correct":sum(x["post_switch_correct"] for x in rows),
                "family_scores":[[x["family_sha256"],x["correct"],x["abstentions"],
                                   x["fitted_state_sha256"]] for x in rows]})
    require(all(x["correct"]==0 and x["abstentions"]==36
                for x in out if x["regime"]=="WITHHELD"),"no-effect false successes")
    return dict(schema=SCHEMA,status="DEV_ONLY_STATE_DEPENDENT_DELAYED_FEEDBACK_NO_TRANSFER_GO",
       families=3,fit_episodes=3,check_episodes=3,steps_per_episode=N,
       delay_ticks=DELAY,interference_step=INTERFERENCE_STEP,
       effects_per_code_nonbijective=True,methods=list(METHODS),
       regimes=list(REGIMES),outcomes=out,
       raw_sequences_persisted=False,
       original_l9_webnlg_consumed=False,
       prospective_first_use_consumed=False,
       native_causal_discovery_proven=False,
       scientific_go=False)

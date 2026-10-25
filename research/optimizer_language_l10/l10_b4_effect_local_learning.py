#!/usr/bin/env python3
"""L10-B4 online local effect association vs equally-informed fitted controls.

Invented L10 DEV_FIT / DEV_CHECK only. Sensor consequences convey semantic
information; a local association is not causal inference or novel cognition.
No L9, WebNLG, future source generator, heldout or paid infrastructure.
"""
from __future__ import annotations
from collections import Counter, defaultdict
from dataclasses import dataclass
from hashlib import sha256
import json
import math
import time
import tracemalloc

import l10_dev_source_custody as source
import l10_semantic_dev_oracle as oracle

SCHEMA="forge.optimizer.language.l10.b4-online-effect-learning-dev-v1"
ROLE="L10_SYNTHETIC_DEV"
REGIMES=("FEEDBACK_OBSERVED","FEEDBACK_WITHHELD","FEEDBACK_PERMUTED")
CHANNELS=(("E0","located_in"),("E1","owns"),("E2","parent_of"))
EFFECTS=tuple(k for k,_ in CHANNELS)
# This is an explicit PUBLIC effect-channel glossary, not inferred language.
GLOSSARY=dict(CHANNELS)
METHODS=("online-local-count","batch-conditional-frequency",
         "dirichlet-posterior-map","no-experience","effect-permutation-ablation")
EMPTY="NO_CONSEQUENCE_SIGNAL"

@dataclass(frozen=True)
class Event:
    role: str
    fit_source_sha256: str
    ordinal: int
    relation_code: str
    effect_channel: str
    event_sha256: str

@dataclass(frozen=True)
class Observation:
    relation_code: str
    effect_channel: str

def require(ok,reason):
    if not ok:raise ValueError("L10_B4_EXPERIENCE_CUSTODY_BLOCKED:"+reason)

def canonical(v):
    return source.canonical_bytes(v)

def _hash(v):
    return sha256(canonical(v)).hexdigest()

def _event_id(f:source.Fixture,index,code,effect,regime):
    return _hash([SCHEMA,ROLE,f.fixture_sha256,index,code,effect,regime])

def _effect_map_from_fixture(f,edge,regime):
    # The WORLD ADAPTER alone inspects DEV_FIT truth to derive a consequence.
    # The online learner and all fitted controls receive Observation only.
    if regime=="FEEDBACK_WITHHELD":return EMPTY
    index={p:i for i,(_,p) in enumerate(CHANNELS)}
    true=next(v.predicate for v in f.target.claims
         if (v.subject,v.object,v.polarity)==
            (edge.subject,edge.object,edge.polarity))
    effect_id=index[true]
    if regime=="FEEDBACK_PERMUTED":effect_id=(effect_id+1)%len(EFFECTS)
    return EFFECTS[effect_id]

def make_fit_events(fit,regime):
    require(regime in REGIMES and type(fit) in (tuple,list)
            and len(fit)==12,"invalid DEV_FIT study design")
    ids=set();entries=[]
    for f in fit:
        source.validate_fixture(f)
        require(f.role==ROLE and f.split=="DEV_FIT"
                and f.input.information_regime=="WITHHELD_MAPPING"
                and not f.input.public_lexicon,"source/semantic mapping leak")
        require(f.fixture_sha256 not in ids,"duplicate fit source")
        ids.add(f.fixture_sha256)
        for index,edge in enumerate(f.input.observed):
            effect=_effect_map_from_fixture(f,edge,regime)
            entries.append(Event(ROLE,f.fixture_sha256,index,
                         edge.relation_code,effect,
                         _event_id(f,index,edge.relation_code,effect,regime)))
    require(len(entries)>=12,"too few observations")
    validate_fit_events(fit,entries,regime)
    return entries

def validate_fit_events(fit,events,regime):
    require(type(events) in (list,tuple) and regime in REGIMES,"untrusted event batch")
    expected=[]
    for f in fit:
        source.validate_fixture(f)
        require(f.split=="DEV_FIT" and f.role==ROLE
                and f.input.information_regime=="WITHHELD_MAPPING",
                "check/heldout fit leakage")
        for index,obs in enumerate(f.input.observed):
            effect=_effect_map_from_fixture(f,obs,regime)
            expected.append(Event(ROLE,f.fixture_sha256,index,obs.relation_code,
                        effect,_event_id(f,index,obs.relation_code,effect,regime)))
    require(tuple(events)==tuple(expected),"reordered/modified/partial event custody")
    require(len(set(e.event_sha256 for e in events))==len(events),
            "duplicate event identity")
    return True

def public_event(event):
    require(type(event) is Event and event.role==ROLE
            and event.relation_code in source.PREDICATE_CODES
            and event.effect_channel in (*EFFECTS,EMPTY),"invalid consequence event")
    return Observation(event.relation_code,event.effect_channel)

def _state_body(counts,n):
    rows=tuple(sorted((code,effect,count)
             for (code,effect),count in counts.items() if count))
    return {"schema":"forge.optimizer.language.l10.b4-local-state-v1",
            "events_seen":n,"relations":list(map(list,rows))}

class LocalMemory:
    def __init__(self):
        self.counts=Counter()
        self.events_seen=0
    def update(self,obs:Observation):
        require(type(obs) is Observation and
                obs.relation_code in source.PREDICATE_CODES
                and obs.effect_channel in (*EFFECTS,EMPTY),"bad local consequence")
        self.events_seen+=1
        if obs.effect_channel!=EMPTY:
            self.counts[(obs.relation_code,obs.effect_channel)]+=1
        return self
    def snapshot(self):
        self.validate()
        return canonical(_state_body(self.counts,self.events_seen))
    def digest(self):
        return sha256(self.snapshot()).hexdigest()
    def validate(self):
        require(type(self.events_seen) is int and self.events_seen>=0,"event count")
        require(all(k[0] in source.PREDICATE_CODES and k[1] in EFFECTS
                    and type(v) is int and v>0 for k,v in self.counts.items()),
                "corrupt local association")
        require(sum(self.counts.values())<=self.events_seen,"source event denominator")
        return True
    @classmethod
    def restore(cls,raw:bytes):
        require(type(raw) is bytes and 0<len(raw)<4096,"bad stored memory size")
        body=json.loads(raw)
        require(type(body) is dict and set(body)=={"schema","events_seen","relations"}
                and body["schema"]=="forge.optimizer.language.l10.b4-local-state-v1"
                and type(body["relations"]) is list,"memory schema")
        obj=cls()
        obj.events_seen=body["events_seen"]
        require(type(obj.events_seen) is int and obj.events_seen>=0,"event count")
        require(all(type(x) is list and len(x)==3 and
                    type(x[0]) is str and type(x[1]) is str and
                    type(x[2]) is int and x[2]>0 for x in body["relations"]),
                "row schema")
        keys=[(x[0],x[1]) for x in body["relations"]]
        require(len(keys)==len(set(keys)),"duplicate stored associations")
        obj.counts.update({(x[0],x[1]):x[2] for x in body["relations"]})
        obj.validate()
        require(obj.snapshot()==raw,"noncanonical state or data drift")
        return obj

def _winner(counts,code,alpha=0.):
    require(type(code) is str and code in source.PREDICATE_CODES,"unknown test code")
    require(type(alpha) in (int,float) and 0<=alpha<=1,"invalid Dirichlet strength")
    scores=tuple((effect,counts.get((code,effect),0)+alpha) for effect in EFFECTS)
    largest=max(v for _,v in scores)
    winners=[e for e,v in scores if v==largest]
    # Prior alone never creates information. Ties and missing counts abstain.
    if len(winners)!=1 or largest<=alpha:return None
    return winners[0]

def translate(inp:source.ModelInput,find_effect):
    require(type(inp) is source.ModelInput and
            inp.information_regime=="WITHHELD_MAPPING"
            and inp.public_lexicon==(),"DEV_CHECK cannot receive direct semantic map")
    out=[]
    for c in inp.observed:
        require(type(c) is source.Observed and c.relation_code in source.PREDICATE_CODES,
                "unseen observation schema")
        effect=find_effect(c.relation_code)
        if effect is None:return None
        pred=GLOSSARY[effect]
        fact=oracle.Claim(c.subject,pred,c.object,c.polarity)
        require(oracle.valid_claim(fact),"illegal learned proposition")
        out.append(f"{fact.subject} :: {fact.predicate} :: {fact.object} :: {'+' if fact.polarity==1 else '-'}")
    return "; ".join(out)

def _learn_all(events):
    memory=LocalMemory()
    for e in events:memory.update(public_event(e))
    return memory

def benchmark_dev(fit,check,regime):
    require(regime in REGIMES and type(fit) in (tuple,list)
            and type(check) in (tuple,list)
            and len(fit)==12 and len(check)==12,"wrong dev role cardinality")
    for f in check:
        source.validate_fixture(f)
        require(f.role==ROLE and f.split=="DEV_CHECK" and
                f.input.information_regime=="WITHHELD_MAPPING","heldout role or mapping leakage")
    events=make_fit_events(fit,regime)
    start=time.perf_counter();cpu=time.process_time()
    tracemalloc.start()
    local=_learn_all(events)
    fit_time=time.perf_counter()-start
    fit_cpu=time.process_time()-cpu
    snap=local.snapshot()
    restored=LocalMemory.restore(snap)
    require(restored.counts==local.counts and restored.events_seen==len(events),
            "restart retention not proven")
    # Strong classical competitors see EXACTLY the same Observation stream.
    fit_start=time.perf_counter();fit_cpu_start=time.process_time()
    batch=Counter((o.relation_code,o.effect_channel) for o in map(public_event,events)
                  if o.effect_channel!=EMPTY)
    batch_time=time.perf_counter()-fit_start;batch_cpu=time.process_time()-fit_cpu_start
    require(batch==local.counts,"information budgets not matched")
    methods={
        "online-local-count":lambda code:_winner(restored.counts,code),
        "batch-conditional-frequency":lambda code:_winner(batch,code),
        "dirichlet-posterior-map":lambda code:_winner(batch,code,alpha=.5),
        "no-experience":lambda code:None,
        "effect-permutation-ablation":lambda code:_winner(
          {(k,EFFECTS[(EFFECTS.index(e)+1)%3]):v for (k,e),v in batch.items()},code)
    }
    require(tuple(methods)==METHODS,"method identity drift")
    output=[]
    for method,resolve in methods.items():
        start_eval=time.perf_counter();start_cpu=time.process_time()
        byfam={name:Counter() for name in source.FAMILIES}
        for f in check:
            # Predictor gets ONLY observed public coded relations.
            observed=source.public_input(f)
            text=translate(observed,resolve)
            measure=oracle.evaluate_one(f.target,text)
            byfam[f.family].update(measure)
            byfam[f.family]["cases"]+=1
        families=[]
        for name in source.FAMILIES:
            c=byfam[name]
            require(c["cases"]==4,"incomplete development family")
            families.append({"family_sha256":sha256(name.encode()).hexdigest(),
                "cases":c["cases"],"exact":c["exact_semantic_graph_success"],
                "abstentions":c["abstentions"],"missing":c["missing_claims"],
                "extra":c["extra_claims"],"contradiction":c["contradictory_claims"]})
        output.append({"method":method,"family_scores":families,
            "dev_check_examples":12,
            "micro_exact":sum(x["exact"] for x in families)/12,
            "micro_abstention":sum(x["abstentions"] for x in families)/12,
            "macro_exact":sum(x["exact"]/x["cases"] for x in families)/3,
            "fit_wall_seconds":round(fit_time if method=="online-local-count" else
                   batch_time if method in METHODS[1:3] else 0.,9),
            "fit_cpu_seconds":round(fit_cpu if method=="online-local-count" else
                   batch_cpu if method in METHODS[1:3] else 0.,9),
            "inference_wall_seconds":round(time.perf_counter()-start_eval,9),
            "inference_cpu_seconds":round(time.process_time()-start_cpu,9),
            "state_bytes":len(snap) if method=="online-local-count" else
                 len(canonical(_state_body(batch,len(events)))) if method in METHODS[1:3] else 0,
            "flops":"NOT_MEASURED","energy":"NOT_MEASURED"})
    peak=tracemalloc.get_traced_memory()[1];tracemalloc.stop()
    require(sum(x["dev_check_examples"] for x in output)==60,"missing control scores")
    if regime=="FEEDBACK_WITHHELD":
        require(output[0]["micro_exact"]==0 and output[0]["micro_abstention"]==1,
                "information-free learned false positives")
    if regime=="FEEDBACK_OBSERVED":
        require(output[0]["micro_exact"]==output[1]["micro_exact"]==
                output[2]["micro_exact"],"local result not matched to conventional")
    return {"schema":SCHEMA,"status":"INVENTED_DEVELOPMENT_CAUSAL_SENSOR_ASSOCIATION_ONLY",
        "regime":regime,"fitted_examples":12,"fit_experience_events":len(events),
        "checked_examples":12,"families":3,"methods":output,
        "event_custody_sha256":_hash([e.event_sha256 for e in events]),
        "learned_state_sha256":sha256(snap).hexdigest(),
        "effect_glossary_sha256":_hash(CHANNELS),
        "peak_python_traced_bytes":peak,
        "restart_state_recovery":True,
        "protection_role":ROLE,"prospective_examples_used":0,
        "l9_used":False,"official_webnlg_test_used":False,
        "native_causal_representation_demonstrated":False,
        "scientific_go":False}

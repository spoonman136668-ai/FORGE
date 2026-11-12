#!/usr/bin/env python3
"""L10-B bounded matched-information comparator interfaces (DEV fixtures only).

Every method sees the same opaque propositions and allowed public relation
lexicon. No method receives the DevelopmentCase truth in evaluation. Model
candidate is an externally supplied callback, never a built-in claimed learner.
No prospective source generation, training or first-use experiment.
"""
from __future__ import annotations
from collections import Counter
from dataclasses import dataclass
from hashlib import sha256
import json
import math
import time
import tracemalloc
from typing import Callable

import l10_dev_source_custody as src
import l10_semantic_dev_oracle as oracle

SCHEMA="forge.optimizer.language.l10.matched-controls-development-v1"
ARMS=("canonical-facts","rule-paraphrase","train-reference-retrieval",
      "memory-table","abstention-negative","shuffled-polarity-negative",
      "candidate-interface")
OBS="DEVELOPMENT_ONLY_NOT_PROSPECTIVE_SCIENTIFIC_EVIDENCE"

@dataclass(frozen=True)
class Interface:
    name:str
    predict:Callable[[src.ModelInput],str|None]
    fitted_state_bytes:int
    fit_wall_seconds:float
    fit_cpu_seconds:float

def require(ok,reason):
    if not ok:raise ValueError("L10_MATCHED_COMPARATOR_BLOCKED:"+reason)

def signature(x:src.ModelInput):
    require(type(x) is src.ModelInput,"models must see observed interface only")
    return tuple((c.subject,c.relation_code,c.object,c.polarity) for c in x.observed)

def allowed(x:src.ModelInput):
    require(type(x) is src.ModelInput and x.information_regime in src.EXPOSURES,
            "unknown model input")
    expected=src.PREDICATE_LEXICON if x.information_regime=="KNOWN_MAPPING" else ()
    require(x.public_lexicon==expected,"unauthorized mapping exposure")
    require(type(x.observed) is tuple and bool(x.observed),"empty observation")
    for c in x.observed:
        require(type(c) is src.Observed and c.relation_code in src.PREDICATE_CODES
                and c.polarity in (-1,1),"unknown observed code")
    return dict(x.public_lexicon)

def project(x:src.ModelInput):
    mapping=allowed(x)
    if not mapping:return None
    claims=[]
    for c in x.observed:
        p=mapping.get(c.relation_code)
        require(p in oracle.PREDICATES,"unknown predicate translation")
        claim=oracle.Claim(c.subject,p,c.object,c.polarity)
        require(oracle.valid_claim(claim),"malformed external observation")
        claims.append(claim)
    return tuple(claims)

def canonical_facts(x):
    claims=project(x)
    if claims is None:return None
    return "; ".join(f"{c.subject} :: {c.predicate} :: {c.object} :: {'+' if c.polarity==1 else '-'}" for c in claims)

_TEMPLATES={
"located_in":("resides in","does not reside in"),
"owns":("owns","does not own"),
"parent_of":("is parent of","is not parent of")}
def rule_paraphrase(x):
    claims=project(x)
    if claims is None:return None
    return "; ".join(f"{c.subject} {_TEMPLATES[c.predicate][int(c.polarity==-1)]} {c.object}."
                    for c in claims)

def flip_polarity(x):
    claims=project(x)
    if claims is None:return None
    return "; ".join(f"{c.subject} :: {c.predicate} :: {c.object} :: {'-' if c.polarity==1 else '+'}" for c in claims)

def freeze_fit(fit_examples):
    require(type(fit_examples) in (tuple,list) and len(fit_examples)>0,"no fitted training examples")
    seen=set()
    rows={}
    for f in fit_examples:
        src.validate_fixture(f)
        require(f.split=="DEV_FIT","fit-leakage DEV_CHECK/heldout")
        require(f.fixture_sha256 not in seen,"duplicate fitting example")
        seen.add(f.fixture_sha256)
        inp=src.public_input(f)
        key=json.dumps([signature(inp),inp.public_lexicon],separators=(",",":"))
        # Only fitting-label text is used here. No heldout truth or evaluation
        # reference enters fit, even when the candidate implements own fitting.
        ref=canonical_facts(inp)
        if ref is not None:rows[key]=ref
    require(len(rows)==len(fit_examples) or all(src.public_input(f).information_regime=="WITHHELD_MAPPING"
                                              for f in fit_examples),"fit records missing")
    state_bytes=src.canonical_bytes(rows)
    return rows,len(state_bytes)

def make_controls(fit_examples,candidate:Callable[[src.ModelInput],str|None]):
    require(callable(candidate),"candidate model callback must be supplied explicitly")
    t=time.perf_counter();cpu=time.process_time()
    state,nbytes=freeze_fit(fit_examples)
    ft=time.perf_counter()-t;fc=time.process_time()-cpu
    def retrieve(x):
        allowed(x)
        key=json.dumps([signature(x),x.public_lexicon],separators=(",",":"))
        return state.get(key)
    # Memorization is a separate simple fitted table, with the same input budget.
    memory=dict(state)
    def memory_lookup(x):
        allowed(x)
        return memory.get(json.dumps([signature(x),x.public_lexicon],separators=(",",":")))
    methods=[
        Interface("canonical-facts",canonical_facts,0,0.,0.),
        Interface("rule-paraphrase",rule_paraphrase,0,0.,0.),
        Interface("train-reference-retrieval",retrieve,nbytes,ft,fc),
        Interface("memory-table",memory_lookup,len(src.canonical_bytes(memory)),ft,fc),
        Interface("abstention-negative",lambda x:None if allowed(x) is not None else None,0,0.,0.),
        Interface("shuffled-polarity-negative",flip_polarity,0,0.,0.),
        Interface("candidate-interface",candidate,0,0.,0.)
    ]
    require(tuple(m.name for m in methods)==ARMS,"method grid drift")
    return methods

def benchmark_dev(fixtures,methods,regime):
    src.validate_collection(fixtures,regime)
    require(type(methods) in (list,tuple) and len(methods)==len(ARMS)
            and tuple(x.name for x in methods)==ARMS,"missing/changed control")
    check=[f for f in fixtures if f.split=="DEV_CHECK"]
    require(len(check)==len(src.FAMILIES)*src.FIXTURES_PER_SPLIT,"missing dev check")
    rows=[]
    for meth in methods:
        counts={fam:Counter() for fam in src.FAMILIES}
        begin=time.perf_counter(); cpu=time.process_time()
        tracemalloc.start()
        for f in check:
            # Never pass target oracle objects, source identity, split, or
            # benchmark labels to a predictor. All arms receive same input.
            input_only=src.public_input(f)
            res=meth.predict(input_only)
            score=oracle.evaluate_one(f.target,res)
            counts[f.family].update(score)
            counts[f.family]["cases"]+=1
        peak=tracemalloc.get_traced_memory()[1];tracemalloc.stop()
        ms=[]
        for fam in src.FAMILIES:
            values=counts[fam]
            n=values["cases"]
            require(n==src.FIXTURES_PER_SPLIT and values["expected_claims"]>0,
                    "missing family scoring")
            ms.append({
               "family_sha256":sha256(fam.encode()).hexdigest(),
               "cases":n,
               "expected_claims":values["expected_claims"],
               "supported_claims":values["supported_claims"],
               "missing_claims":values["missing_claims"],
               "extra_claims":values["extra_claims"],
               "contradictions":values["contradictory_claims"],
               "abstentions":values["abstentions"],
               "unparseable_clauses":values["unparseable_clauses"],
               "duplicate_claims":values["duplicate_claims"],
               "exact_success":values["exact_semantic_graph_success"],
               "exact_rate":round(values["exact_semantic_graph_success"]/n,9)
            })
        rows.append(dict(arm=meth.name,information_regime=regime,
          source_role=src.DEV_ROLE,fit_examples=sum(f.split=="DEV_FIT" for f in fixtures),
          evaluation_examples=len(check),family_metrics=ms,
          macro_exact_rate=round(sum(x["exact_rate"] for x in ms)/len(ms),9),
          micro_exact_rate=round(sum(x["exact_success"] for x in ms)/len(check),9),
          fit_wall_seconds=round(meth.fit_wall_seconds,9),
          fit_cpu_seconds=round(meth.fit_cpu_seconds,9),
          serialized_fitted_state_bytes=meth.fitted_state_bytes,
          inference_wall_seconds=round(time.perf_counter()-begin,9),
          inference_cpu_seconds=round(time.process_time()-cpu,9),
          peak_python_traced_bytes=peak,
          flops="NOT_MEASURED",energy="NOT_MEASURED"))
    out=dict(schema=SCHEMA,status=OBS,source_role=src.DEV_ROLE,
       information_regime=regime,method_count=len(rows),
       methods=rows,source_identity_sha256=sha256(src.canonical_bytes(
          src.manifest_only(fixtures,regime))).hexdigest(),
       comparisons_are_development_only=True,
       candidate_is_untrained_dev_interface=True,
       canonical_baseline_semantic_ceiling=True,
       prospective_source_examples_consumed=0,
       l9_audit_reused=False,official_webnlg_test_consumed=False,
       scientific_go=False)
    require(len(rows)==7 and all(x["evaluation_examples"]==12 for x in rows),"partial controls")
    # Canonical baseline will score 100% on known mapping because complete truth
    # is already present in observations; therefore cannot claim semantic superiority.
    if regime=="KNOWN_MAPPING":
        require(rows[0]["micro_exact_rate"]==1.0,"unexpected oracle baseline failure")
    else:
        require(all(x["micro_exact_rate"]==0.0 for x in rows[:6]),
                "insufficient-information comparator falsely succeeded")
    return out

#!/usr/bin/env python3
"""L9 prespecified unfamiliar-category numerical first-use scoring core.

NO source fetch, filesystem writes, training, checkpoint selection, or protected
reference access at import. This module is qualified on invented data only.
Real first-use admission is a separate, one-shot controlled workflow.
"""
from __future__ import annotations
from collections import Counter, defaultdict
from dataclasses import dataclass
import hashlib
import json
import math
import re
import time
from typing import Callable, Sequence
import l9_model_suite as model
import l9_split_builder as split
import l9_train_select_candidate as select

ROLE_SHA="b9995c1846f5e1d99bf8bc4083dde0ebb41140906284bcf050a7ed6fe0efe726"
SUITE="710ce648a30ffc55647f689c5f4aa3ac13b07066"
SCHEMA="forge.optimizer.language.l9.unfamiliar-category-numeric-first-use-v1"
ARMS=(
    "CANONICAL_FACTS_NONFLUENT_CONTROL",
    "TRAIN_REFERENCE_RETRIEVAL",
    "COMPOSITIONAL_PATTERN",
    "GRU_SEQ2SEQ-1701","GRU_SEQ2SEQ-1702",
    "SMALL_TRANSFORMER-1701","SMALL_TRANSFORMER-1702",
)
EXPECTED_AUDIT_COUNT=319
EXPECTED_CATEGORIES=3
_NEG=re.compile(r"\b(?:not|never|no|without|neither|isn't|wasn't|doesn't|didn't)\b",re.I)
_PLACEHOLDER=re.compile(r"\{[SO]\}|<\s*(?:subject|object|slot)\s*>",re.I)
_TERMINAL=(".","?","!")
_WORD=re.compile(r"\w+",re.UNICODE)
_NINE_DECIMAL=9

@dataclass(frozen=True)
class HeldoutCase:
    category: str
    role: str
    graph_sha256: str
    triples: tuple[model.Triple,...]
    references: tuple[str,...]

def require(ok:bool,message:str)->None:
    if not ok:raise ValueError("L9_AUDIT_SCORER_FAIL_CLOSED:"+message)
def avg(values):
    require(len(values)>0,"empty aggregate")
    return sum(values)/len(values)
def rounded(x):
    require(isinstance(x,(float,int)) and math.isfinite(x),"nonfinite metric")
    return round(x,_NINE_DECIMAL)
def _cat_hash(category:str)->str:
    return hashlib.sha256(split.norm_category(category).encode("utf-8")).hexdigest()
def tokens(text:str)->Counter:
    return Counter(_WORD.findall(model.normalize_space(text).casefold()))
def token_f1(a:str,b:str)->float:
    if not a or not b:return 0.0
    x,y=tokens(a),tokens(b)
    common=sum((x & y).values())
    if not common:return 0.0
    px=common/sum(x.values())
    ry=common/sum(y.values())
    return 2*px*ry/(px+ry)
def _entity_mentioned(entity:str,output:str)->bool:
    alias=model.surface_alias(entity).casefold()
    if not alias:return False
    # Bounded case-insensitive non-alphanumeric word boundaries avoid substring false hits.
    return bool(re.search(r"(?<!\w)"+re.escape(alias)+r"(?!\w)",output.casefold()))
def _validate_cases(cases:Sequence[HeldoutCase],train_select_graphs:set[str],
                    expected_count:int=EXPECTED_AUDIT_COUNT,
                    expected_categories:int=EXPECTED_CATEGORIES):
    require(len(cases)==expected_count and expected_count>0,"held-out count")
    require(len(train_select_graphs)>0,"missing training graph custody")
    categories=set(); seen=set()
    for row in cases:
        require(type(row) is HeldoutCase and row.role=="L9_AUDIT_DEV","non-audit role")
        cat=split.norm_category(row.category)
        require(cat==row.category,"category canonicalization")
        require(split.category_partition(cat)=="L9_AUDIT_CATEGORY","training category leakage")
        categories.add(cat)
        require(type(row.triples) is tuple and len(row.triples)>0
                and all(type(t) is model.Triple for t in row.triples),"triples schema")
        canonical=split.graph_identity(tuple((t.subject,t.predicate,t.object) for t in row.triples))
        require(canonical==row.graph_sha256,"graph hash or content drift")
        require(canonical not in train_select_graphs,"train/audit graph overlap")
        require(type(row.references) is tuple and len(row.references)>0
                and all(type(r) is str and bool(model.normalize_space(r)) for r in row.references),
                "incomplete reference set")
        key=(cat,canonical)
        require(key not in seen,"duplicate audit graph")
        seen.add(key)
    require(len(categories)==expected_categories,"missing held-out categories")
    return sorted(categories)
def _new_stats():
    return dict(examples=0,triples=0,triple_hits=0,subject_object_slots=0,
       subject_object_slot_hits=0,missing_triples=0,abstentions=0,
       negation_marker_examples=0,extra_train_entity_mentions=0,
       terminal_punctuation_examples=0,repeated_adjacent_token_count=0,
       unresolved_placeholder_examples=0,reference_count=0,reference_bytes=0,
       chrF_reference_sum=0.0,token_f1_reference_sum=0.0)
def _score_one(acc,row:HeldoutCase,output:str|None,proxies,known_entities):
    require(output is None or type(output) is str,"inference non-string")
    acc["examples"]+=1
    acc["triples"]+=len(row.triples)
    if output is None:
        acc["abstentions"]+=1
    hit,denom=select.coverage(output,row.triples,proxies)
    require(denom==len(row.triples) and 0<=hit<=denom,"coverage internal")
    acc["triple_hits"]+=hit
    acc["missing_triples"]+=denom-hit
    folded=model.normalize_space(output).casefold() if output else ""
    input_entities={model.surface_alias(v).casefold() for t in row.triples for v in (t.subject,t.object)}
    for t in row.triples:
        for v in (t.subject,t.object):
            acc["subject_object_slots"]+=1
            if output and _entity_mentioned(v,output):
                acc["subject_object_slot_hits"]+=1
    if output and _NEG.search(output):acc["negation_marker_examples"]+=1
    if output and output.rstrip().endswith(_TERMINAL):
        acc["terminal_punctuation_examples"]+=1
    if output and _PLACEHOLDER.search(output):
        acc["unresolved_placeholder_examples"]+=1
    word_seq=_WORD.findall(folded)
    acc["repeated_adjacent_token_count"]+=sum(x==y for x,y in zip(word_seq,word_seq[1:]))
    if output and known_entities:
        acc["extra_train_entity_mentions"]+=sum(
             _entity_mentioned(s,output) for s in known_entities if s not in input_entities
        )
    # All references are scored with equal weight within a case, not best-reference cherry picking.
    n=len(row.references)
    acc["reference_count"]+=n
    acc["reference_bytes"]+=sum(len(ref.encode("utf-8")) for ref in row.references)
    acc["chrF_reference_sum"]+=avg([select.chrf(output,ref) for ref in row.references])
    acc["token_f1_reference_sum"]+=avg([token_f1(output,ref) for ref in row.references])

def _finish(a,category_id):
    n=a["examples"]; d=a["triples"]; slot=a["subject_object_slots"]
    require(n>0 and d>0 and slot==2*d and a["reference_count"]>=n,"invalid stats")
    require(a["missing_triples"]+a["triple_hits"]==d,"coverage denominator")
    require(0<=a["abstentions"]<=n,"abstentions")
    return dict(category_sha256=category_id,examples=n,triples=d,
      triple_proxy_hits=a["triple_hits"],triple_denominator=d,
      missing_triples_proxy=a["missing_triples"],
      requested_content_proxy_coverage=rounded(a["triple_hits"]/d),
      entity_slot_hits=a["subject_object_slot_hits"],entity_slot_denominator=slot,
      normalized_entity_slot_coverage=rounded(a["subject_object_slot_hits"]/slot),
      abstentions=a["abstentions"],reference_count=a["reference_count"],
      reference_bytes=a["reference_bytes"],
      chrF_all_references_mean_per_example=rounded(a["chrF_reference_sum"]/n),
      token_f1_all_references_mean_per_example=rounded(a["token_f1_reference_sum"]/n),
      negation_marker_examples=a["negation_marker_examples"],
      extra_train_entity_mentions=a["extra_train_entity_mentions"],
      terminal_punctuation_examples=a["terminal_punctuation_examples"],
      unresolved_placeholder_examples=a["unresolved_placeholder_examples"],
      repeated_adjacent_token_count=a["repeated_adjacent_token_count"])
def evaluate_arm(arm:str,cases:Sequence[HeldoutCase],
                  render:Callable[[tuple[model.Triple,...]],str|None],proxies:dict,
                  train_select_graphs:set[str],known_train_entities:Sequence[str]=(),
                  expected_count:int=EXPECTED_AUDIT_COUNT,
                  expected_categories:int=EXPECTED_CATEGORIES):
    require(arm in ARMS,"unfrozen arm")
    cats=_validate_cases(cases,train_select_graphs,expected_count,expected_categories)
    require(isinstance(proxies,dict),"missing TRAIN-derived lexical map")
    require(all(type(v) is str for v in known_train_entities),"entity vocabulary malformed")
    # Keep all references inside this function. The model-facing callback receives
    # only a freshly constructed tuple of frozen triples, not a HeldoutCase.
    accum={c:_new_stats() for c in cats}
    begun=time.perf_counter(); cpu=time.process_time()
    for case in cases:
        triples=tuple(model.Triple(t.subject,t.predicate,t.object) for t in case.triples)
        output=render(triples)
        _score_one(accum[case.category],case,output,proxies,known_train_entities)
    category_rows=[_finish(accum[c],_cat_hash(c)) for c in cats]
    all_examples=sum(x["examples"] for x in category_rows)
    all_triples=sum(x["triple_denominator"] for x in category_rows)
    require(all_examples==expected_count and len(category_rows)==expected_categories,
            "incomplete scored audit")
    keys=("requested_content_proxy_coverage","normalized_entity_slot_coverage",
          "chrF_all_references_mean_per_example","token_f1_all_references_mean_per_example")
    macro={k:rounded(avg([x[k] for x in category_rows])) for k in keys}
    result={
      "schema":SCHEMA,"status":"NUMERICAL_PROXIES_ONLY_NOT_INDEPENDENT_SEMANTIC_GO",
      "arm":arm,"source_role_sha256":ROLE_SHA,"frozen_model_suite_git_blob":SUITE,
      "role":"L9_AUDIT_DEV","categories":category_rows,"macro_by_heldout_category":macro,
      "micro_requested_content_proxy_coverage":rounded(
          sum(x["triple_proxy_hits"] for x in category_rows)/all_triples),
      "records":all_examples,"triple_denominator":all_triples,
      "serial_wall_seconds":rounded(time.perf_counter()-begun),
      "serial_cpu_seconds":rounded(time.process_time()-cpu),
      "resource_flops":"NOT_MEASURED","resource_energy":"NOT_MEASURED",
      "all_original_references_scored":True,
      "model_reference_input_count":0,"reference_contents_saved":False,
      "raw_outputs_saved":False,"official_test_consumed":False,"scientific_go":False
    }
    assert_numeric_only(result)
    return result

def assert_numeric_only(d):
    require(d.get("arm") in ARMS,"unknown arm in report")
    require(d.get("schema")==SCHEMA and d.get("scientific_go") is False,
            "report provenance drift")
    require(d.get("raw_outputs_saved") is False
            and d.get("reference_contents_saved") is False,"raw content leakage")
    rows=d.get("categories",[])
    require(type(rows) is list and len(rows)>0,"category reports missing")
    ids=[r.get("category_sha256") for r in rows]
    require(len(set(ids))==len(ids) and all(re.fullmatch(r"[0-9a-f]{64}",x or "")
                  for x in ids),"category label leakage")
    for r in rows:
        for key,val in r.items():
            if key=="category_sha256":continue
            require(type(val) in (int,float) and math.isfinite(val),"unnumeric report field")
    for k,val in d.get("macro_by_heldout_category",{}).items():
        require(k in ("requested_content_proxy_coverage","normalized_entity_slot_coverage",
                      "chrF_all_references_mean_per_example","token_f1_all_references_mean_per_example")
                and type(val) in (int,float) and math.isfinite(val),"invalid macro")
    require(len(d.get("macro_by_heldout_category",{}))==4,"incomplete macro")
    return True

def combine_reports(reports:Sequence[dict],expected_count:int=EXPECTED_AUDIT_COUNT,
                    expected_categories:int=EXPECTED_CATEGORIES):
    require(len(reports)==len(ARMS),"seven-arm audit incomplete")
    require({r.get("arm") for r in reports}==set(ARMS),"missing/duplicate audit method")
    ref_categories=None
    for r in reports:
        assert_numeric_only(r)
        require(r["records"]==expected_count and len(r["categories"])==expected_categories,
                "partial audit records")
        ids=[x["category_sha256"] for x in r["categories"]]
        if ref_categories is None:ref_categories=ids
        require(ids==ref_categories,"category partition disagreement")
        require(r["official_test_consumed"] is False and r["scientific_go"] is False,
                "premature GO or TEST")
    return {"schema":"forge.optimizer.language.l9.seven-arm-numeric-audit-bundle-v1",
      "status":"NUMERICAL_AUDIT_BUNDLE_ONLY_SEMANTIC_REVIEW_REQUIRED",
      "source_role_sha256":ROLE_SHA,"model_suite_git_blob":SUITE,
      "arm_count":7,"heldout_categories":expected_categories,
      "heldout_examples":expected_count,"arms":list(reports),
      "official_test_consumed":False,"scientific_go":False}

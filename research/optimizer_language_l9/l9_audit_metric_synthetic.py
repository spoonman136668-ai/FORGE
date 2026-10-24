#!/usr/bin/env python3
"""L9 seven-method unfamiliar-category metric ENGINE -- synthetic prefit only.

Never imports an L9 model, opens a corpus, fetches any DEV/TEST source,
authorizes first use, or treats text-level proxies as semantic entailment.

A future protected evaluator MUST have independently admitted first-use and
original source custody before it is allowed to invoke any scoring logic.
This CLI has NO argument accepting a source repository, audit file, reference
file, checkpoint, lease, signature or arbitrary user-provided dataset.
"""
from __future__ import annotations

from collections import Counter, defaultdict
import hashlib
import json
import math
from pathlib import Path
import re
import sys

SCHEMA = "forge.optimizer.language.l9.synthetic-seven-method-metrics-v1"
SOURCE_ROLE = "L9_SYNTHETIC_PREFIT_ONLY"
METHODS = (
    "CANONICAL_FACTS",
    "TRAIN_REFERENCE_RETRIEVAL",
    "COMPOSITIONAL_PATTERN",
    "GRU_SEQ2SEQ-seed1701",
    "GRU_SEQ2SEQ-seed1702",
    "SMALL_TRANSFORMER-seed1701-recoveryV2",
    "SMALL_TRANSFORMER-seed1702-recoveryV2",
)
CATEGORIES = ("INVENTED_ALPHA", "INVENTED_BETA", "INVENTED_GAMMA")
TOKEN = re.compile(r"\w+", re.UNICODE)
WS = re.compile(r"\s+")


def require(ok: bool, why: str) -> None:
    if not ok:
        raise ValueError("L9_SYNTHETIC_EVALUATOR_REJECT:" + why)


def normalized(value: str) -> str:
    require(type(value) is str, "NOT_TEXT")
    return WS.sub(" ", value.replace("_", " ").strip()).casefold()


def is_mention(text: str, phrase: str) -> bool:
    """Boundary-anchored entity/lexical phrase proxy; NOT factual entailment."""
    hay=normalized(text)
    needle=normalized(phrase)
    if not needle:
        return False
    return re.search(r"(?<!\w)" + re.escape(needle) + r"(?!\w)", hay) is not None


def grams(value: str, size: int) -> Counter:
    value=normalized(value)
    return Counter(value[i:i+size] for i in range(max(0,len(value)-size+1)))


def chrf_proxy(candidate: str, reference: str) -> float:
    """Explicit approximate chrF2, ngram order 1..4, no corpus dependence."""
    if not candidate or not reference:
        return 0.
    scores=[]
    for n in range(1,5):
        left,right=grams(candidate,n),grams(reference,n)
        shared=sum((left & right).values())
        left_total=sum(left.values())
        right_total=sum(right.values())
        if not left_total or not right_total:
            scores.append(0.)
            continue
        p=shared/left_total
        r=shared/right_total
        scores.append(5*p*r/(4*p+r) if (4*p+r) else 0.)
    return sum(scores)/4


def token_f1_proxy(candidate: str, reference: str) -> float:
    """Unordered lexical token proxy, not semantic truth or fluency."""
    p=Counter(TOKEN.findall(normalized(candidate)))
    r=Counter(TOKEN.findall(normalized(reference)))
    if not p or not r:
        return 0.
    matches=sum((p & r).values())
    return 2*matches/(sum(p.values())+sum(r.values()))


def score_one(record: dict, output: str | None, train_relation_lexemes: dict,
              train_entity_inventory: tuple[str,...]) -> dict:
    require(type(record) is dict and record.get("role")==SOURCE_ROLE,"SYNTHETIC_SOURCE_ONLY")
    triples=record.get("triples")
    refs=record.get("references")
    require(type(triples) is list and 1<=len(triples)<=7,"BAD_TRIPLE_GRID")
    require(type(refs) is list and len(refs)>=1 and
            all(type(x) is str and normalized(x) for x in refs),"BAD_REFERENCES")
    require(type(train_relation_lexemes) is dict and
            all(type(k) is str and type(v) in (list,tuple) and
                all(type(s) is str and normalized(s) for s in v)
                for k,v in train_relation_lexemes.items()),"TRAIN_LEXEMES_ONLY")
    require(type(train_entity_inventory) is tuple and
            all(type(x) is str and normalized(x) for x in train_entity_inventory),
            "TRAIN_ENTITY_INVENTORY")
    for triple in triples:
        require(type(triple) is list and len(triple)==3 and
                all(type(x) is str and normalized(x) for x in triple),"BAD_TRIPLE")
    require(output is None or type(output) is str,"BAD_OUTPUT")
    clean="" if output is None else output.strip()
    abstain=not clean
    source_entities={normalized(x) for s,_,o in triples for x in (s,o)}
    total=len(triples)
    entity_hits=0
    demanded_entity_slots=2*total
    triple_hits=0
    for sub,pred,obj in triples:
        sub_hit=is_mention(clean,sub) if not abstain else False
        obj_hit=is_mention(clean,obj) if not abstain else False
        entity_hits+=int(sub_hit)+int(obj_hit)
        relation_terms=train_relation_lexemes.get(normalized(pred),())
        relation_hit=any(is_mention(clean,t) for t in relation_terms) if not abstain else False
        triple_hits+=int(sub_hit and obj_hit and relation_hit)
    # Only a TRAIN-inventory-based overmention heuristic. Unknown invented
    # entities and real-world hallucinations remain outside this proxy.
    extra=sum(is_mention(clean,e) for e in set(train_entity_inventory)
              if normalized(e) not in source_entities) if not abstain else 0
    # This is a high-recall *marker* proxy, not contradiction detection.
    negation=int(bool(re.search(r"\b(?:not|never|no)\b",normalized(clean)))) if not abstain else 0
    max_f1=max((token_f1_proxy(clean,ref) for ref in refs),default=0.)
    max_chrf=max((chrf_proxy(clean,ref) for ref in refs),default=0.)
    words=TOKEN.findall(normalized(clean))
    repetition=(sum(n-1 for n in Counter(words).values() if n>1)/len(words)
                if words else 0.)
    return {
        "requested_triples":total,
        "triple_hits_proxy":triple_hits,
        "missing_triples_proxy":total-triple_hits,
        "requested_entity_slots":demanded_entity_slots,
        "entity_slots_hit_proxy":entity_hits,
        "extra_train_inventory_entity_mentions_proxy":extra,
        "negation_marker_conflict_proxy":negation,
        "explicit_abstentions":int(abstain),
        "multireference_best_token_f1_proxy":max_f1,
        "multireference_best_chrf_proxy":max_chrf,
        "terminal_punctuation_proxy":int(bool(re.search(r"[.!?]$",clean))) if clean else 0,
        "repetition_rate_proxy":repetition,
        "unresolved_placeholder_proxy":int(("{S}" in clean or "{O}" in clean)) if clean else 0,
        "reference_count":len(refs),
        "semantic_entailment_adjudicated":False,
        "hallucinations_exhaustively_detected":False,
    }


def frozen_matrix(records:list[dict], outputs:dict[str,str|None],
                  train_relation_lexemes:dict,
                  train_entity_inventory:tuple[str,...]) -> dict:
    """Exact 3-category × seven-method synthetic fixture; no DEV/AUDIT role."""
    require(type(records) is list and records,"EMPTY_SYNTHETIC_INPUTS")
    require(type(outputs) is dict,"OUTPUT_MATRIX_NOT_OBJECT")
    cats=defaultdict(list)
    ids=set()
    for record in records:
        require(type(record) is dict and record.get("role")==SOURCE_ROLE,
                "PROTECTED_ROLE_REJECTED")
        cat=record.get("category")
        graph=record.get("graph_id")
        require(cat in CATEGORIES and type(graph) is str and
                re.fullmatch(r"[0-9a-f]{64}",graph) is not None and
                graph not in ids,"CATEGORY_OR_GRAPH_ID")
        ids.add(graph)
        cats[cat].append(record)
    require(set(cats)==set(CATEGORIES),"ALL_THREE_CATEGORIES_MANDATORY")
    expected={r["graph_id"]+":"+method for r in records for method in METHODS}
    require(set(outputs)==expected,"SEVEN_METHOD_GRAPH_COVERAGE")
    category_receipts={}
    for cat in CATEGORIES:
        category_receipts[cat]={}
        for method in METHODS:
            scored=[score_one(rec,outputs[rec["graph_id"]+":"+method],
                              train_relation_lexemes,train_entity_inventory)
                    for rec in cats[cat]]
            n=len(scored)
            triples=sum(x["requested_triples"] for x in scored)
            hits=sum(x["triple_hits_proxy"] for x in scored)
            entity_slots=sum(x["requested_entity_slots"] for x in scored)
            entity_hits=sum(x["entity_slots_hit_proxy"] for x in scored)
            require(triples>0 and 0<=hits<=triples,"TRIPLE_DENOMINATOR")
            category_receipts[cat][method]={
                "graphs":n,"requested_triples":triples,
                "covered_triples_proxy":hits,
                "missing_triples_proxy":triples-hits,
                "per_triple_coverage_proxy":hits/triples,
                "entity_slots":entity_slots,"entity_slots_hit_proxy":entity_hits,
                "entity_slot_coverage_proxy":entity_hits/entity_slots,
                "extra_train_inventory_entity_mentions_proxy":
                    sum(x["extra_train_inventory_entity_mentions_proxy"] for x in scored),
                "negation_marker_conflict_proxy":
                    sum(x["negation_marker_conflict_proxy"] for x in scored),
                "explicit_abstentions":sum(x["explicit_abstentions"] for x in scored),
                "best_ref_token_f1_mean_proxy":
                    sum(x["multireference_best_token_f1_proxy"] for x in scored)/n,
                "best_ref_chrf_mean_proxy":
                    sum(x["multireference_best_chrf_proxy"] for x in scored)/n,
                "terminal_punctuation_rate_proxy":
                    sum(x["terminal_punctuation_proxy"] for x in scored)/n,
                "repetition_rate_proxy":sum(x["repetition_rate_proxy"] for x in scored)/n,
                "unresolved_placeholders":sum(x["unresolved_placeholder_proxy"] for x in scored),
                "semantic_entailment_adjudicated":False,
            }
    summary={}
    for method in METHODS:
        summary[method]={
            "macro_equal_category_triple_coverage_proxy":sum(
                category_receipts[c][method]["per_triple_coverage_proxy"] for c in CATEGORIES)/3,
            "macro_equal_category_best_ref_chrf_proxy":sum(
                category_receipts[c][method]["best_ref_chrf_mean_proxy"] for c in CATEGORIES)/3,
            "all_graphs":len(records),
            "total_abstentions":sum(category_receipts[c][method]["explicit_abstentions"]
                                     for c in CATEGORIES),
        }
    return {
        "schema":SCHEMA,"source_role":SOURCE_ROLE,
        "categories":list(CATEGORIES),"methods":list(METHODS),
        "category_metrics":category_receipts,"macro_metrics":summary,
        "synthetic_graph_count":len(records),
        "real_audit_cases_scored":0,"real_audit_reference_bytes_read":0,
        "official_test_bytes_read":0,
        "first_use_authorized":False,"independent_semantic_adjudication":False,
        "all_quality_metrics_are_lexical_proxies":True,
        "training_selection_or_model_loading_performed":False,
        "scientific_go":False,
    }


def synthetic_fixture()->tuple:
    """Intentionally invented inputs, distinct domains and deterministic controls."""
    specs=[
        ("INVENTED_ALPHA","azurine_101","maps-to","topaz_201"),
        ("INVENTED_BETA","beryllon_301","links-to","cobalt_401"),
        ("INVENTED_GAMMA","ceruleon_501","belongs-to","opal_601"),
    ]
    records=[]
    output={}
    relation={"maps-to":["maps to"],"links-to":["links to"],"belongs-to":["belongs to"]}
    inventory=("azurine_101","topaz_201","beryllon_301","cobalt_401",
               "ceruleon_501","opal_601")
    for idx,(cat,s,p,o) in enumerate(specs):
        gid=hashlib.sha256(("ARTIFICIAL-FIXTURE-"+str(idx)).encode()).hexdigest()
        ref=f"{s} {p.replace('-', ' ')} {o}."
        records.append({"role":SOURCE_ROLE,"category":cat,
                        "graph_id":gid,"triples":[[s,p,o]],
                        "references":[ref,ref+" Indeed."]})
        for method in METHODS:
            value=(ref if method in ("CANONICAL_FACTS","COMPOSITIONAL_PATTERN") else
                   None if method.startswith("SMALL_TRANSFORMER") else
                   f"{s} {p.replace('-', ' ')} {o}.")
            output[gid+":"+method]=value
    return records,output,relation,inventory


def main() -> None:
    # No user-supplied dataset or role is accepted, by design.
    require(len(sys.argv)==3 and sys.argv[1]=="--out","ONLY_FIXED_SYNTHETIC_FIXTURE")
    out=Path(sys.argv[2])
    require(not out.exists(),"REFUSE_OVERWRITE")
    records,outputs,lexemes,entities=synthetic_fixture()
    report=frozen_matrix(records,outputs,lexemes,entities)
    raw=(json.dumps(report,sort_keys=True,ensure_ascii=False,
                    separators=(",",":"))+"\n").encode("utf-8")
    out.write_bytes(raw)
    print("L9_SYNTHETIC_SEVEN_METHOD_AUDIT_METRIC_PREFIT=PASS")
    print("L9_PROTECTED_AUDIT_FIRST_USE=FALSE")
    print("L9_INDEPENDENT_SEMANTIC_ADJUDICATION=FALSE")
    print("L9_SYNTHETIC_RECEIPT_SHA256="+hashlib.sha256(raw).hexdigest())


if __name__=="__main__":
    main()

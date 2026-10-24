#!/usr/bin/env python3
"""RC-L9S: independent, bounded synthetically generated structural-control probe.

Use only invented TRAIN cases and invented unfamiliar entity/composition graphs.
This is NOT protected L9_AUDIT_DEV, WebNLG TEST, scientific first use, or a
semantic entailment evaluator for natural language. L9 frozen code is imported
unchanged; no weights/checkpoints are loaded, no selection is rerun.
"""
from __future__ import annotations
from collections import Counter
import copy
import hashlib
import json
import math
import re
import statistics
import sys
import time
import tracemalloc
from pathlib import Path

import l9_model_suite as m
import l9_train_select_candidate as original

SCHEMA="forge.research-charter.l9.structural-binding-development-v1"
SOURCE_ROLE="RC_L9S_INVENTED_TRAIN"
SEED=1701
RELATIONS={
    "founded":"founded",
    "joined":"joined",
    "acquired":"acquired",
    "locatedAt":"is located at",
}
TEST_CATEGORIES=("SINGLE_NEW_ENTITIES","TWO_RELATION_COMPOSITION",
                 "THREE_RELATION_COMPOSITION","NOVEL_PREDICATE_ABSTENTION")
SIZES=(32,48,48,16)
BENCH_REPEATS=17
CONFIG=m.CandidateConfig(min_template_support=1,max_templates_per_predicate=4,joiner=" ")

def canonical(value):
    return (json.dumps(value,sort_keys=True,ensure_ascii=False,
                       separators=(",",":"))+"\n").encode("utf-8")

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def require(ok,msg):
    if not ok:
        raise ValueError("RC_L9S_REJECT:"+msg)

def training():
    """Same exact facts and complete sentences available to both learners."""
    rows=[]
    for p,relation in RELATIONS.items():
        for i in range(8):
            subject=f"TrainSubject{p}{i}"
            obj=f"TrainObject{p}{i}"
            triple=m.Triple(subject,p,obj)
            ref=f"{subject} {relation} {obj}."
            rows.append(m.Example("L9_TRAIN",sha(ref.encode()),(triple,),ref))
    require(len(rows)==32,"TRAIN_FIXTURE_COUNT")
    return rows

def tests():
    """Predeclared disjoint synthetic entity instances and graph combinations."""
    records=[]
    for category,count in zip(TEST_CATEGORIES,SIZES):
        for idx in range(count):
            if category=="SINGLE_NEW_ENTITIES":
                preds=(tuple(RELATIONS)[idx%4],)
            elif category=="TWO_RELATION_COMPOSITION":
                preds=(tuple(RELATIONS)[idx%4],tuple(RELATIONS)[(idx+1)%4])
            elif category=="THREE_RELATION_COMPOSITION":
                preds=tuple(tuple(RELATIONS)[(idx+j)%4] for j in range(3))
            else:
                preds=("notObservedInTrain",)
            triples=tuple(m.Triple(f"NewSubject{category[:3]}{idx}{j}",pred,
                                   f"NewObject{category[:3]}{idx}{j}")
                          for j,pred in enumerate(preds))
            gid=sha(m.graph_serialization(triples))
            records.append({"category":category,"graph_id":gid,"triples":triples})
    require(len(records)==sum(SIZES) and len({r["graph_id"] for r in records})==sum(SIZES),
            "TEST_GRID_IDENTITY")
    return records

def fit_slot_control(examples):
    """INDEPENDENT simple grammar baseline with same TRAIN facts and references.

    Only extracts the intervening predicate phrase anchored between the known
    subject and object. Unlike L9 candidate, no clause search, support threshold,
    per-predicate top-k or multi-template list is used. Identical structural
    input privileges are intentionally granted.
    """
    counts={}
    for e in examples:
        require(e.role=="L9_TRAIN" and len(e.triples)==1,"BASELINE_FIT_TRAIN_ONLY")
        t=e.triples[0]
        subject=m.surface_alias(t.subject)
        obj=m.surface_alias(t.object)
        sentence=m.normalize_space(e.reference)
        mat=re.fullmatch(re.escape(subject)+r" (.+?) "+re.escape(obj)+r"\.",
                         sentence,flags=re.IGNORECASE)
        require(mat is not None,"UNPARSEABLE_TRAIN_GRAMMAR")
        phrase=m.normalize_space(mat.group(1))
        key=m.normalize_predicate(t.predicate)
        counts.setdefault(key,Counter())[phrase]+=1
    learned={key:sorted(cnt.items(),key=lambda x:(-x[1],len(x[0].encode()),x[0]))[0][0]
             for key,cnt in sorted(counts.items())}
    return {"schema":"rc-l9s.slot-grammar.v1","predicate_phrases":learned}

def realize_slot_control(state,triples):
    phrases=state["predicate_phrases"]
    out=[]
    for triple in triples:
        term=phrases.get(m.normalize_predicate(triple.predicate))
        if term is None:
            return None
        out.append(f"{m.surface_alias(triple.subject)} {term} {m.surface_alias(triple.object)}.")
    return " ".join(out)

def semantic_graph_exact_synthetic(output,triples):
    """Exact artificial controlled-grammar relation binding, NOT real NLI.

    Every clause must bind the appropriate subject, relation and object, with
    direction and multiplicity preserved. Merely mentioning terms does not pass.
    """
    if not output:
        return False
    phrases=sorted(set(RELATIONS.values()),key=len,reverse=True)
    pat=re.compile(r"^([A-Za-z0-9]+) ("+"|".join(map(re.escape,phrases))+
                   r") ([A-Za-z0-9]+)\.$")
    pieces=re.split(r"(?<=\.)\s+",output.strip())
    if len(pieces)!=len(triples):
        return False
    observed=[]
    inverse={v:k for k,v in RELATIONS.items()}
    for clause in pieces:
        mat=pat.fullmatch(clause)
        if mat is None:
            return False
        sub,phrase,obj=mat.groups()
        observed.append((sub,inverse[phrase],obj))
    expected=[(m.surface_alias(t.subject),t.predicate,m.surface_alias(t.object))
              for t in triples]
    return Counter(observed)==Counter(expected)

def evaluate_case(prediction,triples,category):
    if category=="NOVEL_PREDICATE_ABSTENTION":
        return {"exact":False,"appropriate_abstention":prediction is None,
                "reference_free":True}
    return {"exact":semantic_graph_exact_synthetic(prediction,triples),
            "appropriate_abstention":False,"reference_free":True}

def score(method,records):
    values=[]
    for rec in records:
        value=method(rec["triples"])
        values.append((rec,evaluate_case(value,rec["triples"],rec["category"]),value))
    by_cat={}
    for cat,expected in zip(TEST_CATEGORIES,SIZES):
        subset=[v for v in values if v[0]["category"]==cat]
        require(len(subset)==expected,"CATEGORY_DROP")
        by_cat[cat]={
            "count":len(subset),
            "exact_controlled_grammar_graphs":sum(int(v[1]["exact"]) for v in subset),
            "appropriate_abstentions":sum(int(v[1]["appropriate_abstention"]) for v in subset),
            "output_abstentions":sum(int(v[2] is None) for v in subset)}
    quality=(
        sum(v["exact_controlled_grammar_graphs"] for cat,v in by_cat.items()
            if cat!="NOVEL_PREDICATE_ABSTENTION"),
        sum(v["count"] for cat,v in by_cat.items()
            if cat!="NOVEL_PREDICATE_ABSTENTION")
    )
    return {"by_category":by_cat,"known_graph_correct":quality[0],
            "known_graph_denominator":quality[1],
            "unknown_abstentions":by_cat["NOVEL_PREDICATE_ABSTENTION"]["appropriate_abstentions"],
            "total_graphs":len(records),
            "outputs_sha256":sha(canonical([v[2] for v in values]))}

def measure_fit(fit,train):
    tracemalloc.start()
    start_wall=time.perf_counter_ns();start_cpu=time.process_time_ns()
    state=fit(train)
    wall_ns=time.perf_counter_ns()-start_wall
    cpu_ns=time.process_time_ns()-start_cpu
    _,peak=tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return state,{"fit_wall_seconds":wall_ns/1e9,"fit_cpu_seconds":cpu_ns/1e9,
                  "fit_python_traced_peak_bytes":peak,
                  "inference_state_bytes":len(canonical(state)),
                  "inference_state_sha256":sha(canonical(state))}

def benchmark(candidate,control,records):
    # Alternate order to mitigate warmed-loop bias, retain per-pass latency.
    measurements={"COMPOSITIONAL_PATTERN":[],"SLOT_GRAMMAR_CONTROL":[]}
    engines=(("COMPOSITIONAL_PATTERN",candidate),("SLOT_GRAMMAR_CONTROL",control))
    for rep in range(BENCH_REPEATS):
        for name,fn in (engines if rep%2==0 else tuple(reversed(engines))):
            start_w=time.perf_counter_ns();start_c=time.process_time_ns()
            outputs=[fn(rec["triples"]) for rec in records]
            dt_w=(time.perf_counter_ns()-start_w)/1e9
            dt_c=(time.process_time_ns()-start_c)/1e9
            require(len(outputs)==len(records),"INFERENCE_OUTPUT_COUNT")
            measurements[name].append((dt_w,dt_c))
    return {name:{
          "repeats":len(v),"serial_cases_per_repeat":len(records),
          "wall_median_seconds":statistics.median(x[0] for x in v),
          "wall_min_seconds":min(x[0] for x in v),
          "wall_max_seconds":max(x[0] for x in v),
          "cpu_median_seconds":statistics.median(x[1] for x in v)
       } for name,v in measurements.items()}

def adversarial(candidate_state,records):
    proxies=original.relation_proxies(candidate_state)
    a=m.Triple("Alice","founded","Acme")
    b=m.Triple("Bob","joined","Beta")
    wrong="Alice joined Acme. Bob founded Beta."
    right="Alice founded Acme. Bob joined Beta."
    global_right=original.coverage(right,(a,b),proxies)
    global_wrong=original.coverage(wrong,(a,b),proxies)
    require(global_right==(2,2) and global_wrong==(2,2),"MUST_REPRODUCE_GLOBAL_PROXY_FP")
    require(semantic_graph_exact_synthetic(right,(a,b)),"RIGHT_BINDING")
    require(not semantic_graph_exact_synthetic(wrong,(a,b)),"SWAPPED_BINDING_FP")
    require(original.coverage("Alice founded Acmezz.",(a,),proxies)==(1,1),
            "MUST_REPRODUCE_SUBSTRING_FP")
    require(not semantic_graph_exact_synthetic("Alice founded Acmezz.",(a,)),
            "SUBSTRING_BOUNDARY_FP")
    probe=next(r for r in records if r["category"]=="TWO_RELATION_COMPOSITION")
    triples=probe["triples"]
    intact=m.realize_candidate(candidate_state,triples,CONFIG)
    require(semantic_graph_exact_synthetic(intact,triples),"INTACT_BINDING")
    swapped=copy.deepcopy(candidate_state)
    pa,pb=(m.normalize_predicate(x.predicate) for x in triples)
    swapped["templates"][pa],swapped["templates"][pb]=(
          swapped["templates"][pb],swapped["templates"][pa])
    shuffled=m.realize_candidate(swapped,triples,CONFIG)
    require(not semantic_graph_exact_synthetic(shuffled,triples),"SHUFFLE_SHOULD_BREAK_BINDING")
    reversed_output=" ".join(f"{m.surface_alias(t.object)} {RELATIONS[t.predicate]} "
                             f"{m.surface_alias(t.subject)}." for t in triples)
    require(not semantic_graph_exact_synthetic(reversed_output,triples),
            "DIRECTION_REVERSAL")
    missing=" ".join(intact.split(". ")[:1])
    if not missing.endswith("."): missing+="."
    require(not semantic_graph_exact_synthetic(missing,triples),"MISSING_TRIPLE")
    repeated=(triples[0],m.Triple("ExtraSubject1",triples[0].predicate,"ExtraObject1"))
    generated=m.realize_candidate(candidate_state,repeated,CONFIG)
    require(semantic_graph_exact_synthetic(generated,repeated),"REPEATED_PREDICATE")
    novel=m.Triple("NewSubject","notObservedInTrain","NewObject")
    require(m.realize_candidate(candidate_state,(novel,),CONFIG) is None,
            "FORBID_CANONICAL_FALLBACK")
    return {
        "candidate_derived_global_proxy_right_hits":global_right[0],
        "candidate_derived_global_proxy_swapped_hits":global_wrong[0],
        "swapped_binding_false_positive_reproduced":True,
        "partial_entity_substring_false_positive_reproduced":True,
        "triple_local_binding_rejects_swapped":True,
        "triple_local_binding_rejects_partial_entity":True,
        "predicate_template_shuffle_breaks_binding":True,
        "subject_object_reversal_rejected":True,
        "missing_triple_rejected":True,
        "repeated_predicate_exact":True,
        "unseen_predicate_abstains":True
    }

def run():
    train=training()
    records=tests()
    candidate_state,cf=measure_fit(m.fit_candidate,train)
    control_state,sf=measure_fit(fit_slot_control,train)
    candidate=lambda triples:m.realize_candidate(candidate_state,triples,CONFIG)
    control=lambda triples:realize_slot_control(control_state,triples)
    quality_c=score(candidate,records)
    quality_s=score(control,records)
    attack=adversarial(candidate_state,records)
    timing=benchmark(candidate,control,records)
    known=sum(SIZES[:3])
    require(quality_c["known_graph_correct"]==known and
            quality_s["known_graph_correct"]==known,"CONTROLLED_QUALITY_REGRESSION")
    require(quality_c["unknown_abstentions"]==SIZES[3] and
            quality_s["unknown_abstentions"]==SIZES[3],"NOVEL_PREDICATE_ABSTENTIONS")
    return {
        "schema":SCHEMA,
        "status":"BOUNDED_SYNTHETIC_DEVELOPMENT_CONTROL_NEGATIVE_NO_SEMANTIC_GO",
        "source_roles":["L9_TRAIN_SYNTHETIC_ONLY","RC_L9S_INVENTED_TEST_ONLY"],
        "original_model_suite_git_blob":"710ce648a30ffc55647f689c5f4aa3ac13b07066",
        "original_candidate_evaluator_git_blob":"0d2b10cbf9879dd168be1dfc954dfca2928e841e",
        "training_records":len(train),"development_records":len(records),
        "training_source_sha256":sha(canonical([{
           "role":x.role,"triples":[[t.subject,t.predicate,t.object] for t in x.triples],
           "reference":x.reference} for x in train])),
        "development_graphs_sha256":sha(canonical([r["graph_id"] for r in records])),
        "methods":{
            "COMPOSITIONAL_PATTERN":{"fit":cf,"quality":quality_c,
                                     "inference_benchmark":timing["COMPOSITIONAL_PATTERN"]},
            "SLOT_GRAMMAR_CONTROL":{"fit":sf,"quality":quality_s,
                                    "inference_benchmark":timing["SLOT_GRAMMAR_CONTROL"]}},
        "adversarial":attack,
        "equal_train_facts_and_references":True,
        "identical_graph_input_privileges":True,
        "structural_baseline_independent_extraction_algorithm":True,
        "novel_structured_composition_with_known_predicates":True,
        "semantic_measure":"EXACT_ARTIFICIAL_GRAMMAR_BINDING_NOT_NATURAL_LANGUAGE_ENTAILMENT",
        "full_original_webnlg_training_matched":False,
        "full_resource_pareto_proven":False,
        "energy":"NOT_MEASURED","flops":"NOT_MEASURED",
        "official_webnlg_test_consumed":False,
        "l9_audit_dev_consumed":False,
        "scientific_go":False,
        "development_advance":"NO_LEARNED_ADVANTAGE_OVER_EQUAL_INFO_GRAMMAR_CONTROL_ON_SYNTHETIC_FIXTURE"
    }

def main():
    require(len(sys.argv)==3 and sys.argv[1]=="--out","ONLY_SYNTHETIC_OUTPUT_ARG")
    out=Path(sys.argv[2])
    require(not out.exists(),"NO_OVERWRITE")
    result=run()
    out.write_bytes(canonical(result))
    print("RC_L9S_SYNTHETIC_EQUALLY_INFORMED_STRUCTURAL_CONTROL=PASS")
    print("RC_L9S_KNOWN_GRAPH_EXACT="+str(result["methods"]["COMPOSITIONAL_PATTERN"]["quality"]["known_graph_correct"]))
    print("RC_L9S_MATCHED_CONTROL_EXACT="+str(result["methods"]["SLOT_GRAMMAR_CONTROL"]["quality"]["known_graph_correct"]))
    print("RC_L9S_GLOBAL_LEXICAL_FALSE_POSITIVE_REPRODUCED=TRUE")
    print("RC_L9S_L9_AUDIT_DEV_CONSUMED=FALSE")
    print("RC_L9S_SCIENTIFIC_GO=FALSE")
    print("RC_L9S_SOURCE_AND_RESULTS_SHA256="+sha(canonical(result)))

if __name__=="__main__":
    main()

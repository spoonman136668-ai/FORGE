#!/usr/bin/env python3
"""L9 held-out graph-to-frozen-inference wiring; synthetic qualification only.

No DEV reference, model fit or source read at import. Protected corpus access
is available only when a separately approved one-time runner calls loaders.
"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import hashlib
import json
import xml.etree.ElementTree as ET
from typing import Callable
import l9_model_suite as model
import l9_split_builder as split
import l9_train_select_candidate as development
import l9_neural_select_only as neural
import l9_transformer_select_reuse_v2 as transformer
import l9_first_use_scoring_core as score

ROLE_SHA=score.ROLE_SHA
SOURCE_SHA=split.RELEASE_SHA
EXPECTED_TOTAL=319
EXPECTED_CATEGORIES=3
CANDIDATE_STATE_SHA="6bfcae415a3f1145397875b715c7d5015143e1544381be6a031eed636be88c3c"
RETRIEVAL_STATE_SHA="ed7b21b6c4f648b337491aa5240ed1a7326f23164a13a0503748aded689e377b"
SELECTED_CONFIG=model.CandidateConfig(1,4," ")
EXPECTED_NEURAL={
 "GRU_SEQ2SEQ-1701":("GRU_SEQ2SEQ",1701,12,"a24469cf00be1c028cd5dfb25649f7bcc523b35792eb4680fe19aa8912f01daa"),
 "GRU_SEQ2SEQ-1702":("GRU_SEQ2SEQ",1702,12,"1097e800b6ddc2acaa90df62943c6db1a34b1e1e62e51daf056f95303bb8d048"),
 "SMALL_TRANSFORMER-1701":("SMALL_TRANSFORMER",1701,12,"bf731132c64dbfd82ea5bc6121d0006c34527101b040119f9d11d83931a99a84"),
 "SMALL_TRANSFORMER-1702":("SMALL_TRANSFORMER",1702,12,"e5e7baaf4a0ad3be69213933419da96fb85842a0b40adafdecd587d00fccf5a0"),
}

@dataclass(frozen=True)
class GraphOnly:
    category: str
    graph_sha256: str
    triples: tuple[model.Triple,...]
    blob_oid: str
    entry_index: int

def require(ok,reason):
    if not ok: raise ValueError("L9_SOURCE_INFERENCE_BLOCKED:"+reason)
def exact_sha(value):
    return hashlib.sha256(model.canonical_json_bytes(value)).hexdigest()

def graph_only_xml(raw:bytes,blob_oid:str):
    """Parse graph metadata only; never return, store or extract lex reference text."""
    require(type(raw) is bytes and len(raw)>0,"empty DEV XML")
    require(type(blob_oid) is str and len(blob_oid)==40,"invalid source blob oid")
    root=ET.fromstring(raw)
    rows=[]
    for i,e in enumerate(root.iter("entry")):
        category=split.norm_category(e.attrib.get("category",""))
        if split.provisional_role("DEV",category)!="L9_AUDIT_DEV":
            continue
        triples_raw=[split.parse_triple(n.text or "") for n in e.findall("./modifiedtripleset/mtriple")]
        graph=split.graph_identity(triples_raw)
        rows.append(GraphOnly(category,graph,tuple(model.Triple(*x) for x in triples_raw),blob_oid,i))
    return rows

def validate_graph_inputs(rows:list[GraphOnly],trained_graphs:set[str],
                          expected_count:int=EXPECTED_TOTAL,
                          expected_categories:int=EXPECTED_CATEGORIES):
    require(len(rows)==expected_count,"audit example count")
    require(type(trained_graphs) is set and bool(trained_graphs),"trained graph custody")
    cats=set()
    for row in rows:
        require(type(row) is GraphOnly,"unrecognized graph record")
        require(split.category_partition(row.category)=="L9_AUDIT_CATEGORY","training category")
        require(row.graph_sha256 not in trained_graphs,"train/select graph overlap")
        actual=split.graph_identity(tuple((t.subject,t.predicate,t.object) for t in row.triples))
        require(actual==row.graph_sha256,"graph content SHA drift")
        require(type(row.entry_index) is int and row.entry_index>=0,"entry ordinal")
        cats.add(row.category)
    require(len(cats)==expected_categories,"heldout category count")
    return sorted(cats)

def load_graph_only(repo:Path,trained_graphs:set[str],manifest_path:Path):
    """Call ONLY in first-use workflow after all hosted qualifications PASS.

    Source release and all 176 OIDs are validated BEFORE reading any XML body.
    The original split builder reads DEV graph metadata but no lex text.
    """
    manifest,entries=split.load_manifest(manifest_path)
    split.verify_all_blob_identities(repo,entries)
    summary=split.build(repo,manifest_path)
    require(summary["role_identity_sha256"]==ROLE_SHA,"role SHA drift")
    counts=summary["counts"]
    require(counts["roles"]["L9_TRAIN"]==8480 and counts["roles"]["L9_SELECT"]==2154
            and counts["roles"]["L9_AUDIT_DEV"]==319,"role counts")
    require(counts["train_audit_graph_overlap"]==0,"split graph overlap")
    require(counts["audit_categories_present_in_dev"]==3,"audit categories")
    rows=[]
    for entry in entries:
        if entry["role"]!="DEV":continue
        raw=development.git_bytes(repo,entry["oid"])
        rows.extend(graph_only_xml(raw,entry["oid"]))
    categories=validate_graph_inputs(rows,trained_graphs)
    return rows,categories,summary

def fit_frozen_train_states(train):
    """Deterministic reproduction with exact original state hash; never use AUDIT."""
    require(len(train)==8480 and all(x.role=="L9_TRAIN" for x in train),"TRAIN-only fit")
    c=model.fit_candidate(train)
    r=model.fit_retrieval(train)
    require(exact_sha(c)==CANDIDATE_STATE_SHA,"candidate fit-state SHA drift")
    require(exact_sha(r)==RETRIEVAL_STATE_SHA,"retrieval fit-state SHA drift")
    return c,r,development.relation_proxies(c)

def frozen_renderers(candidate,retrieval,selected_nets:dict):
    """Wire only the four exact preselected networks; no references or retuning."""
    require(exact_sha(candidate)==CANDIDATE_STATE_SHA,"candidate state changed")
    require(exact_sha(retrieval)==RETRIEVAL_STATE_SHA,"retrieval state changed")
    require(type(selected_nets) is dict and set(selected_nets)==set(EXPECTED_NEURAL),
            "all four mandatory neural seeds")
    render={
      "CANONICAL_FACTS_NONFLUENT_CONTROL": lambda triples:model.canonical_facts(triples),
      "TRAIN_REFERENCE_RETRIEVAL":lambda triples:model.realize_retrieval(retrieval,triples),
      "COMPOSITIONAL_PATTERN":lambda triples:model.realize_candidate(candidate,triples,SELECTED_CONFIG),
    }
    for label in EXPECTED_NEURAL:
        net=selected_nets[label]
        require(net is not None,"missing selected frozen network")
        if label.startswith("GRU_"):
            render[label]=(lambda triples,n=net:neural.inference_one(n,"GRU_SEQ2SEQ",triples))
        else:
            render[label]=(lambda triples,n=net:transformer.reuse_inference_one(n,triples))
    require(tuple(render)==score.ARMS,"frozen arm identity or order")
    return render

def load_exact_neural_checkpoints(root:Path):
    """Loaded only inside one-time workflow; original checkpoint receipt verified."""
    result={}
    for label,(arm,seed,epoch,expected_hash) in EXPECTED_NEURAL.items():
        path=root/label
        net,info=neural.model_from_checkpoint(arm,seed,epoch,path)
        require(info.get("inference_sha256")==expected_hash,"selected checkpoint hash")
        require(info.get("inference_bytes",0)>0,"checkpoint missing retained size")
        result[label]=net
    require(set(result)==set(EXPECTED_NEURAL),"missing frozen neural seed")
    return result

def prediction_only_pass(graphs:list[GraphOnly],render:dict,train_graphs:set[str],
                         expected_count:int=EXPECTED_TOTAL,
                         expected_categories:int=EXPECTED_CATEGORIES):
    """Every method predicts from graphs only before any references are retrieved.

    Returns ephemeral strings in memory. NEVER serialize or print these values.
    """
    validate_graph_inputs(graphs,train_graphs,expected_count,expected_categories)
    require(type(render) is dict and tuple(render)==score.ARMS,"missing required arms")
    predictions={}
    for arm in score.ARMS:
        output=[]
        for row in graphs:
            triples=tuple(model.Triple(t.subject,t.predicate,t.object) for t in row.triples)
            result=render[arm](triples)
            require(result is None or type(result) is str,"non-text prediction")
            output.append(result)
        require(len(output)==expected_count,"incomplete arm predictions")
        predictions[arm]=output
    require(len(predictions)==7,"missing mandatory prediction arm")
    return predictions

def attach_refs_after_prediction(graphs,predictions,ref_reader:Callable[[GraphOnly],tuple[str,...]],
                                 trained_graphs:set[str],expected_count:int=EXPECTED_TOTAL,
                                 expected_categories:int=EXPECTED_CATEGORIES):
    """Only reference-reading phase, after all seven prediction arrays exist."""
    validate_graph_inputs(graphs,trained_graphs,expected_count,expected_categories)
    require(type(predictions) is dict and tuple(predictions)==score.ARMS,"predictions incomplete")
    require(all(type(predictions[k]) is list and len(predictions[k])==expected_count
                for k in score.ARMS),"prediction vector incomplete")
    cases=[]
    for row in graphs:
        refs=ref_reader(row)
        require(type(refs) is tuple and len(refs)>0 and
                all(type(t) is str and bool(model.normalize_space(t)) for t in refs),
                "empty or malformed heldout refs")
        cases.append(score.HeldoutCase(row.category,"L9_AUDIT_DEV",row.graph_sha256,
                                      tuple(row.triples),refs))
    score._validate_cases(cases,trained_graphs,expected_count,expected_categories)
    return cases

def score_precomputed_arm(arm,cases,predictions,proxies,train_graphs,
                          expected_count:int=EXPECTED_TOTAL,
                          expected_categories:int=EXPECTED_CATEGORIES):
    """Scorer's render callback consumes frozen outputs, never reference objects."""
    require(arm in score.ARMS,"unknown arm")
    values=predictions[arm]
    require(len(values)==len(cases)==expected_count,"missing frozen predictions")
    index=iter(values)
    def emit(triples):
        require(type(triples) is tuple and all(type(t) is model.Triple for t in triples),
                "unexpected input to scoring")
        return next(index)
    result=score.evaluate_arm(arm,cases,emit,proxies,train_graphs,
           expected_count=expected_count,expected_categories=expected_categories)
    try:
        next(index)
    except StopIteration:
        return result
    raise ValueError("unused prediction tail")

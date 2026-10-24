#!/usr/bin/env python3
"""L10-B3 DEV_FIT-only supervised template induction; NOT native-learning proof.

Fits a small compositional surface table to oracle-generated DEV_FIT examples.
This is deliberately weak conventional supervision and cannot outperform the
fully informed canonical/rule ceiling on the known-mapping DEV graph metric.
No L9/WEBNLG, prospective seed, prospective generator or first-use access.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import math
import re
import time
from typing import Sequence

import l10_dev_source_custody as source
import l10_dev_matched_controls as controls
import l10_semantic_dev_oracle as oracle

SCHEMA="forge.optimizer.language.l10.devfit-supervised-template-induction-v1"
ROLE="L10_SYNTHETIC_DEV"
FIT_SPLIT="DEV_FIT"
# This boundary intentionally records which knowledge comes from supervised
# template labels, rather than falsely describing it as unsupervised cognition.
SUPERVISION="DEV_FIT_KNOWN_MAPPING_SUPERVISED_RULE_REFERENCE"
KEYS=tuple(f"{code}:{p}" for code in source.PREDICATE_CODES for p in (-1,1))
_SLOT_S="{SUBJECT}"
_SLOT_O="{OBJECT}"

@dataclass(frozen=True)
class Fitted:
    schema:str
    supervision:str
    regime:str
    fit_role:str
    fit_split:str
    fit_sources_sha256:str
    templates:tuple[tuple[str,str], ...]
    state_sha256:str
    state_bytes:int
    fit_wall_seconds:float
    fit_cpu_seconds:float

def require(ok,reason):
    if not ok:raise ValueError("L10_TRAIN_CUSTODY_BLOCKED:"+reason)

def canonical_body(regime,fit_digest,templates):
    return {
        "schema":SCHEMA,
        "supervision":SUPERVISION if regime=="KNOWN_MAPPING" else "NO_SEMANTIC_SUPERVISION",
        "regime":regime,"fit_role":ROLE,"fit_split":FIT_SPLIT,
        "fit_sources_sha256":fit_digest,
        "templates":list(templates)
    }

def _masked(clause,obs):
    require(type(clause) is str and isinstance(obs,source.Observed),
            "training output schema")
    text=clause.strip()
    require(text.endswith(".") and ";" not in text,"non-atomic fit reference")
    # Whole-entity substitution ensures no partial-string transformations.
    text,n1=re.subn(r"(?<!\w)"+re.escape(obs.subject)+r"(?!\w)",lambda _: _SLOT_S,text)
    text,n2=re.subn(r"(?<!\w)"+re.escape(obs.object)+r"(?!\w)",lambda _: _SLOT_O,text)
    require(n1==1 and n2==1 and text.count(_SLOT_S)==1 and text.count(_SLOT_O)==1,
            "training roles ambiguous")
    require(not re.search(r"\b[A-Z][A-Za-z0-9_]*F\dS\dI\dT\d\b",text),
            "source-entity leakage into learned representation")
    return text

def fit_dev_only(rows:Sequence[source.Fixture]) -> Fitted:
    require(type(rows) in (tuple,list) and len(rows)==len(source.FAMILIES)*source.FIXTURES_PER_SPLIT,
            "full DEV_FIT grid required")
    seen=set()
    groups={fam:0 for fam in source.FAMILIES}
    for row in rows:
        source.validate_fixture(row)
        require(row.split==FIT_SPLIT and row.role==ROLE,"DEV_CHECK/heldout training forbidden")
        require(row.fixture_sha256 not in seen,"duplicate source")
        seen.add(row.fixture_sha256)
        groups[row.family]+=1
    require(all(n==source.FIXTURES_PER_SPLIT for n in groups.values()),"fit family coverage")
    regimes={r.input.information_regime for r in rows}
    require(len(regimes)==1 and regimes.pop() in source.EXPOSURES,"fit information exposure")
    regime=rows[0].input.information_regime
    start=time.perf_counter(); cpu=time.process_time()
    # Bind original fit sample identity rather than generating any heldout items.
    fit_sha=sha256(source.canonical_bytes(sorted(seen))).hexdigest()
    learned={}
    if regime=="KNOWN_MAPPING":
        for row in rows:
            inp=source.public_input(row)
            # Oracle-generated supervised references are available ONLY during
            # DEV_FIT. The candidate does not observe model-target labels at test.
            labelled=controls.rule_paraphrase(inp)
            require(type(labelled) is str,"missing supervised fit references")
            clauses=labelled.split("; ")
            require(len(clauses)==len(inp.observed),"fit/reference cardinality")
            # Ensure training labels express the true fitted graph exactly.
            require(oracle.evaluate_one(row.target,labelled)["exact_semantic_graph_success"]==1,
                    "fit label is semantically invalid")
            for observed,text in zip(inp.observed,clauses):
                key=f"{observed.relation_code}:{observed.polarity}"
                templ=_masked(text,observed)
                if key in learned:
                    require(learned[key]==templ,"inconsistent learned expression")
                learned[key]=templ
    templates=tuple(sorted(learned.items()))
    require(all(k in KEYS and type(v) is str and v.count(_SLOT_S)==1
                and v.count(_SLOT_O)==1 for k,v in templates),"invalid learned templates")
    raw=source.canonical_bytes(canonical_body(regime,fit_sha,templates))
    digest=sha256(raw).hexdigest()
    result=Fitted(SCHEMA,SUPERVISION if regime=="KNOWN_MAPPING" else "NO_SEMANTIC_SUPERVISION",
                  regime,ROLE,FIT_SPLIT,fit_sha,templates,digest,len(raw),
                  time.perf_counter()-start,time.process_time()-cpu)
    validate_state(result)
    return result

def validate_state(s:Fitted):
    require(type(s) is Fitted and s.schema==SCHEMA and s.fit_role==ROLE and s.fit_split==FIT_SPLIT,
            "invalid serialized candidate contract")
    require(s.regime in source.EXPOSURES,"unknown fit regime")
    require(s.supervision==(SUPERVISION if s.regime=="KNOWN_MAPPING" else "NO_SEMANTIC_SUPERVISION"),
            "supervision source tamper")
    require(type(s.templates) is tuple and tuple(sorted(s.templates))==s.templates,
            "nondeterministic fit state")
    require(len({k for k,_ in s.templates})==len(s.templates),"duplicate template code")
    if s.regime=="WITHHELD_MAPPING":
        require(s.templates==(),"hidden code semantics were inferred without information")
    for k,template in s.templates:
        require(k in KEYS and type(template) is str and template.count(_SLOT_S)==1
                and template.count(_SLOT_O)==1 and template.endswith("."),
                "invalid learned template")
    raw=source.canonical_bytes(canonical_body(s.regime,s.fit_sources_sha256,s.templates))
    require(sha256(raw).hexdigest()==s.state_sha256 and len(raw)==s.state_bytes,
            "trained state content hash/length drift")
    require(re.fullmatch(r"[0-9a-f]{64}",s.fit_sources_sha256) is not None,
            "fit source digest missing")
    require(all(type(x) in (int,float) and math.isfinite(x) and x>=0 for x in
                (s.fit_wall_seconds,s.fit_cpu_seconds)),"nonfinite resource measurement")
    return True

def infer(s:Fitted,observed:source.ModelInput) -> str|None:
    validate_state(s)
    controls.allowed(observed)
    require(observed.information_regime==s.regime,"information budget mismatch")
    mapping=dict(s.templates)
    output=[]
    for edge in observed.observed:
        template=mapping.get(f"{edge.relation_code}:{edge.polarity}")
        if template is None:
            return None # full case abstention; no free unknown relation fill-in
        output.append(template.replace(_SLOT_S,edge.subject).replace(_SLOT_O,edge.object))
    return "; ".join(output)

def state_only_receipt(s:Fitted):
    validate_state(s)
    return dict(schema="forge.optimizer.language.l10.devfit-state-receipt-v1",
        status="SUPERVISED_DEVELOPMENT_FIT_NOT_PROSPECTIVE_EVIDENCE",
        model_type="bounded-fitted-template-table",
        fitted_state_sha256=s.state_sha256,
        fit_source_sha256=s.fit_sources_sha256,
        fit_examples=len(source.FAMILIES)*source.FIXTURES_PER_SPLIT,
        fit_role=s.fit_role,
        public_information_regime=s.regime,
        distinct_learned_relation_polarity_patterns=len(s.templates),
        expected_patterns=len(KEYS),
        state_bytes=s.state_bytes,
        fit_wall_seconds=round(s.fit_wall_seconds,9),
        fit_cpu_seconds=round(s.fit_cpu_seconds,9),
        source_labels_saved=False,output_text_saved=False,
        source_study_l9_reused=False,prospective_examples_exposed=0,
        scientific_go=False)

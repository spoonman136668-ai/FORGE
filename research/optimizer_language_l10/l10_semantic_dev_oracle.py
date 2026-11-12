#!/usr/bin/env python3
"""L10 development-only explicit propositional semantic fidelity evaluator.

Independent of WebNLG, L9, external models or APIs. This is intentionally
a bounded interpretable controlled-English semantics oracle, not an evaluator
of arbitrary natural-language entailment. A new prospective first-use
implementation, frozen source custody and permission are required before
processing any L10 held-out examples.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import hashlib
import json
import math
import re
import time
from typing import Callable, Sequence

SCHEMA = "forge.optimizer.language.l10.semantic-fidelity-dev-oracle-v1"
REPORT_SCHEMA = "forge.optimizer.language.l10.semantic-fidelity-development-numeric-v1"
ROLE = "L10_SYNTHETIC_DEV"
PREDICATES = frozenset(("located_in", "owns", "parent_of"))
_ENTITY = r"([A-Z][a-zA-Z0-9_]*)"
_CANON = re.compile(rf"^{_ENTITY} :: (located_in|owns|parent_of) :: {_ENTITY} :: ([+-])$")
# Every alternative is independently specified as an unambiguous reversible mapping
# to a signed atomic proposition. A nonmatching sentence is UNPARSEABLE, not correct.
_PATTERNS = (
    (re.compile(rf"^{_ENTITY} resides in {_ENTITY}\.$"), "located_in", False, 1),
    (re.compile(rf"^{_ENTITY} does not reside in {_ENTITY}\.$"), "located_in", False, -1),
    (re.compile(rf"^{_ENTITY} is home to {_ENTITY}\.$"), "located_in", True, 1),
    (re.compile(rf"^{_ENTITY} is not home to {_ENTITY}\.$"), "located_in", True, -1),
    (re.compile(rf"^{_ENTITY} owns {_ENTITY}\.$"), "owns", False, 1),
    (re.compile(rf"^{_ENTITY} does not own {_ENTITY}\.$"), "owns", False, -1),
    (re.compile(rf"^{_ENTITY} belongs to {_ENTITY}\.$"), "owns", True, 1),
    (re.compile(rf"^{_ENTITY} does not belong to {_ENTITY}\.$"), "owns", True, -1),
    (re.compile(rf"^{_ENTITY} is parent of {_ENTITY}\.$"), "parent_of", False, 1),
    (re.compile(rf"^{_ENTITY} is not parent of {_ENTITY}\.$"), "parent_of", False, -1),
    (re.compile(rf"^{_ENTITY} is child of {_ENTITY}\.$"), "parent_of", True, 1),
    (re.compile(rf"^{_ENTITY} is not child of {_ENTITY}\.$"), "parent_of", True, -1),
)

@dataclass(frozen=True, order=True)
class Claim:
    subject: str
    predicate: str
    object: str
    polarity: int = 1

@dataclass(frozen=True)
class DevelopmentCase:
    family_id: str
    role: str
    source_identity_sha256: str
    claims: tuple[Claim, ...]

@dataclass(frozen=True)
class Parse:
    claims: tuple[Claim, ...]
    abstention: bool
    unparseable_clauses: int
    duplicate_claims: int

def require(ok: bool, reason: str):
    if not ok:
        raise ValueError("L10_SEMANTIC_DEV_FAIL_CLOSED:" + reason)

def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()

def valid_claim(c: Claim):
    return (type(c) is Claim and c.predicate in PREDICATES
            and c.polarity in (1, -1)
            and all(re.fullmatch(_ENTITY, e) for e in (c.subject, c.object))
            and c.subject != c.object)

def parse_clause(value: str) -> Claim | None:
    match = _CANON.fullmatch(value)
    if match:
        a, p, b, pol = match.groups()
        claim = Claim(a, p, b, 1 if pol == "+" else -1)
        return claim if valid_claim(claim) else None
    for pattern, predicate, reverse, polarity in _PATTERNS:
        match = pattern.fullmatch(value)
        if match:
            a, b = match.groups()
            claim = Claim(b, predicate, a, polarity) if reverse else Claim(a, predicate, b, polarity)
            return claim if valid_claim(claim) else None
    return None

def parse(text: str | None) -> Parse:
    require(text is None or type(text) is str, "non-text inference")
    if text is None or text.strip() == "":
        return Parse((), True, 0, 0)
    require(len(text.encode("utf-8")) <= 16000, "unbounded model output")
    pieces = text.strip().split(";")
    require(len(pieces) <= 48, "too many claims")
    seen = set()
    parsed = []
    bad = 0
    duplicate = 0
    for item in pieces:
        claim = parse_clause(item.strip())
        if claim is None:
            bad += 1
        elif claim in seen:
            duplicate += 1
        else:
            seen.add(claim)
            parsed.append(claim)
    return Parse(tuple(parsed), False, bad, duplicate)

def case_identity(c: DevelopmentCase) -> str:
    require(type(c) is DevelopmentCase and len(c.claims) > 0, "case schema")
    require(re.fullmatch(r"[a-z][a-z0-9-]{3,50}", c.family_id) is not None, "family id")
    require(c.role == ROLE, "protected source is not admitted")
    require(len(c.claims) <= 16 and all(valid_claim(p) for p in c.claims), "invalid claims")
    require(len(set(c.claims)) == len(c.claims), "duplicate expected claims")
    require(not any(Claim(p.subject, p.predicate, p.object, -p.polarity) in c.claims
                    for p in c.claims), "contradictory truth fixture")
    canonical = [[p.subject, p.predicate, p.object, p.polarity] for p in sorted(c.claims)]
    raw = json.dumps([c.family_id, canonical], ensure_ascii=False, separators=(",", ":")).encode()
    digest = _sha(raw)
    require(c.source_identity_sha256 == digest, "source identity SHA drift")
    return digest

def constructed_case(family_id: str, claims: Sequence[Claim]) -> DevelopmentCase:
    """Dev-fixture helper only. Do not call this to expose future heldout sources."""
    provisional = DevelopmentCase(family_id, ROLE, "0"*64, tuple(claims))
    require(len(set(provisional.claims)) == len(provisional.claims), "duplicated generated facts")
    require(not any(Claim(p.subject,p.predicate,p.object,-p.polarity) in provisional.claims for p in provisional.claims),
            "generated fixture is self-contradictory")
    require(len(provisional.claims)>0 and len(provisional.claims)<=16
            and all(valid_claim(p) for p in provisional.claims),"invalid generated fixture")
    require(re.fullmatch(r"[a-z][a-z0-9-]{3,50}",family_id) is not None, "invalid fixture family")
    raw=json.dumps([family_id,[[p.subject,p.predicate,p.object,p.polarity]
                 for p in sorted(provisional.claims)]],ensure_ascii=False,separators=(",",":")).encode()
    return DevelopmentCase(family_id,ROLE,_sha(raw),provisional.claims)

def evaluate_one(case: DevelopmentCase, output: str | None) -> dict:
    case_identity(case)
    parsed = parse(output)
    expected = set(case.claims)
    actual = set(parsed.claims)
    supported = len(actual & expected)
    missing = len(expected - actual)
    extras = len(actual - expected)
    contradictions = sum(Claim(q.subject,q.predicate,q.object,-q.polarity) in expected
                         for q in actual - expected)
    require(supported + missing == len(expected), "expected denominator")
    success = int((not parsed.abstention) and not parsed.unparseable_clauses
                  and not parsed.duplicate_claims and not missing and not extras)
    return dict(expected_claims=len(expected),supported_claims=supported,
                missing_claims=missing,extra_claims=extras,contradictory_claims=contradictions,
                abstentions=int(parsed.abstention),unparseable_clauses=parsed.unparseable_clauses,
                duplicate_claims=parsed.duplicate_claims,exact_semantic_graph_success=success)

_COUNTS = ("expected_claims","supported_claims","missing_claims","extra_claims",
           "contradictory_claims","abstentions","unparseable_clauses",
           "duplicate_claims","exact_semantic_graph_success")
def evaluate_dev(cases: Sequence[DevelopmentCase],
                 render: Callable[[tuple[Claim, ...]], str | None],
                 model_id: str, expected_family_count: int | None = None) -> dict:
    require(type(model_id) is str and re.fullmatch(r"[a-z][a-z0-9-]{2,60}",model_id) is not None,
            "unfrozen model id")
    require(type(cases) in (list,tuple) and len(cases)>0, "empty examples")
    require(callable(render),"missing model callback")
    seen = set()
    by_family: dict[str, Counter] = {}
    start = time.perf_counter()
    cpu = time.process_time()
    for c in cases:
        h = case_identity(c)
        require(h not in seen, "duplicate source")
        seen.add(h)
        # Only claims are passed to the model; no oracle labels/target text.
        predicted = render(tuple(c.claims))
        scores = evaluate_one(c, predicted)
        counts = by_family.setdefault(c.family_id, Counter())
        counts.update(scores)
        counts["examples"] += 1
    if expected_family_count is not None:
        require(len(by_family)==expected_family_count, "missing dev family")
    rows=[]
    for family,counts in sorted(by_family.items()):
        n=counts["examples"]
        e=counts["expected_claims"]
        require(n>0 and e>0 and counts["supported_claims"]+counts["missing_claims"]==e,
                "invalid family totals")
        result={"family_sha256":_sha(family.encode()),"examples":n}
        result.update({k:int(counts[k]) for k in _COUNTS})
        result["semantic_exact_rate"]=round(counts["exact_semantic_graph_success"]/n,9)
        result["abstention_rate"]=round(counts["abstentions"]/n,9)
        result["signed_claim_recall"]=round(counts["supported_claims"]/e,9)
        result["signed_claim_precision"]=round(
            counts["supported_claims"]/max(1,counts["supported_claims"]+counts["extra_claims"]),9)
        rows.append(result)
    n=len(cases)
    report=dict(schema=REPORT_SCHEMA,status="SYNTHETIC_DEVELOPMENT_ONLY_NOT_PROSPECTIVE_TRANSFER",
                method_id=model_id,cases=n,families=len(rows),family_rows=rows,
                macro_exact_rate=round(sum(x["semantic_exact_rate"] for x in rows)/len(rows),9),
                micro_exact_rate=round(sum(x["exact_semantic_graph_success"] for x in rows)/n,9),
                micro_abstention_rate=round(sum(x["abstentions"] for x in rows)/n,9),
                serial_wall_seconds=round(time.perf_counter()-start,6),
                serial_cpu_seconds=round(time.process_time()-cpu,6),
                source_role=ROLE,raw_source_saved=False,raw_output_saved=False,
                references_seen_by_model=0,prospective_source_examples_consumed=0,
                scientific_go=False)
    assert_numeric_report(report)
    return report

def assert_numeric_report(r):
    require(r["schema"]==REPORT_SCHEMA and r["source_role"]==ROLE
            and r["scientific_go"] is False,"report scientific/status drift")
    require(r["raw_source_saved"] is False and r["raw_output_saved"] is False
            and r["prospective_source_examples_consumed"]==0
            and r["references_seen_by_model"]==0,"source leakage")
    require(len(r["family_rows"])==r["families"],"missing family")
    must_count=sum(row["examples"] for row in r["family_rows"])
    require(must_count==r["cases"],"partial case reporting")
    for row in r["family_rows"]:
        require(re.fullmatch(r"[0-9a-f]{64}", row["family_sha256"]) is not None,"family name leakage")
        require(all(type(row[key]) is int and row[key]>=0 for key in (*_COUNTS,"examples")),
                "malformed counts")
        require(row["exact_semantic_graph_success"]<=row["examples"]
                and row["abstentions"]<=row["examples"],"invalid success count")
        require(row["supported_claims"]+row["missing_claims"]==row["expected_claims"],
                "missing semantic graph")
        require(row["contradictory_claims"]<=row["extra_claims"],
                "contradiction numerator")
    require(all(type(r[k]) in (float,int) and math.isfinite(r[k]) and r[k]>=0 for k in
                ("macro_exact_rate","micro_exact_rate","micro_abstention_rate",
                 "serial_wall_seconds","serial_cpu_seconds")),"invalid numeric measures")
    return True

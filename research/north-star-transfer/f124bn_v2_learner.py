"""F124-BN compact task-local learned GF(2) relation and causal-path verifier.

V2 precommitted after pre-use-only underpowered fit; no registered case used:
robust independent output-bit affine learning, public-only validation,
invertible 272-bit linear relation, exact predecessor/source continuity.
Sourceblind: cannot inspect true source generator, oracle keys or case labels.
"""
from __future__ import annotations

import hashlib
import json
import random

MAX_RANSAC=2048
MAX_FIT_ERRORS_PER_BIT=6
MAX_CHECK_TOTAL_ERRORS=2
BUDGET_40=40
CHECK_8=8


def need(x,label):
    if not x: raise ValueError("F124BN_LEARN_"+label)


def solve(equations,unknowns):
    """GF(2) Gaussian elimination with explicit inconsistent/underdetermined stop."""
    basis={}
    for coefficients,rhs in equations:
        need(type(coefficients) is int and 0<=coefficients<1<<unknowns
             and rhs in (0,1),"PUBLIC_GF2_ROW")
        x=coefficients
        y=rhs
        while x:
            pivot=x.bit_length()-1
            if pivot not in basis:
                basis[pivot]=(x,y)
                break
            bx,by=basis[pivot]
            x^=bx
            y^=by
        else:
            if y: return None
    if len(basis)!=unknowns: return None
    result=0
    for pivot in sorted(basis):
        row,rhs=basis[pivot]
        lower=row&((1<<pivot)-1)
        # Elimination uses the highest set bit pivot, all remaining
        # coefficients are smaller and already solved.
        bit=rhs^((lower&result).bit_count()&1)
        result|=bit<<pivot
    need(all(((row&result).bit_count()&1)==rhs
             for row,rhs in equations),"SOLVE_INTERNAL")
    return result


def _pairs(fit,check):
    need(type(fit) in (list,tuple) and len(fit)==40
         and type(check) in (list,tuple) and len(check)==8,
         "PUBLIC_40_8")
    for x,y in list(fit)+list(check):
        need(type(x) is int and type(y) is int
             and 0<=x<65536 and 0<=y<65536,"BIT_16")


def _error(equations,weight):
    return sum(((coeff&weight).bit_count()&1)!=rhs
               for coeff,rhs in equations)


def fit(fit_pairs,check_pairs):
    """Training is a finite reproducible public-only optimization."""
    _pairs(fit_pairs,check_pairs)
    seed=int.from_bytes(hashlib.sha256(json.dumps(
        list(fit_pairs),separators=(",",":")).encode()).digest(),"big")
    rows=[]
    bias=0
    trials=0
    for output_bit in range(16):
        equations=[(x|1<<16,(y>>output_bit)&1)
                   for x,y in fit_pairs]
        candidate=solve(equations,17)
        if candidate is None:
            # Randomness is fixed entirely by public FIT, not source identity.
            rng=random.Random(seed ^ ((output_bit+1)*0x9e3779b97f4a7c15))
            best=None
            best_error=41
            for _ in range(MAX_RANSAC):
                indices=rng.sample(range(40),17)
                model=solve([equations[i] for i in indices],17)
                trials+=1
                if model is None: continue
                err=_error(equations,model)
                if err<best_error or (err==best_error and (
                        best is None or model<best)):
                    best,best_error=model,err
                if err<=MAX_FIT_ERRORS_PER_BIT:break
            candidate=best
        need(candidate is not None and
             _error(equations,candidate)<=MAX_FIT_ERRORS_PER_BIT,
             "FIT_CAUSAL_MAPPING_NOT_IDENTIFIABLE")
        rows.append(candidate&65535)
        bias|=((candidate>>16)&1)<<output_bit
    # Full linear relation must be invertible, no silently fitted lookup table.
    matrix=[(row,0) for row in rows]
    need(len(rows)==16 and all(
        solve([(rows[j],int(j==i)) for j in range(16)],16) is not None
        for i in range(16)), "NONINVERTIBLE_LEARNED_RELATION")
    model={"rows":tuple(rows),"bias":bias}
    check_err=sum((forward(x,model)^y).bit_count() for x,y in check_pairs)
    need(check_err<=MAX_CHECK_TOTAL_ERRORS,
         "PUBLIC_CHECK_REJECTED")
    return model,{"fit_samples":40,"check_samples":8,
                  "total_RANSAC_draws":trials,
                  "check_bit_errors":check_err,
                  "parameter_bits":272,
                  "oracle_or_operator_name_used":False,
                  "training_FIT_only":True}


def forward(x,model):
    need(type(x) is int and 0<=x<65536 and len(model["rows"])==16,
         "FORWARD_INPUT")
    return sum((((x&r).bit_count()&1)^((model["bias"]>>j)&1))<<j
               for j,r in enumerate(model["rows"]))


def inverse(y,model):
    need(type(y) is int and 0<=y<65536,"INVERSE_INPUT")
    rows=model["rows"]
    candidate=solve([(r,((y^model["bias"])>>j)&1)
                     for j,r in enumerate(rows)],16)
    need(candidate is not None and forward(candidate,model)==y,
         "INVERSE_UNCERTAIN")
    return candidate


def _value(bits):
    need(isinstance(bits,list) and len(bits)==16
         and all(type(b) is int and b in (0,1) for b in bits),
         "GRAPH_BIT_STRING")
    return sum(v<<i for i,v in enumerate(bits))


def causal_path(graph,model):
    """Reject if any edge's learned predecessor does not match prior carry."""
    need(set(graph)=={"start","target","roles","edges","demos"},
         "UNMODIFIED_NATIVE_GRAPH_FORMAT")
    current=graph["start"]
    carry=None
    operations=0
    for role in graph["roles"]:
        edges=[e for e in graph["edges"]
               if e["from"]==current and e["role"]==role]
        if len(edges)!=1:
            return False,operations
        edge=edges[0]
        source=inverse(_value(edge["src_bits"]),model)
        operations+=1
        if carry is not None and source!=carry:
            return False,operations
        carry=_value(edge["dst_bits"])
        current=edge["to"]
    return current==graph["target"],operations

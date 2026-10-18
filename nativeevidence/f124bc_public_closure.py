"""F124-BC independent public forward-relation XOR closure certificate.

Seven public-only affine-parallelogram checks use the ORIGINAL 24 extra
balanced-basis source query responses (positions 24..47). This code does
not learn/use either inverse, source operator, true graph labels or hidden
key when constructing the certificate. It may VETO, never add positives
or change the original F124-AZ jointly learned whole-task route.
"""
from __future__ import annotations
import f124az_joint_public_inverse as original
import f124q_fresh_source as witness
TOTAL=48
FIT=40
CHECK=8
POLICIES={
 "closure4":{"affine_violation_min":4,"feistel_violation_max":1},
 "closure5":{"affine_violation_min":5,"feistel_violation_max":0}}
PAIR_INDICES=((0,5),(1,6),(2,7),(3,8),(4,9),(5,10),(6,11))
def need(ok,tag):witness.need(ok,"F124BC_PUBLIC_XOR_CERTIFICATE_"+tag)
def value(bits):
    need(type(bits) is list and len(bits)==16 and
         all(type(b) is int and b in (0,1) for b in bits),"ORIGINAL_PUBLIC_16BITS")
    return sum(bit<<i for i,bit in enumerate(bits))
def certificate(demos,query):
    need(type(demos) is list and len(demos)==TOTAL
         and query in ("balanced_basis48","random48"),"PUBLIC_48_ONLY")
    if query=="random48":
        return {"witnesses":0,"violations":0,"certifiable":False,
                "observed_only":True,"extra_public_queries":0,
                "xor_bit_operations_lower":0}
    expected=[0]+[1<<i for i in range(16)]+[
        (1<<i)|(1<<((i+5)%16)) for i in range(7)]
    support=[value(row["input_bits"]) for row in demos[24:]]
    need(support==expected,"INDEPENDENT_PUBLIC_BASIS_WITNESS_IDENTITY")
    out=[value(row["output_bits"]) for row in demos[24:]]
    zero=out[0]
    violated=[]
    for j,(a,b) in enumerate(PAIR_INDICES):
        nonzero=(out[17+j]^out[1+a]^out[1+b]^zero)!=0
        violated.append(bool(nonzero))
    need(len(violated)==7,"EXACT_7_PUBLIC_AFFINE_CLOSURES")
    return {"witnesses":7,"violations":sum(violated),
        "violating_witness_indices":[j for j,x in enumerate(violated) if x],
        "certifiable":True,"observed_only":True,
        "extra_public_queries":0,"xor_bit_operations_lower":7*16*3}
def train(demos,nonce,query,policy):
    need(policy in POLICIES and query in ("balanced_basis48","random48"),
         "ONLY_PRECOMMITTED_QUERY_AND_THRESHOLDS")
    cert=certificate(demos,query)
    model=original.train(demos,nonce,0)
    baseline=model["choice"]
    reject=False
    p=POLICIES[policy]
    if cert["certifiable"] and baseline=="affine":
        reject=cert["violations"]>=p["affine_violation_min"]
    elif cert["certifiable"] and baseline=="feistel":
        reject=cert["violations"]<=p["feistel_violation_max"]
    if reject:model["choice"]="abstain"
    model["public_closure_certificate"]=cert
    model["public_closure_policy"]=policy
    model["original_joint_choice"]=baseline
    model["public_closure_rejected"]=reject
    model["source_operator_seen"]=False
    model["graph_ground_truth_seen"]=False
    model["new_public_source_calls"]=0
    model["extra_public_witness_bits_lower"]=7*16
    model["extra_public_operation_lower"]=cert["xor_bit_operations_lower"]
    return model
def score(graph,base,delta,model,demos):
    need(model["public_closure_policy"] in POLICIES
         and model["new_public_source_calls"]==0
         and model["source_operator_seen"] is False
         and model["graph_ground_truth_seen"] is False,
         "NO_PRIVILEGED_ORACLE_INPUT")
    val,work,diag=original.score(graph,base,delta,model,demos)
    diag.update({"original_joint_choice":model["original_joint_choice"],
                 "public_closure_witnesses":
                      model["public_closure_certificate"]["witnesses"],
                 "public_closure_violations":
                      model["public_closure_certificate"]["violations"],
                 "public_closure_veto":model["public_closure_rejected"],
                 "extra_public_responses":0})
    return val,work,diag

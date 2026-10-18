"""F124-BB task-wide public-only competing inverse contradiction veto.

Unchanged original AZ margin=0 joint model fits affine+structural Feistel
from original 40 PUBLIC FIT pairs. Only if both hypotheses independently
pass their original eligibility rules and the 8-public-CHECK aggregate
contrast is small (<=8 bits) do we reject decisions contradicted by
public CHECK input-bit evidence. No new source query or truth labels.
"""
from __future__ import annotations
import f124az_joint_public_inverse as joint
import f124av_informative_inverse as affine
import f124ay_learned_composition as feistel
import f124q_fresh_source as witness

VETO_BITS=(2,4)
PUBLIC_TOTAL=48
PUBLIC_FIT=40
PUBLIC_CHECK=8
MAX_CONTESTED_AGGREGATE_MARGIN=8
ORIGINAL_CHECK_MIN=96
ORIGINAL_AFFINE_FIT_BUDGET=12
def need(x,label):witness.need(x,"F124BB_PUBLIC_DISAGREEMENT_"+label)

def alternatives_eligible(model):
    info=model["affine_info"]
    a=(model["affine_coefficients"] is not None
       and info["fit_bit_errors"] is not None
       and info["fit_bit_errors"]<=ORIGINAL_AFFINE_FIT_BUDGET
       and model["affine_check"]>=ORIGINAL_CHECK_MIN)
    f=model["feistel_check"]>=ORIGINAL_CHECK_MIN
    return a,f

def public_inverse_correct_bits(row,model):
    output=row["output_bits"]
    target=row["input_bits"]
    need(len(output)==len(target)==16,"EXACT_16_BIT_PUBLIC_PAIR")
    coefficient=model["affine_coefficients"]
    val=None if coefficient is None else affine.gf.inverse_output(
         affine.gf.integer(output),coefficient)
    a=[(val>>j)&1 for j in range(16)] if val is not None else None
    f=feistel.predict(model["feistel_model"],output)
    af=sum(int(x==y) for x,y in zip(a,target)) if a is not None else 0
    fe=sum(int(x==y) for x,y in zip(f,target))
    need(0<=af<=16 and 0<=fe<=16,"PUBLIC_ONLY_BITS")
    return af,fe

def train(demos,nonce,veto_bits):
    need(type(demos) is list and len(demos)==PUBLIC_TOTAL
         and veto_bits in VETO_BITS,"REGISTERED_48_RESPONSE_BUDGET")
    model=joint.train(demos,nonce,0)
    original_choice=model["choice"]
    eligible_affine,eligible_feistel=alternatives_eligible(model)
    contested=bool(eligible_affine and eligible_feistel and
        abs(model["affine_check"]-model["feistel_check"])
        <=MAX_CONTESTED_AGGREGATE_MARGIN
        and original_choice in ("affine","feistel"))
    public_competing_evidence=[]
    if contested:
        for row in demos[PUBLIC_FIT:]:
            a,f=public_inverse_correct_bits(row,model)
            chosen=a if original_choice=="affine" else f
            rival=f if original_choice=="affine" else a
            public_competing_evidence.append({
                "selected_correct_bits":chosen,
                "competing_correct_bits":rival,
                "competing_minus_selected":rival-chosen})
        need(len(public_competing_evidence)==PUBLIC_CHECK,
             "EIGHT_ORIGINAL_PUBLIC_CHECK_ROWS")
    veto=bool(contested and any(
        row["competing_minus_selected"]>=veto_bits
        for row in public_competing_evidence))
    if veto:model["choice"]="abstain"
    model["original_joint_choice_before_public_veto"]=original_choice
    model["public_disagreement_veto_bits"]=veto_bits
    model["original_public_CHECK_contested"]=contested
    model["public_competing_CHECK_evidence"]=public_competing_evidence
    model["public_disagreement_veto_applied"]=veto
    model["extra_public_queries"]=0
    model["extra_CHECK_bit_comparisons_lower"]=(
        PUBLIC_CHECK*16*2 if contested else 0)
    model["extra_public_task_workspace_bits_lower"]=(
        PUBLIC_CHECK*16*2 if contested else 0)
    model["source_operator_label_seen"]=False
    model["graph_positive_negative_label_seen"]=False
    model["oracle_inverse_seen"]=False
    return model

def score(graph,base,delta,model,demos):
    need(model["public_disagreement_veto_bits"] in VETO_BITS
         and model["extra_public_queries"]==0
         and not model["source_operator_label_seen"]
         and not model["graph_positive_negative_label_seen"]
         and not model["oracle_inverse_seen"],
         "PRESERVE_ORIGINAL_JOINT_MODEL_SAFETY")
    value,work,diag=joint.score(graph,base,delta,model,demos)
    diag.update({
        "original_joint_choice_before_veto":
            model["original_joint_choice_before_public_veto"],
        "public_contested":model["original_public_CHECK_contested"],
        "public_veto_applied":model["public_disagreement_veto_applied"],
        "veto_margin_correct_bits":
            model["public_disagreement_veto_bits"],
        "new_public_responses":0,
        "oracle_label_used":False})
    return value,work,diag

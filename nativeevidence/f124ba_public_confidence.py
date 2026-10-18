"""F124-BA source-blind, task-wide lower-tail public CHECK rejection.

The original F124-AZ jointly fitted affine/Feistel router remains unchanged.
Additional evidence comes exclusively from the SAME 8 public CHECK pairs:
even with strong aggregate accuracy, reject a task whose weakest public
CHECK input cannot be reconstructed to 12/16 or 14/16 bits. No new public
queries, source class/oracle data, graph acceptance labels, or extra cells.
"""
from __future__ import annotations
import f124az_joint_public_inverse as old
import f124av_informative_inverse as affine
import f124ay_learned_composition as feistel
import f124q_fresh_source as witness

ROW_FLOORS=(12,14)
TOTAL=48
FIT=40
CHECK=8
MARGIN=0

def need(x,k):witness.need(x,"F124BA_LOWER_TAIL_"+k)

def public_row_correct(model,public_row):
    result=public_row["output_bits"]
    truth=public_row["input_bits"]
    need(len(result)==len(truth)==16,"SAME_16BIT_PUBLIC_EVIDENCE")
    if model["choice"]=="affine":
        coefficient=model["affine_coefficients"]
        if coefficient is None:return 0
        x=affine.gf.inverse_output(affine.gf.integer(result),coefficient)
        if x is None:return 0
        predicted=[(x>>k)&1 for k in range(16)]
    elif model["choice"]=="feistel":
        predicted=feistel.predict(model["feistel_model"],result)
    else:
        return 0
    return sum(int(a==b) for a,b in zip(predicted,truth))

def train(demos,nonce,row_floor):
    need(type(demos) is list and len(demos)==TOTAL
         and row_floor in ROW_FLOORS,"REGISTERED_48_RESPONSE_BUDGET")
    model=old.train(demos,nonce,MARGIN)
    prechoice=model["choice"]
    check_rows=[public_row_correct(model,d) for d in demos[FIT:]]
    need(len(check_rows)==CHECK and
         all(0<=x<=16 for x in check_rows),
         "EXACT_8_HELD_PUBLIC_CHECK_ROWS")
    weakest=min(check_rows)
    if weakest<row_floor:model["choice"]="abstain"
    model["original_joint_route_before_lower_tail"]=prechoice
    model["minimum_check_bits_required_each_row"]=row_floor
    model["weakest_public_check_row_correct_bits"]=weakest
    model["public_CHECK_row_correct_bits"]=check_rows
    model["extra_public_bit_comparisons_lower"]=CHECK*16
    model["model_receives_graph_acceptance_label"]=False
    model["model_receives_source_class"]=False
    model["lower_tail_rejection_only"]=True
    return model

def score(graph,base,delta,model,demos):
    need(model["minimum_check_bits_required_each_row"] in ROW_FLOORS
         and model["lower_tail_rejection_only"]
         and not model["model_receives_graph_acceptance_label"]
         and not model["model_receives_source_class"],
         "UNCHANGED_ORIGINAL_ROUTER_NO_ORACLE")
    value,work,diagnostic=old.score(graph,base,delta,model,demos)
    diagnostic.update({
        "selected_before_lower_tail":
            model["original_joint_route_before_lower_tail"],
        "weakest_public_check_row_correct_bits":
            model["weakest_public_check_row_correct_bits"],
        "minimum_public_check_bits_each_row":
            model["minimum_check_bits_required_each_row"],
        "new_public_queries":0,
        "source_operator_known":False,
        "graph_truth_known":False})
    return value,work,diagnostic

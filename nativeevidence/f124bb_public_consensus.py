"""F124-BB task-wide ORIGINAL public router plus graph-local independent
transition consistency. This is a PUBLIC graph verification pass, not oracle
truth, label inspection, source-key matching, or a replacement of the original
7 active +9 retained scientific scorer.

Exactly the unchanged 48 public responses fit the router; different eta
verifiers use the *same* PUBLIC decoded graph and disclose a second bounded
scoring cost. A veto can only remove predictions, never synthesize positives.
"""
from __future__ import annotations
import math
import f124az_joint_public_inverse as original
import f124am_example_affine_learner as gf
import f124ay_learned_composition as nonlin
import f124aj_example_operator_learner as public
import f124ag_transition_models as trans
import f124q_fresh_source as q

ETAS=(0.,.2)
def need(ok,tag):q.need(ok,"F124BB_PUBLIC_CONSENSUS_"+tag)

def train(demos,nonce):
    need(len(demos)==48 and type(nonce) is str and nonce,
         "EXACT_48_UNCHANGED_PUBLIC_FIT")
    return original.train(demos,nonce,0)

def public_graph(graph,demos,model):
    raw,first,nonce=public.public_task(graph)
    need(first==demos[:24] and model["choice"] in ("affine","feistel"),
         "GRAPH_PUBLIC_TASK_IDENTITY")
    for edge in raw["edges"]:
        output=edge["src_bits"]
        if model["choice"]=="affine":
            from f124av_informative_inverse import gf as affine_gf
            value=affine_gf.inverse_output(affine_gf.integer(output),model["affine_coefficients"])
            need(value is not None,"VALID_AFFINE_INVERSION")
            edge["src_bits"]=[(value>>i)&1 for i in range(16)]
        else:
            edge["src_bits"]=nonlin.predict(model["feistel_model"],output)
    trans.frozen.prior.parent.validate_15(raw)
    return raw

def score(graph,base,delta,model,demos,eta):
    need(eta in ETAS and len(demos)==48 and
         model["margin"]==0,"ONLY_PRECOMMITTED_CONSENSUS")
    original_score,old_work,old_diag=original.score(graph,base,delta,model,demos)
    if original_score<0:
        return original_score,old_work,{"original_accepted":False,
           "consensus_accepted":False,"veto":False,
           "second_pass_performed":False,"extra_edge_decode_bits":0,
           "extra_public_graph_state_bits_lower":0}
    graph_public=public_graph(graph,demos,model)
    res,raw,ratio,work=trans.ygg_transition(graph_public,list(base),list(delta),eta)
    need(math.isfinite(res) and work["max_active"]<=7
         and work["max_retained"]<=9,
         "SECOND_PASS_ORIGINAL_HARD_SEVEN_NINE")
    accept=res>=0
    return original_score if accept else -1e9,old_work,{
        "original_accepted":True,"consensus_accepted":accept,
        "veto":not accept,"second_pass_performed":True,
        "verification_eta":eta,"verification_score":res,
        "max_verifier_active":work["max_active"],
        "max_verifier_retained":work["max_retained"],
        "extra_verifier_public_edge_scans":work["public_edge_scans"],
        "extra_verifier_bit_ops":work["raw_bit_ops"],
        "extra_edge_decode_bits":16*len(graph_public["edges"]),
        "extra_public_graph_state_bits_lower":
             32*len(graph_public["edges"]),
        "operator_or_truth_seen":False}

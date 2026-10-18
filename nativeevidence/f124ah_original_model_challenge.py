"""F124-AH frozen unmodified models and diagnostic-only Wingless hop replay."""
from __future__ import annotations
import types
from types import SimpleNamespace
import f124ah_frozen_source as s
import f124ag_transition_models as ag
import f124ae_scoring_transfer as old
import f124ac_passive_trace as trace
import f124ac_development_evidence as evaluator

def ygg(g,base,delta,arm):
    s.need(arm in ("AG_eta_0_1","AG_eta_0","AD_anchor10",
                   "AB_anchor16","T_original"),"FROZEN_YGG_ARM")
    if arm=="AG_eta_0_1":
        score,raw,ratio,work=ag.ygg_transition(g,base,delta,.1)
    elif arm=="AG_eta_0":
        score,raw,ratio,work=ag.ygg_transition(g,base,delta,0.)
    elif arm=="AD_anchor10":
        score,raw,ratio,work=old.anchored_score(g,base,delta,10)
    elif arm=="AB_anchor16":
        score,raw,ratio,work=old.anchored_score(g,base,delta,16)
    else:
        score,work=old.frozen_t(g,base,delta)
    s.need(work["max_active"]<=7 and work["max_retained"]<=9,
           "ORIGINAL_YGG_HARD_7_PLUS_9")
    return score,work

def wing(g,base,delta,arm):
    s.need(arm in ("AA_original_one","AB_original_three"),
           "ORIGINAL_WING_ARM")
    if arm=="AA_original_one":score,work=old.frozen_packed(g,base,delta)
    else:score,work=old.frozen_three(g,base,delta)
    s.need(work["max_active"]<=64 if arm=="AA_original_one"
           else work["max_active"]<=192,"ORIGINAL_WING_STATE_BUDGET")
    return score,work

def wing_source_blind_trace(g,base,delta):
    """Original AC observer bytecode, scoped structural validator up to 15."""
    proxy=SimpleNamespace(original=SimpleNamespace(parent=SimpleNamespace(
        validate_extended=s.parent.prior.parent.validate_15)),need=s.need)
    env=dict(trace.observe_wing.__globals__)
    env["frozen"]=proxy
    fn=types.FunctionType(trace.observe_wing.__code__,env,
                          trace.observe_wing.__name__,
                          trace.observe_wing.__defaults__)
    value,work,path=fn(g,base,delta)
    original,expected=old.frozen_packed(g,base,delta)
    s.need(value==original and work==expected
           and all(step["hop"]==i and
                   len(step["kept"])<=64
                   for i,step in enumerate(path,1)),
           "ONE_PACKED_STATE_SOURCE_BLIND_TRACE_PARITY")
    return value,work,path

def posthoc_public_path(g,family):
    """Only called by evaluator AFTER source-blind scoring and traces."""
    original=s.restore(g,family)
    carry=[(original["start"],None,[])]
    for role in original["roles"]:
        new=[]
        for node,key,hist in carry:
            for e in original["edges"]:
                if e["from"]!=node or e["role"]!=role:continue
                dist=0 if key is None else sum(a!=b for a,b in
                                                zip(key,e["src_bits"]))
                if key is None or dist<=(1 if family=="rotate4_tolerant" else 0):
                    new.append((e["to"],tuple(e["dst_bits"]),
                                hist+[(e["to"],tuple(e["dst_bits"]))]))
                    s.need(len(new)<=256,"PUBLIC_SCORER_ROUTE_BOUND")
        carry=new
    options=[hist for node,key,hist in carry if node==original["target"]]
    s.need(len(options)==1,"INDEPENDENT_PUBLIC_REFERENCE_POSITIVE")
    return options[0]

def report_wing_positive(g,family,source_blind_trace):
    witness=posthoc_public_path(g,family)
    joined=evaluator.causal_join(source_blind_trace,witness,wing=True)
    # A packed-code match is only a proxy and NEVER proof of raw-key survival.
    collision=evaluator.collision_census(g)
    return {"first_missing_candidate_hop":
            joined["first_reference_missing_candidate_hop"],
            "first_packed_proxy_pruned_hop":
            joined["first_reference_pruned_hop"],
            "packed_proxy_present_final":
            joined["reference_survived_final"],
            "per_hop_proxy":joined["by_hop"],
            "raw_keys_with_same_packed_code":
            collision["all_public_packed_alias_sets"],
            "same_node_role_src_key_collision":
            collision["same_node_role_source_alias_sets"],
            "no_raw_key_path_survival_claim":True}

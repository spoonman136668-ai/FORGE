"""F124-AU graph-conditioned choice of exactly ONE packed 12-bit encoding.

The policy is fitted on TRAIN-FIT only and consumes PUBLIC normalized graph
shape at inference. It never scores parallel alternatives, retains another
path, or accesses source operator identity, target label or graph truth.
"""
from __future__ import annotations
import f124at_packed_collision_controls as previous
import f124q_fresh_source as q

THRESHOLDS=(2.0,3.0,4.0)
ALTERNATIVES=("fixed_12bit_checksum_1234","fixed_12bit_checksum_2413")
ORIGINAL="original_gamma0_checksum_1342"
GRID=tuple((name,threshold) for name in ALTERNATIVES
           for threshold in THRESHOLDS)
def need(ok,tag):q.need(ok,"F124AU_ONE_PACKED_"+tag)

def public_density(graph):
    # Only graph topology and role count; no source identity or true labels.
    need(set(graph)=={"start","target","roles","edges"},"PUBLIC_GRAPH_ONLY")
    return len(graph["edges"])/max(1,len(graph["roles"]))

def choose(graph,policy):
    need(policy in GRID,"FROZEN_POLICY_GRID")
    alternative,threshold=policy
    return alternative if public_density(graph)>threshold else ORIGINAL

def score(graph,base,delta,policy):
    chosen=choose(graph,policy)
    value,work=previous.score12(graph,base,delta,chosen)
    need(work["max_states_per_node"]==1 and
         work["max_packed_bits_per_state"]==12 and
         work["max_active"]<=64,
         "NO_CAPACITY_INCREASE")
    return value,dict(work,policy_mode=chosen,
                      policy_prepass_edge_reads=len(graph["edges"]),
                      retained_policy_selection_bits=0,
                      independently_scored_alternatives=0,
                      source_operator_used=False)

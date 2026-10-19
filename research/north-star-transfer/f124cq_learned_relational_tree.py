"""F124-CQ learned multi-output nonlinear causal binding and online role state.

This is a genuinely trained, source-neutral, oblique relational decision-tree
representation, not the earlier fixed 25-feature GF(2) parameter map.
It learns branching interaction predicates and output bindings from 40 FIT
transitions; eight CHECK transitions only VETO admission.

Only training-free mechanism/synthetic tests are authorized here. No 932/933
source or hidden oracle may be imported or retrained on.
"""
from __future__ import annotations
from typing import NamedTuple
import hashlib
import json

FIT_COUNT=40
CHECK_COUNT=8
MAX_STORED_NODES=60
MAX_SPLIT_DEPTH=5
MIN_BRANCH_ROWS=2
PREDICATE_COUNT=36
FIT_BIT_ERROR_LIMIT=2
CHECK_BIT_ERROR_LIMIT=0
MAX_ROLE_BINDINGS=16

class OnlineState(NamedTuple):
    current:int
    lagged:int

class LearnedModel(NamedTuple):
    tree:tuple
    learned_nodes:int

def need(ok,reason):
    if not ok:raise ValueError("F124CQ_"+reason)

def nib(v):
    return type(v) is int and 0<=v<16

def validate(rows,size):
    need(type(rows) in (list,tuple) and len(rows)==size,"EXACT_PUBLIC_FIT_CHECK")
    need(all(type(r) in (list,tuple) and len(r)==4
             and all(nib(v) for v in r) for r in rows),"BOUNDED_TRANSITIONS")
    return [tuple(r) for r in rows]

def input_bits(event,current,lagged):
    need(all(nib(v) for v in (event,current,lagged)),"PUBLIC_NIBBLE_ONLY")
    e=[(event>>i)&1 for i in range(4)]
    c=[(current>>i)&1 for i in range(4)]
    h=[(lagged>>i)&1 for i in range(4)]
    bank=e+c+h
    for j in range(4):
        bank.extend((e[j]^c[j],e[j]^h[j],c[j]^h[j]))
    for j in range(4):
        bank.extend((e[j]&c[j],e[j]&h[j],c[j]&h[j]))
    need(len(bank)==PREDICATE_COUNT,"EXACT_RELATIONAL_FEATURE_BANK")
    return bank

def leaf(rows):
    # Learns the bitwise majority state vector, not a hardcoded transition law.
    return sum((sum((y>>bit)&1 for _,y in rows)*2>=len(rows))<<bit
               for bit in range(4))

def bit_loss(rows):
    if not rows:return 0
    pred=leaf(rows)
    return sum((pred^y).bit_count() for _,y in rows)

def train(fit,check):
    public=validate(fit,FIT_COUNT)
    veto=validate(check,CHECK_COUNT)
    need(len({r[:3] for r in public+veto})==48,"PUBLIC_FIT_CHECK_DISJOINT_INPUTS")
    train_rows=[(tuple(input_bits(*r[:3])),r[3]) for r in public]
    nodes_used=0
    trained_predicates=set()
    def grow(rows,depth):
        nonlocal nodes_used
        nodes_used+=1
        before=bit_loss(rows)
        val=leaf(rows)
        if depth==MAX_SPLIT_DEPTH or before==0 or nodes_used+2>MAX_STORED_NODES:
            return (-1,val)
        choice=None
        for feature in range(PREDICATE_COUNT):
            left=[r for r in rows if r[0][feature]==0]
            right=[r for r in rows if r[0][feature]==1]
            if min(len(left),len(right))<MIN_BRANCH_ROWS:continue
            gain=before-bit_loss(left)-bit_loss(right)
            if gain>0 and (choice is None or gain>choice[0] or
                           (gain==choice[0] and feature<choice[1])):
                choice=(gain,feature,left,right)
        if choice is None:return (-1,val)
        _,feature,left,right=choice
        trained_predicates.add(feature)
        return (feature,grow(left,depth+1),grow(right,depth+1))
    tree=grow(train_rows,0)
    def count(t):
        return 1 if t[0]==-1 else 1+count(t[1])+count(t[2])
    n=count(tree)
    need(n==nodes_used and n<=MAX_STORED_NODES,"LEARNED_TREE_NODE_BUDGET")
    candidate=LearnedModel(tree,n)
    fit_errors=sum((predict(candidate,r[0],OnlineState(r[1],r[2])).current^r[3]).bit_count()
                   for r in public)
    check_errors=sum((predict(candidate,r[0],OnlineState(r[1],r[2])).current^r[3]).bit_count()
                     for r in veto)
    confident=(fit_errors<=FIT_BIT_ERROR_LIMIT and
               check_errors<=CHECK_BIT_ERROR_LIMIT)
    return candidate if confident else None,{
      "schema":"mass.f124cq.learned-multioutput-relational-tree.v1",
      "FIT_sha256":hashlib.sha256(json.dumps(public,separators=(",",":")).encode()).hexdigest(),
      "FIT_only_learned_structure":True,"CHECK_veto_only":True,
      "FIT_rows":FIT_COUNT,"CHECK_rows":CHECK_COUNT,
      "FIT_bit_errors":fit_errors,"CHECK_bit_errors":check_errors,
      "candidate_admitted":confident,"trained_predicate_ids":sorted(trained_predicates),
      "trained_predicate_count":len(trained_predicates),
      "learned_tree_nodes":n,"max_learned_tree_nodes":MAX_STORED_NODES,
      "max_split_depth":MAX_SPLIT_DEPTH,"max_role_bindings":MAX_ROLE_BINDINGS,
      "role_binding_learner_input":"public event,current,lagged only",
      "source_oracle_imported":False,"prior_932_933_source_replayed":False,
      "scientific_accepted":False,"resource_nonregression_accepted":False
    }

def predict(model,event,state):
    need(isinstance(model,LearnedModel) and
         1<=model.learned_nodes<=MAX_STORED_NODES,"LEARNED_MODEL_BOUNDED")
    need(isinstance(state,OnlineState) and all(nib(v) for v in state),
         "ROLE_STATE_BOUNDED")
    x=input_bits(event,state.current,state.lagged)
    branch=model.tree
    steps=0
    while branch[0]>=0:
        feature=branch[0]
        need(type(feature) is int and feature<PREDICATE_COUNT,
             "TREE_FEATURE_BOUNDED")
        steps+=1
        need(steps<=MAX_SPLIT_DEPTH,"TREE_DEPTH_BOUNDED")
        branch=branch[1] if x[feature]==0 else branch[2]
    need(branch[0]==-1 and nib(branch[1]),"TREE_LEAF_BOUNDED")
    return OnlineState(branch[1],state.current)

def rollout(model,graph):
    """Source-neutral multi-entity binding: role keys select separate online state."""
    need(type(graph) is dict and set(graph)=={"initial","events"},"PUBLIC_GRAPH_ONLY")
    initial=graph["initial"]
    need(type(initial) is dict and 1<=len(initial)<=MAX_ROLE_BINDINGS
         and all(type(k) is str and k and len(k)<=64 and
                 type(v) in (tuple,list) and len(v)==2 and
                 all(nib(z) for z in v) for k,v in initial.items()),
         "BOUNDED_OPAQUE_ROLE_BINDINGS")
    states={role:OnlineState(*pair) for role,pair in initial.items()}
    matched=True
    transitions=0
    for row in graph["events"]:
        need(type(row) is dict and set(row)=={"role","event","observed"}
             and row["role"] in states and nib(row["event"])
             and nib(row["observed"]),"BOUND_TRAJECTORY_EVENT")
        next_state=predict(model,row["event"],states[row["role"]])
        matched=bool(matched and next_state.current==row["observed"])
        states[row["role"]]=next_state
        transitions+=1
    return {"full_trajectory_accepted":matched,"transitions_evaluated":transitions,
            "role_count":len(states),"all_events_evaluated":True}

if __name__=="__main__":
    raise SystemExit("ENGINEERING_ONLY_NO_ORIGINAL_PROSPECTIVE_FIRSTUSE")

"""F124-CQ independent fully trained role-state relational tree competitor.

Separate implementation/training from candidate. Same 40 public FIT, 8
veto-only CHECK and same raw/interacting 36 predicate inventory; 4 independently
trained bitwise Gini trees with a 60-node total capacity ceiling.
No import/call from candidate, no private source or result-dependent tuning.
"""
from __future__ import annotations
from typing import NamedTuple
import hashlib
import json

FIT=40
CHECK=8
MAX_NODES=60
BIT_TREE_DEPTH=3
PREDICATES=36

class State(NamedTuple):
    current:int
    lagged:int

class Model(NamedTuple):
    bit_trees:tuple
    total_nodes:int

def require(ok,msg):
    if not ok:raise ValueError("F124CQ_CONTROL_"+msg)

def valid(v):return type(v) is int and 0<=v<=15

def predicates(event,current,lag):
    require(all(valid(x) for x in (event,current,lag)),"NIBBLE")
    row=[(value>>j)&1 for value in (event,current,lag) for j in range(4)]
    a,b,c=(row[0:4],row[4:8],row[8:12])
    row.extend(x for i in range(4) for x in (a[i]^b[i],a[i]^c[i],b[i]^c[i]))
    row.extend(x for i in range(4) for x in (a[i]&b[i],a[i]&c[i],b[i]&c[i]))
    require(len(row)==PREDICATES,"COMPLETE_RELATIONAL_FEATURES")
    return tuple(row)

def check_rows(rows,count):
    require(type(rows) in (tuple,list) and len(rows)==count,"EXACT_ROW_COUNT")
    require(all(type(x) in (tuple,list) and len(x)==4
                and all(valid(v) for v in x) for x in rows),"PUBLIC_INPUT_ONLY")
    return [tuple(x) for x in rows]

def fit(fit,check):
    rows=check_rows(fit,FIT)
    veto=check_rows(check,CHECK)
    require(len({row[:3] for row in rows+veto})==48,
            "DISJOINT_TRAIN_CHECK_INPUT")
    all_x=[predicates(*r[:3]) for r in rows]
    roots=[]
    total=0
    split_features=set()
    def majority(examples,bit):
        positives=sum((rows[i][3]>>bit)&1 for i in examples)
        return int(2*positives>len(examples))
    def impurity(examples,bit):
        ones=sum((rows[i][3]>>bit)&1 for i in examples)
        zeros=len(examples)-ones
        return ones*zeros
    for bit in range(4):
        used=0
        def build(ids,depth):
            nonlocal used,total
            used+=1;total+=1
            target=majority(ids,bit)
            if depth==BIT_TREE_DEPTH or impurity(ids,bit)==0 or used+2>15:
                return (-1,target)
            best=None
            for fid in range(PREDICATES):
                left=[i for i in ids if not all_x[i][fid]]
                right=[i for i in ids if all_x[i][fid]]
                if min(len(left),len(right))<2:continue
                score=impurity(left,bit)+impurity(right,bit)
                if best is None or score<best[0] or (score==best[0] and fid<best[1]):
                    best=(score,fid,left,right)
            if best is None or best[0]>=impurity(ids,bit):
                return (-1,target)
            _,feature,left,right=best
            split_features.add(feature)
            return (feature,build(left,depth+1),build(right,depth+1))
        roots.append(build(list(range(FIT)),0))
        require(used<=15,"BITWISE_15_NODE_LIMIT")
    require(total<=MAX_NODES,"FULL_60_NODE_CAP")
    model=Model(tuple(roots),total)
    train_err=sum((next_state(model,e,State(c,h)).current^y).bit_count()
                  for e,c,h,y in rows)
    veto_err=sum((next_state(model,e,State(c,h)).current^y).bit_count()
                 for e,c,h,y in veto)
    admitted=train_err<=2 and veto_err==0
    return (model if admitted else None),{
      "schema":"mass.f124cq.independent-fully-trained-bitwise-tree.v1",
      "FIT_sha256":hashlib.sha256(json.dumps(rows,separators=(",",":")).encode()).hexdigest(),
      "FIT_only_training":True,"CHECK_veto_only":True,
      "FIT_rows":40,"CHECK_rows":8,
      "FIT_bit_errors":train_err,"CHECK_bit_errors":veto_err,
      "learned_nodes":total,"max_nodes":MAX_NODES,
      "max_bit_tree_depth":BIT_TREE_DEPTH,
      "independent_candidate_learner_invoked":False,
      "trained_predicates":sorted(split_features),
      "public_information_equal":True,"trained_role_binding":True,
      "scientific_accepted":False,"resource_accepted":False,
      "natural_admission":admitted,
    }

def next_state(model,event,state):
    require(isinstance(model,Model) and 1<=model.total_nodes<=MAX_NODES,
            "BOUND_INDEPENDENT_TREE")
    require(isinstance(state,State) and all(valid(x) for x in state),
            "ROLE_BOUNDED")
    features=predicates(event,*state)
    output=0
    for bit,tree in enumerate(model.bit_trees):
        level=0
        while tree[0]>=0:
            feature=tree[0]
            require(type(feature) is int and feature<PREDICATES,
                    "FROZEN_FEATURE_INDEX")
            level+=1
            require(level<=BIT_TREE_DEPTH,"BITWISE_DEPTH")
            tree=tree[1] if features[feature]==0 else tree[2]
        require(tree[0]==-1 and tree[1] in (0,1),"BITWISE_LEAF")
        output|=tree[1]<<bit
    return State(output,state.current)

def rollout(model,graph):
    require(type(graph) is dict and set(graph)=={"initial","events"},"PUBLIC_ONLY")
    initial=graph["initial"]
    require(type(initial) is dict and 1<=len(initial)<=16 and all(
        type(k) is str and 0<len(k)<=64 and type(v) in (list,tuple)
        and len(v)==2 and all(valid(x) for x in v)
        for k,v in initial.items()),"ROLE_BOUND_REGISTER")
    states={name:State(*vals) for name,vals in initial.items()}
    correct=True
    steps=0
    for row in graph["events"]:
        require(type(row) is dict and set(row)=={"role","event","observed"}
                and row["role"] in states and valid(row["event"])
                and valid(row["observed"]),"PUBLIC_EVENT")
        nextval=next_state(model,row["event"],states[row["role"]])
        correct=bool(correct and nextval.current==row["observed"])
        states[row["role"]]=nextval
        steps+=1
    return {"full_trajectory_accepted":correct,"transitions_evaluated":steps,
            "role_count":len(states),"all_events_evaluated":True}

if __name__=="__main__":
    raise SystemExit("INDEPENDENT_TRAINED_CONTROL_NO_PROSPECTIVE_SOURCE")

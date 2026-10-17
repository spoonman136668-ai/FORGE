"""F125-R path-preserving public-token-keyed sum-product learner.

Every observed (node, incoming 16-bit dst token) hypothesis is retained and
mass/gradient merged only for IDENTICAL public keys. No K=2 routing, oracle
equality feature, label shortcut or protected CONFIRM. Bounded at 256 keys.
"""
from __future__ import annotations
from collections import defaultdict
import hashlib,json,math

import f125r_freeze_admission as freeze
import f125r_train_environment as env

PARAMS=20
EPOCHS=100
RATE=.22
CAP=256
INIT=[-1.2]+[.17]*16+[.05,3.,.5]

def need(ok,why):env.need(bool(ok),"MODEL_"+why)
def sigmoid(t):return 1./(1.+math.exp(-max(-40.,min(40.,t))))
def sha(obj):return hashlib.sha256(json.dumps(obj,sort_keys=True,separators=(",",":")).encode()).hexdigest()
def edge_id(edge):return sha(edge)

def features(last,src,step,depth):
    need(len(last)==len(src)==16,"RAW_TOKEN_BITS")
    return [1.]+[(2*a-1)*(2*b-1) for a,b in zip(last,src)]+[step/depth]

def forward(graph,weights,trace=False):
    env.validate(graph)
    need(type(weights) in (tuple,list) and len(weights)==PARAMS
         and all(type(x) in (float,int) and math.isfinite(x) and abs(x)<=8.
                 for x in weights),"WEIGHT_BOUNDS")
    protocol,_=freeze.frozen()
    need(protocol["mechanism"]["maximum_active_states_per_hop"]==CAP and
         protocol["mechanism"]["no_topk_pruning"] is True and
         protocol["mechanism"]["trainable_parameters"]==PARAMS,"FROZEN_MECHANISM_DRIFT")
    outgoing=defaultdict(list)
    work={"public_edge_visits":0,"index_insertions":0,"edge_hash_bytes":0,
          "adjacency_sort_upper":0,"raw_bit_interactions":0,
          "attention_multiply_adds":0,"gradient_multiply_adds":0,
          "candidate_state_allocations":0,"merged_public_key_states":0,
          "retained_state_storage":0,"state_limit_peak":1}
    for edge in graph["edges"]:
        serialized=json.dumps(edge,sort_keys=True,separators=(",",":")).encode()
        outgoing[(edge["from"],edge["role"])].append((edge_id(edge),edge))
        work["public_edge_visits"]+=1
        work["index_insertions"]+=1
        work["edge_hash_bytes"]+=len(serialized)
    for edges in outgoing.values():
        edges.sort(key=lambda pair:pair[0])
        work["adjacency_sort_upper"]+=len(edges)*max(1,(len(edges)-1).bit_length())
    # public token-state: ((node, incoming-token-or-None) -> mass, dMass/dw18)
    states={(graph["start"],None):(1.,[0.]*18)}
    step_trace=[]
    for step,role in enumerate(graph["roles"]):
        new={}
        for (node,last),(mass,dm) in sorted(states.items(),key=lambda item:
            (item[0][0],str(item[0][1]))):
            for _,edge in outgoing.get((node,role),()):
                if last is None:
                    compatibility,grad=1.,[0.]*18
                else:
                    f=features(last,edge["src_bits"],step,len(graph["roles"]))
                    compatibility=sigmoid(sum(w*v for w,v in zip(weights[:18],f)))
                    grad=[compatibility*(1.-compatibility)*v for v in f]
                    work["raw_bit_interactions"]+=16
                    work["attention_multiply_adds"]+=18
                    work["gradient_multiply_adds"]+=18
                new_mass=mass*compatibility
                new_grad=[x*compatibility+mass*g for x,g in zip(dm,grad)]
                work["gradient_multiply_adds"]+=36
                key=(edge["to"],tuple(edge["dst_bits"]))
                work["candidate_state_allocations"]+=1
                if key in new:
                    before,before_grad=new[key]
                    new[key]=(before+new_mass,
                              [x+y for x,y in zip(before_grad,new_grad)])
                    work["merged_public_key_states"]+=1
                    work["gradient_multiply_adds"]+=18
                else:
                    new[key]=(new_mass,new_grad)
                # Never silently drop/clip a branch or raise the declared cap.
                need(len(new)<=CAP,"PUBLIC_STATE_OVERFLOW_SCORE_FAILURE")
        states=new
        work["retained_state_storage"]+=len(states)
        work["state_limit_peak"]=max(work["state_limit_peak"],len(states))
        if trace:
            step_trace.append({"query_hop":step+1,
                "retained_public_keys":len(states),
                "public_state_digest":sha(sorted(
                    [[node,list(token),round(mass,14)]
                     for (node,token),(mass,_) in states.items()],
                    key=lambda x:(x[0],x[1])))})
        if not states:break
    terminal=[(mass,grad) for (node,token),(mass,grad) in states.items()
              if node==graph["target"]]
    total=sum(m for m,_ in terminal)
    dtotal=[sum(d[k] for _,d in terminal) for k in range(18)]
    gain,cutoff=weights[-2:]
    p=sigmoid(gain*(total-cutoff))
    derivatives=[gain*x for x in dtotal]+[total-cutoff,-gain]
    need(len(derivatives)==PARAMS and
         all(math.isfinite(v) for v in derivatives+[p]),
         "NONFINITE_OUTPUT")
    if trace:
        return p,derivatives,{"work":work,
            "terminal_public_key_count":len(terminal),
            "terminal_mass":total,"state_trace":step_trace,
            "no_public_route":len(terminal)==0,
            "hard_pruned_routes":0,
            "merged_only_identical_public_keys":True}
    return p,derivatives

def fit(rows):
    cfg,_=freeze.frozen()
    need(cfg["mechanism"]["optimizer"]=={
        "epochs":100,"rate":.22,"clip":1,
        "initialization":"fixed precommitted vector with 20 bounded values",
        "full_batch":True,"train_only":True},"FROZEN_OPTIMIZER")
    need(type(rows) is list and len(rows)==128 and
         sum(label for _,label in rows)==64,"FROZEN_TRAIN_COHORT")
    w=list(INIT)
    for _ in range(EPOCHS):
        grad=[0.]*PARAMS
        for graph,label in rows:
            p,dp=forward(graph,w)
            for k,value in enumerate(dp):grad[k]+=(p-label)*value
        for k,g in enumerate(grad):
            w[k]=max(-8.,min(8.,w[k]-RATE*max(-1.,min(1.,g/len(rows)))))
        need(all(math.isfinite(z) for z in w),"UNSTABLE_LEARNER")
    movement=sum((a-b)**2 for a,b in zip(w,INIT))**.5
    need(movement>.0001,"INERT_LEARNING")
    return w,movement

def score(rows,w):
    need(len(rows)%2==0 and len(rows)>0,"INVALID_PAIRING")
    pos=neg=paired=0
    for i in range(0,len(rows),2):
        p,a=rows[i];n,b=rows[i+1]
        need(a==1 and b==0,"PAIRED_LABEL_ORDER")
        goodp=forward(p,w)[0]>=.5
        goodn=forward(n,w)[0]<.5
        pos+=int(goodp);neg+=int(goodn);paired+=int(goodp and goodn)
    return {"pairs":len(rows)//2,"paired_correct":paired,
            "positive_correct":pos,"negative_correct":neg,
            "balanced_accuracy":round((pos+neg)/len(rows),8)}

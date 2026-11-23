"""R11: learn source-specific retention decisions from TRAINING-ONLY proxy benefit.

One fixed 96-slot retained set (32/source) per epoch; each gate's three
logits learn from one-step counterfactual training proxy loss. Future
cross-fold validation and sealed cohorts never influence retention.
"""
import hashlib,json,math
SLOTS=32
def dot(w,x):return sum(a*b for a,b in zip(w,x))
def sigmoid(v):return 1/(1+math.exp(-v))
def gradient(rows,w):
    out=[0.0]*16
    for x,y in rows:
        if y*dot(w,x)<=0:
            for k in range(16):out[k]+=y*x[k]/len(rows)
    return out
def loss(rows,w):
    return sum(max(0.0,1.0-y*dot(w,x)) for x,y in rows)/len(rows)
def selections(pool,w):
    ranked=sorted(range(len(pool)),key=lambda i:(pool[i][1]*dot(w,pool[i][0]),i))
    hard=ranked[:SLOTS]
    bins=[[] for _ in range(16)]
    for idx,(feat,_label) in enumerate(pool):
        dominant=max(range(16),key=lambda i:(abs(feat[i]),-i))
        bins[dominant].append(idx)
    diverse=[]
    for group in bins:
        diverse.extend(sorted(group,key=lambda i:(pool[i][1]*dot(w,pool[i][0]),i))[:2])
    diverse=diverse[:SLOTS]
    chosen=set(diverse)
    for idx in ranked:
        if len(diverse)==SLOTS:break
        if idx not in chosen:diverse.append(idx);chosen.add(idx)
    if len(hard)!=SLOTS or len(diverse)!=SLOTS:raise ValueError("R11_MEMORY_CAPACITY")
    return hard,diverse,ranked
def train(training):
    if len(training)!=3 or any(len(g)!=576 for g in training):raise ValueError("R11_TRAIN_BUDGET")
    w=[0.0]*16
    gates=[0.0]*3
    trace=[]
    for epoch in range(32):
        steps=[]
        rec=[]
        for source,rows in enumerate(training):
            proxy=[row for i,row in enumerate(rows) if (i+epoch)%5==0]
            pool=[row for i,row in enumerate(rows) if (i+epoch)%5!=0]
            if not 112<=len(proxy)<=118 or len(pool)<SLOTS:raise ValueError("R11_TRAIN_PROXY_SOURCE")
            hard,diverse,ranked=selections(pool,w)
            gh=gradient([pool[i] for i in hard],w)
            gd=gradient([pool[i] for i in diverse],w)
            loss_h=loss(proxy,[x+0.1*y for x,y in zip(w,gh)])
            loss_d=loss(proxy,[x+0.1*y for x,y in zip(w,gd)])
            diff=max(-0.5,min(0.5,loss_d-loss_h))
            next_logit=max(-4.0,min(4.0,gates[source]+4.0*diff))
            gates[source]=next_logit
            proportion=sigmoid(next_logit)
            hard_count=round(SLOTS*proportion)
            selected=[]
            used=set()
            for i in hard[:hard_count]+diverse[:SLOTS-hard_count]+ranked:
                if i not in used:used.add(i);selected.append(i)
                if len(selected)==SLOTS:break
            if len(selected)!=SLOTS:raise ValueError("R11_MEMORY_SIZE_DRIFT")
            steps.append(gradient([pool[i] for i in selected],w))
            rec.append({"source":source,"proxy_count":len(proxy),"gate_logit":next_logit,
                        "hard_slots_requested":hard_count,"retained_slots":SLOTS})
        w=[w[i]+0.1*sum(steps[j][i] for j in range(3))/3 for i in range(16)]
        if any(not math.isfinite(v) for v in w+gates):raise ValueError("R11_NONFINITE_CONTROLLER")
        trace.append({"epoch":epoch,"sources":rec})
    d=hashlib.sha256(json.dumps(w,separators=(",",":"),allow_nan=False).encode()).hexdigest()
    return {"weights":w,"weights_sha256":d,"source_counts":{str(i):576 for i in range(3)},
            "gate_logits":gates,"gate_trace":trace,
            "learned_controller_parameters":3,"classifier_parameters":16,
            "persistent_memory_slots":96,
            "retention_rule":"TRAIN_ONLY_COUNTERFACTUAL_PROXY_LOGIT"}

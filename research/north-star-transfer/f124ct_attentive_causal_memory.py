"""F124-CT learned associative recurrent causal memory (source-free).

End-to-end BPTT trains three *persistent role-keyed* latent memories from
eight-event causal sequences. Learned query/key attention retrieves the
source entity's changing memory; shared recurrent transition updates the
target entity. There is no oracle target in recurrence, and no prior
924–935 scientific source, source law or original case access.
"""
from __future__ import annotations
import numpy as np
import f124ct_sequence_protocol as p

SEED=1242081
SCALE=0.17
ATTENTION_DIVISOR=p.HIDDEN**0.5

def new():
    rng=np.random.default_rng(SEED)
    H=p.HIDDEN
    dimensions={
      "Einit":(H,8),"binit":(H,),"Wq":(H,3),"Wqe":(H,4),
      "K":(3,H),"Wself":(H,H),"Wctx":(H,H),"We":(H,4),
      "b":(H,),"Wy":(4,H),"by":(4,)}
    return {key:(np.zeros(shape) if key.startswith("b") else
             rng.normal(0,SCALE,size=shape).astype(np.float64))
            for key,shape in dimensions.items()}

def initial_states(P,episode):
    return np.array([np.tanh(P["Einit"]@p.init_bits(episode["initial"][r])
                   +P["binit"]) for r in p.ROLES],dtype=np.float64)

def forward(P,episode,grad=False):
    h=initial_states(P,episode)
    h0=h.copy()
    records=[]
    outputs=[]
    loss=0.0;bit_errors=0
    for item in episode["events"]:
        target=p.ROLES.index(item["target"])
        source=p.ROLES.index(item["source"])
        x=p.bits(item["event"])
        before=h.copy()
        q=P["Wq"][:,source]+P["Wqe"]@x
        attention=p.softmax(P["K"]@q/ATTENTION_DIVISOR)
        retrieved=attention@before
        z=P["Wself"]@before[target]+P["Wctx"]@retrieved+P["We"]@x+P["b"]
        newstate=np.tanh(z)
        probabilities=p.sigmoid(P["Wy"]@newstate+P["by"])
        y=p.bits(item["observed"])
        output=sum((int(probabilities[i]>=0.5)<<i) for i in range(4))
        bit_errors+=int(np.sum((probabilities>=0.5)!=y))
        loss+=p.loss_bit(probabilities,y)
        h[target]=newstate
        outputs.append(output)
        if grad:
            records.append((target,source,x,before,q,attention,retrieved,
                            newstate,probabilities,y))
    return outputs,loss,bit_errors,(records,h0)

def gradients(P,episode):
    output,loss,errors,(records,h0)=forward(P,episode,grad=True)
    d={key:np.zeros_like(val) for key,val in P.items()}
    H=p.HIDDEN
    future=np.zeros((p.N_ROLES,H),dtype=np.float64)
    for target,source,x,before,q,attention,retrieved,newstate,prob,y in reversed(records):
        dlogits=(prob-y)/4.0
        d["Wy"]+=np.outer(dlogits,newstate)
        d["by"]+=dlogits
        dnew=P["Wy"].T@dlogits+future[target]
        dz=dnew*(1.0-newstate*newstate)
        d["Wself"]+=np.outer(dz,before[target])
        d["Wctx"]+=np.outer(dz,retrieved)
        d["We"]+=np.outer(dz,x)
        d["b"]+=dz
        previous=future.copy()
        previous[target]=0.0
        previous[target]+=P["Wself"].T@dz
        dretrieved=P["Wctx"].T@dz
        previous+=attention[:,None]*dretrieved[None,:]
        dattention=before@dretrieved
        dscores=attention*(dattention-np.dot(dattention,attention))
        d["K"]+=np.outer(dscores,q)/ATTENTION_DIVISOR
        dq=P["K"].T@dscores/ATTENTION_DIVISOR
        d["Wq"][:,source]+=dq
        d["Wqe"]+=np.outer(dq,x)
        future=previous
    for role,r in enumerate(p.ROLES):
        dz=future[role]*(1.0-h0[role]**2)
        d["Einit"]+=np.outer(dz,p.init_bits(episode["initial"][r]))
        d["binit"]+=dz
    return d,loss

def evaluate(P,episodes):
    total=0.;errors=0
    for ep in episodes:
        _,loss,e,_=forward(P,ep)
        total+=loss;errors+=e
    return total/(len(episodes)*p.STEPS_PER_EPISODE*4),errors

def train(fit,check):
    fit=p.validate(fit,p.FIT_EPISODES)
    check=p.validate(check,p.CHECK_EPISODES)
    P=new()
    start,_=evaluate(P,fit)
    for epoch in range(p.EPOCHS):
        for index in p.schedule(epoch):
            d,_=gradients(P,fit[int(index)])
            p.clip_and_update(P,d)
    final,fit_errors=evaluate(P,fit)
    _,check_errors=evaluate(P,check)
    reduction=(start-final)/max(start,1e-9)
    admissible=bool(reduction>=p.MIN_FIT_LOSS_REDUCTION and
        check_errors/(len(check)*p.STEPS_PER_EPISODE*4)<=p.CHECK_ERROR_VETO_RATIO)
    return (P if admissible else None),{
        "schema":"mass.f124ct.sequence-trained-attentive-role-memory.v1",
        "FIT_episode_sha256":p.digest(fit),
        "FIT_count":p.FIT_EPISODES,"CHECK_veto_only_count":p.CHECK_EPISODES,
        "full_sequential_BPTT":True,
        "learned_source_query_and_role_memory_keys":True,
        "independent_entity_hidden_registers":3,
        "learned_parameters":sum(val.size for val in P.values()),
        "hidden_per_role":p.HIDDEN,
        "training_epochs":p.EPOCHS,"optimizer":"bounded_clipped_sequential_SGD",
        "initial_FIT_bit_cross_entropy":float(start),
        "final_FIT_bit_cross_entropy":float(final),
        "FIT_relative_loss_reduction":float(reduction),
        "FIT_bit_errors":int(fit_errors),
        "CHECK_bit_errors":int(check_errors),
        "CHECK_used_to_update_weights":False,
        "natural_model_admission":admissible,
        "source_oracle_or_prior_original_science_used":False,
        "scientific_accepted":False}

def predict_sequence(P,episode):
    p.need(type(P) is dict and all(np.isfinite(v).all() for v in P.values()),
           "FITTED_MODEL_REQUIRED")
    p.validate([episode]*p.FIT_EPISODES,p.FIT_EPISODES)
    return forward(P,episode,grad=False)[0]

if __name__=="__main__":
    raise SystemExit("LEARNED_SEQUENTIAL_MECHANISM_ENGINEERING_ONLY")

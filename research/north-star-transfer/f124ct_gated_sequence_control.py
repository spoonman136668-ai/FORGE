"""F124-CT independently trained gated recurrent multi-role competitor.

Stronger-than-stateless control: receives the SAME full FIT/CHECK episodes,
explicit source/target entity pointers, full eight-event BPTT, and has its
OWN recurrent role memories, learned copy/retention gates, learned output and
initial state encoding. No candidate imports or old scientific source reuse.
"""
from __future__ import annotations
import numpy as np
import f124ct_sequence_protocol as p

SEED=1242082
SCALE=0.17

def new():
    rng=np.random.default_rng(SEED)
    H=p.HIDDEN
    dimensions={
      "Einit":(H,8),"binit":(H,),
      "Wh":(H,H),"Ws":(H,H),"We":(H,4),"bh":(H,),
      "Gh":(H,H),"Gs":(H,H),"Ge":(H,4),"bg":(H,),
      "Wy":(4,H),"by":(4,)}
    return {key:(np.zeros(shape) if key.startswith("b") else
             rng.normal(0,SCALE,size=shape).astype(np.float64))
            for key,shape in dimensions.items()}

def initial_states(P,episode):
    return np.array([np.tanh(P["Einit"]@p.init_bits(episode["initial"][r])
                    +P["binit"]) for r in p.ROLES],dtype=np.float64)

def forward(P,episode,grad=False):
    h=initial_states(P,episode)
    h0=h.copy()
    tape=[]
    output=[]
    loss=0.0;errors=0
    for item in episode["events"]:
        target=p.ROLES.index(item["target"])
        source=p.ROLES.index(item["source"])
        x=p.bits(item["event"])
        before=h.copy()
        own=before[target];other=before[source]
        pre=P["Wh"]@own+P["Ws"]@other+P["We"]@x+P["bh"]
        proposal=np.tanh(pre)
        gate=p.sigmoid(P["Gh"]@own+P["Gs"]@other+P["Ge"]@x+P["bg"])
        nxt=gate*own+(1.0-gate)*proposal
        proba=p.sigmoid(P["Wy"]@nxt+P["by"])
        y=p.bits(item["observed"])
        loss+=p.loss_bit(proba,y)
        errors+=int(np.sum((proba>=0.5)!=y))
        output.append(sum(int(proba[i]>=0.5)<<i for i in range(4)))
        h[target]=nxt
        if grad:
            tape.append((target,source,x,before,proposal,gate,nxt,proba,y))
    return output,loss,errors,(tape,h0)

def gradients(P,episode):
    _,loss,_,(tape,h0)=forward(P,episode,grad=True)
    d={k:np.zeros_like(v) for k,v in P.items()}
    future=np.zeros((p.N_ROLES,p.HIDDEN),dtype=np.float64)
    for target,source,x,before,proposal,gate,nxt,proba,y in reversed(tape):
        dlogits=(proba-y)/4.0
        d["Wy"]+=np.outer(dlogits,nxt)
        d["by"]+=dlogits
        dnext=P["Wy"].T@dlogits+future[target]
        dgate=dnext*(before[target]-proposal)
        dproposal=dnext*(1.0-gate)
        dg=dgate*gate*(1.0-gate)
        dz=dproposal*(1.0-proposal**2)
        d["Wh"]+=np.outer(dz,before[target])
        d["Ws"]+=np.outer(dz,before[source])
        d["We"]+=np.outer(dz,x)
        d["bh"]+=dz
        d["Gh"]+=np.outer(dg,before[target])
        d["Gs"]+=np.outer(dg,before[source])
        d["Ge"]+=np.outer(dg,x)
        d["bg"]+=dg
        previous=future.copy()
        previous[target]=0.0
        previous[target]+=dnext*gate+P["Wh"].T@dz+P["Gh"].T@dg
        previous[source]+=P["Ws"].T@dz+P["Gs"].T@dg
        future=previous
    for i,role in enumerate(p.ROLES):
        dz=future[i]*(1.0-h0[i]*h0[i])
        d["Einit"]+=np.outer(dz,p.init_bits(episode["initial"][role]))
        d["binit"]+=dz
    return d,loss

def evaluate(P,episodes):
    loss=0.0;errors=0
    for ep in episodes:
        _,a,b,_=forward(P,ep)
        loss+=a;errors+=b
    return loss/(len(episodes)*p.STEPS_PER_EPISODE*4),errors

def train(fit,check):
    fit=p.validate(fit,p.FIT_EPISODES)
    check=p.validate(check,p.CHECK_EPISODES)
    P=new()
    start,_=evaluate(P,fit)
    for epoch in range(p.EPOCHS):
        for index in p.schedule(epoch):
            gradient,_=gradients(P,fit[int(index)])
            p.clip_and_update(P,gradient)
    final,fit_errors=evaluate(P,fit)
    _,check_errors=evaluate(P,check)
    improvement=(start-final)/max(start,1e-9)
    admissible=bool(improvement>=p.MIN_FIT_LOSS_REDUCTION and
        check_errors/(len(check)*p.STEPS_PER_EPISODE*4)<=p.CHECK_ERROR_VETO_RATIO)
    return (P if admissible else None),{
      "schema":"mass.f124ct.independently-trained-gated-recurrent-peer.v1",
      "FIT_episode_sha256":p.digest(fit),
      "FIT_count":p.FIT_EPISODES,"CHECK_veto_only_count":p.CHECK_EPISODES,
      "full_sequential_BPTT":True,
      "trained_explicit_source_role_retrieval":True,
      "three_persistent_recurrent_role_memories":True,
      "learned_parameters":sum(a.size for a in P.values()),
      "hidden_per_role":p.HIDDEN,
      "training_epochs":p.EPOCHS,"optimizer":"bounded_clipped_sequential_SGD",
      "initial_FIT_bit_cross_entropy":float(start),
      "final_FIT_bit_cross_entropy":float(final),
      "FIT_relative_loss_reduction":float(improvement),
      "FIT_bit_errors":int(fit_errors),"CHECK_bit_errors":int(check_errors),
      "CHECK_used_to_update_weights":False,
      "natural_model_admission":admissible,
      "candidate_code_imported":False,"prior_original_scientific_source_used":False,
      "scientific_accepted":False}

def predict_sequence(P,episode):
    p.need(type(P) is dict and all(np.isfinite(val).all() for val in P.values()),
           "FITTED_CONTROL_REQUIRED")
    p.validate([episode]*p.FIT_EPISODES,p.FIT_EPISODES)
    return forward(P,episode,grad=False)[0]

if __name__=="__main__":
    raise SystemExit("STRONG_TRAINED_SEQUENCE_CONTROL_ENGINEERING_ONLY")

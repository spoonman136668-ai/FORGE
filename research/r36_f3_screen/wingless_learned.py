"""Bounded train-only R36 Wingless learned mechanisms.

W36-C1: 16 -> 8 rank-limited learnable pairwise projection and joint
classification (8 projection angles + 8 head weights = 16 trained scalars).
Source mean-discrepancy is penalized on training data only.

W36-C3: 16-dimensional shared learner with a learned two-state soft risk
consumer selecting pooled versus highest-risk training-source gradients.

Both return effective 16-dimensional classifiers for the exact immutable
Wingless evaluator. No heldout access, model services, or I/O.
"""
import math

def projection(training, epochs=32):
    angles=[0.0]*8
    heads=[0.01]*8
    for _ in range(epochs):
        cosine=[math.cos(t) for t in angles]
        sine=[math.sin(t) for t in angles]
        g_head=[0.0]*8
        g_angle=[0.0]*8
        source_means=[]
        source_dmeans=[]
        for rows in training:
            m=[0.0]*8
            dm=[0.0]*8
            for x,y in rows:
                z=[cosine[j]*x[2*j]+sine[j]*x[2*j+1] for j in range(8)]
                dz=[-sine[j]*x[2*j]+cosine[j]*x[2*j+1] for j in range(8)]
                for j in range(8):
                    m[j]+=z[j]/len(rows)
                    dm[j]+=dz[j]/len(rows)
                margin=y*sum(heads[j]*z[j] for j in range(8))
                if margin<=0:
                    for j in range(8):
                        g_head[j]+=y*z[j]/(3*len(rows))
                        g_angle[j]+=y*heads[j]*dz[j]/(3*len(rows))
            source_means.append(m)
            source_dmeans.append(dm)
        for j in range(8):
            average=sum(s[j] for s in source_means)/3
            # Derivative of source-conditional mean discrepancy variance.
            penalty=(2/3)*sum((source_means[s][j]-average)*source_dmeans[s][j]
                              for s in range(3))
            g_angle[j]-=0.05*penalty
        angles=[angles[j]+0.1*g_angle[j] for j in range(8)]
        heads=[heads[j]+0.1*g_head[j] for j in range(8)]
        if any(not math.isfinite(v) for v in angles+heads):
            raise ValueError("R36_PROJECTION_NONFINITE")
    output=[]
    for j in range(8):
        output.extend((heads[j]*math.cos(angles[j]), heads[j]*math.sin(angles[j])))
    return output,{"rank":8,"trained_scalar_count":16,"projector_angles":angles,
                   "prediction_head":heads,"source_discrepancy_penalty":0.05}

def risk_consumer(training,gradient,epochs=32):
    w=[0.0]*16
    # Two learned risk-state logits: pooled state and highest-risk state.
    logits=[0.0,0.0]
    for _ in range(epochs):
        grad=[gradient(group,w) for group in training]
        losses=[sum(max(0.0,1.0-y*sum(a*b for a,b in zip(w,x)))
                    for x,y in group)/len(group) for group in training]
        hardest=max(range(3),key=lambda s:(losses[s],-s))
        magnitude=max(losses)-sum(losses)/3
        likelihood=1.0/(1.0+math.exp(max(-50.0,min(50.0,logits[0]-logits[1]))))
        pooled=[sum(g[j] for g in grad)/3 for j in range(16)]
        update=[(1-likelihood)*pooled[j]+likelihood*grad[hardest][j] for j in range(16)]
        w=[w[j]+0.1*update[j] for j in range(16)]
        # Training-only risk gap informs the two-state soft-consumer gate.
        gate_change=0.1*magnitude*likelihood*(1-likelihood)
        logits[0]-=gate_change
        logits[1]+=gate_change
        if any(not math.isfinite(v) for v in w+logits):
            raise ValueError("R36_RISK_NONFINITE")
    return w,{"shared_weight_dimension":16,"gate_state_count":2,
              "learned_risk_logits":logits}

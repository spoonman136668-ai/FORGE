"""Q21 source-free FIT-only conventional comparators and episode-cluster statistics.

No generator, original-source reader, protected holdout or development role is
imported. Trained models consume explicitly supplied public row tuples only.
"""
from __future__ import annotations

import hashlib
import json
import math
import random
import time
import tracemalloc

import sourcefree as public

MODEL_NAMES = (
    "TRAINED_CURRENT_LOGISTIC", "TRAINED_2_STATE_ACTION_RNN",
    "TRAINED_4_STATE_ACTION_RNN", "UNSUPERVISED_2_STATE_ACTION_HMM",
    "UNSUPERVISED_4_STATE_ACTION_HMM",
)
INPUT_WIDTH = 5
LOGISTIC_WIDTH = 8
EPS = 1e-12


def need(ok, label):
    public.require(ok, label)


def checked(rows):
    clean = public.public_rows(rows)
    need(len(clean) > 0, "EMPTY_PUBLIC_FIT_ROWS")
    need(len({r[0] for r in clean}) == 1, "MIXED_FAMILY_FIT")
    return clean


def sigmoid(z):
    if z >= 0:
        return 1 / (1 + math.exp(-z))
    v = math.exp(z)
    return v / (1 + v)


def context_features(row, t):
    _, obs, actions = row
    need(0 <= t < len(actions), "FUTURE_CONTEXT")
    o0, o1 = (2 * b - 1 for b in obs[t])
    act = 2 * actions[t] - 1
    prev = 2 * (actions[t - 1] if t else 0) - 1
    return (1., float(o0), float(o1), float(act), float(prev))


def logistic_features(row, t):
    one, a, b, act, prev = context_features(row, t)
    return (one, a, b, act, prev, a * act, b * act, act * prev)


def init_weights(kind, width, restart):
    seed = int.from_bytes(hashlib.sha256(
        ("forge-q21-model-init:" + kind + ":" + str(restart)).encode()
    ).digest()[:8], "big")
    rand = random.Random(seed)
    return [rand.uniform(-.08, .08) for _ in range(width)]


def adam_step(weights, gradient, first, second, iteration, rate=0.035):
    need(len(weights) == len(gradient), "OPTIMIZER_WIDTH")
    norm = math.sqrt(sum(g*g for g in gradient))
    scale = min(1.0, 5.0/norm) if norm else 1.0
    out = []
    for i, g0 in enumerate(gradient):
        g = g0 * scale
        first[i] = .9 * first[i] + .1 * g
        second[i] = .999 * second[i] + .001 * g*g
        value = weights[i] - rate * (first[i] / (1 - .9**iteration)) / (
            math.sqrt(second[i] / (1 - .999**iteration)) + 1e-8)
        need(math.isfinite(value), "NONFINITE_TRAINED_WEIGHT")
        out.append(value)
    return out


def logit_predictions(weights, row):
    need(len(weights) == 2 * LOGISTIC_WIDTH, "LOGISTIC_WIDTH")
    predictions = []
    for t in range(len(row[2])):
        f = logistic_features(row, t)
        predictions.append(tuple(sigmoid(sum(weights[LOGISTIC_WIDTH*j+i] * f[i]
                                             for i in range(LOGISTIC_WIDTH)))
                                 for j in range(2)))
    return predictions


def gradient_logit(weights, rows):
    gradient = [0.] * len(weights)
    for row in rows:
        preds = logit_predictions(weights, row)
        for t, probs in enumerate(preds):
            feat = logistic_features(row, t)
            for j in (0, 1):
                err = probs[j] - row[1][t+1][j]
                for k, value in enumerate(feat):
                    gradient[LOGISTIC_WIDTH*j+k] += err * value
    total = sum(2*len(row[2]) for row in rows)
    return [g / total for g in gradient]


def rnn_shape(hidden):
    need(hidden in (2, 4), "UNKNOWN_RNN_HIDDEN_WIDTH")
    rec = hidden * hidden
    inp = rec + INPUT_WIDTH * hidden
    bias = inp + hidden
    readout = bias + 2 * hidden
    return rec, inp, bias, readout + 2


def rnn_forward(weights, row, hidden):
    rec, inp, bias, size = rnn_shape(hidden)
    need(len(weights) == size, "RNN_WEIGHT_WIDTH")
    h = [0.] * hidden
    trace = []
    for t in range(len(row[2])):
        x = context_features(row, t)
        prev = h[:]
        h = [math.tanh(weights[inp+i] +
                sum(weights[i*hidden+k]*prev[k] for k in range(hidden)) +
                sum(weights[rec+i*INPUT_WIDTH+k]*x[k]
                    for k in range(INPUT_WIDTH)))
             for i in range(hidden)]
        pred = tuple(sigmoid(weights[bias + 2*hidden + j] +
                sum(weights[bias+j*hidden+k]*h[k] for k in range(hidden)))
                     for j in range(2))
        trace.append((prev, h, x, pred))
    return trace


def rnn_predictions(weights, row, hidden):
    return [entry[-1] for entry in rnn_forward(weights, row, hidden)]


def gradient_rnn(weights, rows, hidden):
    rec, inp, bias, size = rnn_shape(hidden)
    g = [0.] * size
    for row in rows:
        trace = rnn_forward(weights, row, hidden)
        dh_next = [0.] * hidden
        for t in range(len(trace)-1, -1, -1):
            prev, h, x, pred = trace[t]
            err = [pred[j] - row[1][t+1][j] for j in range(2)]
            for j in range(2):
                g[bias + 2*hidden + j] += err[j]
                for k in range(hidden):
                    g[bias + j*hidden + k] += err[j] * h[k]
            dh = [dh_next[k] + sum(weights[bias+j*hidden+k]*err[j]
                                    for j in range(2)) for k in range(hidden)]
            dz = [dh[k] * (1-h[k]*h[k]) for k in range(hidden)]
            for i in range(hidden):
                g[inp+i] += dz[i]
                for k in range(hidden):
                    g[i*hidden+k] += dz[i]*prev[k]
                for k in range(INPUT_WIDTH):
                    g[rec+i*INPUT_WIDTH+k] += dz[i]*x[k]
            dh_next = [sum(weights[i*hidden+k]*dz[i]
                           for i in range(hidden)) for k in range(hidden)]
    scale = sum(2*len(row[2]) for row in rows)
    return [x / scale for x in g]


def mean_nll(rows, predictions):
    n = sum(2*len(r[2]) for r in rows)
    total = sum(public.nll(row, predictions(row)) * 2*len(row[2]) for row in rows)
    return total / n


def fit_gradient(kind, fit_rows, valid_rows, epochs=60, restarts=3):
    fit = checked(fit_rows)
    valid = checked(valid_rows)
    need(fit[0][0] == valid[0][0], "VALID_FAMILY_MISMATCH")
    need(epochs == 60 and restarts == 3, "FROZEN_GRADIENT_BUDGET_DRIFT")
    if kind == MODEL_NAMES[0]:
        width, hidden = 2*LOGISTIC_WIDTH, 0
        forecast = lambda p,r: logit_predictions(p,r)
        grad = lambda p: gradient_logit(p,fit)
    else:
        hidden = 2 if kind == MODEL_NAMES[1] else 4 if kind == MODEL_NAMES[2] else -1
        need(hidden != -1, "UNKNOWN_GRADIENT_KIND")
        width = rnn_shape(hidden)[-1]
        forecast = lambda p,r: rnn_predictions(p,r,hidden)
        grad = lambda p: gradient_rnn(p,fit,hidden)
    start = time.process_time()
    tracemalloc.start()
    best = None
    history = []
    for restart in range(restarts):
        p = init_weights(kind,width,restart)
        m, v = [0.] * width, [0.] * width
        for ep in range(1,epochs+1):
            p = adam_step(p,grad(p),m,v,ep)
            val = mean_nll(valid,lambda r: forecast(p,r))
            need(math.isfinite(val), "GRADIENT_VAL_NONFINITE")
            if best is None or val < best[0]:
                best = (val, tuple(p), ep, restart)
        history.append({"restart":restart,"last_epoch":epochs})
    _,peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    weights = list(best[1])
    return {"kind":kind,"weights":weights,"hidden":hidden}, {
        "fit_valid_cpu_s": time.process_time()-start,
        "tracemalloc_peak_bytes":peak,
        "checkpoint_bytes":len(json.dumps(weights,sort_keys=True,separators=(",",":")).encode()),
        "selected_epoch":best[2],"selected_restart":best[3],
        "fit_validation_nll":best[0],"attempts":history,
        "rss_peak_bytes":None,"rss_qualification":"NATIVE_PEAK_RSS_PENDING"
    }


def normalize(values):
    s = sum(values)
    need(s > 0 and math.isfinite(s), "HMM_ZERO_NORMALIZER")
    return [x/s for x in values]


def hmm_init(hidden,restart):
    need(hidden in (2, 4), "UNKNOWN_HMM_HIDDEN_WIDTH")
    rand = random.Random(int.from_bytes(hashlib.sha256(
        ("forge-q21-hmm-init:"+str(hidden)+":"+str(restart)).encode()
    ).digest()[:8],"big"))
    def sample(n):
        return normalize([rand.uniform(.15,1.0) for _ in range(n)])
    return {"kind":"HMM","hidden":hidden,"prior":sample(hidden),
            "emission":[sample(4) for _ in range(hidden)],
            "transition":[[sample(hidden) for _ in range(hidden)] for _ in range(4)]}


def hmm_context(row,t):
    action=row[2][t]
    prev=row[2][t-1] if t else 0
    return action*2+prev


def forward_backward(model,row):
    k=model["hidden"]
    seq=[public.symbol(x) for x in row[1]]
    alpha,scales=[],[]
    first=[model["prior"][i]*model["emission"][i][seq[0]] for i in range(k)]
    scales.append(sum(first))
    alpha.append(normalize(first))
    for t in range(len(row[2])):
        trans=model["transition"][hmm_context(row,t)]
        raw=[sum(alpha[t][i]*trans[i][j] for i in range(k)) *
             model["emission"][j][seq[t+1]] for j in range(k)]
        scales.append(sum(raw))
        alpha.append(normalize(raw))
    beta=[[1.]*k for _ in seq]
    for t in range(len(row[2])-1,-1,-1):
        trans=model["transition"][hmm_context(row,t)]
        beta[t]=[sum(trans[i][j]*model["emission"][j][seq[t+1]]*
                     beta[t+1][j] for j in range(k))/scales[t+1]
                 for i in range(k)]
    gamma=[normalize([alpha[t][i]*beta[t][i] for i in range(k)])
           for t in range(len(seq))]
    return seq,alpha,beta,gamma,scales


def hmm_em_step(model,rows,pseudo=.5):
    k=model["hidden"]
    prior=[pseudo]*k
    emit=[[pseudo]*4 for _ in range(k)]
    trans=[[[pseudo]*k for _ in range(k)] for _ in range(4)]
    for row in rows:
        syms,alpha,beta,gamma,scales=forward_backward(model,row)
        for i in range(k):
            prior[i]+=gamma[0][i]
        for t,o in enumerate(syms):
            for i in range(k):
                emit[i][o]+=gamma[t][i]
        for t in range(len(row[2])):
            c=hmm_context(row,t)
            matrix=model["transition"][c]
            pairs=[[(alpha[t][i]*matrix[i][j]*
                     model["emission"][j][syms[t+1]]*beta[t+1][j]) /
                     scales[t+1] for j in range(k)] for i in range(k)]
            s=sum(sum(block) for block in pairs)
            need(s > 0 and math.isfinite(s), "HMM_XI_NORM_ZERO")
            for i in range(k):
                for j in range(k):
                    trans[c][i][j] += pairs[i][j]/s
    return {"kind":"HMM","hidden":k,"prior":normalize(prior),
            "emission":[normalize(r) for r in emit],
            "transition":[[normalize(r) for r in block] for block in trans]}


def hmm_predictions(model,row):
    k=model["hidden"]
    emit=model["emission"]
    obs=row[1]
    alpha=normalize([model["prior"][i]*emit[i][public.symbol(obs[0])]
                     for i in range(k)])
    predicted=[]
    for t in range(len(row[2])):
        matrix=model["transition"][hmm_context(row,t)]
        next_state=[sum(alpha[i]*matrix[i][j] for i in range(k)) for j in range(k)]
        next_symbols=[sum(next_state[j]*emit[j][sym] for j in range(k))
                      for sym in range(4)]
        predicted.append((next_symbols[2]+next_symbols[3],
                          next_symbols[1]+next_symbols[3]))
        actual=public.symbol(obs[t+1])
        alpha=normalize([next_state[j]*emit[j][actual] for j in range(k)])
    return predicted


def fit_hmm(hidden,fit_rows,valid_rows,epochs=40,restarts=3):
    fit=checked(fit_rows)
    valid=checked(valid_rows)
    need(fit[0][0] == valid[0][0], "VALID_FAMILY_MISMATCH")
    need(epochs == 40 and restarts == 3, "FROZEN_HMM_BUDGET_DRIFT")
    start=time.process_time()
    tracemalloc.start()
    best=None
    for restart in range(restarts):
        model=hmm_init(hidden,restart)
        for ep in range(1,epochs+1):
            model=hmm_em_step(model,fit)
            val=mean_nll(valid,lambda r:hmm_predictions(model,r))
            need(math.isfinite(val),"HMM_VAL_NONFINITE")
            if best is None or val<best[0]:
                best=(val,model,ep,restart)
    _,peak=tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return best[1],{"fit_valid_cpu_s":time.process_time()-start,
                    "tracemalloc_peak_bytes":peak,
                    "checkpoint_bytes":len(json.dumps(best[1],sort_keys=True,separators=(",",":")).encode()),
                    "selected_epoch":best[2],"selected_restart":best[3],
                    "fit_validation_nll":best[0],
                    "rss_peak_bytes":None,"rss_qualification":"NATIVE_PEAK_RSS_PENDING"}


def model_predict(model,row):
    public.public_rows([row])
    name=model["kind"]
    if name == MODEL_NAMES[0]:
        return logit_predictions(model["weights"],row)
    if name in MODEL_NAMES[1:3]:
        return rnn_predictions(model["weights"],row,model["hidden"])
    if name == "HMM":
        return hmm_predictions(model,row)
    need(False,"UNKNOWN_MODEL_PREDICTION")


def checkpoint_sha(model):
    return hashlib.sha256(json.dumps(model,sort_keys=True,
        separators=(",",":"),allow_nan=False).encode()).hexdigest()


def paired_episode_bootstrap(current_losses,history_losses,seed_text,replicates=2048):
    need(replicates == 2048,"FROZEN_BOOTSTRAP_REPLICATES")
    need(len(current_losses)==len(history_losses) and len(current_losses)>1,
         "EPISODE_CLUSTER_MATCH")
    require_finite = all(math.isfinite(x) for x in current_losses+history_losses)
    need(require_finite,"BOOTSTRAP_NONFINITE")
    diffs=[a-b for a,b in zip(current_losses,history_losses)]
    seed=int.from_bytes(hashlib.sha256(("forge-q21-bootstrap:"+seed_text).encode()).digest()[:8],"big")
    randomizer=random.Random(seed)
    estimates=[]
    n=len(diffs)
    for _ in range(replicates):
        estimates.append(sum(diffs[randomizer.randrange(n)] for _ in range(n))/n)
    estimates.sort()
    return {"gain_nats_per_bit":sum(diffs)/n,
            "lower_95":estimates[math.floor(.025*(replicates-1))],
            "upper_95":estimates[math.ceil(.975*(replicates-1))],
            "resampling_unit":"EPISODE","replicates":replicates}

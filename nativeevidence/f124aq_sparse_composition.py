"""F124-AQ trainable compositional Boolean inverse, no operator catalog.

A source-blind supervised learner fits sparse parity compositions of public
transformed-output atoms to original-input labels. A second arm adds learned
pair-interaction atoms; both fit ONLY 20 publicly observed examples and
calibrate with four different public examples. 24 noisy demonstrations
remain the entire data allowance; no true inverse or source truth is imported.

Task parameters and 20-bit temporary learning feature masks are explicitly
additional inference memory beyond the original Yggdrasil 7+9 cognitive cells.
"""
from __future__ import annotations
import math
import f124aj_example_operator_learner as public
import f124ag_transition_models as ag
import f124q_fresh_source as q

MODES=("sparse_xor_basis","sparse_pair_interaction_basis")
MAX_TERMS=(2,4,6)
VALID_WRONG=(12,24,32)
FIT=20
CHECK=4

def need(ok,key):q.need(ok,"F124AQ_PARITY_"+key)

def atoms(bits,mode):
    need(mode in MODES and len(bits)==16,"PUBLIC_ATOM_MODE")
    result=list(bits)
    if mode==MODES[1]:
        result.extend(bits[a]&bits[b]
                      for a in range(16) for b in range(a+1,16))
    return result

def train(demos,mode,max_terms):
    need(type(demos) is list and len(demos)==24 and
         mode in MODES and max_terms in MAX_TERMS,
         "BOUNDED_PUBLIC_SUPERVISION")
    observations=[atoms(d["output_bits"],mode) for d in demos[:FIT]]
    columns=[sum(observations[i][j]<<i for i in range(FIT))
             for j in range(len(observations[0]))]
    desired=[sum(demos[i]["input_bits"][target]<<i for i in range(FIT))
             for target in range(16)]
    full_mask=(1<<FIT)-1
    rules=[]
    comparisons=0
    for output_target in desired:
        bias=int((output_target^full_mask).bit_count()<output_target.bit_count())
        residual=output_target^(full_mask if bias else 0)
        selected=[]
        remaining=set(range(len(columns)))
        for step in range(max_terms):
            current=residual.bit_count()
            score,feature=min(
                ((residual^columns[j]).bit_count(),j) for j in remaining)
            comparisons+=len(remaining)
            if score>=current:break
            selected.append(feature)
            residual^=columns[feature]
            remaining.remove(feature)
        rules.append((bias,tuple(selected),residual.bit_count()))
    return (mode,tuple(rules)),{
        "fit_count":FIT,"check_count":CHECK,
        "candidate_feature_masks":len(columns),
        "fit_feature_bitset_storage_bits":FIT*len(columns),
        "learned_feature_index_slots":sum(len(x[1]) for x in rules),
        "train_candidate_comparisons":comparisons,
        "additional_model_memory_reported":True}

def predict(model,encoded):
    mode,rules=model
    f=atoms(encoded,mode)
    result=[]
    for bias,indices,train_residual in rules:
        output=bias
        for j in indices:output^=f[j]
        result.append(output)
    return result,len(f)*16+sum(len(x[1]) for x in rules)

def normalize(graph,mode,max_terms,wrong_limit):
    need(wrong_limit in VALID_WRONG and max_terms in MAX_TERMS
         and mode in MODES,"FROZEN_MODEL_OPTIONS")
    raw,demos,nonce=public.public_task(graph)
    model,diag=train(demos,mode,max_terms)
    wrong=0
    operations=diag["train_candidate_comparisons"]
    for d in demos[FIT:]:
        bits,cost=predict(model,d["output_bits"])
        wrong+=sum(x!=y for x,y in zip(bits,d["input_bits"]))
        operations+=cost
    accepted=wrong<=wrong_limit
    meta={"mode":mode,"max_terms":max_terms,
          "validation_wrong_bit_limit":wrong_limit,
          "validation_wrong_bits":wrong,
          "public_fit":FIT,"public_validation":CHECK,
          "abstained":not accepted,"operator_catalog_known":False,
          "source_oracle_used":False,"extra_cognitive_cells":0,
          "feature_bitset_storage_bits":diag["fit_feature_bitset_storage_bits"],
          "model_feature_slots":diag["learned_feature_index_slots"],
          "train_comparisons":diag["train_candidate_comparisons"],
          "total_declared_model_ops":operations,
          "transient_model_storage_disclosed":True}
    if not accepted:return None,meta
    for e in raw["edges"]:
        e["src_bits"],cost=predict(model,e["src_bits"])
        operations+=cost
    meta["total_declared_model_ops"]=operations
    ag.frozen.prior.parent.validate_15(raw)
    return raw,meta

def ygg(graph,base,delta,mode,max_terms,wrong_limit):
    g,meta=normalize(graph,mode,max_terms,wrong_limit)
    if g is None:return -1.e9,None,meta
    score,raw,prob,work=ag.ygg_transition(g,list(base),list(delta),.1)
    need(work["max_active"]<=7 and work["max_retained"]<=9,
         "FIXED_SEVEN_ACTIVE_NINE_RETAINED")
    return score,work,meta

def select(cases,base,delta):
    need(len(cases)==48,"FROZEN_TRAIN_DENOMINATOR")
    scores=[]
    for mode in MODES:
        for terms in MAX_TERMS:
            for wrong in VALID_WRONG:
                paired=fp=fn=abstained=ops=0
                max_extra_bits=0
                for seed,vec,family,operator,nonce,pos,neg in cases:
                    a,wa,da=ygg(pos,base,delta,mode,terms,wrong)
                    b,wb,db=ygg(neg,base,delta,mode,terms,wrong)
                    paired+=int(a>=0 and b<0)
                    fp+=int(b>=0)
                    fn+=int(a<0)
                    abstained+=int(da["abstained"])+int(db["abstained"])
                    ops+=da["total_declared_model_ops"]+db["total_declared_model_ops"]
                    max_extra_bits=max(max_extra_bits,
                        da["feature_bitset_storage_bits"],
                        db["feature_bitset_storage_bits"])
                scores.append({"mode":mode,"max_terms":terms,
                    "validation_wrong_bit_limit":wrong,
                    "paired":paired,"FP":fp,"FN":fn,
                    "abstained_graphs":abstained,
                    "declared_model_ops":ops,
                    "peak_extra_fit_feature_bits":max_extra_bits})
    zero=[s for s in scores if s["FP"]==0]
    eligible=zero if zero else scores
    return sorted(eligible,key=lambda a:(
        -a["paired"],a["FN"],a["declared_model_ops"],
        a["mode"],a["max_terms"],a["validation_wrong_bit_limit"]))[0],scores

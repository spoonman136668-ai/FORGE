"""F124-AP genuinely learned example-conditioned *dual kernel* relation map.

This is NOT a hand-written causal bit-index interpreter. Per public task,
learn sixteen continuous inverse functions from 20 supervised public
observations in a regularized dual feature space. Four separate PUBLIC
observations assess confidence. No source class, operator parser, graph label,
true inverse, oracle, hidden set, or previous DEV data is an input.

A learned per-task 20x16 kernel coefficient table is TRANSIENT auxiliary
working memory beyond Yggdrasil's 7+9 cognitive cells. Disclose it; never
count this as 16 total cells or claim compute equivalence without measurement.
"""
from __future__ import annotations
import math
import f124aj_example_operator_learner as public
import f124ag_transition_models as ag
import f124q_fresh_source as q

KERNELS=("dual_linear_kernel_ridge","dual_quadratic_kernel_ridge")
LAMBDAS=(.25,1.)
BAD_GRID=(4,12)
MARGINS=(0.,.1)
FIT=20
VALID=4

def need(ok,tag):q.need(ok,"F124AP_KERNEL_"+tag)

def kernel(a,b,architecture):
    # Normalized signed-bit similarity; the quadratic reproducing kernel
    # learns pairwise interactions without a manually enumerated operator.
    dot=sum((2*x-1)*(2*y-1) for x,y in zip(a,b))/16.
    return dot if architecture==KERNELS[0] else (1.+dot)**2/4.

def fit(demos,architecture,reg):
    need(len(demos)==FIT+VALID and architecture in KERNELS
         and reg in LAMBDAS,"FROZEN_PUBLIC_FEATURES")
    examples=demos[:FIT]
    supports=[tuple(e["output_bits"]) for e in examples]
    target=[tuple(2*x-1 for x in e["input_bits"]) for e in examples]
    # Gaussian elimination of the same positive-definite Gram+lambda matrix
    # for all 16 response coordinates; deterministic partial pivoting.
    n=FIT
    mat=[]
    for i in range(n):
        mat.append(
            [kernel(supports[i],supports[j],architecture)+
             (reg if i==j else 0.) for j in range(n)]+list(target[i]))
    operations=n*n*16
    for col in range(n):
        pivot=max(range(col,n),key=lambda r:(abs(mat[r][col]),-r))
        mat[col],mat[pivot]=mat[pivot],mat[col]
        d=mat[col][col]
        need(math.isfinite(d) and abs(d)>1.e-12,
             "FINITE_INVERTIBLE_PUBLIC_GRAM")
        for j in range(col,n+16):
            mat[col][j]/=d
            operations+=1
        for row in range(n):
            if row==col:continue
            v=mat[row][col]
            if not v:continue
            for j in range(col,n+16):
                mat[row][j]-=v*mat[col][j]
                operations+=2
    coeff=tuple(tuple(mat[i][n:]) for i in range(n))
    return (supports,coeff,architecture),{
        "support_count":FIT,"validation_count":VALID,
        "task_coefficients":FIT*16,
        "training_gram_elements":FIT*FIT,
        "max_transient_solver_elements":FIT*(FIT+16),
        "model_float_operations_estimated":operations}

def predict(fitted,encoded):
    supports,coeff,arch=fitted
    terms=[kernel(encoded,row,arch) for row in supports]
    logits=[sum(terms[i]*coeff[i][bit] for i in range(FIT))
            for bit in range(16)]
    need(all(math.isfinite(v) for v in logits),"FINITE_KERNEL_PREDICTION")
    return [int(v>=0) for v in logits],min(abs(x) for x in logits),FIT*(16+16)

def normalize(graph,architecture,reg,allowed_bad,margin):
    need(allowed_bad in BAD_GRID and margin in MARGINS,
         "FROZEN_TRAIN_ONLY_CALIBRATION")
    raw,demos,task=public.public_task(graph)
    trained,stats=fit(demos,architecture,reg)
    errors=0
    work=stats["model_float_operations_estimated"]
    min_margin=math.inf
    for demo in demos[FIT:]:
        bits,m,ops=predict(trained,demo["output_bits"])
        errors+=sum(x!=y for x,y in zip(bits,demo["input_bits"]))
        min_margin=min(m,min_margin)
        work+=ops
    accepted=errors<=allowed_bad and min_margin>=margin
    obs={"architecture":architecture,"public_train":FIT,"public_validate":VALID,
         "public_validation_wrong_bits":errors,"min_public_validation_margin":min_margin,
         "abstained":not accepted,"source_operator_known":False,
         "source_oracle_used":False,"extra_cognitive_cells":0,
         "task_coefficients":stats["task_coefficients"],
         "training_gram_elements":stats["training_gram_elements"],
         "max_transient_solver_elements":stats["max_transient_solver_elements"],
         "model_float_operations_estimated":work}
    if not accepted:return None,obs
    for edge in raw["edges"]:
        edge["src_bits"],_,ops=predict(trained,edge["src_bits"])
        work+=ops
    obs["model_float_operations_estimated"]=work
    ag.frozen.prior.parent.validate_15(raw)
    return raw,obs

def ygg(graph,base,delta,architecture,reg,allowed_bad,margin):
    normalized,obs=normalize(graph,architecture,reg,allowed_bad,margin)
    if normalized is None:return -1.e9,None,obs
    value,raw,prob,work=ag.ygg_transition(
        normalized,list(base),list(delta),.1)
    need(work["max_active"]<=7 and work["max_retained"]<=9,
         "ORIGINAL_SEVEN_PLUS_NINE_CELLS")
    return value,work,obs

def select(cases,base,delta):
    need(len(cases)==48,"FROZEN_TRAIN_ONLY")
    results=[]
    for arch in KERNELS:
        for reg in LAMBDAS:
            for allowed in BAD_GRID:
                for margin in MARGINS:
                    paired=fp=fn=abstained=ops=0
                    for seed,vec,fam,op,nonce,pos,neg in cases:
                        a,_,da=ygg(pos,base,delta,arch,reg,allowed,margin)
                        b,_,db=ygg(neg,base,delta,arch,reg,allowed,margin)
                        paired+=int(a>=0 and b<0)
                        fp+=int(b>=0)
                        fn+=int(a<0)
                        abstained+=int(da["abstained"])+int(db["abstained"])
                        ops+=da["model_float_operations_estimated"]+db["model_float_operations_estimated"]
                    results.append({"architecture":arch,"lambda":reg,
                         "bad_bits":allowed,"margin":margin,
                         "paired":paired,"FP":fp,"FN":fn,
                         "abstained_graphs":abstained,
                         "estimated_float_ops":ops})
    zero_fp=[row for row in results if row["FP"]==0]
    eligible=zero_fp if zero_fp else results
    chosen=sorted(eligible,key=lambda r:(
        -r["paired"],r["FN"],r["estimated_float_ops"],
        r["architecture"],r["lambda"],r["bad_bits"],r["margin"]))[0]
    return chosen,results

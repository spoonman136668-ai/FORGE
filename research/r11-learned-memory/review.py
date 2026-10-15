"""Independent R11 auditor: recompute trained controller, native controls and rows.

No imports from the R11 model worker, evaluator, or R36 training code.
All replayed controller decisions use only the frozen train-seed examples.
"""
import argparse,hashlib,importlib.util,json,math,pathlib,subprocess
from protocol import freeze,verify_parent,sha,parse,stop
def close(x,y,tol=1e-8):
    return type(x) in (float,int) and type(y) in (float,int) and math.isfinite(x) and math.isfinite(y) and abs(x-y)<=tol
def dot(w,x):return sum(a*b for a,b in zip(w,x))
def make_training(source,seeds):
    out={}
    for ix,gen in enumerate(source.GEN):
        rows=[]
        for seed in seeds:
            for entity in range(9):
                if entity%3!=(ix+seed)%3:continue
                for site in source.TRAIN_SITES:
                    for amp in (1,2):
                        base,pos,neg=source.w37.recoded_example(seed,entity,gen,"identity",site,amp,True)
                        a=source.w42.feature(base,pos);b=source.w42.feature(base,neg)
                        d=tuple(a[j]-b[j] for j in range(16))
                        rows.append((d,1));rows.append((tuple(-z for z in d),-1))
        if len(rows)!=576:stop("REVIEW_TRAIN_COUNT")
        out[gen]=rows
    return out
def grad(rows,w):
    vector=[0.0]*16
    for feat,y in rows:
        if y*dot(w,feat)<=0:
            for i in range(16):vector[i]+=y*feat[i]/len(rows)
    return vector
def hinge(rows,w):return sum(max(0.0,1-y*dot(w,x)) for x,y in rows)/len(rows)
def c4(groups):
    w=[0.0]*16
    for _ in range(32):
        steps=[]
        for group in groups.values():
            ordered=sorted(range(576),key=lambda idx:(group[idx][1]*dot(w,group[idx][0]),idx))
            steps.append(grad([group[i] for i in ordered[:32]],w))
        w=[w[i]+0.1*sum(step[i] for step in steps)/3 for i in range(16)]
    return w
def minimax(groups):
    w=[0.0]*16
    lst=list(groups)
    for _ in range(32):
        risks=[hinge(groups[g],w) for g in lst]
        choice=max(range(3),key=lambda s:risks[s])
        mem=groups[lst[choice]]
        step=grad(mem,w)
        w=[w[i]+0.1*step[i] for i in range(16)]
    return w
def retained_options(pool,w):
    order=sorted(range(len(pool)),key=lambda idx:(pool[idx][1]*dot(w,pool[idx][0]),idx))
    hard=order[:32]
    groups=[[] for _ in range(16)]
    for idx,(features,_y) in enumerate(pool):
        dominant=max(range(16),key=lambda j:(abs(features[j]),-j))
        groups[dominant].append(idx)
    diverse=[]
    for group in groups:
        diverse+=sorted(group,key=lambda idx:(pool[idx][1]*dot(w,pool[idx][0]),idx))[:2]
    diverse=diverse[:32]
    taken=set(diverse)
    for k in order:
        if len(diverse)>=32:break
        if k not in taken:
            diverse.append(k);taken.add(k)
    if len(hard)!=32 or len(diverse)!=32:stop("REVIEW_MEM_CAPACITY")
    return hard,diverse,order
def learned(groups):
    weights=[0.0]*16;logits=[0.0,0.0,0.0];trace=[]
    for epoch in range(32):
        gradients=[];record=[]
        for ix,group in enumerate(groups.values()):
            observed=[ex for row,ex in enumerate(group) if (row+epoch)%5==0]
            available=[ex for row,ex in enumerate(group) if (row+epoch)%5!=0]
            hard,diverse,order=retained_options(available,weights)
            g1=grad([available[i] for i in hard],weights)
            g2=grad([available[i] for i in diverse],weights)
            after_h=hinge(observed,[weights[k]+0.1*g1[k] for k in range(16)])
            after_d=hinge(observed,[weights[k]+0.1*g2[k] for k in range(16)])
            advantage=max(-0.5,min(0.5,after_d-after_h))
            logits[ix]=max(-4.0,min(4.0,logits[ix]+4.0*advantage))
            count=round(32/(1+math.exp(-logits[ix])))
            retained=[]
            seen=set()
            for v in hard[:count]+diverse[:32-count]+order:
                if v not in seen:
                    retained.append(v);seen.add(v)
                if len(retained)==32:break
            if len(retained)!=32:stop("REVIEW_RETAINED_SIZE")
            gradients.append(grad([available[k] for k in retained],weights))
            record.append({"source":ix,"proxy_count":len(observed),"gate_logit":logits[ix],
                           "hard_slots_requested":count,"retained_slots":32})
        weights=[weights[i]+0.1*sum(x[i] for x in gradients)/3 for i in range(16)]
        trace.append({"epoch":epoch,"sources":record})
    return weights,logits,trace
def evaluate(source,weights,seeds,observed):
    rows=observed.get("by_seed")
    if not isinstance(rows,list) or len(rows)!=32:stop("SEED_ROWS")
    correct={g:0 for g in source.GEN}
    total=0
    for i,seed in enumerate(seeds):
        record=rows[i]
        if record.get("seed")!=seed or record.get("total")!=108 or set(record.get("family_correct",{}))!=set(source.GEN):stop("ROW_ORDER")
        row_count=0
        for gen in source.GEN:
            value=0
            for site in source.SITES:
                for entity in range(9):
                    base,pos,neg=source.w37.recoded_example(seed,entity,gen,"identity",site,3,False)
                    features=source.w42.feature(base,pos)
                    opposite=source.w42.feature(base,neg)
                    margin=dot(weights,[u-v for u,v in zip(features,opposite)])
                    value+=source.w45.credit(margin,True)+source.w45.credit(-margin,False)
            if not close(value,record["family_correct"][gen]):stop("GENERATOR_CASE_MISMATCH")
            correct[gen]+=value;row_count+=value
        if not close(row_count,record.get("correct")):stop("ROW_TOTAL")
        total+=row_count
    overall=total/(32*108)
    byfam={k:correct[k]/(32*36) for k in source.GEN}
    if not close(overall,observed.get("accuracy")) or set(observed.get("family_accuracy",{}))!=set(byfam):stop("ACCURACY_SUMMARY")
    for k in byfam:
        if not close(byfam[k],observed["family_accuracy"][k]):stop("GENERATOR_ACC")
    return overall,byfam
def audit(frozen_raw,parent_raw,record_raw,wingless_root):
    m=freeze(frozen_raw);verify_parent(parent_raw,m)
    if len(record_raw)>1000000:stop("MEASUREMENT_SIZE")
    data=parse(record_raw,cap=1000000)
    if (data.get("schema")!="forge.r11.real-learned-memory.development.v1" or
        data.get("scope")!="ACTUAL_TRAIN_ONLY_PROXY_LEARNER_ON_NEW_PUBLIC_DEVELOPMENT" or
        data.get("frozen_sha256")!=sha(frozen_raw) or data.get("parent_r10_review_sha256")!=sha(parent_raw) or
        data.get("wingless_commit")!=m["pinned"]["wingless_sha"] or
        data.get("method_commit")!=m["pinned"]["r36_sha"] or
        data.get("classifier_parameters")!=16 or
        data.get("additional_learned_gate_parameters")!=3 or
        data.get("fixed_memory_slots")!=96 or data.get("training_epochs")!=32 or
        data.get("sealed_cohorts_accessed") is not False or
        data.get("new_originals_executed")!=0 or data.get("first_use_claims_created")!=0 or
        data.get("scientific_accepted") is not False or data.get("paid_api_calls")!=0):stop("FALSE_AUTHORITY_OR_IDENTITY")
    root=pathlib.Path(wingless_root).resolve(strict=True)
    if subprocess.check_output(["git","-C",str(root),"rev-parse","HEAD"],text=True).strip()!=m["pinned"]["wingless_sha"]:stop("SOURCE_ID")
    spec=importlib.util.spec_from_file_location("r11_reviewer_raw_wingless",root/"research/contrib/chatgpt/20261013-w-r52-batch-diversity/execute.py")
    if not spec or not spec.loader:stop("RAW_SOURCE_MISSING")
    source=importlib.util.module_from_spec(spec);spec.loader.exec_module(source)
    reports=data.get("development_folds")
    if not isinstance(reports,list) or len(reports)!=3:stop("FOLD_COUNT")
    results=[]
    for fold,report in enumerate(reports):
        train=m["development"]["train_blocks"][fold]
        valid=[v for j,block in enumerate(m["development"]["train_blocks"]) if j!=fold for v in block]
        if report.get("fold")!=fold or report.get("train_seeds")!=train or report.get("validation_seeds")!=valid:stop("FOLD_IDENTITY")
        groups=make_training(source,train)
        weights,gates,trace=learned(groups)
        controls={"hard_minimax":minimax(groups),"fixed_C4_memory":c4(groups),"learned_retention":weights}
        if set(report.get("models",{}))!=set(controls) or set(report.get("score_by_arm",{}))!=set(controls):stop("MISSING_CONTROL")
        recorded_gates=report.get("trained_gate_logits")
        if not isinstance(recorded_gates,list) or len(recorded_gates)!=3 or any(not close(a,b) for a,b in zip(gates,recorded_gates)):stop("GATE_LEARNING_DRIFT")
        rec_trace=report.get("retention_trace")
        if not isinstance(rec_trace,list) or len(rec_trace)!=32:stop("TRACE_LENGTH")
        for e in range(32):
            if rec_trace[e].get("epoch")!=e or len(rec_trace[e].get("sources",[]))!=3:stop("TRACE_EPOCH")
            for a,b in zip(rec_trace[e]["sources"],trace[e]["sources"]):
                if a.get("source")!=b["source"] or a.get("proxy_count")!=b["proxy_count"] or a.get("hard_slots_requested")!=b["hard_slots_requested"] or a.get("retained_slots")!=32 or not close(a.get("gate_logit"),b["gate_logit"]):stop("TRAIN_PROXY_DECISION")
        if report.get("retained_slots")!=96 or report.get("controller_trainable_scalar_count")!=3:stop("CAPACITY_CLAIM")
        evaluated={}
        for arm,expected in controls.items():
            original=report["models"][arm]
            x=original.get("weights")
            if not isinstance(x,list) or len(x)!=16 or any(not close(a,b,1e-9) for a,b in zip(x,expected)):stop("TRAINING_REPLAY_FAILED_"+arm)
            fingerprint=hashlib.sha256(json.dumps(x,separators=(",",":"),allow_nan=False).encode()).hexdigest()
            if original.get("weights_sha256")!=fingerprint or report["score_by_arm"][arm].get("weights_sha256")!=fingerprint:stop("WEIGHT_FINGERPRINT")
            if original.get("source_counts")!={k:576 for k in source.GEN} or report["score_by_arm"][arm].get("source_training_example_counts")!={k:576 for k in source.GEN}:stop("SOURCE_BUDGET")
            evaluated[arm]=evaluate(source,expected,valid,report["score_by_arm"][arm])
        base=evaluated["hard_minimax"];candidate=evaluated["learned_retention"]
        gain=min(candidate[1].values())-min(base[1].values())
        deltas={g:candidate[1][g]-base[1][g] for g in source.GEN}
        passing=gain>=0.02 and min(deltas.values())>=-0.05 and candidate[0]>=0.55
        if not close(gain,report.get("preregistered_worst_family_gain")) or report.get("preregistered_development_positive") is not passing:stop("FALSE_DEVELOPMENT_POSITIVE")
        if set(report.get("preregistered_family_deltas",{}))!=set(deltas):stop("FAMILY_DELTA_SET")
        for g in deltas:
            if not close(deltas[g],report["preregistered_family_deltas"][g]):stop("FAMILY_DELTA")
        results.append({"fold":fold,"worst_family_gain":gain,"passed":passing,
                        "hard_minimax_accuracy":base[0],"fixed_memory_accuracy":evaluated["fixed_C4_memory"][0],
                        "learned_memory_accuracy":candidate[0],
                        "independent_train_proxy_steps":96,
                        "independent_validation_seed_arm_rows":96})
    passed=all(v["passed"] for v in results)
    return {"schema":"forge.r11.independent-learned-retention-development.v1",
       "actual_training_reconstructed":True,"retention_gates_independently_reconstructed":True,
       "all_development_rows_independently_verified":True,
       "reviewed_measurement_sha256":sha(record_raw),"source_parent_sha256":sha(parent_raw),
       "model_classifier_scalar_count":16,"learned_memory_controller_scalar_count":3,
       "retained_memory_slots":96,
       "results":results,"all_three_folds_passed":passed,
       "development_candidate_eligible":passed,
       "scientific_improvement_established":False,
       "first_use_authorized":False,"scientific_originals_executed":0,
       "sealed_holdout_accessed":False,"scientific_accepted":False,
       "cloudflare_changed":False,"paid_api_calls":0}
def main():
    p=argparse.ArgumentParser()
    for item in ("frozen","parent","measurement","wingless_root","out"):p.add_argument("--"+item.replace("_","-"),required=True)
    a=p.parse_args()
    result=audit(pathlib.Path(a.frozen).read_bytes(),pathlib.Path(a.parent).read_bytes(),
       pathlib.Path(a.measurement).read_bytes(),a.wingless_root)
    with pathlib.Path(a.out).open("xb") as f:f.write((json.dumps(result,sort_keys=True,indent=2)+"\n").encode())
    print("R11_INDEPENDENT_MEMORY_CONTROLLER_TRAINING_AND_ROWS=PASS")
    print("R11_NEW_FIRST_USE=ZERO")
if __name__=="__main__":main()

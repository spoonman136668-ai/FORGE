"""T15 Mass: 3-role sourceblind learned composition and fair TRAIN controls.
TRAIN sees only public elementary role witnesses; OPEN never-before-seen
3/4-step relation words. A second separately fitted matched TRAIN empirical
learner with the SAME public evidence and inference budget is a strict control.
Nonprotected original development only; no signed scientific promotion.
"""
from __future__ import annotations
import json,sys,time,tracemalloc
from pathlib import Path
D=Path(__file__).parent
def load(file,name):
    import importlib.util
    s=importlib.util.spec_from_file_location(name,file);m=importlib.util.module_from_spec(s)
    sys.modules[name]=m;s.loader.exec_module(m);return m
def measured(fn):
    tracemalloc.start();t=time.process_time_ns()
    try:return fn(),{"cpu_ns":time.process_time_ns()-t,"python_peak_bytes":tracemalloc.get_traced_memory()[1]}
    finally:tracemalloc.stop()
def train_role_maps(train,m):
    votes={role:[[0]*16 for _ in range(16)] for role in "PQR"}
    examples={role:0 for role in "PQR"}
    for word,fit,check,witness,held in train:
        assert len(word)==1 and len(witness)==8
        role=word[0];examples[role]+=len(witness)
        for x,y in witness:
            for bit in (0,4,8,12):
                a,b=(x>>bit)&15,(y>>bit)&15
                votes[role][a][b]+=1
    maps={}
    for role,table in votes.items():
        choices=sorted((-table[i][j],i,j) for i in range(16) for j in range(16))
        result=[None]*16;used=set()
        for neg,i,j in choices:
            if result[i] is None and j not in used:
                result[i]=j;used.add(j)
        assert sorted(result)==list(range(16))
        maps[role]=m.pack(result)
    return maps,examples
def compose(prior,word,m,src):
    result=tuple(range(16))
    for role in word:
        result=src.compose(result,m.unpack(prior[role]))
    return m.pack(result)
def main():
    freeze=json.loads((D/"20261019-mass-t15-preimplementation-freeze.json").read_text())
    assert freeze["schema"]=="northstar.t15.mass.freeze.v1"
    assert freeze["source_blob"]=="16ea3a38bc694f6229654281471b449c3d60ea8e"
    src=load(D/"20261019-mass-t15-source.py","m15src")
    m=load(D/"20261018-mass-t3-learned-sbox.py","m15m")
    t10=load(D/"20261019-mass-t10-shared-map.py","m15t10")
    t13=load(D/"20261019-mass-t13-mechanism.py","m15t13")
    train=[src.birth(s,m) for s in src.TRAIN]
    tests=[src.birth(s,m) for s in src.OPEN]
    (learned,counts),train_cost=measured(lambda:train_role_maps(train,m))
    (empirical,emp_counts),emp_train_cost=measured(lambda:train_role_maps(train,m))
    assert set(learned)==set("PQR") and all(len(v)==8 for v in learned.values())
    identity={role:m.pack(tuple(range(16))) for role in "PQR"}
    rows=[]
    for seed,(word,FIT,CHECK,witness,hidden) in zip(src.OPEN,tests):
        prior=compose(learned,word,m,src)
        independent_prior=compose(empirical,word,m,src)
        fixed_prior=compose(identity,word,m,src)
        (candidate,diag),ccost=measured(lambda:t13.refine(m,t10,prior,FIT,CHECK,witness,"learned"))
        (trained_control,trained_diag),ecost=measured(
            lambda:t13.refine(m,t10,independent_prior,FIT,CHECK,witness,"full_prior"))
        (untrained,zero_diag),zcost=measured(
            lambda:t13.refine(m,t10,fixed_prior,FIT,CHECK,witness,"identity"))
        score=lambda model:sum(m.forward(x,model)==y for x,y in hidden)
        rows.append({"seed":seed,"new_structure":list(word),
          "candidate_correct":score(candidate),"trained_control_correct":score(trained_control),
          "untrained_correct":score(untrained),
          "candidate_cpu_ns":ccost["cpu_ns"],"trained_cpu_ns":ecost["cpu_ns"],
          "untrained_cpu_ns":zcost["cpu_ns"],
          "candidate_peak":ccost["python_peak_bytes"],"trained_peak":ecost["python_peak_bytes"],
          "untrained_peak":zcost["python_peak_bytes"],"candidate_proposals":diag["sourceblind_fixed_proposals"]})
    total=lambda k:sum(row[k] for row in rows)
    out={"schema":"mass.t15.sourceonly-unseen-three-role-composition.v1",
      "TRAIN":len(train),"OPEN":len(tests),"private_held_outputs":len(tests)*16,
      "new_composition_word_types":4,"TRAIN_public_witnesses_each":8,
      "trained_role_maps_bytes":sum(map(len,learned.values())),
      "TRAIN_public_witness_counts_by_role":counts,
      "candidate_correct":total("candidate_correct"),
      "matched_empirical_TRAIN_correct":total("trained_control_correct"),
      "equal_public_untrained_correct":total("untrained_correct"),
      "candidate_regressed_strong_control":sum(1 for r in rows if r["candidate_correct"]<r["trained_control_correct"]),
      "candidate_amortized_cpu_ns":total("candidate_cpu_ns")+train_cost["cpu_ns"]//len(tests),
      "trained_control_amortized_cpu_ns":total("trained_cpu_ns")+emp_train_cost["cpu_ns"]//len(tests),
      "untrained_cpu_ns":total("untrained_cpu_ns"),
      "candidate_training_inclusive_peak_bytes":max(train_cost["python_peak_bytes"],max(z["candidate_peak"] for z in rows)),
      "trained_control_peak_bytes":max(emp_train_cost["python_peak_bytes"],max(z["trained_peak"] for z in rows)),
      "remote_query_service_cost_authenticated":False,"independently_signed_source":False,
      "protected_source_used":False,"signed_scientific_acceptance":False,
      "optimizer_admission":False,"cases":rows}
    assert out["candidate_regressed_strong_control"]==0
    assert total("candidate_correct")<=128
    print(json.dumps(out,sort_keys=True))
if __name__=="__main__":main()

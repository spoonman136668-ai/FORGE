"""T14-B Mass: TRAIN-learned two role bijections, OPEN unseen compositions.
Fair same-information empirical TRAIN control can tie; no auto acceptance.
All private held outputs are scorer-only, never fit or source selectors.
"""
from __future__ import annotations
import json,sys,time,tracemalloc
from pathlib import Path
D=Path(__file__).parent
def load(path,name):
    import importlib.util
    spec=importlib.util.spec_from_file_location(name,path)
    mod=importlib.util.module_from_spec(spec);sys.modules[name]=mod
    spec.loader.exec_module(mod);return mod
def measure(fn):
    tracemalloc.start();t=time.process_time_ns()
    try:return fn(),{"cpu_ns":time.process_time_ns()-t,"python_peak_bytes":tracemalloc.get_traced_memory()[1]}
    finally:tracemalloc.stop()
def public_role_vote(train,m):
    votes={r:[[0]*16 for i in range(16)] for r in ("P","Q")}
    seen={"P":0,"Q":0}
    for roles,FIT,CHECK,witness,_ in train:
        assert len(roles)==1 and len(witness)==16
        role=roles[0]
        for x,y in witness:
            for bits in (0,4,8,12):
                a,b=(x>>bits)&15,(y>>bits)&15
                votes[role][a][b]+=1;seen[role]+=1
    prior={}
    for role in ("P","Q"):
        rows=votes[role];out=[None]*16;used=set()
        pairs=sorted(((-rows[i][j],i,j) for i in range(16) for j in range(16)))
        for _,i,j in pairs:
            if out[i] is None and j not in used:out[i]=j;used.add(j)
        assert sorted(out)==list(range(16))
        prior[role]=m.pack(out)
    return prior,seen
def compose_native(src,m,prior,roles):
    candidate=tuple(range(16))
    for role in roles:candidate=src.compose(candidate,m.unpack(prior[role]))
    return m.pack(candidate)
def main():
    f=json.loads((D/"20261019-mass-t14-complete-source-and-assay-freeze.json").read_text())
    assert f["schema"]=="northstar.t14.mass.complete-source-assay-freeze.v1"
    assert f["source_blob"]=="c9979d6e0ed2fbcaadb9179fdd8640b1ffede002"
    src=load(D/"20261019-mass-t14-source.py","m_t14_src")
    m=load(D/"20261018-mass-t3-learned-sbox.py","m_t14_kernel")
    t10=load(D/"20261019-mass-t10-shared-map.py","m_t14_t10")
    t13=load(D/"20261019-mass-t13-mechanism.py","m_t14_t13")
    training=[src.birth(seed,m) for seed in src.TRAIN]
    opens=[src.birth(seed,m) for seed in src.OPEN]
    (learned,train_info),traincost=measure(lambda:public_role_vote(training,m))
    # Strongest equal-information trained control independently fits the
    # exact same PUBLIC role-disclosed witness record, without PRIVATE truth.
    (empirical,emp_info),emptraincost=measure(lambda:public_role_vote(training,m))
    identity={role:m.pack(range(16)) for role in ("P","Q")}
    assert set(learned)=={"P","Q"} and all(len(p)==8 for p in learned.values())
    records=[]
    for roles,FIT,CHECK,witness,hold in opens:
        assert 2<=len(roles)<=3
        candidate_prior=compose_native(src,m,learned,roles)
        empirical_prior=compose_native(src,m,empirical,roles)
        untrained_prior=compose_native(src,m,identity,roles)
        (c,cd),cc=measure(lambda:t13.refine(m,t10,candidate_prior,FIT,CHECK,witness,"learned"))
        (e,ed),ec=measure(lambda:t13.refine(m,t10,empirical_prior,FIT,CHECK,witness,"full_prior"))
        (z,zd),zc=measure(lambda:t13.refine(m,t10,untrained_prior,FIT,CHECK,witness,"identity"))
        score=lambda p:sum(m.forward(x,p)==y for x,y in hold)
        records.append({"roles":roles,"learned":score(c),"empirical_TRAIN":score(e),
          "untrained":score(z),"candidate_CPU_ns":cc["cpu_ns"],
          "empirical_CPU_ns":ec["cpu_ns"],"untrained_CPU_ns":zc["cpu_ns"],
          "candidate_peak":cc["python_peak_bytes"],
          "empirical_peak":ec["python_peak_bytes"],
          "zero_peak":zc["python_peak_bytes"],"candidate_swaps":cd["improving_swaps"]})
    total=lambda name:sum(r[name] for r in records)
    loss=sum(1 for r in records if r["learned"]<r["empirical_TRAIN"])
    out={"schema":"mass.t14.original-sourceonly-novel-composition-diagnostic.v1",
      "source_blob":f["source_blob"],"TRAIN":len(training),"OPEN":len(opens),
      "out_of_train_compositional_structures":True,
      "holdout_outputs":len(opens)*16,
      "learned_role_parameter_bytes":16,"TRAIN_public_votes":train_info,
      "learned_correct":total("learned"),"best_same_training_empirical_correct":total("empirical_TRAIN"),
      "untrained_structural_correct":total("untrained"),
      "learned_regressed_empirical_cases":loss,
      "training_amortized_learned_cpu_ns":total("candidate_CPU_ns")+traincost["cpu_ns"]//len(opens),
      "trained_control_cpu_ns":total("empirical_CPU_ns")+emptraincost["cpu_ns"]//len(opens),
      "untrained_cpu_ns":total("untrained_CPU_ns"),
      "candidate_peak_including_training":max(traincost["python_peak_bytes"],max(r["candidate_peak"] for r in records)),
      "empirical_peak_including_training":max(emptraincost["python_peak_bytes"],max(r["empirical_peak"] for r in records)),
      "remote_public_query_service_cost_known":False,
      "independent_authority_signed":False,"independent_source_family_replication":False,
      "scientific_acceptance":False,"optimizer_admission":False,"cases":records}
    assert loss==0,"T14_MASS_REGRESSED_TRAINED_EMPIRICAL"
    assert out["learned_correct"]<=len(opens)*16
    print(json.dumps(out,sort_keys=True))
if __name__=="__main__":main()

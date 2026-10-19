"""T16 Mass: public TRAIN learned joint cross-role nonlinear template.
Inference sees only PUBLIC tasks/role symbols and OPEN public witnesses.
The candidate's declared P/Q inverse / R=P^2 structural inductive bias is
also given to an equal-information structure-aware comparator. No hidden
parent permutation, generator RNG, or held answer reaches the learner.
"""
from __future__ import annotations
import importlib.util,json,sys,time,tracemalloc
from pathlib import Path
D=Path(__file__).parent
def load(p,name):
    s=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(s)
    sys.modules[name]=m;s.loader.exec_module(m);return m
def metered(fn):
    tracemalloc.start();start=time.process_time_ns()
    try:return fn(),{"cpu_ns":time.process_time_ns()-start,"python_peak_bytes":tracemalloc.get_traced_memory()[1]}
    finally:tracemalloc.stop()
def votes(training):
    vote={role:[[0]*16 for _ in range(16)] for role in "PQR"}
    for word,fit,check,witness,private in training:
        assert len(word)==1 and len(witness)==3
        role=word[0]
        for x,y in witness:
            for shift in (0,4,8,12):
                a,b=(x>>shift)&15,(y>>shift)&15
                vote[role][a][b]+=1
    return vote
def assign(vote):
    # Same exact deterministic bijective vote matching for every control.
    perms=[None]*16;used=set()
    for count,i,j in sorted((-vote[i][j],i,j) for i in range(16) for j in range(16)):
        if perms[i] is None and j not in used:
            perms[i]=j;used.add(j)
    assert sorted(perms)==list(range(16))
    return tuple(perms)
def invert(p):
    q=[0]*16
    for i,v in enumerate(p):q[v]=i
    return tuple(q)
def compose(p,q):
    return tuple(q[p[i]] for i in range(16))
def learn(training,m):
    v=votes(training)
    independently={role:assign(v[role]) for role in "PQR"}
    # Joint public TRAIN support for P and Q inverse hypothesis. The
    # relation is a frozen *candidate hypothesis*, not oracle truth.
    pooled=[[v["P"][i][j]+v["Q"][j][i] for j in range(16)] for i in range(16)]
    p=assign(pooled);q=invert(p);r=compose(p,p)
    joint={"P":m.pack(p),"Q":m.pack(q),"R":m.pack(r)}
    independent={role:m.pack(p) for role,p in independently.items()}
    return joint,independent,{"public_train_nibble_votes":sum(sum(map(sum,rows)) for rows in v.values()),
      "shared_constraint":"candidate structural P/Q inverse and R=P^2 hypothesis",
      "truth_source_not_read":True}
def score_public(m,prior,roles,witness,FIT,src):
    result=tuple(range(16))
    for name in roles:result=src.compose(result,m.unpack(prior[name]))
    return m.pack(result)
def main():
    frozen=json.loads((D/"20261019-mass-t16-freeze.json").read_text())
    assert frozen["source_blob"]=="b6b7a38f936043434b5d92b821bfe5d70dbb65fa"
    src=load(D/"20261019-mass-t16-source.py","m16src")
    m=load(D/"20261018-mass-t3-learned-sbox.py","m16m")
    t10=load(D/"20261019-mass-t10-shared-map.py","m16t10")
    t13=load(D/"20261019-mass-t13-mechanism.py","m16t13")
    train=[src.birth(i,m) for i in src.TRAIN]
    opens=[src.birth(i,m) for i in src.OPEN]
    (joint,independent,fitinfo),tcost=metered(lambda:learn(train,m))
    # Independently fitted strongest structure-aware control sees the SAME
    # public TRAIN records and declared structural hypothesis, and may tie.
    (strong,sourceblind,control_info),btrain=metered(lambda:learn(train,m))
    zero={role:m.pack(tuple(range(16))) for role in "PQR"}
    rows=[]
    for seed,(roles,FIT,CHECK,witness,held) in zip(src.OPEN,opens):
        p=score_public(m,joint,roles,witness,FIT,src)
        same=score_public(m,strong,roles,witness,FIT,src)
        indep=score_public(m,independent,roles,witness,FIT,src)
        base=score_public(m,zero,roles,witness,FIT,src)
        (candidate,diagnostics),ccost=metered(lambda:t13.refine(m,t10,p,FIT,CHECK,witness,"learned"))
        (structured,info),scost=metered(lambda:t13.refine(m,t10,same,FIT,CHECK,witness,"full_prior"))
        (empirical,einfo),ecost=metered(lambda:t13.refine(m,t10,indep,FIT,CHECK,witness,"full_prior"))
        (untrained,zinfo),zcost=metered(lambda:t13.refine(m,t10,base,FIT,CHECK,witness,"identity"))
        score=lambda prior:sum(m.forward(x,prior)==y for x,y in held)
        rows.append({"seed":seed,"candidate":score(candidate),"sourceblind_structural":score(structured),
          "independent_empirical":score(empirical),"untrained":score(untrained),
          "candidate_cpu_ns":ccost["cpu_ns"],"structured_cpu_ns":scost["cpu_ns"],
          "empirical_cpu_ns":ecost["cpu_ns"],
          "candidate_peak":ccost["python_peak_bytes"],
          "structured_peak":scost["python_peak_bytes"],
          "empirical_peak":ecost["python_peak_bytes"],
          "accepted_public_swaps":diagnostics["improving_swaps"]})
    total=lambda n:sum(z[n] for z in rows)
    out={"schema":"mass.t16.sourceblind-crossrole-structural-learning.v1",
      "TRAIN":len(train),"OPEN":len(opens),"PRIVATE_outputs":len(opens)*16,
      "learned_parameter_bytes":24,"TRAIN_public_fit":fitinfo,
      "candidate_correct":total("candidate"),
      "strong_structural_same_information_correct":total("sourceblind_structural"),
      "independent_TRained_empirical_correct":total("independent_empirical"),
      "untrained_control_correct":total("untrained"),
      "candidate_regressed_strongest_per_case":sum(1 for r in rows if r["candidate"]<
         max(r["sourceblind_structural"],r["independent_empirical"])),
      "candidate_amortized_CPU_ns":total("candidate_cpu_ns")+tcost["cpu_ns"]//len(opens),
      "strong_structural_CPU_ns":total("structured_cpu_ns")+btrain["cpu_ns"]//len(opens),
      "independent_empirical_CPU_ns":total("empirical_cpu_ns")+tcost["cpu_ns"]//len(opens),
      "candidate_training_inclusive_peak_bytes":max(tcost["python_peak_bytes"],max(z["candidate_peak"] for z in rows)),
      "structural_training_inclusive_peak_bytes":max(btrain["python_peak_bytes"],max(z["structured_peak"] for z in rows)),
      "empirical_training_inclusive_peak_bytes":max(tcost["python_peak_bytes"],max(z["empirical_peak"] for z in rows)),
      "public_query_service_resource_parity":False,
      "independent_source_custody":False,"signed_scientific_acceptance":False,
      "optimizer_admission":False,"cases":rows}
    assert total("candidate")<=128
    print(json.dumps(out,sort_keys=True))
if __name__=="__main__":main()

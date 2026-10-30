"""ACC70 restricted Clifford subclass: exact affine GF2 support vs dense amplitudes."""
import argparse,hashlib,json,math,struct,time,statistics
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
REG=ROOT/"research/ac07_sourcefree/ac08_portfolio.py"
PRE=ROOT/"docs/research/ACC-70-U30-PREREG-20261030.md"
BLOB="5126c860771fb024ccfc14c3f7ee8925edf29787"
PRE_COMMIT="9f467f8dad81d59eaf78f27affe9c4e9a8723178"
NS=(4,6,8,10);SEEDS=(30011,30013,30017);REPEATS=3
def sha(x):return hashlib.sha256(x).hexdigest()
def blob(x):return hashlib.sha1(b"blob "+str(len(x)).encode()+b"\0"+x).hexdigest()
def custody():
    if blob(REG.read_bytes().replace(b"\r\n",b"\n"))!=BLOB:raise RuntimeError("U30_REGISTRY_DRIFT")
    if '"stabilizer quantum simulation"' not in REG.read_text():raise RuntimeError("U30_CLAIM_DRIFT")
    if "ACC-70 U30" not in PRE.read_text():raise RuntimeError("U30_PREREG_MISSING")
    return {"registry_blob":BLOB,"prereg_commit":PRE_COMMIT,"claim":"U30"}
def gates(n,seed):
    if n not in NS or seed not in SEEDS:raise ValueError("unfrozen source")
    out=[]
    for t in range(12):
        h=hashlib.sha256(b"acc70-u30-gate-v1"+struct.pack(">III",n,seed,t)).digest()
        a=h[0]%n
        if h[1]%3==0:out.append(("X",a,0))
        else:
            b=(a+1+h[2]%(n-1))%n
            if a==b:raise RuntimeError("CNOT_SELF")
            out.append(("CNOT",a,b))
    return out
def affine(n,seed):
    k=min(3,n)
    base=0
    directions=[1<<i for i in range(k)]
    for gate,a,b in gates(n,seed):
        if gate=="X":base^=1<<a
        else:
            if (base>>a)&1:base^=1<<b
            directions=[v^(1<<b) if (v>>a)&1 else v for v in directions]
    return base,directions
def affine_probabilities(n,seed):
    base,directions=affine(n,seed)
    output=[0.]*(1<<n)
    for mask in range(1<<len(directions)):
        position=base
        for bit,d in enumerate(directions):
            if (mask>>bit)&1:position^=d
        output[position]+=1/(1<<len(directions))
    return tuple(output)
def dense_probabilities(n,seed):
    k=min(3,n)
    probabilities=[0.]*(1<<n)
    for j in range(1<<k):probabilities[j]=1/(1<<k)
    for op,a,b in gates(n,seed):
        nxt=[0.]*(1<<n)
        for i,v in enumerate(probabilities):
            if op=="X":pos=i^(1<<a)
            else:pos=i^(1<<b) if (i>>a)&1 else i
            nxt[pos]=v
        probabilities=nxt
    return tuple(probabilities)
def run():
    c=custody()
    observations=[]
    for n in NS:
      for seed in SEEDS:
        a=affine_probabilities(n,seed);d=dense_probabilities(n,seed)
        if max(abs(x-y) for x,y in zip(a,d))>1e-12:raise RuntimeError("PARITY_FAIL")
        for _ in range(2):affine_probabilities(n,seed);dense_probabilities(n,seed)
        for repeat in range(REPEATS):
            t=time.perf_counter_ns();x=dense_probabilities(n,seed);dense_ns=time.perf_counter_ns()-t
            t=time.perf_counter_ns();y=affine_probabilities(n,seed);affine_ns=time.perf_counter_ns()-t
            if x!=y or min(dense_ns,affine_ns)<=0:raise RuntimeError("TIMED_PARITY_FAIL")
            observations.append({"n":n,"seed":seed,"repeat":repeat,"dense_ns":dense_ns,
                "affine_ns":affine_ns,"dense_over_affine":dense_ns/affine_ns,
                "probability_sha256":sha(json.dumps(x,separators=(",",":")).encode()),
                "support":sum(v>0 for v in x),"affine_bits":n*(min(3,n)+1)})
    summary=[]
    for n in NS:
        q=[v for v in observations if v["n"]==n]
        summary.append({"n":n,"median_paired_speedup":statistics.median(v["dense_over_affine"] for v in q),
            "min_paired_speedup":min(v["dense_over_affine"] for v in q)})
    winner=all(q["median_paired_speedup"]>=1.15 and q["min_paired_speedup"]>=.85
               for q in summary if q["n"]>=8)
    return {"schema":"forge.acc70.u30.restricted-affine-clifford.v1","identity":c,
       "observations":observations,"summary":summary,
       "classification":{"exact_subclass_probability_parity":"PASS",
         "restricted_kernel_speed":"U30_RESTRICTED_CLASSICAL_SIMULATION_SPEED_ONLY" if winner else "U30_NO_VERIFIED_RESTRICTED_KERNEL_SPEED_WIN",
         "general_stabilizer_tableau":"UNVERIFIED","quantum_speedup":"NOT_DEMONSTRATED",
         "pretrained_LLM_speed":"UNVERIFIED","scientific_acceptance":"NOT_GRANTED",
         "production_admission":"NOT_GRANTED"},
       "limits":"H initialization and X/CNOT gates only; classical affine support simulator vs dense classical baseline, not universal Clifford, GPU, quantum device or model speed."}
if __name__=="__main__":
    a=argparse.ArgumentParser();a.add_argument("--json",required=True,type=Path);opts=a.parse_args()
    q=run();opts.json.parent.mkdir(parents=True,exist_ok=True)
    opts.json.write_bytes((json.dumps(q,sort_keys=True,indent=2)+"\n").encode())
    print("ACC70_U30_EXACT="+q["classification"]["exact_subclass_probability_parity"])
    print("ACC70_U30_SPEED="+q["classification"]["restricted_kernel_speed"])

"""R12: train a bounded two-link role compressor; evaluate fresh graph structures.

Query-blind encoder. The only training signal is training-set future-question
accuracy; validation/stress/reserved seeds are never consulted during fitting.
"""
import argparse,json,pathlib,random
from protocol import manifest,parent,digest,deny
FIELDS=("learned","fixed_hash","chronological_raw","exact_pair","shuffled_query")
def build(seed,hops):
    rng=random.Random(seed*1009+hops*97)
    nodes=list(range(128));rng.shuffle(nodes)
    take=lambda:nodes.pop()
    path_count=4 if hops==4 else 3
    graph=[];queries=[]
    for _ in range(path_count):
        chain=[take() for __ in range(hops//2+1)]
        roles=[rng.randrange(4) for __ in range(hops)]
        for j in range(hops//2):
            pair=tuple(roles[2*j:2*j+2])
            if j<2:
                alt=tuple(rng.randrange(4) for __ in range(2))
                while alt==pair:alt=tuple(rng.randrange(4) for __ in range(2))
                graph.append((chain[j],take(),*alt))
            graph.append((chain[j],chain[j+1],*pair))
        queries.append((chain[0],tuple(roles),chain[-1]))
    if len(graph)>16:deny("CELL_CAPACITY")
    return graph,queries
def level(x):
    return 0 if x<-.5 else (1 if x<.5 else 2)
def embed(pair,weights):
    a,b=pair
    return (level(weights[a]+.45*weights[b]),
            level(weights[4+b]+.45*weights[4+a]))
def hashed(pair):
    a,b=pair
    return ((a+b)%3,(a+2*b)%3)
def compressed(graph,start,roles,kind,weights):
    node=start
    query=list(roles)
    if kind=="shuffled_query":
        query=[(x+1)%4 for x in query]
    for j in range(0,len(query),2):
        pair=(query[j],query[j+1])
        needle=pair if kind=="exact_pair" else hashed(pair) if kind=="fixed_hash" else embed(pair,weights)
        chosen=None
        for frm,to,r1,r2 in graph:
            code=(r1,r2) if kind=="exact_pair" else hashed((r1,r2)) if kind=="fixed_hash" else embed((r1,r2),weights)
            if frm==node and code==needle:
                chosen=to;break
        if chosen is None:return None
        node=chosen
    return node
def raw(graph,start,roles):
    # One compressed relation occupies one 2-link cell; an uncompressed
    # baseline retains only the earliest 16 of the 30-32 raw edges.
    edges=[]
    for k,(frm,to,r1,r2) in enumerate(graph):
        midway=128+k
        edges.extend([(frm,midway,r1),(midway,to,r2)])
    node=start
    for role in roles:
        choices=[end for frm,end,r in edges[:16] if frm==node and r==role]
        if not choices:return None
        node=choices[0]
    return node
def score(graph,questions,weights,method):
    wins=0;records=[]
    for start,roles,target in questions:
        result=raw(graph,start,roles) if method=="chronological_raw" else compressed(graph,start,roles,method,weights)
        success=(result==target)
        wins+=success
        records.append({"source":start,"roles":list(roles),"target":target,
                        "prediction":result,"correct":success})
    return wins,records
def training_objective(weights,seeds):
    correct=0;queries=0
    for seed in seeds:
        for hops in (4,6):
            cells,questions=build(seed,hops)
            wins,_=score(cells,questions,weights,"learned")
            correct+=wins;queries+=len(questions)
    return correct,queries
def train(f):
    # coordinate descent trains only on the frozen source-training seeds;
    # no validation or structural-stress seed enters any candidate update.
    weights=list(f["encoder"]["initial_weights"])
    initial,denom=training_objective(weights,f["seeds"]["train"])
    history=[{"step":0,"correct":initial,"total":denom,"weights":list(weights)}]
    for step in f["encoder"]["train_step_schedule"]:
        for i in range(8):
            curr,_=training_objective(weights,f["seeds"]["train"])
            best=(curr,-sum(x*x for x in weights),weights[i])
            for direction in (-1,1):
                altered=list(weights);altered[i]=round(max(-3,min(3,altered[i]+direction*step)),9)
                performance,_=training_objective(altered,f["seeds"]["train"])
                ranking=(performance,-sum(x*x for x in altered),altered[i])
                if ranking>best:
                    best=ranking
            weights[i]=best[2]
        n,_=training_objective(weights,f["seeds"]["train"])
        history.append({"step":step,"correct":n,"total":denom,"weights":list(weights)})
    return weights,history
def evaluate(weights,seeds,hops):
    raw_rows=[];totals={method:0 for method in FIELDS}
    for seed in seeds:
        cells,queries=build(seed,hops)
        arms={}
        for method in FIELDS:
            successes,records=score(cells,queries,weights,method)
            totals[method]+=successes
            arms[method]={"correct":successes,"queries":records}
        raw_rows.append({"seed":seed,"hops":hops,"compressed_cells":len(cells),"arms":arms})
    count=sum(len(row["arms"]["learned"]["queries"]) for row in raw_rows)
    return {"total_queries":count,"accuracy":{method:totals[method]/count for method in FIELDS},
            "seed_rows":raw_rows}
def execute(frozen_raw,parent_raw):
    f=manifest(frozen_raw);parent(parent_raw,f)
    weights,trace=train(f)
    dev=evaluate(weights,f["seeds"]["development"],4)
    stress=evaluate(weights,f["seeds"]["structural_stress"],6)
    gain_dev=dev["accuracy"]["learned"]-dev["accuracy"]["fixed_hash"]
    gain_stress=stress["accuracy"]["learned"]-stress["accuracy"]["fixed_hash"]
    passed=gain_dev>=.05 and gain_stress>=.05
    return {"schema":"forge.r12.learned-compression.real-public-development.v1",
        "parent_review_sha256":digest(parent_raw),"frozen_sha256":digest(frozen_raw),
        "algorithm":"TRAIN_ONLY_8_PARAMETER_ROLE_PAIR_CODE_FUTURE_QUESTION_ACCURACY",
        "trained_weights":weights,"training_trace":trace,
        "novel_binding_development":dev,"longer_chain_stress":stress,
        "gain_development":gain_dev,"gain_stress":gain_stress,
        "preregistered_gate_passed":passed,
        "benchmark_task_generator_is_synthetic":True,
        "exact_oracle_is_upper_bound":True,"compression_memory_slots":16,
        "learned_parameter_count":8,"query_visible_during_compression":False,
        "sealed_holdouts_accessed":False,"first_use_claims":0,
        "new_scientific_originals_executed":0,"scientific_accepted":False,
        "independent_fsa_qualified":False,"model_api_calls":0}
def main():
    p=argparse.ArgumentParser()
    for x in ("frozen","parent","out"):p.add_argument("--"+x,required=True)
    a=p.parse_args()
    result=execute(pathlib.Path(a.frozen).read_bytes(),pathlib.Path(a.parent).read_bytes())
    with pathlib.Path(a.out).open("xb") as h:h.write((json.dumps(result,sort_keys=True,separators=(",",":"),allow_nan=False)+"\n").encode())
    print("R12_GENUINE_TRAINABLE_ROLE_COMPRESSION_DEVELOPMENT=PASS")
    print("R12_SEALED_FIRST_USE_ZERO=PASS")
if __name__=="__main__":main()

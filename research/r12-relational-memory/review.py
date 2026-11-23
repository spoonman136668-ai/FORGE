"""R12 independent science witness: regenerate all graphs, refit and retest.

No imports from the training worker/model. Same documented graph generator
is reimplemented independently to detect tampered outcomes and leakage.
"""
import argparse,json,math,pathlib,random
from protocol import manifest,parent,digest,parse,deny
ARMS=("learned","fixed_hash","chronological_raw","exact_pair","shuffled_query")
def graph_case(seed,hops):
    rand=random.Random(1009*seed+97*hops)
    available=list(range(128))
    rand.shuffle(available)
    cases=[];cells=[]
    for _ in range(4 if hops==4 else 3):
        vertices=[available.pop() for k in range(hops//2+1)]
        labels=[rand.randrange(4) for k in range(hops)]
        for k in range(hops//2):
            truth=(labels[2*k],labels[2*k+1])
            if k<2:
                false=(rand.randrange(4),rand.randrange(4))
                while false==truth:
                    false=(rand.randrange(4),rand.randrange(4))
                cells.append({"src":vertices[k],"dst":available.pop(),"rel":false})
            cells.append({"src":vertices[k],"dst":vertices[k+1],"rel":truth})
        cases.append({"start":vertices[0],"roles":labels,"target":vertices[-1]})
    if len(cells)>16:deny("REVIEW_MEMORY_OVERFLOW")
    return cells,cases
def quant(value):
    if value< -0.5:return 0
    if value<0.5:return 1
    return 2
def rolecode(pair,w):
    return (quant(w[pair[0]]+0.45*w[pair[1]]),
            quant(w[4+pair[1]]+0.45*w[4+pair[0]]))
def fixed(pair):
    return ((pair[0]+pair[1])%3,(pair[0]+2*pair[1])%3)
def reply(cells,query,weights,kind):
    node=query["start"]
    if kind=="chronological_raw":
        edges=[]
        for idx,s in enumerate(cells):
            mid=128+idx
            edges.append((s["src"],mid,s["rel"][0]))
            edges.append((mid,s["dst"],s["rel"][1]))
        for relation in query["roles"]:
            next_node=None
            for frm,dst,role in edges[:16]:
                if frm==node and role==relation:
                    next_node=dst;break
            if next_node is None:return None
            node=next_node
        return node
    roles=query["roles"]
    if kind=="shuffled_query":roles=[(r+1)%4 for r in roles]
    for i in range(0,len(roles),2):
        pattern=(roles[i],roles[i+1])
        lookup=pattern if kind=="exact_pair" else fixed(pattern) if kind=="fixed_hash" else rolecode(pattern,weights)
        dst=None
        for s in cells:
            key=s["rel"] if kind=="exact_pair" else fixed(s["rel"]) if kind=="fixed_hash" else rolecode(s["rel"],weights)
            if s["src"]==node and key==lookup:
                dst=s["dst"];break
        if dst is None:return None
        node=dst
    return node
def train_count(weights,training_seeds):
    hit=0;total=0
    for seed in training_seeds:
        for hops in (4,6):
            cells,questions=graph_case(seed,hops)
            for query in questions:
                hit+=reply(cells,query,weights,"learned")==query["target"]
                total+=1
    return hit,total
def refit(plan):
    w=list(plan["encoder"]["initial_weights"])
    n,denom=train_count(w,plan["seeds"]["train"])
    log=[{"step":0,"correct":n,"total":denom,"weights":list(w)}]
    for delta in plan["encoder"]["train_step_schedule"]:
        for i in range(8):
            best_score,_=train_count(w,plan["seeds"]["train"])
            old=w[i]
            best=(best_score,-sum(v*v for v in w),old)
            for sign in (-1,1):
                trial=w.copy()
                trial[i]=round(max(-3,min(3,old+sign*delta)),9)
                n,_=train_count(trial,plan["seeds"]["train"])
                candidate=(n,-sum(v*v for v in trial),trial[i])
                if candidate>best:best=candidate
            w[i]=best[2]
        n,_=train_count(w,plan["seeds"]["train"])
        log.append({"step":delta,"correct":n,"total":denom,"weights":list(w)})
    return w,log
def verify_data(rows,plan,weights,cohort,hops):
    seeds=plan["seeds"][cohort]
    if not isinstance(rows,dict) or set(rows.get("accuracy",{}))!=set(ARMS):deny("REVIEW_MISSING_CONTROLS")
    given=rows.get("seed_rows")
    if not isinstance(given,list) or len(given)!=len(seeds):deny("REVIEW_COHORT_SIZE")
    totals={key:0 for key in ARMS}
    nq=0
    for number,reported in zip(seeds,given):
        cells,questions=graph_case(number,hops)
        if reported.get("seed")!=number or reported.get("hops")!=hops or reported.get("compressed_cells")!=len(cells):deny("REVIEW_SEED_DRIFT")
        reported_arms=reported.get("arms",{})
        if set(reported_arms)!=set(ARMS):deny("REVIEW_ARM_DRIFT")
        for kind in ARMS:
            got=reported_arms[kind]
            entries=got.get("queries")
            if not isinstance(entries,list) or len(entries)!=len(questions):deny("REVIEW_QUERY_ROWS")
            passed=0
            for expected,record in zip(questions,entries):
                pred=reply(cells,expected,weights,kind)
                correct=(pred==expected["target"])
                if (record.get("source")!=expected["start"] or record.get("roles")!=expected["roles"]
                    or record.get("target")!=expected["target"] or
                    record.get("prediction")!=pred or record.get("correct") is not correct):
                    deny("REVIEW_VARIABLE_BINDING_PREDICTION")
                passed+=correct
            if got.get("correct")!=passed:deny("REVIEW_CASE_TOTAL")
            totals[kind]+=passed
        nq+=len(questions)
    if rows.get("total_queries")!=nq:deny("REVIEW_SAMPLE_COUNT")
    for kind in ARMS:
        if not math.isclose(rows["accuracy"][kind],totals[kind]/nq,rel_tol=0,abs_tol=1e-12):
            deny("REVIEW_ACCURACY")
    return {"query_count":nq,"accuracy":dict(rows["accuracy"]),"role_shuffle_degraded":rows["accuracy"]["shuffled_query"]<rows["accuracy"]["exact_pair"]}
def audit(frozen_raw,parent_raw,measurement_raw):
    plan=manifest(frozen_raw);parent(parent_raw,plan)
    if len(measurement_raw)>600000:deny("REVIEW_MEASUREMENT_SIZE")
    m=parse(measurement_raw,cap=600000)
    if (m.get("schema")!="forge.r12.learned-compression.real-public-development.v1" or
        m.get("parent_review_sha256")!=digest(parent_raw) or m.get("frozen_sha256")!=digest(frozen_raw)
        or m.get("algorithm")!="TRAIN_ONLY_8_PARAMETER_ROLE_PAIR_CODE_FUTURE_QUESTION_ACCURACY"
        or m.get("benchmark_task_generator_is_synthetic") is not True
        or m.get("exact_oracle_is_upper_bound") is not True
        or m.get("compression_memory_slots")!=16 or m.get("learned_parameter_count")!=8
        or m.get("query_visible_during_compression") is not False
        or m.get("sealed_holdouts_accessed") is not False
        or m.get("first_use_claims")!=0 or m.get("new_scientific_originals_executed")!=0
        or m.get("scientific_accepted") is not False
        or m.get("independent_fsa_qualified") is not False
        or m.get("model_api_calls")!=0):deny("REVIEW_FALSE_AUTHORITY")
    trained,history=refit(plan)
    if m.get("trained_weights")!=trained or m.get("training_trace")!=history:
        deny("REVIEW_LEARNING_NOT_REPRODUCIBLE")
    base=verify_data(m.get("novel_binding_development"),plan,trained,"development",4)
    stress=verify_data(m.get("longer_chain_stress"),plan,trained,"structural_stress",6)
    gd=base["accuracy"]["learned"]-base["accuracy"]["fixed_hash"]
    gs=stress["accuracy"]["learned"]-stress["accuracy"]["fixed_hash"]
    passed=(gd>=.05 and gs>=.05)
    if (not math.isclose(m.get("gain_development"),gd,abs_tol=1e-12,rel_tol=0)
        or not math.isclose(m.get("gain_stress"),gs,abs_tol=1e-12,rel_tol=0)
        or m.get("preregistered_gate_passed") is not passed):
        deny("REVIEW_PREDECLARED_OUTCOME")
    if (base["accuracy"]["exact_pair"]<base["accuracy"]["learned"] or
        stress["accuracy"]["exact_pair"]<stress["accuracy"]["learned"]):
        deny("REVIEW_ORACLE_VIOLATION")
    return {"schema":"forge.r12.independent-compositional-memory-review.v1",
        "reviewed_measurement_sha256":digest(measurement_raw),
        "parent_r11_negative_sha256":digest(parent_raw),
        "actual_training_independently_recomputed":True,
        "every_variable_binding_result_recomputed":True,
        "training_has_no_test_or_sealed_queries":True,
        "role_code_trainable_parameters":8,"memory_slots":16,
        "development":base,"unseen_longer_chains":stress,
        "development_gain":gd,"stress_gain":gs,"preregistered_development_passed":passed,
        "symbolic_exact_oracle_control_present":True,
        "benchmark_evidence_is_synthetic":True,
        "native_relationship_reasoning_proven":False,
        "scientific_originals_executed":0,"first_use_claims":0,
        "sealed_holdouts_accessed":False,"independent_fsa_qualified":False,
        "scientific_accepted":False,"paid_api_calls":0}
def main():
    p=argparse.ArgumentParser()
    for key in ("frozen","parent","measurement","out"):p.add_argument("--"+key,required=True)
    a=p.parse_args()
    result=audit(pathlib.Path(a.frozen).read_bytes(),
                 pathlib.Path(a.parent).read_bytes(),
                 pathlib.Path(a.measurement).read_bytes())
    with pathlib.Path(a.out).open("xb") as f:
        f.write((json.dumps(result,sort_keys=True,indent=2,allow_nan=False)+"\n").encode())
    print("R12_INDEPENDENT_TRAIN_REPLAY_AND_VARIABLE_BINDING_VERIFICATION=PASS")
    print("R12_FIRST_USE_ZERO=PASS")
if __name__=="__main__":main()

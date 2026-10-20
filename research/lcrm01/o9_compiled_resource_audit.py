"""O9 exact provider-native resource audit; raw original samples immutable.

Source-free; zero scientific or optimizer acceptance. A zero Windows CPU
sample is censored (clock quantization), not "zero-cost" and never PASS.
"""
import json, statistics, sys
from pathlib import Path

ARMS=("compiled-version-space","independent-symbolic","original-anf")
SCHEMA="forge.lcrm01.o9.sourcefree-native-process.v1"

def audit(file_path):
    rows=[json.loads(line) for line in Path(file_path).read_text(encoding="utf-8-sig").splitlines() if line.strip()]
    if len(rows)!=15:raise ValueError("O9_WRONG_COMPLETE_PROCESS_COUNT")
    group={}
    for arm in ARMS:
        xs=sorted((r for r in rows if r.get("arm")==arm),key=lambda x:x["rep"])
        if len(xs)!=5 or [x["rep"] for x in xs]!=list(range(5)):
            raise ValueError("O9_MISSING_PROCESS:"+arm)
        for x in xs:
            if (x.get("schema")!=SCHEMA or x["episodes"]!=15360 or x["do_queries"]!=122880
                or x["hard_certified"]+x["safe_abstentions"]!=122880
                or x["hard_false_positives"]!=0 or x["process_cpu_ns"]<0
                or x["peak_rss_bytes"]<=0 or x["wall_elapsed_ns"]<=0
                or x["native_cpu_clock_censored"]!=(x["process_cpu_ns"]==0)
                or x.get("source_first_use") or x.get("scientific_accepted")
                or x.get("optimizer_admitted")):
                raise ValueError("O9_INVALID_EXACT_PROCESS_RESULT:"+arm)
        statuses={(x["digest"],x["hard_certified"],x["safe_abstentions"]) for x in xs}
        if len(statuses)!=1:raise ValueError("O9_INTRA_ARM_CAUSAL_DRIFT:"+arm)
        group[arm]={
            "process_cpu_ns":[x["process_cpu_ns"] for x in xs],
            "process_wall_ns":[x["wall_elapsed_ns"] for x in xs],
            "process_peak_rss_bytes":[x["peak_rss_bytes"] for x in xs],
            "median_cpu_ns":int(statistics.median(x["process_cpu_ns"] for x in xs)),
            "max_peak_rss_bytes":max(x["peak_rss_bytes"] for x in xs),
            "cpu_clock_censored":any(x["native_cpu_clock_censored"] for x in xs),
            "hard_certified":xs[0]["hard_certified"],
            "safe_abstentions":xs[0]["safe_abstentions"],
            "digest":xs[0]["digest"]
        }
    control=group["independent-symbolic"]
    for arm,v in group.items():
        for key in ("digest","hard_certified","safe_abstentions"):
            if v[key]!=control[key]:
                raise ValueError("O9_CAUSAL_SEMANTICS_PEER_DIVERGENCE:"+arm+":"+key)
    candidate=group["compiled-version-space"]
    clock_valid=not any(g["cpu_clock_censored"] for g in group.values())
    cpu_equal_or_better=clock_valid and candidate["median_cpu_ns"]<=control["median_cpu_ns"]
    rss_equal_or_better=candidate["max_peak_rss_bytes"]<=control["max_peak_rss_bytes"]
    strict=clock_valid and (candidate["median_cpu_ns"]<control["median_cpu_ns"] or
        candidate["max_peak_rss_bytes"]<control["max_peak_rss_bytes"])
    return {
        "schema":"forge.lcrm01.o9.sourcefree-three-arm-native-comparison.v1",
        "classification":"SOURCE_FREE_MATHEMATICAL_NATIVE_RESOURCE_ONLY",
        "arms":group,"all_arms_semantic_parity":True,
        "native_cpu_clock_uncensored":clock_valid,
        "compiled_vs_symbolic_cpu_nonregression":cpu_equal_or_better,
        "compiled_vs_symbolic_rss_nonregression":rss_equal_or_better,
        "strict_native_cost_benefit":strict,
        "technical_cost_admission":bool(cpu_equal_or_better and rss_equal_or_better and strict),
        "source_first_use":False,"actual_exogenous_provenance_authenticated":False,
        "fully_trained_recurrent_or_relational_peer":False,
        "out_of_grammar_transfer":False,
        "scientific_acceptance":False,"optimizer_admission":False,
        "merge_authorized":False,"retained_processes":len(rows)
    }

if __name__=="__main__":
    if len(sys.argv)!=2:raise SystemExit("O9_EXPECT_SAMPLES_NDJSON")
    print(json.dumps(audit(sys.argv[1]),sort_keys=True))

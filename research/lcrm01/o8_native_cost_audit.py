"""O8 identity-safe aggregation. One row per independent provider-native process.
Scientific / optimizer admission always false: this is SOURCE-FREE cost evidence.
"""
import json,statistics,sys
from pathlib import Path

def fail(s):
    raise RuntimeError("LCRM_O8_"+s)

def run(path):
    raw=Path(path).read_text(encoding="utf-8-sig")
    rows=[json.loads(line) for line in raw.splitlines() if line.strip()]
    arms=("learned-anf","exact-symbolic")
    if len(rows)!=10:fail("INVALID_PROCESS_COUNT")
    per={}
    for arm in arms:
        group=sorted((x for x in rows if x.get("arm")==arm),key=lambda x:x["rep"])
        if len(group)!=5 or [x.get("rep") for x in group]!=list(range(5)):
            fail("INVALID_PROCESS_REPETITIONS_"+arm)
        for r in group:
            if (r.get("schema")!="forge.lcrm01.o8.sourcefree-native-matched-process.v1" or
                r.get("cases")!=6144 or r.get("do_queries")!=49152 or
                r.get("hard_false_positives")!=0 or
                r["hard_certified"]+r["abstentions"]!=49152 or
                r["complete_process_cpu_ns"]<=0 or r["peak_rss_bytes"]<=0 or
                r.get("source_first_use") or r.get("scientific_accepted") or
                r.get("optimizer_admitted")):
                fail("PROCESS_EVIDENCE_INVALID_"+arm)
        stable={(x["output_digest"],x["hard_certified"],x["abstentions"]) for x in group}
        if len(stable)!=1:fail("INTRA_ARM_SEMANTIC_DRIFT_"+arm)
        per[arm]={
          "correct_certificates":group[0]["hard_certified"],
          "safe_abstentions":group[0]["abstentions"],
          "output_digest":group[0]["output_digest"],
          "cpu_samples_ns":[x["complete_process_cpu_ns"] for x in group],
          "rss_samples_bytes":[x["peak_rss_bytes"] for x in group],
          "median_cpu_ns":int(statistics.median(x["complete_process_cpu_ns"] for x in group)),
          "maximum_peak_rss_bytes":max(x["peak_rss_bytes"] for x in group)}
    for key in ("correct_certificates","safe_abstentions","output_digest"):
        if per[arms[0]][key]!=per[arms[1]][key]:
            fail("STRONG_SYMBOLIC_PARITY_FAIL_"+key)
    a,b=per[arms[0]],per[arms[1]]
    verdict={
      "cpu_nonregression":a["median_cpu_ns"]<=b["median_cpu_ns"],
      "rss_nonregression":a["maximum_peak_rss_bytes"]<=b["maximum_peak_rss_bytes"],
      "cpu_strict_benefit":a["median_cpu_ns"]<b["median_cpu_ns"],
      "rss_strict_benefit":a["maximum_peak_rss_bytes"]<b["maximum_peak_rss_bytes"]}
    return {"schema":"forge.lcrm01.o8.sourcefree-native-cost-comparison.v1",
       "state":"SOURCE_FREE_OS_NATIVE_ENGINEERING_ONLY",
       "arms":per,"comparison":verdict,
       "technical_native_admission":verdict["cpu_nonregression"] and verdict["rss_nonregression"],
       "scientific_acceptance":False,"optimizer_admission":False,
       "external_anchor_provenance_authenticated":False,
       "independent_source_first_use":False,
       "fully_trained_recurrent_relational_peers_tested":False,
       "adversarial_unseen_law_transfer_proven":False,
       "required_final_integration_regression_eligible":False,
       "retained_original_process_count":len(rows)}
if __name__=="__main__":
    if len(sys.argv)!=2:fail("USAGE")
    d=run(sys.argv[1])
    print(json.dumps(d,sort_keys=True))

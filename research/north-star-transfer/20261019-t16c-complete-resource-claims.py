"""T16-C read-only prospective resource comparison.

A numerical resource comparison is not independent source authentication,
scientific acceptance, a first-use permit or optimizer admission.
No prospective source or private holdout is instantiated in this module.
"""
from dataclasses import dataclass
import json
import sys
from pathlib import Path

REQUIRED_FIELDS=(
    "name","train_cpu_ns","eval_cpu_ns","validation_cpu_ns","source_queries_cpu_ns",
    "source_queries_count","train_peak_rss_bytes","eval_peak_rss_bytes",
    "validation_peak_rss_bytes","train_tasks","open_tasks",
    "public_train_sha256","public_open_sha256","measurement_environment_sha256",
    "correct_held_outputs","baseline_positive_regressions","hard_false_positives"
)
METRIC_FIELDS=REQUIRED_FIELDS[1:12]+(
    "correct_held_outputs","baseline_positive_regressions","hard_false_positives"
)

def valid_sha(d):
    return type(d) is str and len(d)==64 and all(c in "0123456789abcdef" for c in d)

@dataclass(frozen=True)
class Cost:
    name:str
    train_cpu_ns:int
    eval_cpu_ns:int
    validation_cpu_ns:int
    source_queries_cpu_ns:int
    source_queries_count:int
    train_peak_rss_bytes:int
    eval_peak_rss_bytes:int
    validation_peak_rss_bytes:int
    train_tasks:int
    open_tasks:int
    public_train_sha256:str
    public_open_sha256:str
    measurement_environment_sha256:str
    correct_held_outputs:int
    baseline_positive_regressions:int
    hard_false_positives:int

    @classmethod
    def parse(cls,raw):
        if type(raw) is not dict or set(raw)!=set(REQUIRED_FIELDS):
            raise ValueError("T16C_COMPLETE_COST_SCHEMA_REQUIRED")
        numeric=REQUIRED_FIELDS[1:12]+REQUIRED_FIELDS[-3:]
        if any(type(raw[x]) is not int or raw[x]<0 for x in numeric):
            raise ValueError("T16C_NONNEGATIVE_INT_METRICS_REQUIRED")
        for fld in ("public_train_sha256","public_open_sha256","measurement_environment_sha256"):
            if not valid_sha(raw[fld]):raise ValueError("T16C_FROZEN_PUBLIC_IDENTITY_REQUIRED")
        if not raw["name"] or type(raw["name"]) is not str:
            raise ValueError("T16C_NAMED_CONTROL_REQUIRED")
        if raw["train_tasks"]==0 or raw["open_tasks"]==0:
            raise ValueError("T16C_NONZERO_TASKS_REQUIRED")
        if min(raw["train_peak_rss_bytes"],raw["eval_peak_rss_bytes"],
               raw["validation_peak_rss_bytes"])==0:
            raise ValueError("T16C_TRUE_RSS_REQUIRED")
        return cls(**raw)

    def amortized_cpu(self):
        # TRAIN amortization is a batch-level complete cost, not a free asset.
        return (self.train_cpu_ns+self.eval_cpu_ns+self.validation_cpu_ns
                +self.source_queries_cpu_ns)
    def peak_rss(self):
        return max(self.train_peak_rss_bytes,self.eval_peak_rss_bytes,
                   self.validation_peak_rss_bytes)

def resource_review(candidate_raw,strong_controls_raw):
    candidate=Cost.parse(candidate_raw)
    if type(strong_controls_raw) is not list or not strong_controls_raw:
        raise ValueError("T16C_STRONG_CONTROLS_REQUIRED")
    controls=[Cost.parse(x) for x in strong_controls_raw]
    identities={
      (x.public_train_sha256,x.public_open_sha256,
       x.measurement_environment_sha256,x.train_tasks,x.open_tasks)
      for x in [candidate]+controls
    }
    if len(identities)!=1:raise ValueError("T16C_NOT_EQUAL_SOURCE_OR_MEASUREMENT")
    if len({x.name for x in controls})!=len(controls):
        raise ValueError("T16C_DUPLICATE_STRONG_CONTROL")
    if candidate.name in {x.name for x in controls}:
        raise ValueError("T16C_CONTROL_ALIAS")
    # Different benchmark machines, replay sources, or unmeasured service
    # calls all fail the contract. Equal or lower CPU/RSS must hold for
    # EVERY eligible trained and symbolic control, not just a weak baseline.
    comparisons=[]
    for c in controls:
        comparisons.append({
          "control":c.name,
          "strict_accuracy_gain":candidate.correct_held_outputs>c.correct_held_outputs,
          "no_baseline_regressions":candidate.baseline_positive_regressions==0,
          "no_hard_false_positives":candidate.hard_false_positives==0,
          "cpu_nonregression":candidate.amortized_cpu()<=c.amortized_cpu(),
          "rss_nonregression":candidate.peak_rss()<=c.peak_rss(),
          "public_query_count_nonregression":candidate.source_queries_count<=c.source_queries_count,
          "candidate_complete_cpu_ns":candidate.amortized_cpu(),
          "control_complete_cpu_ns":c.amortized_cpu(),
          "candidate_complete_peak_rss_bytes":candidate.peak_rss(),
          "control_complete_peak_rss_bytes":c.peak_rss()
        })
    parity=all(v["cpu_nonregression"] and v["rss_nonregression"] and
               v["public_query_count_nonregression"] for v in comparisons)
    strict=all(v["strict_accuracy_gain"] for v in comparisons)
    no_wrong=(candidate.baseline_positive_regressions==0 and
              candidate.hard_false_positives==0)
    return {
      "schema":"northstar.t16c.complete-resource-claim-audit.v1",
      "classification":"UNTRUSTED_NUMERIC_CLAIM_NOT_ADMITTED",
      "control_count":len(controls),
      "source_and_measurement_identity_fields_match":True,
      "mathematical_complete_cost_parity_claim":parity,
      "mathematical_heldout_gain_claim":strict,
      "no_reported_wrong_or_baseline_regressions":no_wrong,
      "comparisons":comparisons,
      "independent_source_origination_authenticated":False,
      "signed_source_birth_verified":False,
      "first_use_highwater_custody_reconciled":False,
      "resource_instrumentation_attested":False,
      "independent_reproduction_verified":False,
      "original_execution_authorized":False,
      "scientific_accepted":False,
      "optimizer_admitted":False,
      "merge_authorized":False
    }

def main():
    if len(sys.argv)!=2:
        print(json.dumps({"schema":"northstar.t16c.complete-resource-claim-audit.v1",
          "status":"NO_PROSPECTIVE_EVIDENCE_ADMITTED","original_execution_authorized":False,
          "scientific_accepted":False,"optimizer_admitted":False},sort_keys=True))
        return
    data=json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    if set(data)!={"candidate","strong_controls"}:
        raise ValueError("T16C_INPUT_SCHEMA_DRIFT")
    print(json.dumps(resource_review(data["candidate"],data["strong_controls"]),sort_keys=True))

if __name__=="__main__":main()

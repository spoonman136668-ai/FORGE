"""Q21 authorized-call-only source-free FIT/DEV resource accounting.

No import-side experiments and no standalone development CLI. A separate
controller must authenticate any prospective development execution before
calling execute_development; this module does not grant admission.
"""
import json
import sourcefree as src
import evaluator
import resource_meter as res

ROLES=("FIT_TRAIN","FIT_VALID","DEV")

def sealed(doc):
    authentic=src.protocol()
    src.require(doc==authentic,"FROZEN_PROTOCOL_DRIFT")
    return authentic

def measured(name, operation):
    initial=res.snapshot()
    value=operation()
    # Serialization is actual computational work. It must occur before the
    # closing CPU/I/O/RSS snapshot, otherwise the measured stage silently
    # omits its own evidence-payload encoding. No bytes are persisted here.
    payload=res.canonical_payload_size(value)
    final=res.snapshot()
    evidence=res.measured_delta(initial,final,name)
    evidence["payload"]=payload
    evidence["communication"]=res.communication_receipt("none")
    evidence["rss_scope"]="PROCESS_CUMULATIVE_HIGH_WATER_NOT_ISOLATED_PER_MODEL"
    return value,evidence

def acquire_public_roles(family, doc):
    """Prospective source-free *development* acquisition, never auto-invoked."""
    doc=sealed(doc)
    src.require(family in src.FAMILIES,"UNAUTHORIZED_FAMILY")
    def generate_public():
        roles={}
        for role in ROLES:
            episodes=[]
            for index in range(src.ROLE_COUNTS[role]):
                row, _secret=src.generate(role,family,index,doc)
                episodes.append(row)
            roles[role]=src.public_rows(episodes)
        return roles
    return measured("sourcefree_generation_"+family,generate_public)

def execute_development(doc):
    """Must only be invoked after existing external controller authorizes.

    No source-first-use, protected heldouts, network or controller actions.
    This function is not itself a means to authorize execution.
    """
    doc=sealed(doc)
    first=res.snapshot()
    families={}
    for family in src.FAMILIES:
        public_roles, generation_receipt=acquire_public_roles(family,doc)
        evaluated, evaluation_receipt=measured(
            "full_fit_validation_dev_"+family,
            lambda:evaluator.evaluate_one_family(public_roles,family,doc))
        families[family]={"observed_metrics":evaluated,
                          "source_generation_resources":generation_receipt,
                          "fit_and_dev_resources":evaluation_receipt}
    preliminary=evaluator.preliminary_decision(
        {name:info["observed_metrics"] for name,info in families.items()},doc)
    total=res.measured_delta(first,res.snapshot(),"complete_Q21_development")
    report={"schema":"forge.q21.complete-sourcefree-resource.v1",
            "frozen_protocol_blob":src.PROTOCOL_BLOB,
            "families":families,
            "frozen_preliminary_decision":preliminary,
            "whole_process_resources":total,
            "role_counts_per_family":dict(src.ROLE_COUNTS),
            "process_peak_rss_isolated_per_model":False,
            "communication":res.communication_receipt("none"),
            "scientific_admission":"NOT_GRANTED_BY_THIS_MODULE",
            "protected_heldout_or_original_first_use":False}
    report["receipt_storage"]=res.canonical_payload_size(report)
    return report

def preflight():
    sealed(src.protocol())
    return {"status":"Q21_SOURCEFREE_EXECUTION_CALLABLE_READY",
            "development_generation":"NOT_PERFORMED",
            "fit_validation_dev":"NOT_PERFORMED",
            "original_scientific_first_use":False}

if __name__=="__main__":
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument("--mode",required=True,choices=("preflight",))
    parser.parse_args()
    print("Q21_COMPLETE_RUNNER_PREFLIGHT="+json.dumps(preflight(),sort_keys=True))

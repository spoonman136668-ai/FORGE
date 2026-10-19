"""T2 optimizer native-admission readiness: authentic evidence absence is BLOCKED.

Read only the existing staged source-verified negative manifest; enforce it
cannot become signed LaneEvidence or a randomized prospective audit. No
controller, scheduler, optimizer selection or protected source is invoked.
"""
from __future__ import annotations
import importlib.util,json,sys
from pathlib import Path

HERE=Path(__file__).resolve().parent
EVIDENCE=HERE/"20261018-source-verified-outcomes-staged-not-admitted.json"
FREEZE=HERE/"20261018-optimizer-t2-source-freeze.json"
MODEL=HERE/"20261018-optimizer-learned-kernel.py"
def need(ok,tag):
    if not ok:raise ValueError("OPT_T2_"+tag)
def load():
    spec=importlib.util.spec_from_file_location("t2_opt",MODEL)
    mod=importlib.util.module_from_spec(spec)
    sys.modules[spec.name]=mod;spec.loader.exec_module(mod)
    return mod

def attest():
    freeze=json.loads(FREEZE.read_text())
    evidence=json.loads(EVIDENCE.read_text())
    need(freeze["schema"]=="northstar.t2.optimizer.source-qualified-trial-readiness.v1"
         and freeze["source_anchor_head"]=="ad2e1b2d39d139a4318934af31fc3a603196833e"
         and freeze["authority"]["optimizer_dispatch"] is False,
         "SOURCE_FROZEN")
    need(evidence["schema"]=="forge.research-transfer.existing-optimizerbridge-read-only-staging.v1"
         and evidence["state"]=="SOURCE_VERIFIED_NEGATIVES_STAGED_NOT_ADMITTED"
         and evidence["positive_transfer_outcomes"]==[]
         and all(x["optimizer_admitted"] is False
                 and x["independent_signature_verified"] is False
                 for x in evidence["outcomes"]),
         "CANNOT_ADMIT_UNAUTHENTICATED_NEGATIVE_HISTORY")
    model=load()
    try:model.authorize_optimizer(evidence)
    except ValueError as ex:
        need("SIGNED_EVIDENCE" in str(ex),"EXISTING_NATIVE_AUTHORITY_REQUIRED")
    else:raise AssertionError("native optimizer must fail closed")
    return {"schema":"forge.t2.optimizer-native-readiness.v1",
            "provider_source_negative_observations":len(evidence["outcomes"]),
            "independently_signed_LaneEvidence":0,
            "randomized_assignment_proof":0,
            "authenticated_positive_unseen_transfer":0,
            "existing_optimizerbridge_native_path_needed":True,
            "read_only_shadow_learning_possible":False,
            "real_prospective_randomization_admitted":False,
            "optimizer_promotion":False,"production":False,
            "scientific_first_use":False,"readiness":"BLOCKED_AUTHENTIC_PROVENANCE"}
if __name__=="__main__":print(json.dumps(attest(),sort_keys=True))

"""T4 FORGE optimizer real-evidence trainability gate — intentionally blocked.

A synthetic 4-byte scorer is not proof of optimizer learning on authentic
independent transfer results. No signed/replicated positive observations or
randomized scientific propensities are present in the existing intake.
Fail closed; never pass historical provider negatives to model.fit as wins.
"""
from __future__ import annotations
import json,subprocess,importlib.util,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
FROZEN=HERE/"20261018-optimizer-t4-frozen-train-only.json"
EVIDENCE=HERE/"20261018-source-verified-outcomes-staged-not-admitted.json"
BRIDGE=ROOT/"optimizerbridge/bridge.go"
FREEZE=ROOT/"optimizerbridge/prospective_freeze.go"
AUDIT=ROOT/"optimizerbridge/selection_audit.go"
def need(x,n):
    if not x:raise ValueError("OPT_T4_"+n)
def blob(path):
    return subprocess.run(["git","hash-object",str(path)],
       cwd=ROOT,capture_output=True,check=True,text=True).stdout.strip()
def attest():
    freeze=json.loads(FROZEN.read_text())
    e=json.loads(EVIDENCE.read_text())
    need(freeze["schema"]=="research.northstar.t4.train-only-learning-resource-parity.v1"
         and freeze["frozen_parent_head"]=="d1e9b51ae2a6ba3620bbb729a3ff5da0d64ceb8e"
         and freeze["optimizer_dispatch"] is False,"FROZEN_NO_DISPATCH")
    need(blob(BRIDGE)=="04e275423fc44d86b31d2fa210ae8e285bf52faa"
         and blob(FREEZE)=="a8fe50a52df3f25fb0f8b53cd63052cf4a23d409"
         and blob(AUDIT)=="48810d9935b0cfd119991b22300cbaa783bd9adb",
         "QUALIFIED_NATIVE_BRIDGE_MUST_NOT_CHANGE")
    need(e["state"]=="SOURCE_VERIFIED_NEGATIVES_STAGED_NOT_ADMITTED"
         and len(e["outcomes"])==3 and e["positive_transfer_outcomes"]==[]
         and all(not x["independent_signature_verified"]
                 and not x["optimizer_admitted"] for x in e["outcomes"]),
         "NEVER_TRAIN_ON_UNSIGNED_NEGATIVES")
    return {"schema":"forge.optimizer.t4.admission-and-learning.v1",
       "historical_source_proven_negatives":len(e["outcomes"]),
       "independently_signed_transfer_positives":0,
       "valid_randomized_prospective_assignments":0,
       "authenticated_eligible_training_pairs":0,
       "model_training_performed":False,
       "cannot_claim_learned_transfer_utility":True,
       "original_Dream_RSI_Pareto_protected":True,
       "full_resource_parity_measured":False,
       "original_research_protected_sources_consumed":0,
       "no_CKB_plane_dependency":True,
       "real_world_dispatch_enabled":False,
       "scientific_acceptance":False,
       "disposition":"BLOCKED_MISSING_SIGNED_AND_REPLICATED_TRANSFER_EVIDENCE"}
if __name__=="__main__":print(json.dumps(attest(),sort_keys=True))

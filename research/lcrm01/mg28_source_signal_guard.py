#!/usr/bin/env python3
"""MG28 frozen dual-native source-mechanism authorization guard.

Only checks pinned retrospective MG27 evidence and source-only obligations.
Does not execute any MiniGrid reset, native policy, new seed or training.
"""
import copy,hashlib,json
from pathlib import Path

HERE=Path(__file__).resolve().parent
PROTOCOL=HERE/"mg28_independent_native_source_change_prereg.json"
EXPECTED="itd02.mg28.independent-native-onpolicy-public-change.v1"
PARENT="4134f8fb268d78fdd527a1c67f1974ae77977252"
RESULT="ef7e420985078371752fcb42abfb05342abadfc9721411de6cedf5993c8a3534"

def frozen(p):
    if (type(p) is not dict or p.get("schema")!=EXPECTED or
        p.get("phase")!="PROSPECTIVE_FROZEN_SOURCE_ONLY_NO_NEW_WORLD_FIRST_USE" or
        p["parents"]["FORGE_MG27"]!=PARENT or
        p["parents"]["FORGE_MG27_RECEIPT_SHA256"]!=RESULT or
        p["parents"]["Wingless_MG23"]!="f4b29adfac260150e7ed83b37f69ee9f0371056f" or
        p["parents"]["Yggdrasil_MG23"]!="a052b06b010ec9e61e4a46e0d57f544a76590c33" or
        p["parents"]["Farama"]!="7f5853792ea7f04f75614661006d87fcf949f26d" or
        p["prior_proof"]["native_steps"]!=2033 or
        p["prior_proof"]["original_supported"]!=836 or
        p["prior_proof"]["permuted_matched"]!=671 or
        p["native_design"]["source_fields"]!=["image","direction","mission"] or
        p["native_design"]["max_samples"]!=4096 or
        p["native_design"]["max_contexts"]!=4096 or
        p["qualification"]["unseen_dev_cohorts_unassigned"] is not True or
        p["qualification"]["sealed_evaluation_unreleased"] is not True or
        not all(p["authority"].values())):
        raise ValueError("MG28_PREREG_OR_SOURCE_AUTHORITY_DRIFT")
    evidence=p["prior_proof"]
    if (evidence["uninformed_brier"]-evidence["original_brier"]<0.02 or
        evidence["matched_scrambled_brier"]-evidence["matched_original_brier"]<0.02 or
        not all(v for v in p["controls"].values() if type(v)is bool) or
        not all(v for v in p["native_design"].values() if type(v)is bool) or
        not all(v for v in p["qualification"].values() if type(v)is bool)):
        raise ValueError("MG28_UNSUPPORTED_OR_UNCONTROLLED_NEXT_NATIVE_MECHANISM")
    return hashlib.sha256(json.dumps(p,sort_keys=True,separators=(",",":"),
                          ensure_ascii=True,allow_nan=False).encode("ascii")).hexdigest()

if __name__=="__main__":
    source=json.loads(PROTOCOL.read_text(encoding="utf-8"))
    first=frozen(source)
    negative=copy.deepcopy(source)
    negative["authority"]["no_F139_owner_controller_scheduler_mutation"]=False
    try:
        frozen(negative)
    except ValueError:
        pass
    else:
        raise SystemExit("MG28_SAFETY_GUARD_NEGATIVE_TEST_FAILED")
    negative=copy.deepcopy(source)
    negative["prior_proof"]["matched_scrambled_brier"]=0.10
    try:
        frozen(negative)
    except ValueError:
        pass
    else:
        raise SystemExit("MG28_UNSUPPORTED_PREDICTION_CONTROL_NOT_REJECTED")
    print("MG28_FROZEN_PROSPECTIVE_SOURCE_ONLY_DUAL_NATIVE_PROTOCOL_PASS_NOT_SCIENCE "+first)

"""F124-BL equal-native-workload diagnostic.

Run the unchanged F124-AZ science decision first. If it abstains, keep that
abstention; separately benchmark a frozen AZ Feistel component through the
unchanged native Yggdrasil scorer solely for resource comparability.
This intentionally FORCES diagnostic work and is never an eligible scientific
baseline/prediction. Neither source/private recipe nor labels enter models.
"""
from __future__ import annotations
import importlib.util
import math
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
NATIVE=ROOT/"nativeevidence"
FREEZE="3d97bbdd6bd649e1c131ec159d546819094489ff"


def need(value,why):
    if not value:
        raise RuntimeError("F124BL_"+why)


def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    need(spec and spec.loader,"IMPORT")
    m=importlib.util.module_from_spec(spec)
    sys.modules[name]=m
    spec.loader.exec_module(m)
    return m


def verify_bl():
    import subprocess
    p=subprocess.run(["git","rev-parse","HEAD:research/north-star-transfer/f124bl-workload-freeze.json"],
                     cwd=ROOT,capture_output=True,text=True,check=True)
    # Frozen preregistration must be immutable throughout qualification.
    need(p.stdout.strip()=="UNSET_BLOB","FROZEN_METHOD_DRIFT")


def evaluate(arm,tag):
    need(arm in ("learned","AZ_forced_diagnostic") and tag in ("U","R"),
         "ONLY_NEGATIVE_ENGINEERING_FIXTURES")
    bk=module("f124bl_frozen_bk",HERE/"f124bk_native_graph.py")
    bk.verify_origins()
    fit,check=bk.source_public(tag)
    pub=bk.sha256_public(fit+check)
    graph=bk.public_native_graph(fit,check)
    graph_digest=bk.sha256_public(graph)
    if arm=="learned":
        output=bk.evaluate("learned",tag,source=(fit,check))
        witness=output["native_path_evidence"]
        work=witness["graph_work"]
        need(witness["original_native_scorer_invoked"] and
             witness["edge_inverse_calls"]==12,
             "LEARNED_NATIVE_EXECUTION")
        result={
            "scientifically_admissible":False,
            "original_AZ_policy_decision":"NOT_THE_AZ_ARM",
            "forced_native_work":False,
            "native_graph_calls":1,
            "native_work":work,
            "native_score":witness["native_score"],
            "learned_param_bits_lower":32}
    else:
        old,native,parser,kernel=bk.origin_controls()
        demos=[{"input_bits":bk.bits16(x),"output_bits":bk.bits16(y)}
               for x,y in fit+check]
        trained=old.train(demos,"F124BL-FROZEN-PUBLIC-DIAGNOSTIC",0)
        original_score,original_work,original_diag=old.score(
            graph,list(bk.NATIVE_BASE),list(bk.NATIVE_DELTA),trained,demos)
        # As observed in BK both negative fixtures cause honest scientific
        # AZ abstention, so native scoring of the actual AZ policy is skipped.
        need(trained["choice"]=="abstain" and
             original_work is None and original_diag["abstained"] is True,
             "ORIGINAL_AZ_NOT_ABSTAINING")
        parsed,original_support,nonce=parser.public_task(graph)
        need(original_support==demos[:24] and nonce==bk.NONCE,
             "NO_GRAPH_SUPPORT_DRIFT")
        native.frozen.prior.parent.validate_15(parsed)
        feistel=trained["feistel_model"]
        for edge in parsed["edges"]:
            edge["src_bits"]=old.nonlinear.predict(
                feistel,edge["src_bits"])
        native.frozen.prior.parent.validate_15(parsed)
        value,raw,ratio,work=native.ygg_transition(
            parsed,list(bk.NATIVE_BASE),list(bk.NATIVE_DELTA),.1)
        need(math.isfinite(value),"DIAGNOSTIC_NATIVE_PATH")
        result={
            "scientifically_admissible":False,
            "original_AZ_policy_decision":"abstain",
            "original_AZ_unmodified_score":original_score,
            "original_AZ_unmodified_native_execution":False,
            "forced_native_work":True,
            "native_graph_calls":1,
            "native_work":work,
            "native_score":value,
            "feistel_model_bits_lower":feistel["parameters_bits_lower"],
            "diagnostic_override_changes_AZ_policy":False}
    need(work["max_active"]<=7 and work["max_retained"]<=9
         and result["native_graph_calls"]==1,
         "SEVEN_PLUS_NINE")
    return {"schema":"mass.f124bl.ineligible-native-work-diagnostic.v1",
            "arm":arm,"tag":tag,
            "same_public_48_sha256":pub,
            "same_native_graph_sha256":graph_digest,
            "source_fixture_private_information_to_model":False,
            "native_7_active_9_retained":True,
            "native_workload":result,
            "original_192_TRAIN_replayed":False,
            "protected_validation_or_U_R_used":False,
            "scientific_accepted":False,
            "whole_resource_parity_qualified":False}

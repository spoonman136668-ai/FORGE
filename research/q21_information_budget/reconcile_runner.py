"""Q21 read-only two-OS comparison of the ACTUAL sourcefree_runner report.

This checks internally consistent *reported* evidence, not independent source
birth or CKB authentication. It neither acquires episodes nor trains models.
"""
from __future__ import annotations
import math
import re
import evaluator as ev
import resource_meter as rm
import sourcefree as p

SHA256 = re.compile(r"[0-9a-f]{64}\Z")
GITSHA = re.compile(r"[0-9a-f]{40}\Z")
SCHEMA = "forge.q21.complete-sourcefree-resource.v1"
TOL = 1e-6

def need(ok, why):
    if not ok: raise ValueError("Q21_R30_"+why)

def nonnegative(x, why, positive=False):
    need(type(x) in (int,float) and math.isfinite(x) and
         (x>0 if positive else x>=0), why)
    return x

def sha(x, why, pattern=SHA256):
    need(isinstance(x,str) and pattern.fullmatch(x) is not None,why)
    return x

def cost(stage, os_name, title):
    need(isinstance(stage,dict) and stage.get("schema")==
         "forge.q21.native-process-resource.v1",title+"_STAGE_MISSING")
    need(stage.get("platform")==os_name,title+"_PLATFORM_MISMATCH")
    need(stage.get("rss_scope")==
         "PROCESS_CUMULATIVE_HIGH_WATER_NOT_ISOLATED_PER_MODEL" if title!="whole" else
         stage.get("rss_scope")=="CUMULATIVE_PROCESS_HIGH_WATER_NOT_ISOLATED_STAGE",
         title+"_RSS_SCOPE")
    cpu=nonnegative(stage.get("process_cpu_seconds"),title+"_CPU")
    rss=nonnegative(stage.get("process_peak_rss_bytes"),title+"_RSS",True)
    need(nonnegative(stage.get("start_process_peak_rss_bytes"),
                     title+"_START_RSS",True)<=rss,title+"_RSS_NONMONOTONIC")
    io=stage.get("io")
    need(isinstance(io,dict) and stage.get("io_measurement_source")==
         ("windows_getprocessiocounters" if os_name=="Windows" else
          "linux_proc_self_io"),title+"_IO_PROVENANCE")
    for name in ("read_transfer_bytes","write_transfer_bytes",
                 "disk_read_bytes","disk_write_bytes"):
        if io.get(name) is None:
            need(os_name=="Windows" and name.startswith("disk_"),
                 title+"_IO_UNMEASURED")
        else: nonnegative(io[name],title+"_IO_"+name)
    return cpu,rss

def transport(decl, why):
    need(isinstance(decl,dict) and decl.get("adapter_mode")=="none"
         and decl.get("wire_bytes")==0 and decl.get("adapter_bytes")==0,
         why+"_NO_TRANSPORT_MISSING")

def payload(item, observed, why):
    need(isinstance(item,dict) and item.get("encoding")==
         "canonical_json_utf8",why+"_PAYLOAD_FORMAT")
    expected=rm.canonical_payload_size(observed)
    need(item==expected,why+"_PAYLOAD_INTEGRITY")

def scores(observed, family):
    need(isinstance(observed,dict) and observed.get("family")==family,
         "FAMILY_DRIFT")
    need(observed.get("protected_scientific_first_use") is False,
         "ILLEGAL_FIRST_USE")
    need(observed.get("native_peak_rss_qualified") is False,
         "FORGED_NATIVE_RSS_ADMISSION")
    cohort=observed.get("role_sha256")
    need(isinstance(cohort,dict) and set(cohort)==p.ROLES,
         "COHORT_ROLE_DRIFT")
    for v in cohort.values(): sha(v,"COHORT_DIGEST_MISSING")
    need(len(set(cohort.values()))==3,"COHORT_COLLISION")
    arms=observed.get("arm_results")
    need(isinstance(arms,dict) and set(arms)==set(ev.ARM_NAMES),
         "SEVEN_ARM_INVENTORY")
    best={}
    checkpoint={}
    for name in ev.ARM_NAMES:
        arm=arms[name]
        need(isinstance(arm,dict),"ARM_RECORD")
        fit=arm.get("fit_cost")
        result=arm.get("result")
        need(isinstance(fit,dict) and isinstance(result,dict),
             "ARM_TRAIN_AND_DEV")
        nonnegative(fit.get("fit_validation_nll"),"FIT_VALID_NLL")
        nonnegative(fit.get("checkpoint_bytes"),"CHECKPOINT_SIZE",True)
        checkpoint[name]=sha(fit.get("checkpoint_sha256"),
                             "CHECKPOINT_ID")
        losses=result.get("episode_nll")
        need(isinstance(losses,list) and
             len(losses)==p.ROLE_COUNTS["DEV"],"EPISODE_COUNT")
        for value in losses: nonnegative(value,"EPISODE_NLL")
        mean=nonnegative(result.get("mean_nll"),"MEAN_NLL")
        need(abs(mean-sum(losses)/len(losses))<1e-8,
             "MEAN_NLL_RECOMPUTE")
        best[name]=mean
    current=ev.select_pre_dev_arm(arms,ev.MEMORYLESS)
    history=ev.select_pre_dev_arm(arms,ev.HISTORY)
    need(observed.get("best_current")==current and
         observed.get("best_history")==history,
         "DEV_SET_WINNER_SELECTION")
    boot=observed.get("gain")
    need(isinstance(boot,dict) and boot.get("replicates")==2048
         and boot.get("resampling_unit")=="EPISODE",
         "FROZEN_BOOTSTRAP")
    for name in ("gain_nats_per_bit","lower_95","upper_95"):
        need(type(boot.get(name)) in (float,int) and
             math.isfinite(boot[name]),"BOOTSTRAP_FINITE")
    need(boot["lower_95"]<=boot["upper_95"],"BOOTSTRAP_ORDER")
    need(abs(boot["gain_nats_per_bit"]-
             (best[current]-best[history]))<1e-8,
         "GAIN_RECOMPUTE")
    oracle=nonnegative(observed.get("privileged_oracle_nll"),
                       "PRIVILEGED_ORACLE")
    need(observed.get("oracle_is_not_matched_comparator") is True,
         "ORACLE_NOT_PRIVILEGED")
    need(abs(observed.get("public_oracle_headroom",math.nan)-
             (best[current]-oracle))<1e-8,
         "ORACLE_HEADROOM")
    return {"cohort":cohort,"nll":best,"checkpoints":checkpoint,
            "gain":boot,"oracle":oracle,
            "headroom":observed["public_oracle_headroom"]}

def inspect(envelope,doc):
    need(doc.get("schema")==p.SCHEMA and
         doc.get("frozen_dev_decision") is not None,
         "FROZEN_PROTOCOL")
    need(isinstance(envelope,dict) and
         envelope.get("schema")=="forge.q21.external-readonly-envelope.v1",
         "ENVELOPE_SCHEMA")
    platform=envelope.get("os_name")
    need(platform in ("Windows","Linux"),"OS_NAME")
    sha(envelope.get("candidate_source_sha"),"CANDIDATE_SHA",GITSHA)
    report=envelope.get("runner_report")
    need(isinstance(report,dict) and report.get("schema")==SCHEMA,
         "REAL_RUNNER_SCHEMA")
    need(report.get("frozen_protocol_blob")==p.PROTOCOL_BLOB,
         "PREREG_ID")
    need(report.get("scientific_admission")=="NOT_GRANTED_BY_THIS_MODULE"
         and report.get("protected_heldout_or_original_first_use") is False,
         "FALSE_SCIENTIFIC_AUTHORITY")
    need(report.get("process_peak_rss_isolated_per_model") is False,
         "FAKE_MODEL_RSS_ISOLATION")
    need(report.get("role_counts_per_family")==p.ROLE_COUNTS,
         "ROLE_BUDGET_CHANGED")
    transport(report.get("communication"),"WHOLE")
    families=report.get("families")
    need(isinstance(families,dict) and set(families)==set(p.FAMILIES),
         "FAMILY_SET")
    total=report.get("whole_process_resources")
    overall_cpu,overall_rss=cost(total,platform,"whole")
    observed={}
    component_cpu=0
    peaks=[]
    for family in p.FAMILIES:
        item=families[family]
        need(isinstance(item,dict),"FAMILY_RESULT_MISSING")
        data=item.get("observed_metrics")
        observed[family]=scores(data,family)
        gen=item.get("source_generation_resources")
        evr=item.get("fit_and_dev_resources")
        for receipt,label in ((gen,"generation"),(evr,"evaluation")):
            cpu,rss=cost(receipt,platform,label)
            component_cpu+=cpu
            peaks.append(rss)
            transport(receipt.get("communication"),label)
            need(receipt.get("payload") is not None,
                 label+"_SERIALIZED_PAYLOAD_MISSING")
        payload(evr["payload"],data,"EVAL")
        sha(gen["payload"].get("serialized_sha256"),"GEN_BYTES_HASH")
        nonnegative(gen["payload"].get("serialized_bytes"),
                    "GEN_BYTES",True)
    need(overall_cpu+1e-6>=component_cpu,
         "WHOLE_PROCESS_CPU_EXCLUDES_COMPONENTS")
    need(overall_rss>=max(peaks),
         "WHOLE_PROCESS_RSS_BELOW_STAGES")
    stored=report.get("receipt_storage")
    unsealed={k:v for k,v in report.items() if k!="receipt_storage"}
    payload(stored,unsealed,"FINAL_RECEIPT")
    preliminary=ev.preliminary_decision(
        {family:families[family]["observed_metrics"]
         for family in p.FAMILIES},doc)
    need(report.get("frozen_preliminary_decision")==preliminary,
         "FROZEN_DECISION_MISMATCH")
    return observed,preliminary

def compare(windows,linux,doc):
    a,ad=inspect(windows,doc)
    b,bd=inspect(linux,doc)
    need(windows["os_name"]=="Windows" and linux["os_name"]=="Linux",
         "OS_PAIR")
    need(windows["candidate_source_sha"]==linux["candidate_source_sha"],
         "SOURCE_CROSS_OS_DRIFT")
    need(ad["q21_development_thresholds_met"]==
         bd["q21_development_thresholds_met"] and
         ad["per_real_family_meets_thresholds"]==
         bd["per_real_family_meets_thresholds"],
         "CROSS_OS_DECISION_DRIFT")
    divergences=[]
    for family in p.FAMILIES:
        aa,bb=a[family],b[family]
        need(aa["cohort"]==bb["cohort"],"COHORT_SOURCE_DRIFT")
        for arm in ev.ARM_NAMES:
            need(abs(aa["nll"][arm]-bb["nll"][arm])<=TOL,
                 "NLL_CROSS_OS_DRIFT")
            if aa["checkpoints"][arm]!=bb["checkpoints"][arm]:
                divergences.append(family+":"+arm)
        for key in ("gain_nats_per_bit","lower_95","upper_95"):
            need(abs(aa["gain"][key]-bb["gain"][key])<=TOL,
                 "BOOTSTRAP_CROSS_OS_DRIFT")
        need(abs(aa["oracle"]-bb["oracle"])<=TOL and
             abs(aa["headroom"]-bb["headroom"])<=TOL,
             "ORACLE_CROSS_OS_DRIFT")
    return {
        "schema":"forge.q21.runner-reconciliation-advisory.v1",
        "source_sha":windows["candidate_source_sha"],
        "frozen_protocol_blob":p.PROTOCOL_BLOB,
        "matched_reported_cohorts":True,
        "scores_reproducible_within_1e_minus_6":True,
        "checkpoint_hash_divergences":divergences,
        "frozen_dev_thresholds_met":ad["q21_development_thresholds_met"],
        "scientific_first_use":"NOT_AUTHENTICATED_NOT_AUTHORIZED",
        "ckb_plane_acceptance":"NOT_AUTHORIZED_BY_THIS_RECONCILER",
    }

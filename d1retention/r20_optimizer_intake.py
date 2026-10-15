"""R20: observational archived source-to-D1 byte identity gate.

The readback callback must be bound by the existing authorized Worker client.
This module neither trusts the historical data as optimizer training nor
creates signed assignment logs, first-use authorization or experiments.
"""
import pathlib,hmac
from collections import Counter
import r19_intake as source

class R20Blocked(ValueError): pass

def qualify(manifest_raw, observation_raw, evidence_dir, verified_d1_readback):
    if not callable(verified_d1_readback):
        raise R20Blocked("D1_READBACK_NOT_BOUND")
    entries=source.manifest_entries(manifest_raw)
    manifest_sha=source.sha(manifest_raw)
    source.verify_observation(observation_raw,entries,manifest_sha)
    if Counter(e["lane"] for e in entries)!=Counter({"Wingless":3,"Yggdrasil":3}):
        raise R20Blocked("DUAL_LANE_COHORT_DRIFT")
    for field in ("run_id","artifact_id","head_sha","archive_sha256"):
        if len({e[field] for e in entries})!=6:
            raise R20Blocked("SOURCE_REUSE_"+field)
    originals=[]
    folder=pathlib.Path(evidence_dir).resolve(strict=True)
    for e in entries:
        path=folder/(str(e["run_id"])+".zip")
        if path.is_symlink() or not path.is_file():
            raise R20Blocked("SOURCE_FILE_MISSING")
        raw=path.read_bytes()
        if not 0<len(raw)<=source.MAX_ZIP_BYTES or not hmac.compare_digest(
               source.sha(raw),e["archive_sha256"]):
            raise R20Blocked("SOURCE_DIGEST_DRIFT")
        originals.append((e,raw))
    # Complete local verification before any Cloudflare readback.
    for e,raw in originals:
        readback_len=verified_d1_readback(e,manifest_sha,raw)
        if type(readback_len) is not int or readback_len!=len(raw):
            raise R20Blocked("D1_ORIGINAL_READBACK_DRIFT")
    return {
        "schema":"forge.optimizer.authentic-archive-inventory.v1",
        "mode":"REAL_ORIGINAL_BYTES_ONLY_NOT_POLICY_ADMISSION",
        "source_manifest_sha256":manifest_sha,
        "github_d1_originals_joined":6,
        "wingless_originals":3,
        "yggdrasil_originals":3,
        "original_bytes_readback":sum(len(raw) for _,raw in originals),
        "archive_integrity_reconciled":True,
        "independent_scientific_custody_qualified":False,
        "complete_first_use_reconciled":False,
        "randomized_selection_audits_verified":False,
        "signed_optimizer_training_history_admitted":False,
        "five_optimizer_shadow_admitted":False,
        "prospective_policy_improvement_established":False,
        "scientific_accepted":False,
        "optimizer_dispatch_authorized":False,
        "new_experiments":0
    }

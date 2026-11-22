#!/usr/bin/env python3
"""F57 immutable proposal/preflight ONLY. No fresh Acrobot evaluation.

Protocol-first ancestor 6ba111800081505c8482024beeef4a529ab89566.
This deliberately provides no route to dispatch, simulate, score, or authorize
an original scientific experiment. A future independently authenticated FSA
must implement and separately qualify first-use on private FORGE resources.
"""
import hashlib
import json
from pathlib import Path
import sys

SCHEMA = "forge.eureka.f57.original-acrobot-reward-trial.preflight.v1"
PROTOCOL_COMMIT = "6ba111800081505c8482024beeef4a529ab89566"
SOURCE_PARENT = "84bdd242344a00e82f89038b3cca5881cad70189"
BASE_MAIN = "e4052145d35feca0063ae6435b2636afe94662d6"
PROTOCOL_BLOB = "026af1ee4f734e2160936df71935aa6f0b455fdf"
OLD_FIT_SHA256 = "63d31930006ec2f465e4becd989c1a0b922e15a0842ef991fe424074d436a31a"
OLD_FQI_SHA256 = "968c8353334256634707097ff510bcbee60177253280850f7ed56f7a0c1a93a1"
OLD_FIT_ROOTS = (21011,21017,21019,21023,21029,21031)
F51_TRANSFER = (31011,31013,31017,31019,31021,31023,31027,31029,31031,31033,31037,31039)
F51_RETENTION = (32011,32013,32017,32019,32023,32029,32031,32037)
F53_TRANSFER = (41011,41013,41017,41019,41021,41023,41027,41029,41031,41033,41037,41039,41041,41047,41051,41057)
F53_RETENTION = (42011,42013,42017,42019,42023,42029,42031,42037)
PROPOSED_TRANSFER = (51011,51013,51017,51019,51021,51023,51027,51029,
                     51031,51033,51037,51039,51041,51047,51051,51057)
PROPOSED_RETENTION = (52011,52013,52017,52019,52023,52029,52031,52037)
PROTECTED = (59,83)
ARMS = ("quantile-supported", "momentum-rule", "frozen-fqi", "always-td",
        "quantile-margin-only", "f53-fixed-margin", "rotated-credit")
CONVENTIONAL = ("momentum-rule","frozen-fqi","always-td")
MIN_PAIRED_WINS = 12
MIN_MEAN_GAIN = 15.0
MIN_NEGATIVE_GAIN = 15.0
MIN_DEVIATING_TRANSFER_SEEDS = 4
MIN_RETENTION_MARGIN = -10.0
MAX_STEPS = 500
F57_ERROR = "F57_AUTHORITY_BLOCKED_NO_FIRST_USE"
PROJECT = Path(__file__).resolve().parents[1]

# Exact original source pins are versioned inputs only, NOT original signatures.
PINNED_FILES = {
    "AGENTS.md": "39926d2277ac01c8114f03561bd8e001fcc3b582",
    "docs/NATIVE-DISCOVERY-F57-ORIGINAL-ACROBOT-REWARD-TRIAL.md": PROTOCOL_BLOB,
    "research/f51_original_acrobot_transfer_dev.py": "d3114ac66589e6b9f623318da721449090cfd54a",
    "research/f53_original_acrobot_supported_residual_dev.py": "cd8bc0d1163569adaa69371697e3448bfd4b4e01",
    "research/f54_original_acrobot_fit_quantile_action_audit.py": "5338c929e8e4101cc04211dfa4ad34bbca52d1f4",
    "research/f55_original_acrobot_oof_fit_action.py": "7ef1033a83c977fc7c5fef7951be03531af6e054",
    "research/f56_original_acrobot_fit_ips_proxy.py": "00a6901daa1b479e96d923bf46daa5a1f1be45b4",
}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",",":"), allow_nan=False).encode("utf-8")


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def git_blob_sha1(path):
    """Compute local content Git blob identity; never invokes git or network."""
    payload = Path(path).read_bytes()
    return hashlib.sha1(b"blob " + str(len(payload)).encode("ascii") + b"\0" + payload).hexdigest()


def frozen_proposal():
    """Advisory frozen trial specification. Not an FSA-approved intent."""
    return {
        "schema": SCHEMA,
        "protocol_commit": PROTOCOL_COMMIT,
        "parent_sha": SOURCE_PARENT,
        "protected_main_sha": BASE_MAIN,
        "protocol_blob": PROTOCOL_BLOB,
        "source_git_blobs": dict(PINNED_FILES),
        "independent_upstream_commit": "365080941ea3a815ac09e57a7d4ee263a142651d",
        "original_acrobot_blob": "28c440af281858c30e95fb6023f19923065d64fe",
        "python": "3.11",
        "numpy": "2.0.2",
        "gymnasium": "1.2.3",
        "historical_fit_roots": OLD_FIT_ROOTS,
        "historical_fit_records": 8974,
        "historical_fit_episodes": 48,
        "historical_fit_sha256": OLD_FIT_SHA256,
        "historical_40pass_fqi_sha256": OLD_FQI_SHA256,
        "proposed_transfer_nips_seeds": PROPOSED_TRANSFER,
        "proposed_retention_book_seeds": PROPOSED_RETENTION,
        "arms": ARMS,
        "conventional": CONVENTIONAL,
        "negative_control": "rotated-credit",
        "max_original_steps_per_episode": MAX_STEPS,
        "new_scored_episodes": 7 * 24,
        "cold_replay_episodes": 7 * 24,
        "cold_replay_required_exact": 7 * 24,
        "controls_fit_same_historical_source": True,
        "candidate_online_learning_allowed": False,
        "strong_conventional_selection": "highest_transfer_original_return_ties_in_written_order",
        "frozen_development_thresholds": {
            "min_mean_transfer_gain": MIN_MEAN_GAIN,
            "min_paired_strict_wins": MIN_PAIRED_WINS,
            "nondegraded_transfer_success": True,
            "min_negative_credit_margin": MIN_NEGATIVE_GAIN,
            "min_retention_margin": MIN_RETENTION_MARGIN,
            "min_transfer_seeds_with_action_deviation": MIN_DEVIATING_TRANSFER_SEEDS,
            "require_exact_replays": 168,
            "measure_absolute_and_ratio_compute": True,
        },
        "scientific_authority": "independent_FORGE_FSA_signed_one_shot_required",
        "global_cohort_ledger_verified": False,
        "original_source_independently_authenticated": False,
        "original_start_witness_authenticated": False,
        "worker_or_owner_executed": False,
        "fresh_cohort_consumed": False,
        "scientific_acceptance": False,
        "deployment_or_promotion": False,
    }


def validate_structure(proposal):
    """Pure invariant check: never authorizes experiment or validates FSA."""
    if canonical(proposal) != canonical(frozen_proposal()):
        raise ValueError("F57_PROSPECTIVE_PROTOCOL_OR_SCIENTIFIC_BUDGET_MUTATED")
    proposed = (*PROPOSED_TRANSFER, *PROPOSED_RETENTION)
    past = (*OLD_FIT_ROOTS, *F51_TRANSFER, *F51_RETENTION,
            *F53_TRANSFER, *F53_RETENTION, *PROTECTED)
    if (len(PROPOSED_TRANSFER)!=16 or len(PROPOSED_RETENTION)!=8 or
        len(set(proposed))!=24 or len(set(past))!=len(past) or
        set(proposed)&set(past) or len(ARMS)!=7 or
        len(set(ARMS))!=7 or len(CONVENTIONAL)!=3 or
        not set(CONVENTIONAL).issubset(ARMS) or
        len(set(CONVENTIONAL))!=3 or
        "quantile-supported" not in ARMS or "rotated-credit" not in ARMS or
        MIN_PAIRED_WINS>16 or MIN_PAIRED_WINS<1 or
        MAX_STEPS>500 or MAX_STEPS<1 or
        7*(len(PROPOSED_TRANSFER)+len(PROPOSED_RETENTION))!=168):
        raise ValueError("F57_LOCAL_SEED_OR_COMPARATOR_CUSTODY_INVALID")
    return True


def inspect_source_pins(root=PROJECT):
    """Read-only local byte identity check, not independent trust or FSA."""
    root=Path(root)
    return {name: git_blob_sha1(root/name) for name in PINNED_FILES}


def preflight(root=PROJECT):
    """Explicitly blocked even when all local source-only checks pass."""
    frozen=frozen_proposal()
    validate_structure(frozen)
    try:
        observed=inspect_source_pins(root)
    except (OSError, ValueError) as exc:
        raise RuntimeError("F57_SOURCE_ONLY_PREFLIGHT_UNVERIFIED") from exc
    mismatched={k:{"expected":v,"observed":observed[k]}
                for k,v in PINNED_FILES.items() if observed[k]!=v}
    if mismatched:
        raise RuntimeError("F57_ORIGINAL_SOURCE_OR_PROTOCOL_PIN_MISMATCH:"+
                           ",".join(sorted(mismatched)))
    return {
        "schema": SCHEMA,
        "disposition": F57_ERROR,
        "local_original_source_blobs_match": True,
        "local_internal_seed_disjointness_verified": True,
        "independent_global_seed_ledger_checked": False,
        "fsa_authenticated_execution_grant_present": False,
        "signed_original_start_receipt_present": False,
        "fsa_authenticated_durable_monotonic_witness_present": False,
        "fsa_worker_authorized": False,
        "fresh_scored_episodes_executed": 0,
        "science_accepted": False,
        "ready_for_live_scored_execution": False,
        "proposed_manifest_sha256": digest(frozen),
    }


def start_scientific_experiment(*_args, **_kwargs):
    """No caller-supplied boolean, token, callback or test key may bypass."""
    raise PermissionError(F57_ERROR)


def main():
    if len(sys.argv)!=1:
        raise ValueError("F57_SOURCE_ONLY_PREFLIGHT_TAKES_NO_ARGUMENTS")
    result=preflight()
    print("F57_ADMISSION="+result["disposition"])
    print("F57_MANIFEST_SHA256="+result["proposed_manifest_sha256"])
    print("F57_SOURCE_ONLY_PREFLIGHT=PASS; SCIENCE_NOT_RUN")
    return result


if __name__=="__main__":
    main()

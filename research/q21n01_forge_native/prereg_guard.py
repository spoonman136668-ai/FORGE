"""Q21N-01 frozen-protocol preflight. Never generates FIT, VALID or DEV data.

This is design validation only. It does not activate FORGE FSA, issue a worker
ticket, authorize first-use, or train models. Original Q21 stays byte-identical.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
NEW_PROTOCOL = HERE / "FROZEN_PROTOCOL.json"
LEGACY_PROTOCOL = ROOT / "research" / "q21_information_budget" / "FROZEN_PROTOCOL.json"
NEW_PROTOCOL_BLOB = "2b913a183043d06fd9eac7b18a36499a89517a49"
LEGACY_PROTOCOL_BLOB = "d7c35c10f80b36a758b78e0deedf36d74bf5767d"
PARENT_SHA = "79a7ea1df2a790ff186b7e5fa837494f46373990"
SCHEMA = "forge.optimizer.q21n01.native-information-budget-prereg.v1"
FAMILIES = ("A_PERSISTENT_ACTION_FLIP", "B_DELAYED_ACTION_CHANGE",
            "NULL_ACTION_INDEPENDENT")
ROLES = {"FIT_TRAIN": 256, "FIT_VALID": 64, "DEV": 128}


class ProtocolRefused(ValueError):
    pass


def require(ok, code):
    if not ok:
        raise ProtocolRefused("Q21N01_" + code)


def git_blob(raw):
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\\0" + raw).hexdigest()


def read_protocol():
    raw = NEW_PROTOCOL.read_bytes()
    require(git_blob(raw) == NEW_PROTOCOL_BLOB, "SUCCESSOR_BLOB_CHANGED")
    legacy = LEGACY_PROTOCOL.read_bytes()
    require(git_blob(legacy) == LEGACY_PROTOCOL_BLOB, "PREDECESSOR_BLOB_CHANGED")
    return json.loads(raw), json.loads(legacy)


def validate(doc, predecessor):
    require(isinstance(doc, dict) and doc.get("schema") == SCHEMA,
            "SCHEMA_DRIFT")
    require(doc.get("state") == "FROZEN_SOURCE_ONLY_NO_COHORTS_GENERATED"
            and doc.get("stage") == "PROSPECTIVE_DEVELOPMENT_ONLY"
            and doc.get("scientific_identity") == "Q21N-01", "PREMATURE_SCIENCE")
    require(doc.get("owner") == "FORGE_SCIENTIFIC_AUTHORITY_ONLY"
            and doc.get("source_parent") == PARENT_SHA,
            "SCIENTIFIC_AUTHORITY_OR_PARENT_DRIFT")
    earlier = doc.get("predecessor", {})
    require(earlier.get("protocol_blob_sha") == LEGACY_PROTOCOL_BLOB and
            earlier.get("source_commit_sha") ==
            "0d49a1cc01e9dff9db060ca0981beaf6748f3127" and
            earlier.get("disposition") ==
            "HISTORIC_DESIGN_ONLY_NEVER_SCIENTIFICALLY_EXECUTED",
            "PREDECESSOR_REINTERPRETED")
    require(predecessor.get("schema") ==
            "forge.nci04.q21.information_budget_prereg.v1" and
            predecessor.get("state") == "FROZEN_DESIGN_ONLY_NOT_EXECUTED",
            "PREDECESSOR_STATE_DRIFT")
    generator = doc.get("generator", {})
    require(generator.get("seed_namespace") == "forge-q21n01-v1" and
            generator.get("seed_namespace") != "forge-q21-v1" and
            generator.get("rng") ==
            "python_random_Random_MT19937_64bit_integer_seed",
            "SEED_NAMESPACE_REUSE")
    require(generator.get("initial_seed_spec") ==
            "int.from_bytes(sha256(utf8('forge-q21n01-v1:'+role+':'+family+':'+str(index))).digest()[:8],'big')",
            "SEED_SPEC_CHANGED")
    families = generator.get("families", [])
    old_families = predecessor.get("source_free_families", [])
    require(isinstance(families, list) and len(families) == 3 and
            tuple(x.get("id") for x in families) == FAMILIES and
            [x.get("fixed_generator") for x in families] ==
            [x.get("fixed_generator") for x in old_families],
            "FAMILY_PARAMETER_DRIFT")
    roles = doc.get("roles", {})
    require(all(roles.get(k) == count for k,count in ROLES.items()) and
            roles.get("per_family") is True and
            roles.get("training_on_dev") == "FORBIDDEN" and
            roles.get("selection_on_dev") == "FORBIDDEN" and
            set(roles.get("forbid_roles", [])) >=
            {"HELD", "ORIGINAL", "Q20_FIT", "Q20_DEV", "Q20_HELD",
             "Q21_FIT", "Q21_DEV"},
            "ROLE_CUSTODY_DRIFT")
    cmp = doc.get("comparators", {})
    require(cmp.get("full_current") ==
            ["FULL_CURRENT_COUNTS", "TRAINED_CURRENT_LOGISTIC"] and
            cmp.get("history") ==
            ["LAGGED_PUBLIC_COUNTS", "TRAINED_2_STATE_ACTION_RNN",
             "TRAINED_4_STATE_ACTION_RNN", "UNSUPERVISED_2_STATE_ACTION_HMM",
             "UNSUPERVISED_4_STATE_ACTION_HMM"] and
            cmp.get("training") == {
               "rnn_epochs":60, "rnn_restarts":3,"hmm_em_epochs":40,
               "hmm_restarts":3,
               "checkpoint_selection":"minimum FIT_VALID NLL separately among current and history models",
               "retrain_on_fit_validation":False},
            "COMPARATOR_DRIFT")
    inherited = predecessor["frozen_dev_decision"]
    decision = doc.get("development_decision", {})
    matches = {
        "history_gain_min_each_real_family":
            "history_gain_min_nats_per_bit_each_real_family",
        "history_gain_95pct_bootstrap_lower_bound_min_each_real_family":
            "history_gain_95pct_bootstrap_lower_bound_each_real_family_min",
        "public_oracle_headroom_vs_best_memoryless_min_each_real_family":
            "public_oracle_headroom_vs_best_memoryless_min_nats_each_real_family",
        "null_max_apparent_history_gain":
            "null_family_max_apparent_history_gain_nats"}
    require(all(type(decision.get(new)) is float and
                decision.get(new) == inherited[old]
                for new,old in matches.items()),
            "FROZEN_THRESHOLD_DRIFT")
    require(decision.get("paired_bootstrap_replicates") == 2048 and
            decision.get("resampling_unit") == "episode" and
            decision.get("cross_os_native_required") ==
                ["Windows", "Linux"] and
            decision.get("nll_tolerance_cross_os") == 1e-6 and
            decision.get("require_same_episode_digests_cross_os") is True
            and decision.get("oracle_must_not_be_counted_as_matched_comparator") is True,
            "CROSS_OS_OR_STATISTICS_DRIFT")
    admitted = doc.get("admission", {})
    require(admitted.get("authority") == "FORGE_FSA_ONLY" and
            admitted.get("current_authorization") == "NONE" and
            admitted.get("known_source_state") == "FSA_ACTIVATION_NOT_INDEPENDENTLY_VERIFIED"
            and admitted.get("controller") == "EXISTING_FORGE_CONTROLLER_ONLY"
            and admitted.get("protected_original_first_use") is False and
            admitted.get("no_external_paid_models") is True and
            admitted.get("no_cross_project_private_dependencies") is True,
            "UNAUTHORIZED_OR_PRIVATE_DEPENDENCY")
    require(doc.get("resource_accounting") and
            doc.get("guardrails") and
            doc.get("development_decision",{}).get("not_evidence_of") ==
            "UNSEEN_TASK_TRANSFER_OR_GENERAL_INTELLIGENCE",
            "SCIENCE_SCOPE_DRIFT")
    return {
        "schema": SCHEMA,
        "state": "SOURCE_ONLY_FROZEN_PROTOCOL_PASS",
        "protocol_git_blob": NEW_PROTOCOL_BLOB,
        "predecessor_git_blob": LEGACY_PROTOCOL_BLOB,
        "authority_admitted": False,
        "cohorts_generated": 0,
        "models_trained": 0,
        "scientific_first_use": False
    }


def preflight():
    return validate(*read_protocol())


if __name__ == "__main__":
    print(json.dumps(preflight(), sort_keys=True))

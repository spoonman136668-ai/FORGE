"""Read-only authenticated metadata for two genuine historical DEV archives.

This DOES NOT admit feature vectors or independent scientific outcomes. Historical
ZIP and contained JSON hashes are frozen source references; live API metadata
alone cannot prove the contained row-level records are still intact.
"""
import hashlib
import json
import re
import sys

SCHEMA = "forge.autonomy.f98.real-historical-metadata-shadow.v1"
BLOCK = "FORGE_F98_REAL_SOURCE_CUSTODY_BLOCKED_"
HEX40 = re.compile(r"^[0-9a-f]{40}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")
SPECS = (
    dict(lane="Wingless", repository="spoonman136668-ai/Wingless",
         experiment="W-F10", run_id=38646170288,
         source_sha="fab5f094a29203a5ef1d63fb40225a3aa9a7e57f",
         workflow_path=".github/workflows/w-f10-depth-identifiability.yml",
         artifact_id=11932322023,
         artifact_name="W-F10-original-exact-depth-identifiability-development",
         zip_sha256="cf160c2abe1dcc32425f89eb445a20de47ba01c5b158e4fb9242507554dbaadf",
         payload_sha256="f397e0f45b0f1664426bca7d5a196eacc5d131d417c9030cc276aa9342a15d92",
         archival_pairs=96, archival_questions=192,
         old_interface_failure="REQUESTED_DEPTH_ABSENT_FROM_FROZEN_INTERFACE"),
    dict(lane="Yggdrasil", repository="spoonman136668-ai/Yggdrasil",
         experiment="Y-F9", run_id=38646109265,
         source_sha="714e10f9df0d036f66e4baea229470ed4fe86f04",
         workflow_path=".github/workflows/y-f9-typed-role-binding.yml",
         artifact_id=11932008018,
         artifact_name="Y-F9-original-typed-role-identifiability-dev",
         zip_sha256="cc20faf2c31607ace820b2a9bd90d334b52902a2f776384f938a91884a99fb9e",
         payload_sha256="669c3564d7715621e97aa345ee081912223a91c337a17bd3e7dc1c5e6f38f4af",
         archival_pairs=192, archival_questions=384,
         old_interface_failure="TYPED_RELATION_ROLES_ABSENT_FROM_FROZEN_INTERFACE"),
)
class Blocked(ValueError):
    pass
def need(ok, reason):
    if not ok:
        raise Blocked(BLOCK + reason)
def pairs_unique(pairs):
    result = {}
    for key, value in pairs:
        need(key not in result, "DUPLICATE_JSON_KEY")
        result[key] = value
    return result
def strict_loads(raw):
    need(isinstance(raw, bytes) and 0 < len(raw) <= 524288,
         "UNBOUNDED_OR_MISSING_JSON")
    try:
        obj = json.loads(raw.decode("utf-8"), object_pairs_hook=pairs_unique,
                         parse_constant=lambda _: need(False, "NONFINITE"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise Blocked(BLOCK + "INVALID_JSON") from exc
    need(type(obj) is dict, "EXPECTED_JSON_OBJECT")
    return obj
def sha(raw):
    return hashlib.sha256(raw).hexdigest()
def verify_one(spec, run, artifacts):
    need(type(run) is dict and type(artifacts) is dict,
         "MISSING_LIVE_GITHUB_READBACK")
    need(run.get("id") == spec["run_id"] and type(run.get("id")) is int and
         run.get("repository", {}).get("full_name") == spec["repository"] and
         run.get("head_repository", {}).get("full_name") == spec["repository"] and
         run.get("head_sha") == spec["source_sha"] and
         run.get("path") == spec["workflow_path"] and
         run.get("event") == "push" and
         run.get("status") == "completed" and run.get("conclusion") == "success" and
         run.get("run_attempt") == 1 and type(run.get("run_attempt")) is int and
         type(run.get("workflow_id")) is int and run["workflow_id"] > 0,
         "RUN_SOURCE_OR_TERMINAL_IDENTITY_DRIFT")
    items = artifacts.get("artifacts")
    need(type(items) is list and 1 <= len(items) <= 100 and
         type(artifacts.get("total_count")) is int and
         1 <= artifacts["total_count"] <= 100 and
         len(items) == artifacts["total_count"],
         "INCOMPLETE_ARTIFACT_LIST")
    seen = set()
    pinned = []
    for item in items:
        need(type(item) is dict and type(item.get("id")) is int and
             item["id"] not in seen and item["id"] > 0,
             "REPEATED_OR_INVALID_ARTIFACT_ID")
        seen.add(item["id"])
        if item["id"] == spec["artifact_id"]:
            pinned.append(item)
    need(len(pinned) == 1, "PINNED_ARTIFACT_ABSENT")
    item = pinned[0]
    own = item.get("workflow_run")
    need(type(own) is dict and own.get("id") == spec["run_id"] and
         own.get("head_sha") == spec["source_sha"] and
         item.get("name") == spec["artifact_name"] and
         item.get("digest") == "sha256:" + spec["zip_sha256"] and
         item.get("expired") is False and type(item.get("size_in_bytes")) is int and
         item["size_in_bytes"] > 0,
         "ZIP_DIGEST_OR_RUN_LINKAGE_DRIFT")
    return dict(
        lane=spec["lane"], repository=spec["repository"],
        experiment=spec["experiment"], run_id=spec["run_id"],
        git_source_sha=spec["source_sha"], workflow_path=spec["workflow_path"],
        artifact_id=spec["artifact_id"], archive_zip_sha256=spec["zip_sha256"],
        pinned_contained_json_sha256=spec["payload_sha256"],
        frozen_archival_pair_count=spec["archival_pairs"],
        frozen_archival_question_count=spec["archival_questions"],
        previous_interface_failure=spec["old_interface_failure"],
        github_run_metadata_verified=True,
        artifact_metadata_zip_digest_verified=True,
        actual_zip_bytes_downloaded_and_rehashed=False,
        contained_row_data_reaudited_now=False,
        authenticated_train_only_feature_vectors_available=False,
        genenv_train_history_admitted=False,
        original_science_accepted=False,
    )
def assess(readbacks, source_sha):
    need(type(source_sha) is str and HEX40.fullmatch(source_sha) is not None,
         "FORGE_SOURCE_SHA_INVALID")
    need(type(readbacks) is list and len(readbacks) == 2,
         "INDEPENDENT_TWO_LANE_READBACKS_REQUIRED")
    observed = []
    for spec, pair in zip(SPECS, readbacks):
        need(type(pair) is tuple and len(pair) == 2, "INPUT_PAIR_INVALID")
        observed.append(verify_one(spec, *pair))
    need(observed[0]["lane"] == "Wingless" and
         observed[1]["lane"] == "Yggdrasil" and
         observed[0]["artifact_id"] != observed[1]["artifact_id"] and
         observed[0]["git_source_sha"] != observed[1]["git_source_sha"],
         "CROSS_LANE_ORIGINAL_SOURCE_ALIAS")
    return dict(
        schema=SCHEMA, forge_source_sha=source_sha,
        disposition="REAL_TWO_LANE_HISTORICAL_METADATA_LINKED_TRAIN_ONLY_FEATURES_NOT_ADMITTED",
        source="GITHUB_AUTHENTICATED_READONLY_RUN_AND_ARTIFACT_METADATA",
        historical_reviewed_records=observed,
        genuinely_observed_lanes=2,
        new_trainable_genenv_records=0,
        optimizer_promotion_authorized=False,
        new_scientific_originals_executed=0,
        sealed_original_first_use_authorized=False,
        experiment_worker_dispatched=False,
        accepted_reference_mutations=0,
        model_calls=0, codex_calls=0, external_api_billing=False,
        ckb_plane_accessed=False,
    )
def main(argv):
    need(len(argv) == 5, "EXPECTED_TWO_RUN_AND_ARTIFACT_JSON_PAIRS_PLUS_FORGE_SHA")
    source, wr, wa, yr, ya = argv
    with open(wr, "rb") as stream: w_run = strict_loads(stream.read(524289))
    with open(wa, "rb") as stream: w_art = strict_loads(stream.read(524289))
    with open(yr, "rb") as stream: y_run = strict_loads(stream.read(524289))
    with open(ya, "rb") as stream: y_art = strict_loads(stream.read(524289))
    report = assess([(w_run,w_art), (y_run,y_art)], source)
    print(json.dumps(report, sort_keys=True, separators=(",", ":")))
if __name__ == "__main__":
    try:
        main(sys.argv[1:])
    except (Blocked, OSError, TypeError, KeyError) as exc:
        print("FORGE_F98_REAL_HISTORICAL_METADATA=QUARANTINED", file=sys.stderr)
        raise SystemExit(1)

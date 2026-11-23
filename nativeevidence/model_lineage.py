"""Read-only FORGE evidence check for Wingless/Yggdrasil portable model lineage.

Verifies checkpoint *integrity and parentage*, not genuine cold-process
restoration, learning, retention, transfer, or scientific acceptance.
No controller, network, worker dispatch, model invocation, or mutation.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re

SCHEMA = "research.portable-checkpoint.v1"
REPORT_SCHEMA = "forge.native-model-lineage-readonly.v1"
SHA40 = re.compile(r"[0-9a-f]{40}\Z")
SHA64 = re.compile(r"[0-9a-f]{64}\Z")
MAX_MANIFEST = 65536
MAX_FILES = 64
MAX_BYTES_PER_FILE = 128 * 1024 * 1024
ROLES = {"learned_parameters", "resumable_state", "replay_input", "replay_output", "metadata"}
REQUIRED = ROLES - {"metadata"}
NO_AUTHORITY = {
    "accepted_state_mutation": False,
    "execution_authority": False,
    "promotion_authority": False,
    "production_authority": False,
    "successor_authority": False,
    "retraining_required": False,
}

class Rejected(ValueError):
    pass

def need(condition, reason):
    if not condition:
        raise Rejected("FORGE_MODEL_LINEAGE_" + reason)

def sha256(raw):
    return hashlib.sha256(raw).hexdigest()

def canonical(data):
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf8")

def _unique(pairs):
    result = {}
    for key, value in pairs:
        need(key not in result, "DUPLICATE_JSON_KEY")
        result[key] = value
    return result

def _nonfinite(value):
    raise Rejected("FORGE_MODEL_LINEAGE_NONFINITE_JSON")

def _read_manifest(root):
    root = Path(root)
    need(not root.is_symlink() and root.is_dir(), "CHECKPOINT_ROOT_INVALID")
    file = root / "manifest.json"
    need(not file.is_symlink() and file.is_file() and 0 < file.stat().st_size <= MAX_MANIFEST,
         "MANIFEST_MISSING_OR_OVERSIZE")
    try:
        manifest = json.loads(file.read_bytes().decode("utf8"), object_pairs_hook=_unique,
                              parse_constant=_nonfinite)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise Rejected("FORGE_MODEL_LINEAGE_MANIFEST_INVALID_JSON") from exc
    need(type(manifest) is dict and manifest.get("schema") == SCHEMA, "MANIFEST_SCHEMA")
    recorded = manifest.get("checkpoint_content_sha256")
    need(type(recorded) is str and SHA64.fullmatch(recorded) is not None,
         "CHECKPOINT_DIGEST_INVALID")
    without_digest = dict(manifest)
    without_digest.pop("checkpoint_content_sha256")
    need(sha256(canonical(without_digest)) == recorded, "CHECKPOINT_DIGEST_DRIFT")
    need(manifest.get("project") in ("Wingless", "Yggdrasil"), "PROJECT")
    need(type(manifest.get("mechanism_id")) is str and bool(manifest["mechanism_id"]),
         "MECHANISM_ID")
    need(manifest.get("authority") == NO_AUTHORITY and
         manifest.get("scientific_classification") is None,
         "AUTHORITY_OR_SCIENCE_ESCALATION")
    identity = manifest.get("qualification_identity")
    need(type(identity) is dict, "QUALIFICATION_IDENTITY")
    for field in ("source_commit_sha", "source_tree_sha"):
        need(type(identity.get(field)) is str and SHA40.fullmatch(identity[field]) is not None,
             "SOURCE_IDENTITY")
    for field in ("source_schema_sha256", "qualification_contract_sha256"):
        need(type(identity.get(field)) is str and SHA64.fullmatch(identity[field]) is not None,
             "CONTRACT_IDENTITY")
    need(type(identity.get("toolchain_id")) is str and bool(identity["toolchain_id"]),
         "TOOLCHAIN_IDENTITY")
    lineage = manifest.get("lineage")
    need(type(lineage) is dict and type(lineage.get("experiment_id")) is str and
         bool(lineage["experiment_id"]), "EXPERIMENT_IDENTITY")
    parent = lineage.get("parent_checkpoint_sha256")
    need(parent is None or type(parent) is str and SHA64.fullmatch(parent) is not None,
         "PARENT_IDENTITY")
    interface = manifest.get("interface")
    need(type(interface) is dict, "INTERFACE")
    if manifest["project"] == "Wingless":
        need(interface.get("signature") ==
             "state_former(raw_input, history) -> fixed_size_state" and
             type(interface.get("fixed_state_dimension")) is int and
             interface["fixed_state_dimension"] > 0 and
             type(interface.get("fixed_readout_capacity")) is int and
             interface["fixed_readout_capacity"] > 0 and
             interface.get("capacity_growth") is False, "WINGLESS_INTERFACE")
    else:
        need(interface.get("signature") ==
             "cognition_consumer(retained_state, local_state) -> decision_state" and
             all(type(interface.get(k)) is int and interface[k] == v for k,v in
                 (("total_slots",16),("active_slots",7),("retained_slots",9))) and
             all(interface.get(k) is False for k in
                 ("hidden_persistent_memory_growth","addressing_change","capacity_growth")),
             "YGGDRASIL_INTERFACE")
    resources = manifest.get("resource_envelope")
    need(type(resources) is dict and resources.get("comparison") ==
         "equal-or-lower-than-baseline" and
         type(resources.get("baseline_id")) is str and bool(resources["baseline_id"]) and
         all(type(resources.get(k)) is int and resources[k] >= 0 for k in
             ("max_parameters","max_context_bytes","max_model_calls")), "RESOURCE_ENVELOPE")
    files = manifest.get("files")
    need(type(files) is list and 4 <= len(files) <= MAX_FILES, "FILE_INVENTORY")
    files_root = root / "files"
    need(not files_root.is_symlink() and files_root.is_dir(), "FILES_ROOT")
    seen, roles, by_path = set(), set(), {}
    for item in files:
        need(type(item) is dict, "FILE_RECORD")
        name, role = item.get("path"), item.get("role")
        need(type(name) is str and "\\" not in name and
             all(p not in ("", ".", "..") for p in name.split("/")) and
             not PurePosixPath(name).is_absolute() and
             name not in seen and role in ROLES, "FILE_PATH_OR_ROLE")
        seen.add(name)
        roles.add(role)
        need(type(item.get("size_bytes")) is int and
             0 <= item["size_bytes"] <= MAX_BYTES_PER_FILE and
             type(item.get("sha256")) is str and
             SHA64.fullmatch(item["sha256"]) is not None, "FILE_IDENTITY")
        path = files_root
        for segment in name.split("/"):
            path = path / segment
            need(not path.is_symlink(), "FILE_SYMLINK")
        need(path.is_file() and path.resolve().is_relative_to(files_root.resolve()),
             "FILE_MISSING_OR_ESCAPED")
        h = hashlib.sha256()
        size = 0
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                size += len(chunk)
                need(size <= MAX_BYTES_PER_FILE, "FILE_SIZE_DRIFT")
                h.update(chunk)
        need(size == item["size_bytes"] and h.hexdigest() == item["sha256"],
             "FILE_CONTENT_DRIFT")
        by_path[name] = item
    need(REQUIRED.issubset(roles), "REQUIRED_FILES_MISSING")
    replay = manifest.get("replay")
    need(type(replay) is dict and type(replay.get("vectors")) is list and
         0 < len(replay["vectors"]) <= 64 and
         replay.get("runtime_replay_required_before_promotion") is True,
         "REPLAY_CONTRACT")
    vectors = set()
    for vector in replay["vectors"]:
        need(type(vector) is dict and type(vector.get("id")) is str and
             vector["id"] not in vectors and
             by_path.get(vector.get("input_path"), {}).get("role") == "replay_input" and
             by_path.get(vector.get("output_path"), {}).get("role") == "replay_output" and
             by_path[vector["input_path"]]["sha256"] == vector.get("input_sha256") and
             by_path[vector["output_path"]]["sha256"] == vector.get("output_sha256"),
             "REPLAY_VECTOR_IDENTITY")
        vectors.add(vector["id"])
    portability = manifest.get("portability")
    need(type(portability) is dict and
         portability.get("retraining_required") is False and
         portability.get("restore_supported") is True and
         portability.get("requalification_required_before_promotion") is True,
         "PORTABILITY_CONTRACT")
    return manifest

def compare(parent_root, child_root, *, parent_pin, child_pin):
    """Validate bounded artifact chain; pins must be independently authenticated by caller."""
    need(type(parent_pin) is str and SHA64.fullmatch(parent_pin) is not None and
         type(child_pin) is str and SHA64.fullmatch(child_pin) is not None,
         "EXTERNAL_PIN_REQUIRED")
    parent = _read_manifest(parent_root)
    child = _read_manifest(child_root)
    need(parent["checkpoint_content_sha256"] == parent_pin and
         child["checkpoint_content_sha256"] == child_pin, "EXTERNAL_PIN_MISMATCH")
    need(parent_pin != child_pin and parent["project"] == child["project"] and
         parent["lineage"]["experiment_id"] != child["lineage"]["experiment_id"] and
         child["lineage"]["parent_checkpoint_sha256"] == parent_pin,
         "PARENT_CHILD_IDENTITY")
    need(parent["interface"] == child["interface"], "INTERFACE_DRIFT")
    before = {x["path"]: x["sha256"] for x in parent["files"]
              if x["role"] == "learned_parameters"}
    after = {x["path"]: x["sha256"] for x in child["files"]
             if x["role"] == "learned_parameters"}
    changed = before != after
    return {
        "schema": REPORT_SCHEMA,
        "lane": child["project"],
        "parent_checkpoint_sha256": parent_pin,
        "child_checkpoint_sha256": child_pin,
        "parent_experiment_id": parent["lineage"]["experiment_id"],
        "child_experiment_id": child["lineage"]["experiment_id"],
        "artifact_integrity": "PASS",
        "parent_child_identity": "PASS",
        "parameters_changed": changed,
        "source_authentication": "NOT_ESTABLISHED_BY_ADAPTER",
        "independent_cold_process_restore": "UNVERIFIED",
        "continued_training": "UNVERIFIED",
        "retained_capability": "UNVERIFIED",
        "matched_control_improvement": "UNVERIFIED",
        "scientific_acceptance": False,
        "optimizer_update_authorized": False,
        "live_owner_changed": False,
    }

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--parent", type=Path, required=True)
    parser.add_argument("--child", type=Path, required=True)
    parser.add_argument("--parent-pin", required=True)
    parser.add_argument("--child-pin", required=True)
    args = parser.parse_args()
    print(json.dumps(compare(args.parent, args.child,
                             parent_pin=args.parent_pin, child_pin=args.child_pin),
                     sort_keys=True, separators=(",", ":")))

if __name__ == "__main__":
    main()

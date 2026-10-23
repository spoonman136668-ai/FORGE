"""Independent, read-only GitHub-hosted audit of two original F139 native runs.

No access to the original owner SQLite, FSA first use, or worker dispatch.
Checks authenticated GitHub issue, run and artifact metadata and all four
downloaded native receipts. Never upgrades a provider success into owner custody.
"""
import argparse
import base64
import hashlib
import json
import pathlib
import re

SOURCE = "fe54d7b8f819f04d3c4a2e771e1dc0f0b6f9ddc5"
TARGET = "48ba343b403bc9b4389ce1777130e546b3c446bd"
TREE = "b01a516bbe5ba0938abcaadb3b8ad996799558eb"
REPO = "spoonman136668-ai/FORGE"
UPSTREAM = "spoonman136668-ai/Wingless"
EXPECTED = (
    (778, 39942845762, "ubuntu-latest", 12497420531,
     "bdb9d5cc0ec97f0f65969e741aa9294f7faa34bb4b6b3a39a4a5f4edb9eb3f0a"),
    (778, 39942845762, "windows-latest", 12496328946,
     "7257492a242875d143aeac96160f23e34cee3292a19bba030398fed342afc47f"),
    (779, 39942935746, "ubuntu-latest", 12496473860,
     "af68e9c42b542d6cd7e276602c11ef166314aac332c67ea052321f9b4b3560c0"),
    (779, 39942935746, "windows-latest", 12496423807,
     "4948df1940564e676300ab7613bfffddb232aa14436ad1286e65e78b5f0d3a30"),
)
EXPECTED_COMMANDS = (
    ["go", "test", "-count=1", "./cognition"],
    ["go", "vet", "./cognition"],
    ["go", "test", "-count=1", "./..."],
    ["go", "build", "./..."],
)
HEX = re.compile(r"^[0-9a-f]{64}$")
SCHEMA = "forge.f139.nci04.native-execution-receipt.v1"


def require(predicate, reason):
    if not predicate:
        raise ValueError("F139_RECEIPT_AUDIT_" + reason)


def canonical(obj):
    return json.dumps(
        obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("ascii")


def sha(data):
    return hashlib.sha256(data).hexdigest()


def load(path):
    raw = pathlib.Path(path).read_bytes()
    require(0 < len(raw) < 100000, "FILE_SIZE")
    obj = json.loads(raw)
    require(isinstance(obj, dict), "DOCUMENT_TYPE")
    return obj


def audit(root):
    root = pathlib.Path(root)
    output = []
    for issue_number, run_id, os_name, artifact_id, zip_hash in EXPECTED:
        stem = f"{issue_number}-{os_name}"
        issue = load(root / f"issue-{issue_number}.json")
        run = load(root / f"run-{run_id}.json")
        artifact = load(root / f"artifact-{artifact_id}.json")
        folder = root / stem
        require(issue["number"] == issue_number
                and issue["user"]["login"] == "spoonman136668-ai"
                and issue["state"] == "open"
                and "f139-native-development-eligible" in
                {lab["name"] for lab in issue["labels"]}, "OWNER_ISSUE")
        outer_raw = issue["body"]
        outer = json.loads(outer_raw)
        require(outer["schema"] == "forge.f139.nci04.owner-native-development.v1"
                and outer["source_sha"] == SOURCE
                and outer["lane"] == "Wingless"
                and outer["scientific_first_use"] is False
                and outer["paid_model_calls"] == 0, "OWNER_INTENT")
        intent_raw = base64.b64decode(
            outer["intent_base64"], validate=True)
        intent = json.loads(intent_raw)
        require(canonical(intent) == intent_raw
                and intent["schema"] == "forge.f139.nci04.native-candidate-intent.v1"
                and intent["controller_source_sha"] == SOURCE
                and intent["lane"] == "Wingless"
                and intent["target_repository"] == UPSTREAM
                and intent["target_commit"] == TARGET
                and intent["target_tree_sha"] == TREE
                and intent["worker_mode"] == "isolated-candidate-only"
                and intent["scientific_first_use"] is False
                and all(intent[k] == 0 for k in (
                    "paid_api_calls", "accepted_ref_mutations",
                    "optimizer_policy_mutations",
                    "protected_holdouts_accessed")), "INTENT_IDENTITY")
        candidate = base64.b64decode(intent["after_base64"], validate=True)
        require(0 < len(candidate) <= 32768
                and sha(candidate) == intent["after_sha256"]
                and intent["before_sha256"] == sha(b"")
                and intent["path"].startswith("cognition/")
                and intent["path"].endswith("_test.go"), "CANDIDATE_DIGEST")
        require(run["id"] == run_id
                and run["status"] == "completed"
                and run["conclusion"] == "success"
                and run["run_attempt"] == 1
                and run["event"] == "workflow_dispatch"
                and run["head_sha"] == SOURCE
                and run["display_title"].endswith(
                    "f139-nci04-i" + str(issue_number) + "-" + SOURCE[:12]
                    + "-" + sha(intent_raw)[:8]), "RUN_SOURCE")
        require(artifact["id"] == artifact_id
                and artifact["name"] ==
                f"forge-f139-native-receipt-{os_name}"
                and artifact["expired"] is False
                and artifact["digest"] == "sha256:" + zip_hash
                and artifact["workflow_run"]["id"] == run_id,
                "IMMUTABLE_ARTIFACT_METADATA")
        files = {p.name for p in folder.iterdir()}
        require(files == {
            "f139-receipt.json", "f139-receipt.sha256",
            "f139-native-report.json"}, "THREE_RECEIPT_MEMBERS")
        receipt_bytes = (folder / "f139-receipt.json").read_bytes()
        sidecar = (folder / "f139-receipt.sha256").read_bytes()
        report = load(folder / "f139-native-report.json")
        receipt = json.loads(receipt_bytes)
        require(sidecar == (
            sha(receipt_bytes) + "  f139-receipt.json\n"
        ).encode("ascii"), "SIDECAR_BYTES")
        require(receipt["schema"] == SCHEMA
                and receipt["issue_number"] == issue_number
                and receipt["issue_id"] == issue["id"]
                and receipt["run_id"] == run_id
                and receipt["os"] == os_name
                and receipt["lane"] == "Wingless"
                and receipt["source_sha"] == SOURCE
                and receipt["target_commit"] == TARGET
                and receipt["target_tree_sha"] == TREE
                and receipt["native_intent_sha256"] == sha(intent_raw)
                and receipt["native_qualified"] is True
                and receipt["native_report_sha256"] == sha(canonical(report)),
                "RECEIPT_BINDING")
        require(receipt["development_only"] is True
                and receipt["controller_unattended_verified"] is False
                and receipt["local_custody_verified"] is False
                and receipt["scientific_first_use_authorized"] is False
                and receipt["scientific_originals_dispatched"] == 0
                and receipt["paid_model_calls"] == 0
                and receipt["accepted_ref_mutations"] == 0,
                "AUTHORITY_NOT_ESCALATED")
        require(report["schema"] ==
                "forge.f139.nci04.native-development-diagnostic.v1"
                and report["qualification_complete"] is True
                and report["candidate_file"] == intent["path"]
                and report["candidate_sha256"] == sha(candidate)
                and report["intent_sha256"] == sha(intent_raw)
                and report["qualification_key"] ==
                    receipt["qualification_key"]
                and report["target_commit"] == TARGET
                and report["target_tree_sha"] == TREE
                and report["lane"] == "Wingless"
                and report["real_code_changed_in_isolated_copy"] is True
                and report["scientific_first_use"] is False
                and report["durable_controller_custody_verified"] is False
                and report["unattended_controller_dispatch_verified"] is False
                and all(report[k] == 0 for k in (
                    "paid_model_calls", "accepted_ref_mutations",
                    "protected_holdouts_accessed")), "REPORT_LIMITS")
        commands = report["commands"]
        require(len(commands) == 4 and
                [c["command"] for c in commands] ==
                list(EXPECTED_COMMANDS), "FIXED_COMMANDS")
        for c in commands:
            require(c["returncode"] == 0
                    and c["outcome"] == "PASS"
                    and type(c["output_bytes"]) is int
                    and 0 <= c["output_bytes"] <= 1048576
                    and HEX.fullmatch(c["output_sha256"]) is not None
                    and c["elapsed_ms"] >= 0, "COMMAND_RESULT")
        require("ok" in commands[0]["excerpt"], "FOCUSED_TEST_RAN")
        require("ok" in commands[2]["excerpt"], "FULL_TEST_RAN")
        output.append({
            "issue": issue_number,
            "run": run_id,
            "os": os_name,
            "artifact": artifact_id,
            "github_zip_sha256": zip_hash,
            "receipt_sha256": sha(receipt_bytes),
            "canonical_report_sha256": sha(canonical(report)),
            "intent_sha256": sha(intent_raw),
            "candidate_sha256": sha(candidate),
            "commands_passed": 4,
            "original_owner_sqlite_verified": False,
            "scientific_first_use": False,
        })
    require(len(output) == 4
            and len({(x["issue"], x["os"]) for x in output}) == 4,
            "COMPLETE_MATRIX")
    return {"schema": "forge.f139.native-public-provider-audit.v1",
            "source_sha": SOURCE, "provider_receipts": output,
            "read_only": True, "original_owner_sqlite_verified": False,
            "scientific_first_use": False, "new_controller": False,
            "provider_runs_replayed": False}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("input_folder")
    parser.add_argument("output_file")
    args = parser.parse_args()
    result = audit(args.input_folder)
    pathlib.Path(args.output_file).write_bytes(canonical(result) + b"\n")
    print("F139_FOUR_AUTHENTIC_PROVIDER_RECEIPTS=PASS")
    print("F139_TWO_ORIGINAL_RUNS=VERIFIED")
    print("F139_ORIGINAL_OWNER_SQLITE=NOT_VERIFIED")
    print("F139_SCIENTIFIC_FIRST_USE=FALSE")
    print("F139_NO_WRITES_OR_WORKER_DISPATCH=TRUE")

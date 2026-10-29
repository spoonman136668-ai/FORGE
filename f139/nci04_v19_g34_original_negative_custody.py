"""F139 V19 G34: read authentic FAILED provider ZIPs + original-owner read-only log.

The real V19 owner HMAC and provider credentials are NOT present. GitHub's
authenticated read-only API and independently pinned Actions artifact ZIP
digests bind this historical NEGATIVE. It must never become a new signed
provider receipt, ledger terminal, retry, promotion, or positive worker proof.
"""
from __future__ import annotations
import argparse
import hashlib
import io
import json
from pathlib import Path
import re
import zipfile

OWNER_SOURCE = "0743ca22b76ebd943a66f05a36ea919301676be0"
OWNER_RUN = 40870419796
OWNER_JOB = 123435731436
OWNER_HEAD = "0968ec09ae9ad5886ef97e25af9df294e2da0fbe"
PROVIDER_RUN = 40861987373
ISSUE = 1138
TICKET = "f139-nci04-i1138-0743ca22b76e-8face43d"
SOURCE_TREE = "93620bd8e46bfbae1dbcd8e4ce397e27044de4f1"
TARGET = "021423311027517c9096c76bed7d35ac53c4a229"
OWNER_LEDGER_HASH = "13b00c37edf9685879c3ad66664f9a000134207a4c7a2e6e99aeb1387cac62a5"
SCHEMA = "forge.f139.v19.g34.real-failed-provider-owner-readonly.v1"
EXPECTED = {
    "ubuntu-latest": {
        "id": 12892091559,
        "name": "forge-f139-native-receipt-ubuntu-latest",
        "digest": "a8be7c06879c80d471578afd94a2dce9fd00894f4815dc84f67aed98a699c592"},
    "windows-latest": {
        "id": 12892316111,
        "name": "forge-f139-native-receipt-windows-latest",
        "digest": "34ebd629f8ee1535ed9cfc062653367368ccbd7edc071c99dfbb678d0d7a3dfe"},
}
ZIP_NAMES = frozenset(("f139-receipt.json", "f139-receipt.sha256",
                        "f139-native-report.json"))
MAX_INPUT = 300_000
SHA64 = re.compile(r"[a-f0-9]{64}\Z")


class G34Denied(ValueError):
    pass


def require(value, reason):
    if not value:
        raise G34Denied("F139_V19_G34_" + reason)


def sha(blob):
    return hashlib.sha256(blob).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True).encode("ascii")


def json_obj(raw, name):
    require(type(raw) is bytes and 0 < len(raw) <= MAX_INPUT, name + "_SIZE")
    def pairs(values):
        o = {}
        for key, value in values:
            require(key not in o, name + "_DUPLICATE_KEY")
            o[key] = value
        return o
    try:
        o = json.loads(raw, object_pairs_hook=pairs)
    except (ValueError, UnicodeError) as exc:
        if isinstance(exc, G34Denied):
            raise
        raise G34Denied("F139_V19_G34_" + name + "_JSON") from exc
    require(type(o) is dict, name + "_OBJECT")
    return o


def validate_run(r, *, run_id, source, result, event, branch):
    require(type(r) is dict and type(r.get("id")) is int
            and r["id"] == run_id and r.get("head_sha") == source
            and r.get("head_branch") == branch
            and r.get("event") == event
            and type(r.get("run_attempt")) is int
            and r["run_attempt"] == 1
            and r.get("status") == "completed"
            and r.get("conclusion") == result
            and r.get("repository", {}).get("full_name") ==
                "spoonman136668-ai/FORGE"
            and r.get("head_repository", {}).get("full_name") ==
                "spoonman136668-ai/FORGE"
            and r.get("actor", {}).get("login") == "spoonman136668-ai",
            "RUN_PROVIDER_OR_SOURCE_DRIFT_" + str(run_id))


def owner_log_extract(raw, *, expected_owner_job=None):
    require(type(raw) is bytes and 0 < len(raw) < 200_000, "OWNER_LOG_BOUNDS")
    # Log lines have GitHub timestamps and job steps. Only the single actual
    # emitted statement (not workflow script text) counts.
    try:
        lines = raw.decode("utf-8-sig").splitlines()
    except UnicodeError as exc:
        raise G34Denied("F139_V19_G34_OWNER_LOG_NOT_UTF8") from exc
    def one(marker):
        prefix = "F139_I1138_" + marker + "="
        found = []
        for line in lines:
            idx = line.find(prefix)
            if idx >= 0 and line[idx:idx + len(prefix)] == prefix:
                chunk = line[idx+len(prefix):]
                if chunk.startswith("{") and chunk.endswith("}"):
                    found.append(chunk)
        require(len(found) == 1, "OWNER_" + marker + "_MISSING_DUPLICATE")
        return json_obj(found[0].encode("utf-8"), "OWNER_" + marker)
    ledger = one("ORIGINAL_OWNER_POSTFAIL_CUSTODY")
    task = one("ORIGINAL_OWNER_TASK_READONLY")
    require(ledger.get("schema") ==
                "forge.f139.v19.i1138.postfailed-custody.readonly.v1"
            and ledger.get("source_sha") == OWNER_SOURCE
            and ledger.get("issue") == ISSUE
            and ledger.get("ticket") == TICKET
            and ledger.get("original_run") == PROVIDER_RUN
            and ledger.get("head_seq") == 322
            and ledger.get("head_sha256") == OWNER_LEDGER_HASH
            and ledger.get("stage") == "QUARANTINED"
            and ledger.get("quarantine_reason") == "FAILED_OR_CANCELLED_NO_REPLAY"
            and ledger.get("native_inflight") == 0
            and ledger.get("run_id") is None
            and ledger.get("manual_dispatch") is False
            and ledger.get("original_sqlite_writes") == 0
            and ledger.get("github_writes") == 0
            and ledger.get("scientific_first_use") is False,
            "ORIGINAL_LEDGER_NO_REPLAY_INVALID")
    expected_events = [
        ("ATTEMPT_QUARANTINED", 322),
        ("NATIVE_FAILED_PROVIDER_CUSTODY", 321),
        ("DISPATCH_POST_RETURNED", 320),
        ("BEFORE_DISPATCH_INTENT", 319),
        ("TASK_INTAKE", 318),
        ("NATIVE_DEVELOPMENT_ADMITTED", 317),
    ]
    require([(x.get("kind"), x.get("seq"))
             for x in ledger.get("recent_events", [])] == expected_events,
            "OWNER_LEDGER_EVENT_SEQUENCE_DRIFT")
    require(task.get("task_state") == "Running"
            and task.get("same_original_task") is True
            and task.get("worker_run_completed_failure") is True
            and task.get("original_sqlite_writes") == 0
            and task.get("github_writes") == 0
            and task.get("task_changes") == 0,
            "OWNER_READONLY_TASK_WITNESS_INVALID")
    return {"head_seq": 322, "head_sha256": OWNER_LEDGER_HASH,
            "stage": "QUARANTINED",
            "original_failed_job_consumer": True,
            "verified_as_historical_readonly_observation": True,
            "real_owner_HMAC_verified_by_this_gate": False,
            "contemporaneous_process_running_verified": False}


def provider_artifacts(raw, zip_blobs):
    listing = json_obj(raw, "PROVIDER_ARTIFACTS")
    require(type(listing.get("artifacts")) is list
            and type(listing.get("total_count")) is int
            and listing["total_count"] == len(listing["artifacts"])
            and set(zip_blobs) == set(EXPECTED),
            "PROVIDER_ARTIFACT_INVENTORY_INVALID")
    reports = {}
    for platform, pinned in EXPECTED.items():
        rows = [a for a in listing["artifacts"] if type(a) is dict
                and a.get("id") == pinned["id"]]
        require(len(rows) == 1, "MISSING_ARTIFACT_" + platform)
        meta = rows[0]
        require(meta.get("name") == pinned["name"]
                and meta.get("digest") == "sha256:" + pinned["digest"]
                and meta.get("expired") is False
                and type(meta.get("size_in_bytes")) is int
                and 0 < meta["size_in_bytes"] <= 100_000
                and meta.get("archive_download_url") ==
                    "https://api.github.com/repos/spoonman136668-ai/FORGE/actions/artifacts/"
                    + str(pinned["id"]) + "/zip"
                and type(meta.get("workflow_run")) is dict
                and meta["workflow_run"].get("id") == PROVIDER_RUN
                and meta["workflow_run"].get("head_sha") == OWNER_SOURCE,
                "ARTIFACT_METADATA_INVALID_" + platform)
        raw_zip = zip_blobs[platform]
        require(type(raw_zip) is bytes
                and len(raw_zip) == meta["size_in_bytes"]
                and sha(raw_zip) == pinned["digest"],
                "ARTIFACT_ZIP_INTEGRITY_INVALID_" + platform)
        try:
            with zipfile.ZipFile(io.BytesIO(raw_zip)) as z:
                entries = z.infolist()
                require(len(entries) == len(ZIP_NAMES)
                        and {i.filename for i in entries} == ZIP_NAMES
                        and all(not x.is_dir() and
                                not (x.flag_bits & 1) and
                                0 < x.file_size < MAX_INPUT and
                                0 < x.compress_size < MAX_INPUT
                                for x in entries),
                        "ARTIFACT_ZIP_INVENTORY_" + platform)
                data = {name: z.read(name) for name in ZIP_NAMES}
        except (ValueError, OSError, RuntimeError, zipfile.BadZipFile) as exc:
            if isinstance(exc, G34Denied):
                raise
            raise G34Denied("F139_V19_G34_ZIP_UNREADABLE_" + platform) from exc
        digestline = (sha(data["f139-receipt.json"]) +
                      "  f139-receipt.json\n").encode("ascii")
        require(data["f139-receipt.sha256"] in
                (digestline, digestline.replace(b"\n", b"\r\n")),
                "RECEIPT_DIGESTFILE_INVALID_" + platform)
        receipt = json_obj(data["f139-receipt.json"], "RECEIPT_" + platform)
        report = json_obj(data["f139-native-report.json"], "REPORT_" + platform)
        require(receipt.get("schema") ==
                    "forge.f139.nci04.native-execution-receipt.v1"
                and receipt.get("ticket") == TICKET
                and receipt.get("source_sha") == OWNER_SOURCE
                and receipt.get("run_id") == PROVIDER_RUN
                and receipt.get("os") == platform
                and receipt.get("native_qualified") is False
                and receipt.get("development_only") is True
                and receipt.get("scientific_first_use_authorized") is False
                and receipt.get("accepted_ref_mutations") == 0
                and receipt.get("paid_model_calls") == 0
                and receipt.get("local_custody_verified") is False
                and receipt.get("controller_unattended_verified") is False
                and receipt.get("target_commit") == TARGET
                and receipt.get("target_tree_sha") == SOURCE_TREE,
                "ORIGINAL_NEGATIVE_RECEIPT_INVALID_" + platform)
        require(report.get("qualification_complete") is False
                and report.get("target_commit") == TARGET
                and report.get("target_tree_sha") == SOURCE_TREE
                and report.get("scientific_first_use") is False,
                "ORIGINAL_NEGATIVE_REPORT_INVALID_" + platform)
        require(receipt.get("native_report_sha256") ==
                sha(canonical(report)), "REPORT_DIGEST_BINDING_INVALID_" + platform)
        reports[platform] = {
            "artifact_id": pinned["id"],
            "original_zip_sha256": pinned["digest"],
            "native_qualified": False,
            "receipt_sha256": sha(data["f139-receipt.json"]),
            "report_sha256": sha(data["f139-native-report.json"])}
    return reports


def verify_source(run_blob, owner_run_blob, job_blob, artifact_blob,
                  linux_zip, windows_zip, owner_logs):
    provider = json_obj(run_blob, "PROVIDER_RUN")
    owner = json_obj(owner_run_blob, "OWNER_RUN")
    job = json_obj(job_blob, "OWNER_JOBS")
    validate_run(provider, run_id=PROVIDER_RUN, source=OWNER_SOURCE,
                 result="failure", event="workflow_dispatch",
                 branch="f139-owner-release-" + OWNER_SOURCE)
    validate_run(owner, run_id=OWNER_RUN, source=OWNER_HEAD,
                 result="success", event="push",
                 branch="qualification/f139-v19-i1138-postfailed-custody-ro-20261029")
    jobs = job.get("jobs")
    require(type(jobs) is list
            and len([j for j in jobs if
                     type(j) is dict and j.get("id") == OWNER_JOB and
                     j.get("conclusion") == "success" and
                     j.get("name") == "inspect-original"]) == 1,
            "OWNER_WITNESS_JOB_IDENTITY_INVALID")
    owner_record = owner_log_extract(owner_logs)
    reports = provider_artifacts(
        artifact_blob, {"ubuntu-latest": linux_zip,
                        "windows-latest": windows_zip})
    return {
        "schema": SCHEMA, "original_owner_source_sha": OWNER_SOURCE,
        "original_provider_failed_run_id": PROVIDER_RUN,
        "original_owner_readonly_run_id": OWNER_RUN,
        "original_owner_readonly_job_id": OWNER_JOB,
        "original_owner_historical_custody": owner_record,
        "original_os_failed_provider_receipts": reports,
        "original_negative_preserved": True,
        "signed_native_v3_provider_success": False,
        "genuine_v3_provider_keys_provisioned": False,
        "new_owner_admission_and_consumption_verified": False,
        "continuous_autonomous_native_development_restored": False,
        "production_release_authorized": False,
        "scientific_first_use": False,
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    base = args.input.resolve(strict=True)
    files = ("provider-run.json", "owner-run.json", "owner-jobs.json",
             "provider-artifacts.json", "linux.zip", "windows.zip", "owner.log")
    require(base.is_dir() and not base.is_symlink()
            and sorted(x.name for x in base.iterdir()) == sorted(files)
            and all((base / n).is_file()
                    and not (base / n).is_symlink() for n in files),
            "INPUT_FILE_SCOPE_INVALID")
    result = verify_source(*((base / n).read_bytes() for n in files))
    require(args.output.parent.is_dir() and not args.output.exists(),
            "OUTPUT_NOT_ISOLATED")
    args.output.write_bytes(canonical(result))
    print("F139_G34_ORIGINAL_FAILED_PROVIDER_ZIPS=READONLY_AUTHENTICATED")
    print("F139_G34_ORIGINAL_OWNER_QUARANTINE=READONLY_AUTHENTICATED")
    print("F139_G34_REAL_NEW_PROVIDER_SIGNING=NOT_VERIFIED")
    print("F139_G34_REAL_NEW_OWNER_SQLITE_CONSUMPTION=NOT_VERIFIED")
    print("F139_G34_AUTONOMY=NOT_RESTORED")
    print("F139_G34_PRODUCTION_RELEASE=HOLD")


if __name__ == "__main__":
    try:
        main()
    except (G34Denied, OSError) as exc:
        raise SystemExit("F139_V19_G34_FAIL_CLOSED " + str(exc)) from exc

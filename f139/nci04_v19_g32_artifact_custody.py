"""F139 V19 G32: strictly read-only custody of authentic G29 Actions artifacts.

The GitHub-hosted downloader authenticates metadata and ZIP transport with a
read-only Actions token. This module receives *only files*; it never receives a
credential or contacts GitHub. A digest is not an independent signer. No owner,
worker, ledger, dispatch, accepted-ref or scientific authority is granted.
"""
from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path
import re
import zipfile

from f139.nci04_v19_g31_diagnostic_reconcile import reconcile, G31Denied

REPO = "spoonman136668-ai/FORGE"
RUN = 40885501321
SOURCE = "21a28b17ed5c0d544bec924d85cc2f74c7454ae3"
BRANCH = "research/f139-v19-g29-inherited-negative-inventory-20261029"
SCHEMA = "forge.f139.v19.g32.github-diagnostic-artifact-custody.v1"
EXPECTED = {
    "linux": (12900619626, "f139-g29-inherited-negative-ubuntu-latest",
              "f139-g29-inherited-Linux.json",
              "4cd4bf9a236dff693e35173e2c4774b6a0cf6abf0cfc2d6724903ab6e21a5c19"),
    "windows": (12901923435, "f139-g29-inherited-negative-windows-latest",
                "f139-g29-inherited-Windows.json",
                "8f47dae9acc904d778aea5874795b11d92f8d1ec2feb5aee2834f43dd4d0e15e"),
}
DIGEST = re.compile(r"[0-9a-f]{64}\Z")
MAX_ZIP = 100_000
MAX_JSON = 400_000


class G32Denied(ValueError):
    pass


def require(ok, reason):
    if not ok:
        raise G32Denied("F139_V19_G32_" + reason)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) +
            "\n").encode("utf-8")


def json_object(raw, label, *, strict=False):
    require(type(raw) is bytes and 0 < len(raw) < MAX_JSON,
            label + "_SIZE_INVALID")
    try:
        value = json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeError) as exc:
        raise G32Denied("F139_V19_G32_" + label + "_JSON_INVALID") from exc
    require(type(value) is dict, label + "_NOT_OBJECT")
    if strict:
        require(canonical(value) == raw, label + "_NONCANONICAL")
    return value


def verify_run(run):
    require(type(run) is dict and run.get("id") == RUN
            and type(run["id"]) is int
            and run.get("head_sha") == SOURCE
            and run.get("head_branch") == BRANCH
            and run.get("event") == "push"
            and run.get("run_attempt") == 1
            and type(run["run_attempt"]) is int
            and run.get("status") == "completed"
            and run.get("conclusion") == "success"
            and run.get("repository", {}).get("full_name") == REPO
            and run.get("head_repository", {}).get("full_name") == REPO
            and run.get("actor", {}).get("login") == "spoonman136668-ai",
            "RUN_PROVENANCE_INVALID")


def artifact_object(artifacts, platform):
    identifier, name, _, expected_digest = EXPECTED[platform]
    require(type(artifacts) is dict
            and type(artifacts.get("artifacts")) is list
            and type(artifacts.get("total_count")) is int
            and artifacts["total_count"] == len(artifacts["artifacts"]),
            "ARTIFACT_LIST_INCOMPLETE")
    exact = [a for a in artifacts["artifacts"]
             if type(a) is dict and a.get("name") == name]
    require(len(exact) == 1, "MISSING_OR_DUPLICATE_" + platform.upper())
    a = exact[0]
    require(a.get("id") == identifier and type(a["id"]) is int
            and a.get("name") == name
            and a.get("digest") == "sha256:" + expected_digest
            and a.get("expired") is False
            and type(a.get("size_in_bytes")) is int
            and 0 < a["size_in_bytes"] < MAX_ZIP
            and a.get("archive_download_url") ==
                "https://api.github.com/repos/" + REPO +
                "/actions/artifacts/" + str(identifier) + "/zip",
            "ARTIFACT_PROVENANCE_INVALID_" + platform.upper())
    bound = a.get("workflow_run")
    if bound is not None:
        require(type(bound) is dict and bound.get("id") == RUN
                and bound.get("head_sha") == SOURCE,
                "ARTIFACT_WORKFLOW_BINDING_INVALID")
    return a


def open_artifact(raw, metadata, platform):
    _, _, member, expected_digest = EXPECTED[platform]
    require(type(raw) is bytes and 0 < len(raw) < MAX_ZIP,
            "ZIP_SIZE_INVALID_" + platform.upper())
    require(len(raw) == metadata["size_in_bytes"]
            and sha(raw) == expected_digest
            and metadata["digest"] == "sha256:" + sha(raw),
            "ZIP_SHA_OR_SIZE_MISMATCH_" + platform.upper())
    try:
        with zipfile.ZipFile(io.BytesIO(raw), "r") as bundle:
            info = bundle.infolist()
            require(len(info) == 1 and info[0].filename == member,
                    "ZIP_MEMBER_SET_INVALID_" + platform.upper())
            entry = info[0]
            require(not entry.is_dir() and not (entry.flag_bits & 1)
                    and 0 < entry.file_size < MAX_JSON
                    and entry.compress_size < MAX_ZIP
                    and (entry.external_attr >> 16) & 0o170000 != 0o120000,
                    "ZIP_UNSAFE_MEMBER_" + platform.upper())
            data = bundle.read(entry)
    except (OSError, ValueError, RuntimeError, zipfile.BadZipFile, EOFError) as exc:
        if isinstance(exc, G32Denied):
            raise
        raise G32Denied("F139_V19_G32_ZIP_INVALID_" + platform.upper()) from exc
    return json_object(data, platform.upper() + "_G29", strict=True)


def verify(run_data, artifact_data, linux_zip, windows_zip):
    run = json_object(run_data, "RUN")
    verify_run(run)
    listing = json_object(artifact_data, "ARTIFACTS")
    a = artifact_object(listing, "linux")
    b = artifact_object(listing, "windows")
    linux = open_artifact(linux_zip, a, "linux")
    windows = open_artifact(windows_zip, b, "windows")
    try:
        diagnostic = reconcile(linux, windows)
    except G31Denied as exc:
        raise G32Denied("F139_V19_G32_G31_DIAGNOSTIC_REJECTED") from exc
    require(diagnostic.get("native_qualified") is False
            and diagnostic.get("signed_provider_success") is False
            and diagnostic.get("production_release_authorized") is False
            and diagnostic.get("windows_historical_regression") ==
                "NEGATIVE_RETAINED",
            "FALSE_SUCCESS_CLASSIFICATION")
    return {
        "schema": SCHEMA,
        "source_run_id": RUN,
        "source_run_sha": SOURCE,
        "git_authenticated_metadata_download_required": True,
        "original_artifact_ids": {
            platform: EXPECTED[platform][0] for platform in EXPECTED},
        "original_zip_sha256": {
            platform: EXPECTED[platform][3] for platform in EXPECTED},
        "report_sha256": {
            "linux": sha(canonical(linux)), "windows": sha(canonical(windows))},
        "diagnostic": diagnostic,
        "provider_receipt_signed": False,
        "original_owner_consumed": False,
        "native_qualified": False,
        "full_native_worker_regression_qualified": False,
        "production_release_authorized": False,
        "scientific_first_use": False,
    }


def from_files(folder: Path):
    folder = folder.resolve(strict=True)
    require(folder.is_dir() and not folder.is_symlink(),
            "INPUT_DIRECTORY_INVALID")
    inputs = ("run.json", "artifacts.json", "linux.zip", "windows.zip")
    require(sorted(x.name for x in folder.iterdir()) == sorted(inputs)
            and all((folder / name).is_file()
                    and not (folder / name).is_symlink() for name in inputs),
            "INPUT_FILES_INVALID")
    return verify(*(folder / x).read_bytes() for x in inputs)


def main():
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--input", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    report = from_files(args.input)
    require(not args.output.exists() and args.output.parent.is_dir(),
            "OUTPUT_ALREADY_EXISTS_OR_PARENT_MISSING")
    args.output.write_bytes(canonical(report))
    print("F139_V19_G32_REAL_ACTIONS_ARTIFACT_CUSTODY=PASS")
    print("F139_V19_G32_ZIP_SHA256_AND_METADATA=PASS")
    print("F139_V19_G32_G29_HISTORICAL_WINDOWS_NEGATIVE=RETAINED")
    print("F139_V19_G32_SIGNED_PROVIDER=NOT_QUALIFIED")
    print("F139_V19_G32_ORIGINAL_OWNER_CONSUMPTION=NOT_QUALIFIED")
    print("F139_V19_G32_PRODUCTION_RELEASE=HOLD")
    print("F139_V19_G32_REPORT_SHA256=" + sha(args.output.read_bytes()))


if __name__ == "__main__":
    try:
        main()
    except (OSError, G32Denied) as exc:
        raise SystemExit("F139_V19_G32_FAIL_CLOSED " + str(exc)) from exc

"""Independent source-bound read of existing *negative* G32 reports.

Read-only GitHub metadata and ZIP files are collected by CI using a temporary
actions:read token. This verifier has neither token nor owner/provider keys.
No new signed native receipt or controller action is produced.
"""
from __future__ import annotations
import argparse
import io
import json
from pathlib import Path
import zipfile

from f139.nci04_v19_g32_artifact_custody import canonical, sha
from f139.nci04_v19_g33_signature_contract import (
    SCHEMA, inspect_real_g32_pair, G33Denied)

G32_RUN = 40947362897
G32_HEAD = "3ed0efefc1986e247154c90fe0f5cb9d42c66277"
REPO = "spoonman136668-ai/FORGE"
ORIGINAL = {
    "linux": (12929263863,
              "f139-v19-g32-readonly-original-g29-custody-ubuntu-24.04",
              "20c141f6b2f78e7b7c86217a98cb6923bceeab043d1db74c620707ce246b45cf"),
    "windows": (12929448135,
                "f139-v19-g32-readonly-original-g29-custody-windows-2022",
                "226beb6a21ecb95ee053b9770a21fac284b74b79b7d3acb7ba4ceebe7f7feb1d"),
}
MEMBER = "f139-v19-g32-authentic-g29-report.json"
MAX_ZIP = 100_000


def require(cond, code):
    if not cond:
        raise G33Denied("F139_V19_G33_REAL_G32_" + code)


def parse(raw):
    require(type(raw) is bytes and 0 < len(raw) < MAX_ZIP, "JSON_SIZE")
    try:
        obj = json.loads(raw)
    except (ValueError, UnicodeError) as exc:
        raise G33Denied("F139_V19_G33_REAL_G32_BAD_JSON") from exc
    require(type(obj) is dict, "NONOBJECT")
    return obj


def verify_from_files(folder):
    folder = Path(folder).resolve(strict=True)
    require(folder.is_dir() and not folder.is_symlink(), "DIRECTORY_INVALID")
    require(sorted(p.name for p in folder.iterdir()) ==
            ["artifacts.json", "linux.zip", "run.json", "windows.zip"],
            "FILE_INVENTORY_INVALID")
    for child in folder.iterdir():
        require(child.is_file() and not child.is_symlink(), "FILE_TYPE_INVALID")
    run = parse((folder / "run.json").read_bytes())
    require(run.get("id") == G32_RUN and type(run.get("id")) is int
            and run.get("head_sha") == G32_HEAD
            and run.get("head_branch") ==
                "research/f139-v19-g32-github-artifact-custody-20261029"
            and run.get("run_attempt") == 1 and
                type(run.get("run_attempt")) is int
            and run.get("status") == "completed"
            and run.get("conclusion") == "success"
            and run.get("event") == "push"
            and run.get("repository", {}).get("full_name") == REPO
            and run.get("head_repository", {}).get("full_name") == REPO
            and run.get("actor", {}).get("login") == "spoonman136668-ai",
            "AUTHENTICATED_RUN_OR_SOURCE_INVALID")
    a = parse((folder / "artifacts.json").read_bytes())
    require(type(a.get("total_count")) is int and a["total_count"] == 2
            and type(a.get("artifacts")) is list
            and len(a["artifacts"]) == 2, "ARTIFACT_COUNT_INVALID")
    reports = {}
    for platform, (expected_id, name, digest) in ORIGINAL.items():
        rows = [x for x in a["artifacts"] if
                type(x) is dict and x.get("id") == expected_id]
        require(len(rows) == 1, "ARTIFACT_MISSING_" + platform)
        record = rows[0]
        require(record.get("name") == name
                and record.get("digest") == "sha256:" + digest
                and record.get("expired") is False
                and type(record.get("size_in_bytes")) is int
                and 0 < record["size_in_bytes"] < MAX_ZIP
                and record.get("archive_download_url") ==
                    "https://api.github.com/repos/" + REPO +
                    "/actions/artifacts/" + str(expected_id) + "/zip"
                and type(record.get("workflow_run")) is dict
                and record["workflow_run"].get("id") == G32_RUN
                and record["workflow_run"].get("head_sha") == G32_HEAD,
                "METADATA_SOURCE_INVALID_" + platform)
        blob = (folder / (platform + ".zip")).read_bytes()
        require(len(blob) == record["size_in_bytes"]
                and sha(blob) == digest, "ZIP_AUTHENTICITY_INVALID_" + platform)
        try:
            with zipfile.ZipFile(io.BytesIO(blob)) as archive:
                contents = archive.infolist()
                require(len(contents) == 1 and contents[0].filename == MEMBER
                        and not contents[0].is_dir()
                        and not (contents[0].flag_bits & 1)
                        and 0 < contents[0].file_size < MAX_ZIP
                        and contents[0].compress_size < MAX_ZIP,
                        "ZIP_MEMBER_INVENTORY_INVALID_" + platform)
                report_raw = archive.read(MEMBER)
        except (ValueError, RuntimeError, OSError, zipfile.BadZipFile) as exc:
            raise G33Denied("F139_V19_G33_REAL_G32_ZIP_UNREADABLE") from exc
        report = parse(report_raw)
        require(canonical(report) == report_raw,
                "G32_CANONICAL_RECORD_MISMATCH_" + platform)
        reports[platform] = report
    out = inspect_real_g32_pair(reports["linux"], reports["windows"])
    require(out["production_release_authorized"] is False,
            "DIAGNOSTIC_FALSE_PROMOTION")
    return {"schema": SCHEMA, "original_g32_run": G32_RUN,
            "original_g32_head": G32_HEAD,
            "actual_g32_report_digest": sha(canonical(reports["linux"])),
            "original_zip_sha256": {p: ORIGINAL[p][2] for p in ORIGINAL},
            "origin_checked_using_actions_read": True,
            "negative_g32_retained": out,
            "genuine_provider_signed_v3_receipts": False,
            "original_owner_sqlite_consumption": False,
            "native_qualified": False,
            "production_release_authorized": False,
            "scientific_first_use": False}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    report = verify_from_files(args.input)
    require(args.output.parent.is_dir() and not args.output.exists(),
            "OUTPUT_NOT_FRESH")
    args.output.write_bytes(canonical(report))
    print("F139_V19_G33_REAL_G32_ARTIFACTS=VERIFIED_NEGATIVE")
    print("F139_V19_G33_REAL_PROVIDER_SIGNED_V3=NOT_QUALIFIED")
    print("F139_V19_G33_REAL_ORIGINAL_OWNER_CONSUMPTION=NOT_QUALIFIED")
    print("F139_V19_G33_PRODUCTION_RELEASE=HOLD")


if __name__ == "__main__":
    try:
        main()
    except (G33Denied, OSError) as exc:
        raise SystemExit("F139_V19_G33_FAIL_CLOSED " + str(exc)) from exc

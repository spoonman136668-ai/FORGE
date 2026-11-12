"""F138-C2: inspect a complete authenticated GitHub Actions artifact *member* archive.

This is read-only, no GitHub token, dispatch, persistence automation, scientific
admission or production state mutation. A content hash is integrity, NOT an
independent issuer signature. The exact GitHub ZIP envelope is not retained;
the exact bytes of every original archive member are.
"""
from __future__ import annotations
import base64
import binascii
import hashlib
import json
import lzma
from pathlib import Path
import re
import struct

ROOT = Path(__file__).resolve().parents[1]
BUNDLE = ROOT / "reference/research-intake/f138-c2-provider-39124429721.members.xz.b64"
SOURCE = "e2fca32e0d4439aed801dac6b697ecea28855017"
PROVIDER_ARTIFACT = 12135755671
ORIGINAL_ZIP_SHA256 = "f9aadbfd12a22c199a46c8b0e2a15b309721101d6aa982f30d0679996cb11b0c"
PACKED_SHA256 = "c52e6ed950d5c4f8fc10d5efce926d7253e5880e8e75b7efbbb2b8b332ffdbf5"
COMPRESSED_SHA256 = "290e5d21c7071bb3fe0300e240484d6b64d10fef2382a4900c5abaf8b9d84dde"
SNAPSHOT_SHA256 = "db33583bba8dab8e9782f1ec57b26fd55de17a20a6ce48406516910f7e11cfa7"
DECISION_SHA256 = "99bcac81fa37c89f5e1890a97a95043842a31a7f4d1b4fcffb123fc5a822a2f4"
MAGIC = b"F138C2A1"
PARENTS = (39119993456, 39121294863, 39122641881, 39123993228)
CHILDREN = (39120007064, 39121310943, 39122657120, 39124007071)
OS = ("ubuntu-latest", "windows-latest")
SHA64 = re.compile(r"^[a-f0-9]{64}$")
MAX_PACKED = 160_000

class InvalidCustody(ValueError):
    pass

def demand(value, failure):
    if not value:
        raise InvalidCustody("F138_C2_" + failure)

def sha(data):
    return hashlib.sha256(data).hexdigest()

def load_bundle(path=BUNDLE):
    data = Path(path).read_bytes()
    demand(0 < len(data) < 20_000, "B64_SIZE")
    try:
        coded = b"".join(data.split())
        compressed = base64.b64decode(coded, validate=True)
        demand(sha(compressed) == COMPRESSED_SHA256, "COMPRESSED_HASH_DRIFT")
        obj = lzma.LZMADecompressor(format=lzma.FORMAT_XZ)
        packed = obj.decompress(compressed, max_length=MAX_PACKED)
        demand(obj.eof and not obj.unused_data and sha(packed) == PACKED_SHA256,
               "PACKED_HASH_DRIFT")
    except (ValueError, lzma.LZMAError, binascii.Error, EOFError) as exc:
        if isinstance(exc, InvalidCustody):
            raise
        raise InvalidCustody("F138_C2_DECODING_REJECTED") from exc
    return unpack(packed)

def names_expected():
    names = {"snapshot.json", "snapshot.json.sha256", "decision.json",
             "decision.json.sha256"}
    names.update(str(pid) + "/decision.json" for pid in PARENTS)
    for child in CHILDREN:
        for osname in OS:
            for suffix in ("json", "sha256"):
                names.add(f"{child}/{osname}/f138-lineage.{suffix}")
    return names

def unpack(packed):
    demand(type(packed) is bytes and len(packed) <= MAX_PACKED
           and packed[:8] == MAGIC and len(packed) >= 12, "MAGIC_OR_BOUND")
    count = struct.unpack_from(">I", packed, 8)[0]
    demand(count == 24, "EXACT_MEMBER_COUNT")
    i = 12
    output = {}
    for _ in range(count):
        demand(i + 6 <= len(packed), "MEMBER_HEADER_TRUNCATED")
        n, size = struct.unpack_from(">HI", packed, i)
        i += 6
        demand(0 < n < 128 and 0 < size < 100_000 and i+n+size <= len(packed),
               "MEMBER_BOUND")
        try:
            name = packed[i:i+n].decode("utf-8")
        except UnicodeDecodeError as ex:
            raise InvalidCustody("F138_C2_FILENAME_UTF8") from ex
        i += n
        demand(name not in output and name in names_expected(),
               "UNKNOWN_OR_DUPLICATE_MEMBER")
        output[name] = packed[i:i+size]
        i += size
    demand(i == len(packed) and set(output) == names_expected(),
           "MEMBER_SET_INCOMPLETE")
    return output

def strict_json(data):
    demand(type(data) is bytes and len(data) < 100_000, "JSON_BOUND")
    def no_dupe(pairs):
        d = {}
        for k,v in pairs:
            demand(k not in d, "DUPLICATE_JSON_KEY")
            d[k] = v
        return d
    try:
        return json.loads(data, object_pairs_hook=no_dupe,
                          parse_constant=lambda x: demand(False, "NONFINITE"))
    except (UnicodeError, ValueError) as ex:
        if isinstance(ex, InvalidCustody):
            raise
        raise InvalidCustody("F138_C2_JSON_INVALID") from ex

def check_receipt(files, name):
    data = files[name]
    expected = sha(data) + "  " + name.split("/")[-1] + "\n"
    receipt = files[name + ".sha256"] if name.endswith("snapshot.json") or name.endswith("decision.json") and "/" not in name else None
    # Per-OS witness locations: f138-lineage.json + f138-lineage.sha256.
    if receipt is None:
        receipt = files[name[:-4] + "sha256"]
    demand(receipt == expected.encode("ascii"), "SHA256_RECEIPT_MISMATCH")

def assert_provider(snapshot, decision, files):
    demand(type(snapshot) is dict and type(decision) is dict, "SOURCE_TYPES")
    demand(snapshot.get("schema") == "forge.autonomy.f138.provider-snapshot.v1"
           and snapshot.get("source_sha") == SOURCE
           and snapshot.get("merged_at") == "2026-10-18T10:26:37Z"
           and decision.get("schema") == "forge.autonomy.f138.continuity-decision.v1"
           and decision.get("source_sha") == SOURCE
           and decision.get("verdict") == "PENDING"
           and decision.get("verified_unattended_runs") == 4
           and decision.get("genuine_scheduled_count") == 0
           and decision.get("windows_recovery_continuity_verified") is True
           and decision.get("permanent_custody_verified") is False
           and decision.get("scientific_first_use_authorized") is False
           and decision.get("accepted_ref_mutations") == 0,
           "FALSE_FULL_ADMISSION")
    def idx(block, key):
        demand(type(block) is dict and type(block.get("total_count")) is int
               and type(block.get(key)) is list
               and block["total_count"] == len(block[key]), "TRUNCATED_PROVIDER_HISTORY")
        rows = block[key]
        ids = [x.get("id") for x in rows]
        demand(all(type(x) is int and x > 0 for x in ids)
               and len(set(ids)) == len(ids), "DUPLICATE_PROVIDER_RECORDS")
        return {x["id"]: x for x in rows}
    children = idx(snapshot.get("integrated_index"), "workflow_runs")
    controllers = idx(snapshot.get("controller_index"), "workflow_runs")
    demand(len(children) == 45 and len(controllers) == 43,
           "HISTORY_SIZE_MISMATCH")
    demand(type(snapshot.get("jobs")) is dict
           and type(snapshot.get("artifacts")) is dict,
           "INDEX_DATA_MISSING")
    demand(type(decision.get("evidence")) is list
           and len(decision["evidence"]) == 4
           and [e.get("run_id") for e in decision["evidence"]] == list(CHILDREN),
           "WRONG_SOURCE_COHORT")
    previous_end = ""
    nonces = set()
    for p,c,e in zip(PARENTS,CHILDREN,decision["evidence"]):
        parent_row, child_row = controllers.get(p), children.get(c)
        demand(type(parent_row) is dict and type(child_row) is dict
               and parent_row.get("event") == child_row.get("event") == "workflow_dispatch"
               and parent_row.get("head_sha") == child_row.get("head_sha") == SOURCE
               and parent_row.get("run_attempt") == child_row.get("run_attempt") == 1
               and parent_row.get("conclusion") == child_row.get("conclusion") == "success"
               and parent_row.get("status") == child_row.get("status") == "completed"
               and child_row.get("created_at") == e.get("created_at")
               and child_row.get("updated_at") == e.get("updated_at")
               and (not previous_end or previous_end < child_row.get("created_at")),
               "RUN_REPLAY_OVERLAP_OR_DRIFT")
        previous_end = child_row["updated_at"]
        control = strict_json(files[f"{p}/decision.json"])
        demand(control.get("controller_run_id") == p
               and control.get("source_sha") == SOURCE
               and control.get("dispatch") is True
               and control.get("origin") == "f137-windows-recovery"
               and control.get("reasons") == []
               and control.get("daily_cap") == 96
               and control.get("genuine_schedule_claim") is False
               and control.get("scientific_first_use_authorized") is False
               and control.get("science_originals") == 0
               and control.get("accepted_ref_mutations") == 0
               and control.get("paid_api_calls") == 0
               and control.get("codex_calls") == 0
               and control.get("wake_nonce") == e.get("nonce")
               and control["wake_nonce"] not in nonces,
               "CONTROLLER_UNQUALIFIED")
        nonces.add(control["wake_nonce"])
        reports = []
        for osname in OS:
            name = f"{c}/{osname}/f138-lineage.json"
            check_receipt(files, name)
            child = strict_json(files[name])
            demand(child.get("schema") == "forge.autonomy.f138.development-lineage.v1"
                   and child.get("parent_run_id") == p
                   and child.get("parent_source_sha") == SOURCE
                   and child.get("run_id") == c and child.get("source_sha") == SOURCE
                   and child.get("repository") == "spoonman136668-ai/FORGE"
                   and child.get("run_attempt") == 1
                   and child.get("origin") == "f137-windows-recovery"
                   and child.get("event") == "workflow_dispatch"
                   and child.get("genuine_integrated_schedule") is False
                   and child.get("scientific_first_use_authorized") is False
                   and child.get("accepted_ref_mutations") == 0
                   and child.get("scientific_originals_dispatched") == 0
                   and child.get("optimizer_promotions") == 0
                   and child.get("codex_calls") == 0 and child.get("paid_model_calls") == 0,
                   "CROSS_PLATFORM_FALSE_AUTHORITY")
            reports.append(files[name])
            artifacts = idx(snapshot["artifacts"].get(str(c)), "artifacts")
            demand(any(x.get("name") == f"forge-f138-lineage-{osname}"
                       and x.get("expired") is False
                       and x.get("workflow_run",{}).get("id") == c
                       for x in artifacts.values()), "PROVIDER_ARTIFACT_MISSING")
        demand(reports[0] == reports[1], "CROSS_OS_REPORT_DIFF")
        jobs = idx(snapshot["jobs"].get(str(c)), "jobs")
        required = {"two-lane-synthetic (ubuntu-latest)",
                    "two-lane-synthetic (windows-latest)", "f129-durable-cross-run-proof"}
        demand(required.issubset({job.get("name") for job in jobs.values()
                                  if job.get("status") == "completed"
                                  and job.get("conclusion") == "success"}),
               "DEVELOPMENT_JOB_FAILED")
    return {"schema":"forge.autonomy.f138.c2-member-custody-proof.v1",
            "source_sha":SOURCE,"source_run_id":39124429721,
            "source_artifact_id":PROVIDER_ARTIFACT,
            "source_artifact_zip_sha256":ORIGINAL_ZIP_SHA256,
            "archive_member_count":len(files),
            "provider_integrated_history_count":len(children),
            "provider_controller_history_count":len(controllers),
            "controller_source_decisions":len(PARENTS),
            "os_lineage_reports":len(CHILDREN)*len(OS),
            "all_original_archive_member_bytes_preserved":True,
            "original_github_zip_envelope_preserved":False,
            "permanent_main_custody_qualified":False,
            "genuine_direct_schedules_in_captured_cohort":0,
            "f138_operational_verdict":"PENDING",
            "scientific_first_use_authorized":False,
            "accepted_ref_mutations":0}

def verify(files):
    demand(type(files) is dict and set(files) == names_expected(),
           "INCORRECT_MEMBERS")
    demand(sha(files["snapshot.json"]) == SNAPSHOT_SHA256
           and sha(files["decision.json"]) == DECISION_SHA256,
           "SOURCE_HASH_DRIFT")
    for f in ("snapshot.json","decision.json"):
        check_receipt(files,f)
    return assert_provider(strict_json(files["snapshot.json"]),
                           strict_json(files["decision.json"]),files)

if __name__ == "__main__":
    import sys
    try:
        result = verify(load_bundle())
    except (InvalidCustody, OSError) as exc:
        sys.exit("F138_C2_FAIL_CLOSED: " + str(exc))
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    print("F138_C2_EXACT_MEMBER_BYTES=PASS")
    print("F138_C2_COMPLETE_PROVIDER_HISTORY=PASS")
    print("F138_C2_GENUINE_SCHEDULED_CONTINUITY=PENDING")

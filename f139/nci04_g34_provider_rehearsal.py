"""G34: synthetic V2 inner ZIP for an actual GitHub Actions upload.

No original owner signing, actual native execution or scientific authorization.
"""
import argparse
import os
from pathlib import Path
import re
import subprocess
from f139.nci04_native_contract import canonical, digest
from f139.nci04_signed_native import NativeAdmission
from f139.nci04_worker_v2 import receipt_v2
from f139.nci04_v2_artifact_package import (
    PACKAGE, INPUT_RECEIPT, INPUT_REPORT, package_v2_development_output,
)
from f139.nci04_provider_receipt_v2 import verify_v2_provider_zip
from f139.test_nci04_worker_v2 import V2ContractTests


class G34Denied(ValueError):
    pass


def require(ok, reason):
    if not ok:
        raise G34Denied("F139_G34_" + reason)


def build_fixture(output, source_sha, platform):
    require(isinstance(source_sha, str) and re.fullmatch(r"[a-f0-9]{40}", source_sha)
            and platform in ("ubuntu-latest", "windows-latest")
            and ((os.name == "nt") == (platform == "windows-latest")),
            "SOURCE_OR_PLATFORM_INVALID")
    output = Path(output)
    require(output.is_dir() and not output.is_symlink()
            and not any(output.iterdir()), "OUTPUT_NOT_FRESH")
    fixture = V2ContractTests()
    fixture.setUp()
    candidate = fixture.c
    number = 991234
    admission = NativeAdmission(
        "f139-nci04-i" + str(number) + "-" + source_sha[:12] +
        "-" + candidate.intent_sha256[:8],
        "Yggdrasil", source_sha, 1, platform, number, 991234567, candidate,
        digest(b"NOT_REAL_OWNER_SIGNATURE_G34_SYNTHETIC_ONLY"))
    report = fixture.report(platform)
    receipt = receipt_v2(admission, report)
    require(receipt["development_only"] and
            not receipt["scientific_first_use_authorized"], "AUTHORITY_DRIFT")
    (output / INPUT_RECEIPT).write_bytes(canonical(receipt))
    (output / INPUT_REPORT).write_bytes(canonical(report))
    proof = package_v2_development_output(output, admission)
    inner = (output / PACKAGE).read_bytes()
    fake_local_meta = {
        "digest": "sha256:" + digest(inner), "size_in_bytes": len(inner),
        "run_id": admission.run_id, "runner_os": platform,
        "source_sha": source_sha}
    result = verify_v2_provider_zip(inner, fake_local_meta, admission)
    require(result["qualified"] and proof["zip_sha256"] == digest(inner)
            and not proof["provider_origin_authenticated"], "V2_ZIP_ROUNDTRIP")
    return {"sha256": digest(inner), "synthetic": True,
            "owner_dispatch": False, "native_execution": False,
            "provider_origin_authenticated": False, "science": False}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--output", required=True, type=Path)
    args = p.parse_args()
    e = os.environ
    require(e.get("GITHUB_REPOSITORY") == "spoonman136668-ai/FORGE"
            and e.get("GITHUB_EVENT_NAME") == "pull_request"
            and re.fullmatch(r"refs/pull/[1-9][0-9]*/merge",
                             e.get("GITHUB_REF", ""))
            and not any(e.get(k) for k in
                        ("F139_WORKER_HMAC_KEY", "GH_TOKEN", "GITHUB_TOKEN",
                         "OPENAI_API_KEY", "CLOUDFLARE_API_TOKEN")),
            "PR_ONLY_WITHOUT_OWNER_KEY")
    source = e.get("GITHUB_SHA")
    git = subprocess.run(["git", "rev-parse", "HEAD"], check=False,
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                         timeout=10)
    require(git.returncode == 0 and
            git.stdout.decode("ascii").strip() == source,
            "CHECKOUT_SOURCE_DRIFT")
    platform = "windows-latest" if os.name == "nt" else "ubuntu-latest"
    proof = build_fixture(args.output, source, platform)
    print("F139_G34_SYNTHETIC_G14_INNER_ZIP=" + proof["sha256"])
    print("F139_G34_ORIGINAL_OWNER_AND_NATIVE_EXECUTION=NOT_TESTED")


if __name__ == "__main__":
    main()

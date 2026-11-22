"""D2K isolated job binding (not standalone authentication).

Trust requires protected workflow's successful secret-bearing d2k-admit
prerequisite through GitHub needs.<job>.outputs. No new controller or signer.
"""
from __future__ import annotations
import argparse
import hashlib
import hmac
import json
import os
import re

from f139.verify_ticket import D2K_PACKAGES, REPO, admit, demand, inputs_from_env

SCHEMA = "forge.f139.d2k.job-bound-authorization.v1"
FIELDS = (
    "repository", "ref", "event", "head_sha", "run_attempt", "run_id",
    "ticket", "lane", "source_sha", "epoch", "signature",
    "issue_number", "issue_id", "body_sha256", "target_package",
)


def digest(inputs):
    demand(inputs.get("repository") == REPO
           and inputs.get("ref") == "refs/heads/main"
           and inputs.get("event") == "workflow_dispatch"
           and inputs.get("head_sha") == inputs.get("source_sha")
           and inputs.get("run_attempt") == "1"
           and isinstance(inputs.get("ticket"), str)
           and inputs["ticket"].startswith("f139-d2k-")
           and inputs.get("lane") in ("Wingless", "Yggdrasil", "Qualification")
           and inputs.get("target_package") in D2K_PACKAGES
           and isinstance(inputs.get("signature"), str)
           and re.fullmatch(r"[a-f0-9]{64}", inputs["signature"]),
           "D2K_UNTRUSTED_JOB_IDENTITY")
    payload = {"schema": SCHEMA}
    for field in FIELDS:
        demand(isinstance(inputs.get(field), str), "D2K_UNTRUSTED_JOB_FIELD")
        payload[field] = inputs[field]
    return hashlib.sha256(
        (json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n").encode()
    ).hexdigest()


def authorize(inputs):
    """Only the secret-bearing admission job issues this bound job output."""
    admit(inputs)
    return digest(inputs)


def verify_claim(inputs, environ):
    """Credential-free job checks the prereq's original-bound job output."""
    demand(environ.get("GITHUB_JOB") == "d2k-execute",
           "D2K_CREDENTIAL_FREE_JOB_REQUIRED")
    demand(not any(environ.get(k) for k in (
        "F139_WORKER_HMAC_KEY", "GH_TOKEN", "GITHUB_TOKEN", "OPENAI_API_KEY")),
        "D2K_EXECUTION_HAS_CREDENTIALS")
    token = environ.get("F139_D2K_AUTHORIZATION_SHA256", "")
    demand(isinstance(token, str) and re.fullmatch(r"[a-f0-9]{64}", token),
           "D2K_AUTHORIZED_JOB_OUTPUT_MISSING")
    demand(hmac.compare_digest(digest(inputs), token),
           "D2K_AUTHORIZED_JOB_OUTPUT_MISMATCH")
    demand(inputs.get("os") in ("ubuntu-latest", "windows-latest"),
           "D2K_RUNNER_OS_UNTRUSTED")
    return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("authorize", "verify"))
    args = parser.parse_args()
    inputs = inputs_from_env()
    if args.mode == "authorize":
        print(authorize(inputs))
    else:
        verify_claim(inputs, os.environ)
        print("F139_D2K_CREDENTIAL_FREE_JOB_BOUND=PASS")


if __name__ == "__main__":
    main()

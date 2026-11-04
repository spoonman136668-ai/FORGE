"""Bounded, read-only same-owner gh-config diagnostic; no credential export.

Job tokens are excluded from child environments. This tests the owner's stored
CLI context, which may differ from the running controller's inherited context.
No authentication repair, dispatch, retry, or owner-state mutation is permitted.
"""
from __future__ import annotations

import json
import os
import re
import subprocess

OWNER_SOURCE = "5680e7448276a9f257413570e0283fcab7e392ec"
OWNER_API_STDOUT_LIMIT = 2_100_000
ROUTES = (
    "repos/spoonman136668-ai/FORGE/branches/main",
    "repos/spoonman136668-ai/FORGE/actions/runs?per_page=1",
    "repos/spoonman136668-ai/Yggdrasil/pulls?state=open&per_page=1",
    "repos/spoonman136668-ai/FORGE/issues/807",
    "repos/spoonman136668-ai/FORGE/branches/f139-owner-release-" + OWNER_SOURCE,
    "repos/spoonman136668-ai/FORGE/compare/" + OWNER_SOURCE + "...80ae30719bcd9f179da4aa4e8f14dc36fd15818e",
    "repos/spoonman136668-ai/FORGE/actions/workflows/forge-development-succession.yml",
    "repos/spoonman136668-ai/FORGE/actions/workflows/forge-development-succession.yml/runs?per_page=100",
    "repos/spoonman136668-ai/FORGE/actions/workflows/forge-integrated-synthetic-cycle.yml",
    "repos/spoonman136668-ai/FORGE/actions/workflows/forge-integrated-synthetic-cycle.yml/runs?per_page=100",
    "repos/spoonman136668-ai/FORGE/actions/workflows/forge-f139-development-worker.yml/runs?branch=f139-owner-release-" + OWNER_SOURCE + "&event=workflow_dispatch&per_page=100&page=1",
)
ENV_KEYS = frozenset({
    "PATH", "PATHEXT", "SYSTEMROOT", "WINDIR", "SYSTEMDRIVE", "COMSPEC",
    "HOME", "USERPROFILE", "APPDATA", "LOCALAPPDATA", "TMP", "TEMP",
    "GH_CONFIG_DIR", "HTTPS_PROXY", "HTTP_PROXY", "NO_PROXY",
    "SSL_CERT_FILE", "SSL_CERT_DIR", "LANG", "LC_ALL",
})


def probe(*, environment=None, runner=subprocess.run):
    source = os.environ if environment is None else environment
    env = {k: v for k, v in source.items() if k.upper() in ENV_KEYS}
    env.update(GH_PROMPT_DISABLED="1", GIT_TERMINAL_PROMPT="0")
    rows = []
    for route in ROUTES:
        argv = ["gh", "api", "--hostname", "github.com", "--method", "GET",
                "--include", route]
        try:
            result = runner(argv, env=env, stdin=subprocess.DEVNULL,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            timeout=20, check=False)
            raw = result.stdout or b""
            error = result.stderr or b""
            match = re.search(rb"(?m)^HTTP/[0-9.]+\s+([0-9]{3})\b", raw)
            if match is None:
                match = re.search(rb"\bHTTP ([0-9]{3})\b", error)
            status = int(match[1]) if match else None
            if status == 200 and result.returncode == 0:
                classification = "READ_OK"
            elif status == 401:
                classification = "AUTHENTICATION_REJECTED"
            elif status == 403:
                classification = "FORBIDDEN_OR_RATE_LIMITED"
            elif status == 429:
                classification = "RATE_LIMITED"
            elif status is not None:
                classification = "HTTP_FAILURE"
            elif b"gh auth login" in error or b"GH_TOKEN" in error:
                classification = "NO_CLI_AUTHENTICATION"
            else:
                classification = "CLI_OR_TRANSPORT_FAILURE"
            remaining = re.search(rb"(?im)^x-ratelimit-remaining:\s*([0-9]+)\s*$", raw)
            if status == 403 and remaining and int(remaining[1]) == 0:
                classification = "RATE_LIMITED"
            separator = b"\r\n\r\n" if b"\r\n\r\n" in raw else b"\n\n"
            body_bytes = len(raw.split(separator, 1)[1]) if separator in raw else None
            rows.append({"route": route, "classification": classification,
                         "response_body_bytes": body_bytes,
                         "original_stdout_limit_exceeded": body_bytes >= OWNER_API_STDOUT_LIMIT if body_bytes is not None else None,
                         "http_status": status, "exit_code": result.returncode,
                         "rate_limit_remaining": int(remaining[1]) if remaining else None})
        except subprocess.TimeoutExpired:
            rows.append({"route": route, "classification": "READ_TIMEOUT",
                         "http_status": None, "exit_code": None,
                         "rate_limit_remaining": None})
        except FileNotFoundError:
            rows.append({"route": route, "classification": "CLI_NOT_FOUND",
                         "http_status": None, "exit_code": None,
                         "rate_limit_remaining": None})
    return {"schema": "forge.f139.owner-gh-config-readonly-probe.v1",
            "owner_source_scope": OWNER_SOURCE,
            "original_stdout_limit": OWNER_API_STDOUT_LIMIT,
            "credential_context": "same-owner-gh-config-without-job-tokens",
            "controller_inherited_environment_verified": False,
            "raw_output_retained": False, "credential_mutations": 0,
            "owner_mutations": 0, "dispatches": 0, "retries": 0,
            "scientific_first_use": False, "reads": rows}


if __name__ == "__main__":
    print("F139_OWNER_GH_CONFIG_READONLY=" + json.dumps(probe(), sort_keys=True))

"""Bounded, issue-specific Go package diagnostic. Not code generation or science."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

from f139.verify_ticket import (
    D2K_DIAGNOSTIC_SCHEMA, D2K_PACKAGES, admit, inputs_from_env, demand,
)

MAX_OUTPUT = 100000
MAX_EXCERPT = 12000
TIMEOUT_SEC = 110

def diagnose(inputs: dict, *, command_runner=subprocess.run, clock=time.monotonic):
    admit(inputs)
    demand(inputs["ticket"].startswith("f139-d2k-")
           and inputs["target_package"] in D2K_PACKAGES,
           "D2K_TARGET_NOT_AUTHORIZED")
    env = os.environ.copy()
    env.pop("F139_WORKER_HMAC_KEY", None)
    env.pop("GH_TOKEN", None)
    env.pop("GITHUB_TOKEN", None)
    cmd = ["go", "test", "-count=1", "-timeout=90s", inputs["target_package"]]
    began=clock()
    try:
        process = command_runner(cmd, check=False, stdin=subprocess.DEVNULL,
                                 stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                 timeout=TIMEOUT_SEC, env=env)
        raw=process.stdout if isinstance(process.stdout,bytes) else b""
        demand(len(raw) <= MAX_OUTPUT,"D2K_OUTPUT_TOO_LARGE")
        code=int(process.returncode)
        outcome="PASS" if code==0 else "TEST_FAILURE"
        demand(0 <= code <= 255, "D2K_EXIT_CODE_INVALID")
    except subprocess.TimeoutExpired as exc:
        raw=exc.stdout if isinstance(exc.stdout,bytes) else b""
        demand(len(raw) <= MAX_OUTPUT, "D2K_TIMEOUT_OUTPUT_TOO_LARGE")
        code=-1
        outcome="TIMEOUT"
    milliseconds=min(120000,max(0,round((clock()-began)*1000)))
    return {
        "schema":D2K_DIAGNOSTIC_SCHEMA,
        "source_sha":inputs["head_sha"],
        "issue_number":int(inputs["issue_number"]),
        "issue_id":int(inputs["issue_id"]),
        "body_sha256":inputs["body_sha256"],
        "target_package":inputs["target_package"],
        "run_id":int(inputs["run_id"]),
        "os":inputs["os"],
        "outcome":outcome,
        "returncode":code,
        "duration_ms":milliseconds,
        "output_sha256":hashlib.sha256(raw).hexdigest(),
        "output_excerpt":raw[:MAX_EXCERPT].decode("utf-8",errors="replace"),
        "output_bytes":len(raw),
        "scientific_first_use":False,
        "paid_model_calls":0,
    }

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    demand(args.output.parent.is_dir() and not args.output.exists(),
           "D2K_OUTPUT_PATH_EXISTS")
    report=diagnose(inputs_from_env())
    data=(json.dumps(report,sort_keys=True,separators=(",",":"),ensure_ascii=True)+"\n").encode()
    demand(len(data) <= 32768, "D2K_RESULT_OVERSIZE")
    with args.output.open("xb") as fp:
        fp.write(data)
        fp.flush()
        os.fsync(fp.fileno())
    print("F139_D2K_PACKAGE_DIAGNOSTIC_RECORDED="+report["outcome"])
    print("F139_D2K_SCIENCE_ORIGINALS=ZERO")

if __name__=="__main__":
    main()

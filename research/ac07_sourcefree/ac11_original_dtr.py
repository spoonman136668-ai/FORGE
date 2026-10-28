"""AC-11: install ORIGINAL pinned CausalGym dependencies in an isolated runner venv.

This is an authentic, externally authored DTR public-development smoke only.
No scientific first-use, hidden counterfactual calls, model training, stub,
generated substitute environment, or modified upstream source is allowed.
A packaging error is durable BLOCKED evidence, not a fake PASS.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import venv

import ac10_upstream_contract as ac10

SCHEMA = "forge.ac11.original-dtr-public-compatibility.v1"
MAX_INSTALL_SECONDS = 420
MAX_CHILD_SECONDS = 45
SMOKE_SEEDS = (759011, 759013)
PUBLIC_FIELDS = frozenset(ac10.PROTO["allowed_event_fields"])
FORBIDDEN = frozenset(ac10.PROTO["forbidden_to_learner"])

# The only exchange between authentic source process and the driver is the
# restricted public tuple. The learner has no reference to the upstream SCM.
_SMOKE_CHILD = r"""
import json
from causal_gym.envs.dtr import DTRPCH
from causal_gym.core.task import Task, LearningRegime

forbidden={"u","env","get_graph","ctf_do","full_info","oracle",
           "private_scm","source_code"}
allowed={"stage","observation","action","next_observation",
         "reward","terminated","truncated","valid_actions"}
rows=[]
seeds=(759011,759013)
for seed in seeds:
    env=DTRPCH()
    env.task=Task(learning_regime=LearningRegime.do)
    # Test that the real PCH task disallows counterfactual intervention.
    try:
        env.ctf_do(lambda *_: 0)
    except PermissionError:
        ctf_denied=True
    else:
        raise AssertionError("COUNTERFACTUAL_PERMISSION_NOT_DENIED")
    s1,reset_info=env.reset(seed=seed)
    assert int(s1) in (0,1) and reset_info["stage"]==0
    # Only the wrapper's public do-policy interface is used. Policy takes
    # public inputs but returns a fixed action. It never reads hidden u/SCM.
    s2,reward1,term1,trunc1,private_info1=env.do(lambda *_: 0)
    assert int(s2) in (0,1) and int(reward1)==0
    assert term1 is False and trunc1 is False
    obs2,reward2,term2,trunc2,private_info2=env.do(lambda *_: 1)
    assert obs2 is None and int(reward2) in (0,1)
    assert term2 is True and trunc2 is False
    # Never serialize or expose raw info or the env object. The output is
    # reconstructed explicitly from the safe public API tuple only.
    events=(
       dict(stage=0,observation=int(s1),action=0,
            next_observation=int(s2),reward=int(reward1),
            terminated=bool(term1),truncated=bool(trunc1),
            valid_actions=[0,1]),
       dict(stage=1,observation=int(s2),action=1,
            next_observation=None,reward=int(reward2),
            terminated=bool(term2),truncated=bool(trunc2),
            valid_actions=[0,1])
    )
    assert all(set(event)==allowed and not (set(event)&forbidden)
               for event in events)
    rows.append({"seed":seed,"events":events,
                 "ctf_do_permission_denied":ctf_denied})
print(json.dumps({"schema":"forge.ac11.actual-upstream-public-smoke.v1",
                  "source_owned_episodes":len(rows),
                  "source_owned_actions":sum(len(x["events"]) for x in rows),
                  "records":rows,
                  "learner_receives_unfiltered_info":False,
                  "source_env_exposed_to_learner":False,
                  "native_model_trained":False,
                  "original_scientific_first_use":False},sort_keys=True))
"""

def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def run_cmd(argv, *, cwd, env=None, timeout=60):
    start=time.monotonic_ns()
    try:
        result=subprocess.run(argv,cwd=cwd,env=env,capture_output=True,
                              timeout=timeout,check=False)
        return result.returncode, result.stdout, result.stderr, time.monotonic_ns()-start,False
    except subprocess.TimeoutExpired as exc:
        return None,exc.stdout or b"",exc.stderr or b"",time.monotonic_ns()-start,True

def classification(stderr:bytes, timeout:bool):
    if timeout:return "UPSTREAM_DEPENDENCY_TIMEOUT"
    if b"ModuleNotFoundError" in stderr:return "UPSTREAM_MODULE_NOT_FOUND"
    if b"Failed building wheel" in stderr or b"build wheel" in stderr.lower():return "UPSTREAM_BUILD_FAILURE"
    if b"ERROR:" in stderr:return "UPSTREAM_INSTALL_ERROR"
    return "UPSTREAM_RUNTIME_OR_PACKAGING_ERROR"

def validate_smoke(report):
    if report["schema"]!="forge.ac11.actual-upstream-public-smoke.v1":
        raise RuntimeError("AC11_PUBLIC_REPORT_SCHEMA_MISMATCH")
    if [x["seed"] for x in report["records"]]!=list(SMOKE_SEEDS):
        raise RuntimeError("AC11_SMOKE_SEED_DRIFT")
    if report["source_owned_episodes"]!=2 or report["source_owned_actions"]!=4:
        raise RuntimeError("AC11_STAGE_OR_EPISODE_MISMATCH")
    if report["learner_receives_unfiltered_info"] or report["source_env_exposed_to_learner"]:
        raise RuntimeError("AC11_PRIVILEGED_INFORMATION_EXPOSED")
    if report["native_model_trained"] or report["original_scientific_first_use"]:
        raise RuntimeError("AC11_ILLICIT_SCIENCE_CLAIM")
    for record in report["records"]:
        if record["ctf_do_permission_denied"] is not True:
            raise RuntimeError("AC11_FORBIDDEN_COUNTERFACTUAL_PERMISSION")
        if len(record["events"])!=2:
            raise RuntimeError("AC11_PUBLIC_STAGE_COUNT")
        for event in record["events"]:
            if set(event)!=PUBLIC_FIELDS or set(event)&FORBIDDEN:
                raise RuntimeError("AC11_PUBLIC_DATA_ALLOWLIST_BROKEN")
            if event["action"] not in (0,1) or event["reward"] not in (0,1):
                raise RuntimeError("AC11_INVALID_PUBLIC_TRANSITION")
            if event["valid_actions"]!=[0,1]:
                raise RuntimeError("AC11_INVALID_ACTION_RIGHTS")
        if record["events"][0]["terminated"] or not record["events"][1]["terminated"]:
            raise RuntimeError("AC11_WRONG_TERMINAL_STAGE")

def run(upstream: Path, out: Path, freeze_path:Path, venv_path:Path):
    inspected=ac10.inspect_upstream(upstream)
    # Refuse running from a checkout with changed source identity. No hidden
    # scientific family or FIT/VALID/DEV seed is exposed or consumed.
    if tuple(ac10.PROTO["public_smoke_seeds"]) != SMOKE_SEEDS:
        raise RuntimeError("AC11_PREDECLARED_SEED_DRIFT")
    if venv_path.resolve().is_relative_to(upstream.resolve()):
        raise RuntimeError("AC11_VENV_INSIDE_UPSTREAM_FORBIDDEN")
    venv.EnvBuilder(with_pip=True,clear=False).create(venv_path)
    py=(venv_path/("Scripts/python.exe" if os.name=="nt" else "bin/python"))
    if not py.is_file():
        raise RuntimeError("AC11_EPHEMERAL_PYTHON_MISSING")
    env=os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"]="1"
    env["PYTHONPATH"]=str(upstream.resolve())
    env["PIP_DISABLE_PIP_VERSION_CHECK"]="1"
    env["PIP_NO_INPUT"]="1"
    env["PIP_NO_CACHE_DIR"]="1"
    env["PIP_RETRIES"]="1"
    env["PIP_DEFAULT_TIMEOUT"]="20"
    # Install the *source repository's actual setup.py* requirements, not a
    # forged lightweight replacement, editable fork or artificial stub.
    install=[str(py),"-m","pip","install","--no-cache-dir","--no-input",
             "--disable-pip-version-check",str(upstream.resolve())]
    rc,stdout,stderr,elapsed,timeout=run_cmd(
        install,cwd=venv_path,env=env,timeout=MAX_INSTALL_SECONDS
    )
    status="DEPENDENCY_INSTALL_BLOCKED"
    diagnostic=classification(stderr,timeout) if (rc!=0 or timeout) else None
    import_status="NOT_ATTEMPTED_INSTALL_BLOCKED"
    source_smoke=None
    if rc==0:
        status="DEPENDENCIES_INSTALLED"
        import_cmd=[str(py),"-B","-c",
                    "from causal_gym.envs.dtr import DTRPCH,DTRSCM;print('REAL_ORIGINAL_IMPORT_OK')"]
        irc,io,ie,_,it=run_cmd(import_cmd,cwd=venv_path,env=env,timeout=MAX_CHILD_SECONDS)
        if irc==0 and b"REAL_ORIGINAL_IMPORT_OK" in io:
            import_status="ORIGINAL_IMPORT_PASS"
            src_rc,src_out,src_err,_,src_timeout=run_cmd(
                [str(py),"-B","-c",_SMOKE_CHILD],
                cwd=venv_path,env=env,timeout=MAX_CHILD_SECONDS)
            if src_rc==0 and not src_timeout:
                try:
                    source_smoke=json.loads(src_out.decode("utf-8").strip())
                    validate_smoke(source_smoke)
                    status="ACTUAL_SOURCE_PUBLIC_SMOKE_PASS"
                except (UnicodeError,json.JSONDecodeError,RuntimeError) as exc:
                    diagnostic="PUBLIC_OUTPUT_VALIDATION_FAILED:"+type(exc).__name__
                    status="PUBLIC_SMOKE_BLOCKED"
            else:
                status="PUBLIC_SMOKE_BLOCKED"
                diagnostic=classification(src_err,src_timeout)
        else:
            import_status="ORIGINAL_IMPORT_BLOCKED"
            status="ORIGINAL_IMPORT_BLOCKED"
            diagnostic=classification(ie,it)
    freeze_path.parent.mkdir(parents=True,exist_ok=True)
    fr_rc,fr_out,_,_,fr_to=run_cmd(
        [str(py),"-m","pip","freeze"],cwd=venv_path,env=env,timeout=20
    )
    frozen=fr_out.decode("utf-8","replace") if fr_rc==0 and not fr_to else ""
    freeze_path.write_text(frozen,encoding="utf-8")
    report={
        "schema":SCHEMA,"scope":"AUTHENTIC_SOURCE_PUBLIC_DEVELOPMENT_ONLY",
        "upstream_source_sha":inspected["sha"],
        "upstream_tree_sha":inspected["tree"],
        "upstream_verified_git_blobs":inspected["verified_git_blobs"],
        "upstream_original_dtr_sha256":inspected["dtr_original_git_blob_sha256"],
        "original_setup_py_used":True,
        "full_declared_dependency_install_attempted":True,
        "install_limit_seconds":MAX_INSTALL_SECONDS,
        "install_return_code":rc,"install_timed_out":timeout,
        "install_wall_ns":elapsed,
        "install_log_stdout_sha256":sha(stdout),
        "install_log_stderr_sha256":sha(stderr),
        "installation_diagnostic":diagnostic,
        "full_freeze_sha256":sha(frozen.encode("utf-8")),
        "dependency_freeze_entry_count":len(frozen.splitlines()),
        "upstream_import_status":import_status,
        "public_development_smoke_status":status,
        "public_smoke":source_smoke,
        "source_owned_episodes_executed":2 if source_smoke is not None and status=="ACTUAL_SOURCE_PUBLIC_SMOKE_PASS" else 0,
        "source_owned_actions_executed":4 if source_smoke is not None and status=="ACTUAL_SOURCE_PUBLIC_SMOKE_PASS" else 0,
        "reserved_fit_seeds_used":False,
        "reserved_validation_seeds_used":False,
        "reserved_dev_seeds_used":False,
        "native_model_training_performed":False,
        "real_scientific_first_use":False,
        "independent_original_source_birth_attested":False,
        "accepted_model_or_controller_modified":False,
        "no_stubs_and_no_source_edit":True
    }
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    return report

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--upstream",type=Path,required=True)
    ap.add_argument("--out",type=Path,required=True)
    ap.add_argument("--freeze",type=Path,required=True)
    ap.add_argument("--venv",type=Path,required=True)
    a=ap.parse_args()
    result=run(a.upstream,a.out,a.freeze,a.venv)
    print("AC11_SOURCE_IDENTITY="+result["upstream_source_sha"])
    print("AC11_PACKAGE_STATUS="+result["public_development_smoke_status"])
    print("AC11_IMPORT_STATUS="+result["upstream_import_status"])
    print("AC11_REPORT_SHA256="+sha(a.out.read_bytes()))
    print("AC11_SCIENTIFIC_FIRST_USE=FALSE")

if __name__=="__main__":
    main()

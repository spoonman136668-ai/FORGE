"""AC-12: authentic upstream import repair, source-only public-development gate.

Reuses verified AC-11 isolated venv; adds ONLY genuine pinned Minigrid wheel
if and only if the original unmodified import fails with missing "minigrid".
No stubs, no modified upstream, no original science, no native model fitting.
Next missing module is reported accurately, never papered over.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
import time
import ac10_upstream_contract as ac10
import ac11_original_dtr as ac11

SCHEMA="forge.ac12.source-native-missing-dependency.v1"
PINNED_EXTRA="minigrid==2.3.1"
# https://pypi.org/project/minigrid/2.3.1/
# PyPI published py3-none-any wheel with known SHA-256; pin wheel artifact
# in addition to package version, not an attacker-selected transitive package.
MINIGRID_WHEEL_SHA256="6e841a9f95378abe1fdb053d4dfaead1613ceb2fa1e9548a8525882fbdb4f6f3"
IMPORT_CMD="from causal_gym.envs.dtr import DTRPCH,DTRSCM;print('AC12_ORIGINAL_DTR_IMPORT_OK')"
EXCEPTION_PATTERN=re.compile(rb"(?:ModuleNotFoundError|ImportError): No module named ['\"]([A-Za-z0-9_.-]{1,100})['\"]")
MAX_IMPORT_SECONDS=40
MAX_INSTALL_SECONDS=105

def read_exception(stderr: bytes) -> dict:
    match=EXCEPTION_PATTERN.search(stderr[-16384:])
    if match:
        return {"kind":"MISSING_MODULE","module":match.group(1).decode("ascii")}
    if b"ImportError" in stderr:
        return {"kind":"IMPORT_ERROR_OTHER","module":None}
    if b"AttributeError" in stderr:
        return {"kind":"UPSTREAM_ATTRIBUTE_ERROR","module":None}
    if b"ModuleNotFoundError" in stderr:
        return {"kind":"MISSING_MODULE_UNPARSED","module":None}
    return {"kind":"OTHER_OR_NO_ERROR","module":None}

def sha(data: bytes)->str:
    return hashlib.sha256(data).hexdigest()

def classify_import(py: Path, root: Path, env: dict) -> dict:
    rc,out,err,ns,timeout=ac11.run_cmd(
        [str(py),"-B","-c",IMPORT_CMD],cwd=root,env=env,timeout=MAX_IMPORT_SECONDS)
    ok=rc==0 and b"AC12_ORIGINAL_DTR_IMPORT_OK" in out and not timeout
    return {
        "status":"ORIGINAL_IMPORT_PASS" if ok else ("ORIGINAL_IMPORT_TIMEOUT" if timeout else "ORIGINAL_IMPORT_BLOCKED"),
        "return_code":rc,"timed_out":timeout,"wall_ns":ns,
        "exception":read_exception(err),
        "stderr_sha256":sha(err),"stdout_sha256":sha(out)
    }

def run(upstream:Path,venv:Path,out:Path,freeze:Path):
    original=ac10.inspect_upstream(upstream)
    venv=venv.resolve(strict=True)
    py=venv/("Scripts/python.exe" if sys.platform=="win32" else "bin/python")
    if not py.is_file():
        raise RuntimeError("AC12_VERIFIED_AC11_VENV_MISSING")
    if venv.is_relative_to(upstream.resolve()):
        raise RuntimeError("AC12_NO_VENV_INSIDE_ORIGINAL_UPSTREAM")
    # Re-verify source before any install, pin only original repo checkout.
    env=__import__("os").environ.copy()
    env.update({"PYTHONPATH":str(upstream.resolve()),"PYTHONDONTWRITEBYTECODE":"1",
                "PIP_DISABLE_PIP_VERSION_CHECK":"1","PIP_NO_INPUT":"1",
                "PIP_NO_CACHE_DIR":"1","PIP_RETRIES":"1",
                "PIP_DEFAULT_TIMEOUT":"20"})
    before=classify_import(py,upstream,env)
    install_attempted=False
    actual_wheel_verified=False
    install_rc=None
    install_timeout=False
    install_wall_ns=None
    install_stdout_hash=None
    install_stderr_hash=None
    dependency_install_error=None
    after=before
    if before["status"]=="ORIGINAL_IMPORT_BLOCKED" and before["exception"]=={"kind":"MISSING_MODULE","module":"minigrid"}:
        install_attempted=True
        # Fetch exact PyPI wheel by version; validate its unchanged content
        # BEFORE installation, then install the downloaded artifact, no source fork.
        wheels=out.parent/"ac12-wheelhouse"
        wheels.mkdir(parents=True,exist_ok=True)
        download=[str(py),"-m","pip","download","--no-cache-dir","--no-input",
                  "--only-binary=:all:","--no-deps","--dest",str(wheels),
                  PINNED_EXTRA]
        drc,dout,derr,dns,dtimeout=ac11.run_cmd(
            download,cwd=venv,env=env,timeout=MAX_INSTALL_SECONDS)
        expected=wheels/"minigrid-2.3.1-py3-none-any.whl"
        if drc==0 and not dtimeout and expected.is_file() and sha(expected.read_bytes())==MINIGRID_WHEEL_SHA256:
            actual_wheel_verified=True
            # Install the exact verified wheel and its legitimate dependencies,
            # rather than any replacement module or unpredictable PyPI version.
            ins=[str(py),"-m","pip","install","--no-cache-dir","--no-input",
                 "--disable-pip-version-check",str(expected)]
            install_rc,iout,ierr,install_wall_ns,install_timeout=ac11.run_cmd(
                ins,cwd=venv,env=env,timeout=MAX_INSTALL_SECONDS)
            install_stdout_hash=sha(iout); install_stderr_hash=sha(ierr)
            if install_rc!=0 or install_timeout:
                dependency_install_error=ac11.classification(ierr,install_timeout)
            else:
                after=classify_import(py,upstream,env)
        else:
            dependency_install_error="PYPI_WHEEL_UNAVAILABLE_OR_SHA256_MISMATCH"
            install_rc=drc;install_timeout=dtimeout;install_wall_ns=dns
            install_stdout_hash=sha(dout);install_stderr_hash=sha(derr)
    elif before["status"]!="ORIGINAL_IMPORT_PASS":
        dependency_install_error="FIRST_IMPORT_NOT_MINIGRID_NO_UNAPPROVED_INSTALL"

    # Only original, permissions-checked public smoke; no fallback source,
    # no reserved FIT/VALID/DEV/unknown-family seeds and no native model.
    smoke_status="NOT_ATTEMPTED_IMPORT_BLOCKED"
    smoke_attempted=False
    smoke_count=0
    action_count=0
    smoke=None
    smoke_exception=None
    if after["status"]=="ORIGINAL_IMPORT_PASS":
        smoke_attempted=True
        src_rc,src_out,src_err,_,src_timeout=ac11.run_cmd(
            [str(py),"-B","-c",ac11._SMOKE_CHILD],cwd=upstream,env=env,timeout=ac11.MAX_CHILD_SECONDS)
        if src_rc==0 and not src_timeout:
            try:
                smoke=json.loads(src_out.decode("utf-8").strip())
                ac11.validate_smoke(smoke)
                smoke_status="ACTUAL_ORIGINAL_PUBLIC_SMOKE_PASS"
                smoke_count=smoke["source_owned_episodes"]
                action_count=smoke["source_owned_actions"]
            except (ValueError,UnicodeError,RuntimeError,KeyError) as exc:
                smoke_status="PUBLIC_SMOKE_BLOCKED"
                smoke_exception="VALIDATION_"+type(exc).__name__
        else:
            smoke_status="PUBLIC_SMOKE_BLOCKED"
            smoke_exception=ac11.classification(src_err,src_timeout)
        if smoke_status!="ACTUAL_ORIGINAL_PUBLIC_SMOKE_PASS":
            # Some source-owned actions may have executed before error.
            smoke_count=None
            action_count=None
            smoke=None
    fr_rc,fr_out,_,_,fr_timeout=ac11.run_cmd(
        [str(py),"-m","pip","freeze"],cwd=venv,env=env,timeout=25)
    frozen=fr_out.decode("utf-8","replace") if fr_rc==0 and not fr_timeout else ""
    freeze.parent.mkdir(parents=True,exist_ok=True)
    freeze.write_text(frozen,encoding="utf-8")
    result={
        "schema":SCHEMA,
        "scope":"EXACT_AUTHENTIC_UPSTREAM_PUBLIC_DEVELOPMENT_ONLY",
        "original_source_sha":original["sha"],"original_source_tree":original["tree"],
        "original_git_blobs":original["verified_git_blobs"],
        "original_dtr_sha256":original["dtr_original_git_blob_sha256"],
        "first_original_import":before,
        "pinned_extra_name":PINNED_EXTRA,
        "pinned_wheel_sha256":MINIGRID_WHEEL_SHA256,
        "pinned_extra_install_attempted":install_attempted,
        "authentic_pypi_wheel_sha256_verified":actual_wheel_verified,
        "dependency_install_return_code":install_rc,
        "dependency_install_timed_out":install_timeout,
        "dependency_install_wall_ns":install_wall_ns,
        "dependency_install_stdout_sha256":install_stdout_hash,
        "dependency_install_stderr_sha256":install_stderr_hash,
        "dependency_install_error":dependency_install_error,
        "original_import_after_pinned_extra":after,
        "public_smoke_status":smoke_status,
        "public_smoke_attempted":smoke_attempted,
        "public_smoke":smoke,
        "smoke_error_class":smoke_exception,
        "source_public_episodes_executed":smoke_count,
        "source_public_actions_executed":action_count,
        "reserved_fit_validation_dev_seeds_used":False,
        "science_unknown_family_touched":False,
        "fitted_models_count":0,"native_model_modified":False,
        "original_first_use_authorized":False,
        "scientific_admission":False,"forged_causal_source_created":False,
        "source_files_edited":False,"controller_or_queue_mutated":False,
        "freeze_sha256":sha(frozen.encode("utf-8")),
        "freeze_packages":len(frozen.splitlines())
    }
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    return result

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--upstream",type=Path,required=True)
    p.add_argument("--venv",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    p.add_argument("--freeze",type=Path,required=True)
    a=p.parse_args()
    r=run(a.upstream,a.venv,a.out,a.freeze)
    print("AC12_ORIGINAL_FIRST_EXCEPTION="+str(r["first_original_import"]["exception"]["module"]))
    print("AC12_WHEEL_IDENTITY="+str(r["authentic_pypi_wheel_sha256_verified"]))
    print("AC12_ORIGINAL_IMPORT_AFTER="+r["original_import_after_pinned_extra"]["status"])
    print("AC12_PUBLIC_SMOKE="+r["public_smoke_status"])
    print("AC12_FIRST_USE=NO")

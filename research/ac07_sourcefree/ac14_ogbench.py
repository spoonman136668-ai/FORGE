"""AC-14: authenticate real PyPI OGBench wheel and check untouched original DTR.

No alternate environment, unverified artifact, native model training, FSA
scientific first use, controller or source editing. Only preregistered public
smoke seeds may be consumed once the original real import succeeds.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import urllib.request
import urllib.error

import ac10_upstream_contract as ac10
import ac11_original_dtr as ac11
import ac12_import_repair as ac12
import ac13_cpu_torchvision as ac13

SCHEMA="forge.ac14.original-ogbench-compatibility.v1"
VERSION="1.2.1"
WHEEL=f"ogbench-{VERSION}-py3-none-any.whl"
WHEEL_SHA256="597ac2207935e4edc46de5d5742e940a753f2329e18612e9cfe7f9e857435f83"
WHEEL_BYTES=8940331
PYPI_JSON=f"https://pypi.org/pypi/ogbench/{VERSION}/json"
MAX_WHEEL_DOWNLOAD=120
MAX_WHEEL_INSTALL=180

def digest(b:bytes)->str:
    return hashlib.sha256(b).hexdigest()

def cmd(args,*,cwd,env,timeout):
    rc,stdout,stderr,ns,to=ac11.run_cmd(
        args,cwd=cwd,env=env,timeout=timeout)
    return {"code":rc,"stdout":stdout,"stderr":stderr,
            "wall_ns":ns,"timed_out":to}

def official_wheel_record()->dict:
    request=urllib.request.Request(
        PYPI_JSON,headers={"User-Agent":"FORGE-AC14-source-only/1"})
    with urllib.request.urlopen(request,timeout=20) as response:
        blob=response.read(1_000_000)
    meta=json.loads(blob.decode("utf-8"))
    if meta.get("info",{}).get("name")!="ogbench" or meta.get("info",{}).get("version")!=VERSION:
        raise RuntimeError("AC14_PYPI_NAME_VERSION_DRIFT")
    matches=[x for x in meta.get("urls",[])
             if x.get("filename")==WHEEL and x.get("packagetype")=="bdist_wheel"]
    if len(matches)!=1:
        raise RuntimeError("AC14_PYPI_WHEEL_IDENTITY_MISSING_OR_AMBIGUOUS")
    x=matches[0]
    if (x.get("digests",{}).get("sha256")!=WHEEL_SHA256 or
        x.get("size")!=WHEEL_BYTES or x.get("yanked") is not False or
        x.get("url","").split("/")[2]!="files.pythonhosted.org"):
        raise RuntimeError("AC14_PYPI_HASH_SIZE_OR_PUBLISHER_DRIFT")
    # Record only the allowed metadata: no remote script execution, no
    # indexes beyond HTTPS PyPI and real local wheel installation.
    return {"filename":WHEEL,"sha256":WHEEL_SHA256,
            "size_bytes":WHEEL_BYTES,"pypi_api_version":VERSION,
            "pypi_host":"files.pythonhosted.org"}

def verify_parent(root:Path,prior:Path):
    source=ac10.inspect_upstream(root)
    report=json.loads(prior.read_text(encoding="utf-8"))
    if (report.get("schema")!=ac13.SCHEMA or
        report.get("original_commit")!=source["sha"] or
        report.get("original_tree")!=source["tree"] or
        report.get("original_dtr_sha256")!=source["dtr_original_git_blob_sha256"] or
        report.get("dependency_status")!="ORIGINAL_DTR_IMPORT_BLOCKED" or
        report.get("original_import_result",{}).get("exception")!={"kind":"MISSING_MODULE","module":"ogbench"} or
        report.get("install_return_code")!=0 or
        report.get("pinned_torch")!=ac13.TORCH or
        report.get("pinned_torchvision")!=ac13.VISION or
        report.get("source_public_smoke_attempted") or
        report.get("scientific_first_use") or
        report.get("controller_or_queue_mutated")):
        raise RuntimeError("AC14_AC13_SOURCE_AND_OGBENCH_PRECONDITIONS_NOT_MET")
    verified=report.get("downloaded_sha256",{})
    pinned=report.get("official_index_sha256",{})
    if set(verified)!={"torch","torchvision"} or verified!=pinned:
        raise RuntimeError("AC14_CPU_WHEEL_PROVENANCE_MISSING")
    return source

def run(root:Path,venv:Path,ac13_report:Path,out:Path,freeze:Path):
    original=verify_parent(root,ac13_report)
    venv=venv.resolve(strict=True)
    if venv.is_relative_to(root.resolve()):
        raise RuntimeError("AC14_VENV_INSIDE_UPSTREAM_FORBIDDEN")
    py=venv/("Scripts/python.exe" if sys.platform=="win32" else "bin/python")
    if not py.is_file():
        raise RuntimeError("AC14_AC11_13_REAL_VENV_MISSING")
    env=os.environ.copy()
    env.update({"PYTHONPATH":str(root.resolve()),"PYTHONDONTWRITEBYTECODE":"1",
                "PIP_NO_INPUT":"1","PIP_DISABLE_PIP_VERSION_CHECK":"1",
                "PIP_NO_CACHE_DIR":"1","PIP_RETRIES":"1",
                "PIP_DEFAULT_TIMEOUT":"20"})
    wheel_record=None
    downloaded_hash=None
    downloaded_bytes=0
    wheel_verified=False
    install_attempted=False
    install_rc=None
    install_time_ns=None
    install_diagnostic=None
    import_after=None
    smoke_attempted=False
    smoke_status="NOT_ATTEMPTED_IMPORT_BLOCKED"
    smoke=None
    public_episodes=0
    public_actions=0
    state="NO_WHEEL_METADATA"
    error=None
    try:
        wheel_record=official_wheel_record()
        state="PYPI_WHEEL_METADATA_VERIFIED"
        wheels=out.parent/"ac14-wheelhouse"
        wheels.mkdir(parents=True,exist_ok=True)
        d=cmd([str(py),"-m","pip","download","--only-binary=:all:",
              "--no-deps","--no-cache-dir","--no-input",
              "--index-url","https://pypi.org/simple",
              "--dest",str(wheels),f"ogbench=={VERSION}"],
              cwd=venv,env=env,timeout=MAX_WHEEL_DOWNLOAD)
        path=wheels/WHEEL
        if d["code"]!=0 or d["timed_out"] or not path.is_file():
            state="WHEEL_DOWNLOAD_BLOCKED"
            error="DOWNLOAD_TIMEOUT" if d["timed_out"] else ac11.classification(d["stderr"],False)
        else:
            downloaded_bytes=path.stat().st_size
            downloaded_hash=digest(path.read_bytes())
            if downloaded_hash!=WHEEL_SHA256 or downloaded_bytes!=WHEEL_BYTES:
                state="WHEEL_IDENTITY_MISMATCH"
                error="EXACT_PYPI_WHEEL_HASH_SIZE_MISMATCH"
            else:
                wheel_verified=True
                state="WHEEL_AUTHENTIC"
                install_attempted=True
                # Wheel-only resolver disallows native source compilation,
                # heavy train extras, network scientific datasets and forks.
                i=cmd([str(py),"-m","pip","install",
                       "--only-binary=:all:","--no-cache-dir","--no-input",
                       "--disable-pip-version-check",str(path)],
                      cwd=venv,env=env,timeout=MAX_WHEEL_INSTALL)
                install_rc=i["code"]
                install_time_ns=i["wall_ns"]
                if i["code"]!=0 or i["timed_out"]:
                    state="GENUINE_OGBENCH_DEPENDENCY_INSTALL_BLOCKED"
                    install_diagnostic="INSTALL_TIMEOUT" if i["timed_out"] else ac11.classification(i["stderr"],False)
                else:
                    state="GENUINE_OGBENCH_INSTALLED"
                    import_after=ac12.classify_import(py,root,env)
                    if import_after["status"]!="ORIGINAL_IMPORT_PASS":
                        state="ORIGINAL_DTR_IMPORT_BLOCKED"
                        error=import_after["exception"]["kind"]
                    else:
                        smoke_attempted=True
                        e=cmd([str(py),"-B","-c",ac11._SMOKE_CHILD],
                              cwd=root,env=env,timeout=ac11.MAX_CHILD_SECONDS)
                        if not e["timed_out"] and e["code"]==0:
                            try:
                                smoke=json.loads(e["stdout"].decode("utf-8").strip())
                                ac11.validate_smoke(smoke)
                                smoke_status="REAL_SOURCE_PUBLIC_SMOKE_PASS"
                                state=smoke_status
                                public_episodes=smoke["source_owned_episodes"]
                                public_actions=smoke["source_owned_actions"]
                            except (UnicodeError,json.JSONDecodeError,RuntimeError,ValueError,KeyError) as exc:
                                error="PUBLIC_OUTPUT_VALIDATION_"+type(exc).__name__
                        else:
                            error="PUBLIC_SUBPROCESS_TIMEOUT" if e["timed_out"] else ac11.classification(e["stderr"],False)
                        if smoke_status!="REAL_SOURCE_PUBLIC_SMOKE_PASS":
                            state="REAL_SOURCE_PUBLIC_SMOKE_BLOCKED"
                            smoke_status=state
                            smoke=None
                            public_episodes=None
                            public_actions=None
    except (RuntimeError,ValueError,OSError,TimeoutError,urllib.error.URLError) as exc:
        state="PINNED_WHEEL_OR_METADATA_BLOCKED"
        error=type(exc).__name__+(
            ":"+str(exc)[:150] if isinstance(exc,RuntimeError) else "")

    fr=cmd([str(py),"-m","pip","freeze"],
           cwd=venv,env=env,timeout=25)
    frozen=fr["stdout"].decode("utf-8","replace") if fr["code"]==0 and not fr["timed_out"] else ""
    freeze.parent.mkdir(parents=True,exist_ok=True)
    freeze.write_text(frozen,encoding="utf-8")
    post=ac10.inspect_upstream(root)
    if post["sha"]!=original["sha"] or post["tree"]!=original["tree"]:
        raise RuntimeError("AC14_ORIGINAL_GIT_CONTENT_MUTATED")
    result={
        "schema":SCHEMA,"scope":"AUTHENTIC_SOURCE_PUBLIC_ENGINEERING_ONLY",
        "original_commit":original["sha"],"original_tree":original["tree"],
        "original_dtr_sha256":original["dtr_original_git_blob_sha256"],
        "pypi_version":VERSION,"expected_wheel_sha256":WHEEL_SHA256,
        "official_wheel_metadata":wheel_record,
        "downloaded_wheel_sha256":downloaded_hash,
        "downloaded_wheel_bytes":downloaded_bytes,
        "wheel_verified":wheel_verified,
        "install_attempted":install_attempted,
        "install_return_code":install_rc,
        "install_wall_ns":install_time_ns,
        "install_diagnostic":install_diagnostic,
        "state":state,"error_class":error,
        "original_import_after_install":import_after,
        "smoke_attempted":smoke_attempted,"smoke_status":smoke_status,
        "actual_public_smoke":smoke,
        "source_owned_public_episodes":public_episodes,
        "source_owned_public_actions":public_actions,
        "frozen_environment_sha256":digest(frozen.encode("utf-8")),
        "freeze_packages":len(frozen.splitlines()),
        "source_files_modified":False,
        "original_source_birth_signed":False,
        "reserved_fit_valid_dev_used":False,
        "unknown_family_used":False,
        "native_model_trained":False,"native_model_changed":False,
        "scientific_first_use":False,"scientific_admission":False,
        "controller_or_f139_queue_changed":False,
        "accepted_science_updated":False
    }
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    return result

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--upstream",type=Path,required=True)
    p.add_argument("--venv",type=Path,required=True)
    p.add_argument("--ac13-report",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    p.add_argument("--freeze",type=Path,required=True)
    a=p.parse_args()
    r=run(a.upstream,a.venv,a.ac13_report,a.out,a.freeze)
    print("AC14_OFFICIAL_WHEEL="+str(r["wheel_verified"]))
    print("AC14_DEPENDENCY_STATUS="+r["state"])
    print("AC14_PUBLIC_SOURCE="+r["smoke_status"])
    print("AC14_FIRST_USE=NO")

"""AC-13: exact authentic upstream DTR import with official PyTorch CPU pair.

A package dependency gate; no original scientific first use, native training,
source modification, synthetic world, plugin scheduler or FORGE controller.
"""
from __future__ import annotations
import argparse
from html.parser import HTMLParser
import hashlib
import json
import os
from pathlib import Path
import sys
import urllib.parse
import urllib.request

import ac10_upstream_contract as ac10
import ac11_original_dtr as ac11
import ac12_import_repair as ac12

SCHEMA="forge.ac13.original-pytorch-cpu-import.v1"
TORCH="2.3.1+cpu"
VISION="0.18.1+cpu"
INDEX="https://download.pytorch.org/whl/cpu"
MAX_DOWNLOAD_SECONDS=420
MAX_INSTALL_SECONDS=240
ORIGINAL_SHA=ac10.SOURCE_COMMIT

class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links=[]
    def handle_starttag(self,tag,attrs):
        if tag=="a":
            href=dict(attrs).get("href")
            if href:
                self.links.append(href)

def digest(data:bytes)->str:
    return hashlib.sha256(data).hexdigest()

def wheel_names():
    if sys.version_info[:2]!=(3,11):
        raise RuntimeError("AC13_PY311_EXACT_REQUIRED")
    if sys.platform=="win32":
        suffix="win_amd64"
    elif sys.platform.startswith("linux"):
        suffix="linux_x86_64"
    else:
        raise RuntimeError("AC13_NO_UNQUALIFIED_PLATFORM")
    return {
        "torch":f"torch-2.3.1+cpu-cp311-cp311-{suffix}.whl",
        "torchvision":f"torchvision-0.18.1+cpu-cp311-cp311-{suffix}.whl"
    }

def official_index_hashes(expected:dict)->dict:
    hashes={}
    for pkg,name in expected.items():
        url=f"{INDEX}/{pkg}/"
        request=urllib.request.Request(url,headers={"User-Agent":"FORGE-AC13-source-only/1"})
        with urllib.request.urlopen(request,timeout=25) as response:
            data=response.read(3_000_000)
        parser=Links()
        parser.feed(data.decode("utf-8"))
        matching=[]
        for href in parser.links:
            parsed=urllib.parse.urlsplit(href)
            filename=urllib.parse.unquote(urllib.parse.urlsplit(href).path).split("/")[-1]
            if filename==name:
                pairs=urllib.parse.parse_qs(parsed.fragment)
                hash_values=pairs.get("sha256",[])
                if len(hash_values)==1 and len(hash_values[0])==64:
                    matching.append(hash_values[0].lower())
        if len(matching)!=1:
            raise RuntimeError("AC13_OFFICIAL_INDEX_DIGEST_MISSING_OR_AMBIGUOUS:"+pkg)
        hashes[pkg]=matching[0]
    return hashes

def cmd(argv,*,cwd,env,timeout):
    rc,out,err,elapsed,expired=ac11.run_cmd(argv,cwd=cwd,env=env,timeout=timeout)
    return {"rc":rc,"out":out,"err":err,"wall_ns":elapsed,"timeout":expired}

def install_pair(root:Path,venv:Path,out:Path,ac12_report:Path,freeze:Path):
    original=ac10.inspect_upstream(root)
    prev=json.loads(ac12_report.read_text(encoding="utf-8"))
    if (prev.get("schema")!=ac12.SCHEMA or
        prev.get("original_source_sha")!=ORIGINAL_SHA or
        prev.get("original_source_tree")!=ac10.SOURCE_TREE or
        prev.get("authentic_pypi_wheel_sha256_verified") is not True or
        prev.get("dependency_install_return_code")!=0 or
        prev.get("original_import_after_pinned_extra",{}).get("exception")!={"kind":"MISSING_MODULE","module":"torchvision"} or
        prev.get("public_smoke_attempted") or
        prev.get("science_unknown_family_touched") or
        prev.get("scientific_admission")):
        raise RuntimeError("AC13_AC12_SOURCE_AND_IMPORT_PRECONDITIONS_NOT_MET")
    venv=venv.resolve(strict=True)
    if venv.is_relative_to(root.resolve()):
        raise RuntimeError("AC13_VENV_MUST_STAY_OUTSIDE_UPSTREAM")
    py=venv/("Scripts/python.exe" if sys.platform=="win32" else "bin/python")
    if not py.is_file():
        raise RuntimeError("AC13_AC11_VENV_MISSING")
    env=os.environ.copy()
    env.update({
        "PYTHONPATH":str(root.resolve()),
        "PYTHONDONTWRITEBYTECODE":"1",
        "PIP_DISABLE_PIP_VERSION_CHECK":"1",
        "PIP_NO_INPUT":"1","PIP_NO_CACHE_DIR":"1",
        "PIP_RETRIES":"1","PIP_DEFAULT_TIMEOUT":"30"
    })
    wheels=wheel_names()
    status="NO_INSTALL_STARTED"
    error=None
    expected_hashes={}
    got_hashes={}
    file_sizes={}
    download_seconds=0
    install_seconds=0
    install_rc=None
    import_result=None
    smoke_attempted=False
    smoke_status="NOT_ATTEMPTED_IMPORT_BLOCKED"
    smoke=None
    smoke_exception=None
    episodes=0
    actions=0
    try:
        expected_hashes=official_index_hashes(wheels)
        status="OFFICIAL_INDEX_HASHES_VERIFIED"
        wheelhouse=out.parent/"ac13-cpu-wheelhouse"
        wheelhouse.mkdir(parents=True,exist_ok=True)
        # Only exact CPU wheel versions from official PyTorch index.
        d=cmd([str(py),"-m","pip","download","--only-binary=:all:",
               "--no-deps","--no-cache-dir","--no-input",
               "--index-url",INDEX,
               "--dest",str(wheelhouse),
               f"torch=={TORCH}",f"torchvision=={VISION}"],
              cwd=venv,env=env,timeout=MAX_DOWNLOAD_SECONDS)
        download_seconds=d["wall_ns"]/1e9
        if d["timeout"] or d["rc"]!=0:
            status="OFFICIAL_CPU_DOWNLOAD_BLOCKED"
            error="TIMEOUT" if d["timeout"] else ac11.classification(d["err"],False)
        else:
            missing=[]
            for pkg,name in wheels.items():
                path=wheelhouse/name
                if not path.is_file():
                    missing.append(pkg)
                    continue
                actual=digest(path.read_bytes())
                got_hashes[pkg]=actual
                file_sizes[pkg]=path.stat().st_size
                if actual!=expected_hashes[pkg]:
                    missing.append(pkg)
            if missing:
                status="OFFICIAL_CPU_WHEEL_HASH_OR_PLATFORM_MISMATCH"
                error="INVALID_OFFICIAL_WHEEL_DIGEST_OR_WHEEL_NAME"
            else:
                status="OFFICIAL_CPU_WHEELS_VERIFIED"
                i=cmd([str(py),"-m","pip","install","--no-cache-dir",
                       "--no-input","--disable-pip-version-check",
                       str(wheelhouse/wheels["torch"]),
                       str(wheelhouse/wheels["torchvision"])],
                      cwd=venv,env=env,timeout=MAX_INSTALL_SECONDS)
                install_seconds=i["wall_ns"]/1e9
                install_rc=i["rc"]
                if i["timeout"] or i["rc"]!=0:
                    status="OFFICIAL_CPU_INSTALL_BLOCKED"
                    error="TIMEOUT" if i["timeout"] else ac11.classification(i["err"],False)
                else:
                    status="OFFICIAL_CPU_PAIR_INSTALLED"
                    import_result=ac12.classify_import(py,root,env)
                    if import_result["status"]!="ORIGINAL_IMPORT_PASS":
                        status="ORIGINAL_DTR_IMPORT_BLOCKED"
                        error=import_result["exception"]["kind"]
                    else:
                        smoke_attempted=True
                        run=cmd([str(py),"-B","-c",ac11._SMOKE_CHILD],
                                cwd=root,env=env,timeout=ac11.MAX_CHILD_SECONDS)
                        if not run["timeout"] and run["rc"]==0:
                            try:
                                smoke=json.loads(run["out"].decode("utf-8").strip())
                                ac11.validate_smoke(smoke)
                                status="ACTUAL_SOURCE_PUBLIC_SMOKE_PASS"
                                smoke_status=status
                                episodes=smoke["source_owned_episodes"]
                                actions=smoke["source_owned_actions"]
                            except (ValueError,RuntimeError,UnicodeError,KeyError) as exc:
                                smoke=None
                                smoke_status="PUBLIC_SMOKE_BLOCKED"
                                error="PUBLIC_VALIDATION_"+type(exc).__name__
                        else:
                            smoke_status="PUBLIC_SMOKE_BLOCKED"
                            error="TIMEOUT" if run["timeout"] else ac11.classification(run["err"],False)
                        if smoke_status!="ACTUAL_SOURCE_PUBLIC_SMOKE_PASS":
                            status="PUBLIC_SMOKE_BLOCKED"
                            episodes=None  # partial source episodes may have occurred
                            actions=None
    except (RuntimeError,ValueError,OSError,TimeoutError,urllib.error.URLError) as exc:
        status="OFFICIAL_CPU_METADATA_OR_DEPENDENCY_BLOCKED"
        error=type(exc).__name__+":"+(str(exc)[:160] if isinstance(exc,RuntimeError) else "external fetch or IO failure")

    fr=cmd([str(py),"-m","pip","freeze"],cwd=venv,env=env,timeout=25)
    frozen=fr["out"].decode("utf-8","replace") if fr["rc"]==0 and not fr["timeout"] else ""
    freeze.parent.mkdir(parents=True,exist_ok=True)
    freeze.write_text(frozen,encoding="utf-8")
    # Git identity must hold after all package operations, no source patch.
    after_identity=ac10.inspect_upstream(root)
    if after_identity["sha"]!=original["sha"] or after_identity["tree"]!=original["tree"]:
        raise RuntimeError("AC13_ORIGINAL_SOURCE_MODIFIED")
    result={
        "schema":SCHEMA,
        "scope":"AUTHENTIC_ORIGINAL_PUBLIC_DEVELOPMENT_COMPATIBILITY_ONLY",
        "original_commit":original["sha"],"original_tree":original["tree"],
        "original_dtr_sha256":original["dtr_original_git_blob_sha256"],
        "source_edited":False,
        "prior_ac12_missing":"torchvision",
        "cpu_only":True,"official_index":INDEX,
        "pinned_torch":TORCH,"pinned_torchvision":VISION,
        "expected_platform_wheels":wheels,
        "official_index_sha256":expected_hashes,
        "downloaded_sha256":got_hashes,
        "downloaded_wheel_bytes":file_sizes,
        "total_downloaded_wheel_bytes":sum(file_sizes.values()),
        "download_wall_seconds":download_seconds,
        "install_wall_seconds":install_seconds,
        "install_return_code":install_rc,
        "dependency_status":status,"failure_class":error,
        "original_import_result":import_result,
        "source_public_smoke_attempted":smoke_attempted,
        "public_smoke_status":smoke_status,
        "public_smoke":smoke,
        "source_owned_episodes":episodes,
        "source_owned_actions":actions,
        "freeze_sha256":digest(frozen.encode("utf-8")),
        "freeze_package_count":len(frozen.splitlines()),
        "reserved_fit_validation_dev_used":False,
        "unknown_family_used":False,
        "trained_native_model":False,
        "scientific_first_use":False,
        "scientific_admission":False,
        "controller_or_queue_mutated":False,
        "accepted_model_changed":False
    }
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    return result

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--upstream",type=Path,required=True)
    p.add_argument("--venv",type=Path,required=True)
    p.add_argument("--ac12-report",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    p.add_argument("--freeze",type=Path,required=True)
    a=p.parse_args()
    r=install_pair(a.upstream,a.venv,a.out,a.ac12_report,a.freeze)
    print("AC13_PACKAGE_STATUS="+r["dependency_status"])
    print("AC13_ORIGINAL_IMPORT="+str(r["original_import_result"]))
    print("AC13_PUBLIC_SMOKE="+r["public_smoke_status"])
    print("AC13_SCIENTIFIC_FIRST_USE=NO")

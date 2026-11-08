"""G123 development-only original-vs-sealed V30 fixture full-suite A/B/B/A.

Every original test is run once in each arm, with no assertion or method
modification; the sole intervention is the original setUp vs fresh-file sealed
setup, on the same source tree, runner, interpreter, and test-discovery order.
"""
from __future__ import annotations
import hashlib
import io
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time
import unittest

ROOT=Path(__file__).resolve().parents[1]
BASE="e6747858be6d3516aae26c5a89ce7b6b89f41df8"
BRANCH="engineering/rar-g123-v30-sealed-fixture-dev-20261107"
EXPECTED=1443
CASE_IDS_SHA="b3fcf34229cb3a2a0eb03cfea735804cf474646a830c41875fa58b30ad4cec3b"
WIN_SKIPS_SHA="2454be52b27ce0c78314b658efa2d9b5298fca718458486943462bd0ad8f111a"
MIN_WINDOWS_GAIN=1.05
MIN_LINUX_GAIN=1.02
MIN_PAIR=1.00
MAX_ARM_SECONDS=420
ORDER=("baseline","candidate","candidate","baseline")

def git(*args):
    return subprocess.check_output(["git",*args],cwd=ROOT,text=True,timeout=75).strip()

def stable(sha):
    if git("rev-parse","HEAD")!=sha or git("status","--porcelain","--untracked-files=all"):
        raise ValueError("G123_SOURCE_OR_UNTRACKED_DRIFT")

def flattened(suite):
    for x in suite:
        if isinstance(x,unittest.TestSuite):
            yield from flattened(x)
        else:
            yield x

class CaptureResult(unittest.TextTestResult):
    def __init__(self,*a,**kw):
        super().__init__(*a,**kw)
        self.ids=[]
    def startTest(self,test):
        self.ids.append(test.id())
        super().startTest(test)

def main():
    if (os.getenv("GITHUB_ACTIONS")!="true" or
        os.getenv("GITHUB_REPOSITORY")!="spoonman136668-ai/FORGE" or
        os.getenv("GITHUB_EVENT_NAME")!="pull_request" or
        os.getenv("GITHUB_HEAD_REF")!=BRANCH or
        not os.getenv("RUNNER_TEMP")):
        raise ValueError("G123_DEVELOPMENT_PR_ONLY")
    sha=git("rev-parse","HEAD")
    if sha!=os.getenv("FORGE_G123_HEAD") or git("merge-base",BASE,sha)!=BASE:
        raise ValueError("G123_SOURCE_CUSTODY_INVALID")
    expected_paths={".github/workflows/qualify.yml",
                    "f139/test_nci04_v30_source_transition.py",
                    "scripts/check_rar_g123_fixture_abba.py"}
    if set(git("diff","--name-only",BASE,sha).splitlines())!=expected_paths:
        raise ValueError("G123_UNAUTHORIZED_DIFF")
    stable(sha)
    sys.path.insert(0,str(ROOT))
    sys.path.insert(0,str(ROOT/"f139"))
    # Resolve the class actually used by original unittest discovery.
    discovery=unittest.defaultTestLoader.discover("f139",pattern="test_*.py")
    cases=list(flattened(discovery))
    if any(isinstance(t,unittest.loader._FailedTest) for t in cases):
        raise ValueError("G123_FAILED_TEST_IMPORT")
    ids=[t.id() for t in cases]
    digest=hashlib.sha256("\n".join(ids).encode()).hexdigest()
    if len(ids)!=EXPECTED or len(set(ids))!=EXPECTED or digest!=CASE_IDS_SHA:
        raise ValueError("G123_FROZEN_TEST_INVENTORY_DRIFT")
    target=sys.modules.get("test_nci04_v30_source_transition")
    if target is None:
        raise ValueError("G123_TARGET_TEST_MODULE_NOT_DISCOVERED")
    cls=target.PendingTransferTests
    old_set_up=cls._build_uncached_fixture
    candidate_set_up=cls.setUp
    if old_set_up is candidate_set_up:
        raise ValueError("G123_BASELINE_AND_CANDIDATE_IDENTICAL")
    scope="Windows" if os.name=="nt" else "Linux"
    min_gain=MIN_WINDOWS_GAIN if os.name=="nt" else MIN_LINUX_GAIN
    out=Path(os.environ["RUNNER_TEMP"])/("rar-g123-abba-"+scope+".json")
    report=dict(schema="forge.rar.g123.v30-sealed-fullsuite.abba.dev.v1",
        source_sha=sha,source_tree=git("rev-parse","HEAD^{tree}"),base_main=BASE,
        run_id=os.getenv("GITHUB_RUN_ID"),run_attempt=os.getenv("GITHUB_RUN_ATTEMPT"),
        platform=platform.platform(),python=sys.version,os=scope,
        frozen_order=list(ORDER),case_count=EXPECTED,case_ids_sha256=digest,
        complete_original_test_methods_unchanged=True,
        original_setUp_body_preserved=True,
        original_full_ci_serial_suite_retained=True,
        first_run_cold_performance_proven=False,
        hosted_job_total_speedup_proven=False,
        default_ci_optimization_enabled=False,
        thresholds=dict(min_gain=min_gain,min_pair=MIN_PAIR),
        verdict="INVALID_UNVERIFIED",arms=[])
    try:
        for i,mode in enumerate(ORDER,1):
            stable(sha)
            cls.setUp=old_set_up if mode=="baseline" else candidate_set_up
            suite=unittest.defaultTestLoader.discover("f139",pattern="test_*.py")
            selected=list(flattened(suite))
            this_ids=[t.id() for t in selected]
            if this_ids!=ids:
                raise ValueError("G123_CASE_SELECTION_OR_ORDER_DRIFT")
            stream=io.StringIO()
            start=time.perf_counter()
            result=unittest.TextTestRunner(
                stream=stream,verbosity=1,resultclass=CaptureResult
            ).run(unittest.TestSuite(selected))
            seconds=time.perf_counter()-start
            skip=sorted(t.id() for t,_ in result.skipped)
            skip_sha=hashlib.sha256("\n".join(skip).encode()).hexdigest()
            arm=dict(index=i,mode=mode,seconds=round(seconds,6),
                tests_run=result.testsRun,executed_ids_sha256=hashlib.sha256(
                    "\n".join(result.ids).encode()).hexdigest(),
                skip_ids_sha256=skip_sha,skips=len(skip),
                failure_ids=[t.id() for t,_ in result.failures],
                error_ids=[t.id() for t,_ in result.errors],
                unexpected_successes=[t.id() for t in result.unexpectedSuccesses],
                expected_failures=[t.id() for t,_ in result.expectedFailures],
                successful=result.wasSuccessful())
            report["arms"].append(arm)
            out.write_text(json.dumps(report,sort_keys=True,indent=2)+"\n",encoding="utf-8")
            if (seconds>MAX_ARM_SECONDS or result.ids!=ids or
                result.testsRun!=EXPECTED or not result.wasSuccessful() or
                arm["failure_ids"] or arm["error_ids"] or
                arm["unexpected_successes"] or arm["expected_failures"] or
                (scope=="Windows" and
                 (len(skip)!=7 or skip_sha!=WIN_SKIPS_SHA))):
                raise ValueError("G123_COMPLETE_REGRESSION_PARITY_FAIL:"+stream.getvalue()[-500:])
        cls.setUp=candidate_set_up
        stable(sha)
        a,b,c,d=report["arms"]
        if len(set(arm["skip_ids_sha256"] for arm in report["arms"]))!=1:
            raise ValueError("G123_SKIP_IDENTITY_DRIFT")
        pairs=[a["seconds"]/b["seconds"],d["seconds"]/c["seconds"]]
        gain=(a["seconds"]+d["seconds"])/(b["seconds"]+c["seconds"])
        report["paired_speedups"]=[round(v,6) for v in pairs]
        report["aggregate_speedup"]=round(gain,6)
        report["verdict"]=(
            "PASS_DEV_ONLY" if gain>=min_gain and min(pairs)>=MIN_PAIR
            else "NO_GO_PERFORMANCE")
        return 0
    except BaseException as exc:
        report["failure"]=type(exc).__name__+":"+str(exc)[:600]
        raise
    finally:
        cls.setUp=candidate_set_up
        out.write_text(json.dumps(report,sort_keys=True,indent=2)+"\n",encoding="utf-8")
        print("FORGE_RAR_G123_"+scope+"="+report["verdict"],flush=True)
        if "aggregate_speedup" in report:
            print("FORGE_RAR_G123_"+scope+"_GAIN="+str(report["aggregate_speedup"]),flush=True)

if __name__=="__main__":
    sys.exit(main())

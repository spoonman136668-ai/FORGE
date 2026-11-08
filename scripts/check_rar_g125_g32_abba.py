"""RAR-G125 DEV: same-source G32/G38 original synthetic fixture focused ABBA.

The mandatory original 1,443-case Linux/Windows regression runs separately
unchanged. All 27 selected cases preserve original bodies, order and results.
Only the original 180-event G32 disposable setup vs a closed-byte synthetic
prefix is switched. No science, owner, production or acceptance authority.
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
BASE="dfafc5bcf10fc38f851ca5bafb4089986122c7c1"
BRANCH="engineering/rar-g125-g32-untrusted-prefix-abba-20261107"
EXPECTED_FULL=1443
FULL_IDS_SHA="b3fcf34229cb3a2a0eb03cfea735804cf474646a830c41875fa58b30ad4cec3b"
COHORT={"test_nci04_g32_owner_custody","f139.test_nci04_g32_owner_custody","test_nci04_g38_owner_terminal"}
COHORT_COUNT=27
COHORT_IDS_SHA="fa6c5ac8749c469d25cf4b2eb274b003048ee44cb0eaf4ccbc47f1afdb271fd1"
MIN_GAIN_WINDOWS=1.20
MIN_GAIN_LINUX=1.10
MIN_PAIR=1.05
MAX_ARM_SEC=240
ORDER=("original","sealed","sealed","original")

def git(*args):
    return subprocess.check_output(["git",*args],cwd=ROOT,text=True,timeout=75).strip()

def stable(sha):
    if git("rev-parse","HEAD")!=sha or git("status","--porcelain","--untracked-files=all"):
        raise ValueError("G125_SOURCE_OR_UNTRACKED_DRIFT")

def flatten(suite):
    for case in suite:
        if isinstance(case,unittest.TestSuite):
            yield from flatten(case)
        else:
            yield case

class CaptureResult(unittest.TextTestResult):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
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
        raise ValueError("G125_DEVELOPMENT_PR_ONLY")
    sha=git("rev-parse","HEAD")
    if sha!=os.getenv("FORGE_G125_HEAD") or git("merge-base",BASE,sha)!=BASE:
        raise ValueError("G125_EXACT_SOURCE_CUSTODY_INVALID")
    expected={".github/workflows/qualify.yml",
              "f139/test_nci04_g32_owner_custody.py",
              "scripts/check_rar_g125_g32_abba.py"}
    if set(git("diff","--name-only",BASE,sha).splitlines())!=expected:
        raise ValueError("G125_UNQUALIFIED_SOURCE_DIFF")
    stable(sha)
    sys.path[:0]=[str(ROOT),str(ROOT/"f139")]
    suite=unittest.defaultTestLoader.discover("f139",pattern="test_*.py")
    all_cases=list(flatten(suite))
    if any(isinstance(t,unittest.loader._FailedTest) for t in all_cases):
        raise ValueError("G125_DISCOVERY_IMPORT_ERROR")
    all_ids=[t.id() for t in all_cases]
    if (len(all_ids)!=EXPECTED_FULL or len(set(all_ids))!=EXPECTED_FULL or
            hashlib.sha256("\n".join(all_ids).encode()).hexdigest()!=FULL_IDS_SHA):
        raise ValueError("G125_FROZEN_FULL_CASE_INVENTORY_DRIFT")
    selected=[t for t in all_cases if type(t).__module__ in COHORT]
    ids=[t.id() for t in selected]
    cohort_hash=hashlib.sha256("\n".join(ids).encode()).hexdigest()
    if (len(ids)!=COHORT_COUNT or len(set(ids))!=COHORT_COUNT or
            cohort_hash!=COHORT_IDS_SHA):
        raise ValueError("G125_FROZEN_27_CASE_COHORT_DRIFT")
    target_modules=("test_nci04_g32_owner_custody","f139.test_nci04_g32_owner_custody")
    originals=[]
    for name in target_modules:
        module=sys.modules.get(name)
        if module is None:
            raise ValueError("G125_MODULE_NOT_LOADED:"+name)
        klass=module.OriginalOwnerG32Tests
        old=klass._build_uncached_fixture
        new=klass.setUp
        if old is new or not hasattr(module,"_sealed_g32_untrusted_prefix"):
            raise ValueError("G125_BASELINE_CANDIDATE_NOT_DISTINCT")
        originals.append((klass,old,new,module._sealed_g32_untrusted_prefix))
    if originals[0][0] is originals[1][0]:
        raise ValueError("G125_G32_ALIAS_CONFOUND")
    scope="Windows" if os.name=="nt" else "Linux"
    threshold=MIN_GAIN_WINDOWS if scope=="Windows" else MIN_GAIN_LINUX
    dest=Path(os.environ["RUNNER_TEMP"])/("rar-g125-abba-"+scope+".json")
    report=dict(schema="forge.rar.g125.g32-synthetic-27case-abba.dev.v1",
        source_sha=sha,source_tree=git("rev-parse","HEAD^{tree}"),
        base_main=BASE,os=scope,run_id=os.getenv("GITHUB_RUN_ID"),
        run_attempt=os.getenv("GITHUB_RUN_ATTEMPT"),
        runner_image=os.getenv("ImageOS"),image_version=os.getenv("ImageVersion"),
        processor_model=platform.processor(),logical_cpus=os.cpu_count(),
        python=sys.version,case_count=COHORT_COUNT,cohort_ids_sha256=cohort_hash,
        full_original_ids_sha256=FULL_IDS_SHA,
        original_mandatory_full_regression_unchanged=True,
        original_test_methods_and_assertions_unchanged=True,
        no_production_or_science_changes=True,
        first_full_cold_speedup_proven=False,hosted_critical_path_speedup_proven=False,
        default_activation=False,
        frozen_arm_order=list(ORDER),
        threshold_gain=threshold,threshold_bracket=MIN_PAIR,
        verdict="INVALID_UNVERIFIED",arms=[])
    try:
        for index,mode in enumerate(ORDER,1):
            stable(sha)
            for klass,old,new,cache in originals:
                klass.setUp=old if mode=="original" else new
                if mode=="sealed":
                    cache.cache_clear()
            this=list(flatten(unittest.defaultTestLoader.discover("f139",pattern="test_*.py")))
            current=[t for t in this if type(t).__module__ in COHORT]
            if [t.id() for t in current]!=ids:
                raise ValueError("G125_SELECTED_IDS_OR_ORDER_DRIFT")
            stream=io.StringIO()
            t=time.perf_counter()
            run=unittest.TextTestRunner(stream=stream,verbosity=1,
                resultclass=CaptureResult).run(unittest.TestSuite(current))
            elapsed=time.perf_counter()-t
            skips=sorted(t.id() for t,_ in run.skipped)
            arm=dict(index=index,mode=mode,seconds=round(elapsed,6),
                executed_ids_sha256=hashlib.sha256("\n".join(run.ids).encode()).hexdigest(),
                tests_run=run.testsRun,skips=skips,
                failures=[t.id() for t,_ in run.failures],
                errors=[t.id() for t,_ in run.errors],
                expected_failures=[t.id() for t,_ in run.expectedFailures],
                unexpected_successes=[t.id() for t in run.unexpectedSuccesses],
                successful=run.wasSuccessful())
            report["arms"].append(arm)
            dest.write_text(json.dumps(report,sort_keys=True,indent=2)+"\n",
                            encoding="utf-8")
            if (elapsed>MAX_ARM_SEC or run.ids!=ids or
                    run.testsRun!=COHORT_COUNT or skips or
                    not run.wasSuccessful() or arm["failures"] or arm["errors"] or
                    arm["expected_failures"] or arm["unexpected_successes"]):
                raise ValueError("G125_ORIGINAL_COHORT_PARITY_FAILED:"+
                                 stream.getvalue()[-750:])
        stable(sha)
        a,b,c,d=report["arms"]
        pair=[a["seconds"]/b["seconds"],d["seconds"]/c["seconds"]]
        gain=(a["seconds"]+d["seconds"])/(b["seconds"]+c["seconds"])
        report["paired_gain"]=[round(v,6) for v in pair]
        report["aggregate_gain"]=round(gain,6)
        report["verdict"]=("PASS_DEV_ONLY_FOCUSED"
            if gain>=threshold and min(pair)>=MIN_PAIR
            else "NO_GO_FOCUSED_PERFORMANCE")
        return 0
    except BaseException as e:
        report["failure"]=type(e).__name__+":"+str(e)[:600]
        raise
    finally:
        for klass,old,new,cache in originals:
            klass.setUp=new
        dest.write_text(json.dumps(report,sort_keys=True,indent=2)+"\n",
                        encoding="utf-8")
        print("FORGE_RAR_G125_"+scope+"="+report["verdict"],flush=True)
        if "aggregate_gain" in report:
            print("FORGE_RAR_G125_"+scope+"_GAIN="+
                  str(report["aggregate_gain"]),flush=True)

if __name__=="__main__":
    sys.exit(main())

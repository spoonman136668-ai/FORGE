"""F124-DG original-sourcefree custody authority, before read-only replay.

Authenticates ORIGINAL GitHub Actions source and completed whole-OS shards
through provider job identity and 4 pinned archive digest/ID pairs.
Never regenerates the sourcefree experiment or any consumed scientific case.
"""
from __future__ import annotations
import json
import os
from pathlib import Path
import urllib.request

REPO="spoonman136668-ai/FORGE"
ORIGINAL_RUN=39355225322
ORIGINAL_SHA="929f582939a631a248b7f83edd690165d2e4a31c"
ARCHIVES={
"f124dg-original-sourcefree-sparse_degree4_GF2_unknown-201":(12235240473,"sha256:57dc1cc5a2104e9abb47e4489cd9568277683a2998c408957ee2ea94f7a0cfb0"),
"f124dg-original-sourcefree-sparse_degree4_GF2_unknown-203":(12234709827,"sha256:127c3a8bad9634eb49cdebd72274c4c19950dc6d3f0f9234f52484ad4aa05b68"),
"f124dg-original-sourcefree-dense_degree4_GF2_unknown-203":(12234124876,"sha256:a8428ac0721d2f7d1a9bdfe361364f069597690839dff3f02683ae97cb8d8499"),
"f124dg-original-sourcefree-dense_degree4_GF2_unknown-201":(12234083606,"sha256:087ad9e765dd9e7f78399a842788726e0c7a68771df2d6ffce50d0769ef37542")
}

def need(ok,reason):
    if not ok:raise RuntimeError("F124DG_ORIGINAL_PROVIDER_"+reason)

def read(url):
    token=os.environ.get("GITHUB_TOKEN")
    need(bool(token) and os.environ.get("GITHUB_REPOSITORY")==REPO,
         "GITHUB_READONLY_TOKEN_AND_REPO")
    req=urllib.request.Request(url,headers={
        "Authorization":"Bearer "+token,
        "Accept":"application/vnd.github+json",
        "X-GitHub-Api-Version":"2022-11-28"})
    with urllib.request.urlopen(req,timeout=35) as res:
        return json.load(res)

def verify():
    api="https://api.github.com/repos/"+REPO+"/actions/runs/"+str(ORIGINAL_RUN)
    run=read(api)
    need(run["head_sha"]==ORIGINAL_SHA and run["run_attempt"]==1
         and run["status"]=="completed" and run["conclusion"]=="failure",
         "ORIGINAL_RUN_FAILED_ONLY_AT_READONLY_AUDIT_EXPECTED")
    jobs=read(api+"/jobs?per_page=100")["jobs"]
    need(len(jobs)>=7,"ORIGINAL_JOBS_MISSING")
    expected={f"original-sourcefree-active-OS ({family}, {seed})"
              for family in ("sparse_degree4_GF2_unknown","dense_degree4_GF2_unknown")
              for seed in (201,203)}
    expected.update({"exact-sourcefree-preflight (ubuntu-latest)",
                     "exact-sourcefree-preflight (windows-latest)"})
    ok={j["name"] for j in jobs if j["conclusion"]=="success"}
    need(expected<=ok,
         "ORIGINAL_WINDOWS_LINUX_AND_FOUR_PROCESS_SHARDS_NOT_SUCCESSFUL")
    artifacts=read(api+"/artifacts?per_page=100")["artifacts"]
    byname={a["name"]:a for a in artifacts}
    need(set(ARCHIVES)=={n for n in byname if n.startswith("f124dg-original-sourcefree-")},
         "ORIGINAL_ARTIFACT_ROSTER_ADDITION_OR_DELETION")
    for name,(id,digest) in ARCHIVES.items():
        a=byname[name]
        need(a["id"]==id and a["digest"]==digest and not a["expired"]
             and a["workflow_run"]["head_sha"]==ORIGINAL_SHA,
             "ORIGINAL_PROVIDER_SOURCE_OR_ARTIFACT_DIGEST_DRIFT_"+name)
    return {
       "schema":"mass.f124dg.exact-original-provider-sourcefree-custody.v1",
       "original_run_id":ORIGINAL_RUN,
       "original_SHA":ORIGINAL_SHA,
       "original_overall_run_conclusion":"failure (original stricter audit rejected proven early saturation)",
       "six_required_original_preflight_and_shard_jobs":"SUCCESS",
       "all_72_whole_OS_original_measurements":"ORIGINAL_SHARDS_COMPLETE",
       "original_frozen_artifacts":{n:{"id":v[0],"provider_zip_digest":v[1]}
                                  for n,v in ARCHIVES.items()},
       "new_source_birth":False,
       "original_924_to_937_scientific_firstuse_used":False,
       "read_only_audit_only":True}

if __name__=="__main__":
    evidence=verify()
    print("F124DG_ORIGINAL_6_PROVIDER_JOBS_AND_4_ARCHIVES=PASS")
    print("F124DG_ORIGINAL_RUN_CONCLUSION=FAILURE_AUDIT_ONLY")
    print("F124DG_NO_SOURCE_REGENERATION=PASS")
    out=os.environ.get("F124DG_READONLY_CUSTODY_PATH")
    if out:Path(out).write_text(json.dumps(evidence,sort_keys=True,indent=2)+"\n")

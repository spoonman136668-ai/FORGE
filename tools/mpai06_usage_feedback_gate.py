"""MP-AI06: real usage feedback classification and accepted cold-readback.

Existing private Mind-Palace source, authentic original research receipts, and
canonical collector. Read-only, one-shot, no scheduler or accepted memory writes.
"""
import hashlib,json,os,pathlib,re,shutil,subprocess,sys,urllib.request

MAIN="https://github.com/spoonman136668-ai/Mind-Palace.git"
RUNS={"40865946484":"f5900a0336995123238e22d124f90875ea1154c0",
      "40869961276":"4f07f231d2e237065d5c1a480548e2de541edf58"}
IDS={"Wingless":"project_state/wingless-p6o-native-bayesian-causal-policy-equal-control-negative-20261021",
     "Yggdrasil":"project_state/yggdrasil-mr29-original-native-causal-alias-dev-signal-negative-20261021"}
NEW="lesson/mpai06-p16-memory-efficacy-public-development-no-go-20261029"
STAGE="PRECHECK"
GUARD=(".ice/records.json",".ice/source-ledger.json","archive/index.json",
 ".ice/remote-bootstrap.json",".ice/remote-catalog.json",".ice/remote-index.ndjson",
 ".ice/chat-delta-state.json",".ice/project-state-capsules.json",
 ".ice/project-dependency-graph.json")
def check(ok,code):
    if not ok:raise RuntimeError("MPAI06_"+code)
def process(cmd,cwd=None,timeout=160):
    p=subprocess.run(cmd,cwd=cwd,capture_output=True,text=True,timeout=timeout)
    check(p.returncode==0,"PRIVATE_SOURCE_COMMAND")
    return p.stdout.strip()
def git(*args,cwd=None):
    return process(["git",*args],cwd)
def authentic_runs():
    for run,sha in RUNS.items():
        url="https://api.github.com/repos/spoonman136668-ai/FORGE/actions/runs/"+run
        req=urllib.request.Request(url,headers={"User-Agent":"MPAI06-source-custody"})
        with urllib.request.urlopen(req,timeout=35) as r:
            val=json.loads(r.read(150000))
        check(val.get("id")==int(run) and val.get("head_sha")==sha
              and val.get("status")=="completed" and val.get("conclusion")=="success"
              and val.get("repository",{}).get("full_name")=="spoonman136668-ai/FORGE",
              "UPSTREAM_RUN_PROVENANCE")
def cold(root,head):
    script=(
        "import pathlib,sys,json\n"
        "p=pathlib.Path(sys.argv[1]);h=sys.argv[2]\n"
        "sys.path.insert(0,str(p/'tools'))\n"
        "from mindpalace_readonly import MemorySnapshot\n"
        "s=MemorySnapshot(p,h,['Wingless','Yggdrasil','Mind-Palace'])\n"
        "ids={'Wingless':'project_state/wingless-p6o-native-bayesian-causal-policy-equal-control-negative-20261021','Yggdrasil':'project_state/yggdrasil-mr29-original-native-causal-alias-dev-signal-negative-20261021'}\n"
        "for project,key in ids.items():\n"
        "  r=s.get_record(h,key,[project]);assert r['found'] and r['record']['status']=='observed'\n"
        "  assert r['record']['details']['scientific_acceptance'] is False\n"
        "  q='wingless p6o bayesian causal control' if project=='Wingless' else 'yggdrasil mr29 causal alias'\n"
        "  v=s.recall(h,q,[project]);assert any(x['id']==key for x in v['matches'])\n"
        "  assert not s.get_record(h,ids['Yggdrasil' if project=='Wingless' else 'Wingless'],[project])['found']\n"
        "assert not s.get_record(h,'"+NEW+"',['Mind-Palace'])['found']\n"
        "print(s.records_sha256)\n")
    p=subprocess.run([sys.executable,"-B","-c",script,str(root),head],
                     capture_output=True,text=True,timeout=90)
    if p.returncode:
        # Never export private record contents or arbitrary traceback.
        diag="PRIVATE_COLD_ASSERTION"
        for marker in ("source digest mismatch","source schema mismatch",
               "snapshot count mismatch","source identity mismatch",
               "ambiguous project labels","unrecognized project",
               "invalid context budget profile","record not found",
               "KeyError: 'details'","AssertionError","FileNotFoundError",
               "ModuleNotFoundError"):
            if marker in p.stderr:
                diag=marker.upper().replace(" ","_").replace(":","").replace("'","")
                break
        print("MPAI06_COLD_DIAG="+diag,flush=True)
        check(False,"ACCEPTED_SOURCE_COLD_RECALL")
    return p.stdout.strip()
def batch():
    commit="https://github.com/spoonman136668-ai/FORGE/commit/"+RUNS["40865946484"]
    run="https://github.com/spoonman136668-ai/FORGE/actions/runs/40865946484"
    confirm="https://github.com/spoonman136668-ai/FORGE/actions/runs/40869961276"
    return {
    "schema":"mind-palace.collector-batch.v1",
    "collector":{"name":"mpai06-verified-usage-feedback","version":"1",
                 "source_kind":"repo","observed_at":"2026-10-29T12:04:00Z"},
    "sources":[
      {"type":"commit","ref":commit,"name":"P16 source-pinned experiment",
       "version":RUNS["40865946484"],"content_sha256":None,"role":"primary",
       "authority":"authoritative"},
      {"type":"acceptance","ref":run,"name":"P16 original Windows result",
       "version":"40865946484","role":"corroborating","authority":"acceptance-evidence"},
      {"type":"acceptance","ref":confirm,"name":"P17 scorer controls",
       "version":"40869961276","role":"corroborating","authority":"acceptance-evidence"}],
    "candidates":[{
      "schema_version":1,"kind":"lesson","key":NEW.split("/",1)[1],
      "project":"Mind-Palace","importance":"warm",
      "statement":"Original Windows P16 ran 96 genuine non-Qwen CPU-local model calls against 16 public development tasks, with 13 original deterministic scored cases per arm. SmolLM2 360M scored 1/13 for no-memory, lexical and diversified-memory. SmolLM2 1.7B scored 1/13 no-memory, 2/13 lexical, 1/13 diversified. The isolated lexical gain did not survive retrieval-policy comparison; no durable model-level learning or scientific generalization improvement was established. P17 confirmed known-correct and deliberately wrong official scorer controls both 13/13. Preserve the negative development finding for future experiments; do not promote this as autonomously learned production behavior.",
      "details":{"source_sha":RUNS["40865946484"],"run_id":40865946484,
        "diagnostic_run_id":40869961276,"development_only":True,
        "local_model_calls":96,"official_scored_per_arm":13,
        "independent_first_use":False,"scientific_acceptance":False,
        "production_deployment":False},
      "tags":["mind-palace","mpai","usage-feedback","p16","p17",
              "development-negative","memory-efficiency","science-no-go"],
      "supersedes":[],"disposition_hint":"auto",
      "source_refs":[{"type":"commit","ref":commit,"note":"Original source, not release."},
         {"type":"acceptance","ref":run,"note":"Original Windows 96-call development evidence."},
         {"type":"acceptance","ref":confirm,"note":"Original scorer control diagnostic."}]
    }]}
def main():
    check(os.name=="nt" and os.getenv("RUNNER_NAME")=="FORGE-CODEX-REMOTE"
          and os.getenv("GITHUB_REPOSITORY")=="spoonman136668-ai/FORGE",
          "ORIGINAL_WINDOWS")
    check(not os.getenv("OPENAI_API_KEY"),"NO_PAID_MODEL_API")
    scratch=pathlib.Path(os.environ["MPAI06_SCRATCH"])
    check(not scratch.exists() and shutil.disk_usage(scratch.parent).free>500000000,
          "SCRATCH_BOUND")
    scratch.mkdir()
    global STAGE
    STAGE="AUTH_RUNS"
    authentic_runs()
    STAGE="PRIVATE_CLONE"
    root=scratch/"mind-palace"
    process(["git","clone","--quiet","--filter=blob:none","--depth","1",
             "--single-branch","--branch","main",MAIN,str(root)],timeout=170)
    STAGE="PRIVATE_SOURCE_READ"
    head=git("rev-parse","HEAD",cwd=root)
    check(re.fullmatch("[a-f0-9]{40}",head)!=None,"SOURCE_SHA")
    before={k:hashlib.sha256((root/k).read_bytes()).hexdigest() for k in GUARD}
    STAGE="COLD_RECALL"
    snap=cold(root,head)
    batchfile=scratch/"feedback.json"
    batchfile.write_text(json.dumps(batch(),indent=2),encoding="utf-8")
    STAGE="CLASSIFY_EXISTING_COLLECTOR"
    data=process(["powershell.exe","-NoProfile","-NonInteractive",
        "-ExecutionPolicy","Bypass","-File",str(root/"tools"/"collect.ps1"),
        "classify","-InputPath",str(batchfile)],cwd=root)
    result=json.loads(data)
    check(result.get("schema")=="mind-palace.collector-result.v1"
          and result.get("candidate_count")==1 and result.get("primary_source_count")==1,
          "COLLECTOR_BUNDLE_RESULT")
    inner=result["result"]
    check(inner.get("schema")=="mind-palace.ingest-result.v1"
          and inner.get("command")=="classify" and inner.get("candidate_count")==1
          and len(inner.get("results",[]))==1,"COLLECTOR_CLASSIFY_RESULT")
    choice=inner["results"][0]
    check(choice.get("candidate_id")==NEW and choice.get("action") in
          ("new","review","merge","archive","ignore"),"CLASSIFICATION_IDENTITY")
    STAGE="DURABLE_INTEGRITY"
    check(before=={k:hashlib.sha256((root/k).read_bytes()).hexdigest()
                    for k in GUARD},"PROTECTED_DURABLE_FILE_CHANGED")
    check(git("rev-parse","HEAD",cwd=root)==head,"PRIVATE_HEAD_CHANGED")
    check(not git("status","--porcelain","--untracked-files=all",cwd=root),
          "SOURCE_WORKTREE_DIRTY")
    check(git("ls-remote","--exit-code",MAIN,"refs/heads/main").split()[0]==head,
          "PRIVATE_MAIN_RACED")
    check(cold(root,head)==snap,"POST_CLASSIFY_COLD_RECALL_CHANGED")
    print("MPAI06_REAL_RUNS=2_AUTHENTIC")
    print("MPAI06_ORIGINAL_WINDOWS=PASS")
    print("MPAI06_ACCEPTED_COLD_RECALL=2_PASS")
    print("MPAI06_PROJECT_SCOPE=PASS")
    print("MPAI06_CANONICAL_COLLECTOR_CLASSIFY=PASS")
    print("MPAI06_NEW_USAGE_FEEDBACK_DISPOSITION="+choice["action"].upper())
    print("MPAI06_NEW_FEEDBACK_ACCEPTED=FALSE")
    print("MPAI06_PRIVATE_SOURCE_SHA="+head)
    print("MPAI06_NINE_PROTECTED_HASHES=PASS")
    print("MPAI06_PRIVATE_MAIN_STABLE=PASS")
    print("MPAI06_AUTOMATIC_INGESTION=FALSE")
    print("MPAI06_PRODUCTION_WRITES=0")
    print("MPAI06_SCIENTIFIC_ACCEPTANCE=FALSE")
if __name__=="__main__":
    try:main()
    except Exception as exc:
        msg=str(exc)
        print("MPAI06_SAFE_FAILURE="+
          (msg if re.fullmatch("MPAI06_[A-Z0-9_]{3,80}",msg) else "PRIVATE_FAILURE"))
        print("MPAI06_SAFE_ERROR_TYPE="+type(exc).__name__)
        print("MPAI06_SAFE_STAGE="+STAGE)
        sys.exit(2)

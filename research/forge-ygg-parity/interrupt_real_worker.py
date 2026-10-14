"""One-shot forced interruption of actual pinned Yggdrasil scientific evaluation.

Never retries the interrupted original; the only retry path is rejection.
"""
import argparse,hashlib,json,os,subprocess,sys,time
from pathlib import Path
ID="Y-FORGE-REAL-INTERRUPT-01"
def atomic(path,payload):
    fd=os.open(str(path),os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,"wb") as f:f.write(payload);f.flush();os.fsync(f.fileno())
def run(ygg,root):
    root.mkdir(parents=True,exist_ok=True)
    if (root/"started.json").exists() or (root/"interrupted.json").exists():raise ValueError("YGG_INTERRUPTED_FIRST_USE_ALREADY_STARTED")
    marker=root/"first-real-evaluation.json"
    args=[sys.executable,"-B",str(Path(__file__).with_name("run_original.py")),
        "--study",ID,"--ygg-root",str(ygg),"--out",str(root/"original.json"),
        "--real-interrupt-marker",str(marker)]
    atomic(root/"started.json",(json.dumps({"schema":"forge.ygg.worker-start.v1",
        "experiment_id":ID,"once_only":True,"second_invocation_allowed":False})+"\n").encode())
    p=subprocess.Popen(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    try:
        deadline=time.monotonic()+150
        while not marker.exists():
            if p.poll() is not None:
                output=p.communicate(timeout=3)
                raise RuntimeError("YGG_WORKER_EXITED_BEFORE_REAL_EVALUATION:"+str(output)[-1600:])
            if time.monotonic()>deadline:raise TimeoutError("YGG_REAL_EVALUATOR_NEVER_REPORTED")
            time.sleep(.05)
        evidence=json.loads(marker.read_bytes())
        if evidence.get("experiment_id")!=ID or evidence.get("evaluations_completed")!=1 or evidence.get("worker_pid")!=p.pid:
            raise ValueError("YGG_FAKE_OR_INVALID_EVALUATOR_MARKER")
        if p.poll() is not None:raise ValueError("YGG_WORKER_COMPLETED_BEFORE_INTERRUPTION")
        p.terminate()
        try:p.wait(timeout=12)
        except subprocess.TimeoutExpired:
            p.kill();p.wait(timeout=8)
        if p.returncode==0 or (root/"original.json").exists():
            raise ValueError("YGG_WORKER_DID_NOT_ABORT")
        receipt={"schema":"forge.ygg.real-worker-interrupted.v1","experiment_id":ID,
            "scientific_evaluations_completed_at_least":1,
            "actual_worker_killed":True,"exit_code":p.returncode,
            "original_artifact_exists":False,"first_use_consumed":True,
            "rerun_allowed":False,"quarantine_required":True}
        atomic(root/"interrupted.json",(json.dumps(receipt,sort_keys=True)+"\n").encode())
        print("YGG_REAL_SCIENTIFIC_WORKER_INTERRUPTED=PASS",flush=True)
        print("YGG_REAL_EVALUATION_BEFORE_STOP=PASS",flush=True)
    finally:
        if p.poll() is None:p.kill();p.wait(timeout=8)
        if p.stdout:p.stdout.close()
        if p.stderr:p.stderr.close()
def quarantine(evidence_root,out):
    started=json.loads((evidence_root/"started.json").read_bytes())
    interrupted=json.loads((evidence_root/"interrupted.json").read_bytes())
    marker=json.loads((evidence_root/"first-real-evaluation.json").read_bytes())
    if started.get("experiment_id")!=ID or interrupted.get("experiment_id")!=ID or interrupted.get("actual_worker_killed") is not True or interrupted.get("first_use_consumed") is not True or interrupted.get("rerun_allowed") is not False or marker.get("evaluations_completed")!=1 or (evidence_root/"original.json").exists():
        raise ValueError("YGG_INTERRUPTED_EVIDENCE_INVALID")
    receipt={"schema":"forge.ygg.consumed-real-worker-recovery.v1","experiment_id":ID,
        "classification":"CONSUMED_INDETERMINATE",
        "interruption_receipt_sha256":hashlib.sha256((evidence_root/"interrupted.json").read_bytes()).hexdigest(),
        "real_scientific_evaluation_performed":True,"original_replayed":False,
        "rerun_allowed":False,"independently_quarantined":True}
    atomic(out,(json.dumps(receipt,sort_keys=True,indent=2)+"\n").encode())
    print("YGG_INDEPENDENT_RECOVERY_WITHOUT_REPLAY=PASS",flush=True)
def main():
    p=argparse.ArgumentParser()
    p.add_argument("mode",choices=("interrupt","quarantine"))
    p.add_argument("--ygg-root");p.add_argument("--root",required=True);p.add_argument("--out")
    a=p.parse_args()
    if a.mode=="interrupt":
        if not a.ygg_root:raise ValueError("YGG_ROOT_MISSING")
        run(Path(a.ygg_root),Path(a.root))
    else:
        if not a.out:raise ValueError("YGG_QUARANTINE_OUT_MISSING")
        quarantine(Path(a.root),Path(a.out))
if __name__=="__main__":main()

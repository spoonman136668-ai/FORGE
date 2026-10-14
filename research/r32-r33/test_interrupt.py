"""Controlled interruption proof: disposable worker only, never actual Wingless science."""
import json,os,subprocess,sys,tempfile,time,unittest
from pathlib import Path

def create_only(path,record):
    payload=(json.dumps(record,sort_keys=True,separators=(",",":"))+"\n").encode()
    fd=os.open(str(path),os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,"wb") as f:
        f.write(payload);f.flush();os.fsync(f.fileno())
    return payload

def reconcile(root):
    claim=root/"claim.json"
    if not claim.is_file():raise ValueError("RECOVERY_NO_CLAIM")
    c=json.loads(claim.read_bytes())
    if c!={"schema":"forge.disposable.once.v1","experiment_id":"TEST_ONLY_R32_R33_INTERRUPTED_WORKER",
          "consumed":True,"rerun_allowed":False}:raise ValueError("RECOVERY_CLAIM_DRIFT")
    quarantine=root/"quarantine.json"
    receipt={"schema":"forge.disposable.recovery.v1","experiment_id":c["experiment_id"],
             "outcome":"CONSUMED_INDETERMINATE","rerun_allowed":False,"worker_replayed":False}
    if quarantine.exists():
        if json.loads(quarantine.read_bytes())!=receipt:raise ValueError("RECOVERY_RECEIPT_DRIFT")
    else:create_only(quarantine,receipt)
    return receipt

class ControlledRecovery(unittest.TestCase):
    def test_interrupt_running_disposable_worker_without_replay(self):
        with tempfile.TemporaryDirectory(prefix="forge-recovery-") as td:
            root=Path(td)
            create_only(root/"claim.json",{"schema":"forge.disposable.once.v1",
                "experiment_id":"TEST_ONLY_R32_R33_INTERRUPTED_WORKER",
                "consumed":True,"rerun_allowed":False})
            p=subprocess.Popen([sys.executable,"-B",__file__,"--worker",td],
                               stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            try:
                deadline=time.monotonic()+8
                while not (root/"started.txt").exists():
                    if p.poll() is not None:raise RuntimeError("DISPOSABLE_WORKER_PREMATURE_EXIT")
                    if time.monotonic()>deadline:raise TimeoutError("DISPOSABLE_WORKER_DID_NOT_START")
                    time.sleep(.02)
                self.assertIsNone(p.poll())
                p.terminate()
                p.wait(timeout=5)
                self.assertIsNotNone(p.returncode)
                with self.assertRaises(FileExistsError):
                    create_only(root/"claim.json",{"retry":True})
                initial=reconcile(root)
                self.assertEqual(initial["outcome"],"CONSUMED_INDETERMINATE")
                self.assertEqual(reconcile(root),initial)
                self.assertEqual(len(list(root.glob("started*"))),1)
                (root/"quarantine.json").write_text("{}")
                with self.assertRaises(ValueError):reconcile(root)
                print("R32_R33_REAL_DISPOSABLE_WORKER_INTERRUPT=PASS")
                print("R32_R33_AUTOMATIC_RECONCILIATION_NO_REPLAY=PASS")
            finally:
                if p.poll() is None:
                    p.kill();p.wait(timeout=5)
    def test_reserved_no_worker_is_never_replayed(self):
        with tempfile.TemporaryDirectory(prefix="forge-reservation-") as td:
            root=Path(td)
            create_only(root/"claim.json",{"schema":"forge.disposable.once.v1",
                "experiment_id":"TEST_ONLY_R32_R33_INTERRUPTED_WORKER",
                "consumed":True,"rerun_allowed":False})
            self.assertEqual(reconcile(root)["outcome"],"CONSUMED_INDETERMINATE")
            with self.assertRaises(FileExistsError):
                create_only(root/"claim.json",{"retry":True})

if __name__=="__main__" and len(sys.argv)==3 and sys.argv[1]=="--worker":
    root=Path(sys.argv[2])
    if not (root/"claim.json").is_file():sys.exit(3)
    with (root/"started.txt").open("x") as f:
        f.write("DISPOSABLE_INTERRUPTION_TEST_ONLY\n")
        f.flush();os.fsync(f.fileno())
    time.sleep(30)
elif __name__=="__main__":
    unittest.main()

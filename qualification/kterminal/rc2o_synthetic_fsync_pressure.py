#!/usr/bin/env python3
"""RC2-O bounded same-volume Windows fsync pressure, test-only.

Owns only an empty designated RUNNER_TEMP child directory. Never opens a K-Terminal
source, profile, account, or production ledger file; it writes a capped synthetic
file and exports aggregate counters, without paths or customer content.
"""
import json
import os
import pathlib
import statistics
import sys
import time

def main():
    if len(sys.argv)!=2:
        raise RuntimeError("SINGLE_PRIVATE_DIRECTORY_REQUIRED")
    root=pathlib.Path(sys.argv[1]).resolve(strict=True)
    if not root.is_dir() or any(root.iterdir()):
        raise RuntimeError("FSYNC_WORKSPACE_MUST_BE_EMPTY")
    ready=root/"ready.flag"
    stop=root/"stop.flag"
    data=root/"synthetic-overwrite.bin"
    summary=root/"fsync-summary.json"
    block=(b"RC2O_DATA_NON_SENSITIVE_"*7000)[:131072]
    duration=[]
    count=0
    total=0
    fail=0
    started=time.perf_counter()
    ready.write_text("READY",encoding="ascii")
    try:
        with data.open("w+b",buffering=0) as f:
            while time.perf_counter()-started<105 and not stop.exists():
                try:
                    f.seek((count%64)*len(block))
                    before=time.perf_counter()
                    f.write(block)
                    f.flush()
                    os.fsync(f.fileno())
                    duration.append((time.perf_counter()-before)*1000)
                    count+=1
                    total+=len(block)
                except OSError:
                    fail+=1
                    break
                time.sleep(.012)
    finally:
        values=sorted(duration)
        p95=values[min(len(values)-1,int(.95*(len(values)-1)))] if values else None
        evidence={"schema":"kterminal.rc2o.synthetic-fsync-load.v1",
            "count":count,"total_written_bytes":total,"write_errors":fail,
            "max_fsync_ms":round(max(values),3) if values else None,
            "p95_fsync_ms":round(p95,3) if p95 is not None else None,
            "elapsed_s":round(time.perf_counter()-started,3),
            "synthetic_files_only":True,"bounded_file_size_bytes":64*len(block)}
        summary.write_text(json.dumps(evidence,sort_keys=True),encoding="utf-8")
    return 0 if count>0 and fail==0 else 2

if __name__=="__main__":
    try:sys.exit(main())
    except Exception as e:
        print("KTERM_RC2O_PRESSURE=FAIL_CLOSED:"+type(e).__name__)
        sys.exit(2)

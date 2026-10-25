#!/usr/bin/env python3
"""L10-C10: SOURCE-FREE local Linux namespace masking diagnostic.

NOT a complete scientific model sandbox. Tests denial for one invented source
canary after mount masking and privilege dropping; this does not secure other
paths, network, devices, or Windows. Must fail closed if host lacks primitives.
"""
from __future__ import annotations
import hashlib
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile

CANARY = b'UNPUBLIC_RELATION_MAP = {"P0": "located_in"}\n'
PAYLOAD = r'''import json,pathlib,subprocess,sys
p=pathlib.Path(sys.argv[1])
def try_read(path):
    try:
        path.read_bytes()
        return "READABLE"
    except OSError as err:
        return type(err).__name__
result={
    "direct":try_read(p),
    "proc1_root":try_read(pathlib.Path("/proc/1/root"+str(p))),
}
try:
    result["unmount_exit"] = subprocess.run(
        ["umount",str(p.parent)],capture_output=True,text=True,timeout=2
    ).returncode
except (OSError,subprocess.TimeoutExpired):
    result["unmount_exit"] = "BLOCKED_OR_UNAVAILABLE"
print(json.dumps(result,sort_keys=True))'''
BIND_SCRIPT = '''set -eu
mount --bind "$1" "$2"
shift 2
exec setpriv --no-new-privs --bounding-set=-all -- "$@"
'''


def check():
    if not sys.platform.startswith("linux"):
        return {"status":"BLOCKED_UNSUPPORTED_PLATFORM", "scientific_go":False}
    if any(shutil.which(x) is None for x in ("unshare","mount","setpriv","umount")):
        return {"status":"BLOCKED_MISSING_ISOLATION_TOOLS", "scientific_go":False}
    with tempfile.TemporaryDirectory(prefix="l10-c10-sourcefree-") as tmp:
        root=pathlib.Path(tmp)
        trusted,empty,worker=(root/x for x in ("trusted-source","empty","worker"))
        for d in (trusted,empty,worker): d.mkdir()
        canary=trusted/"canary.txt"
        canary.write_bytes(CANARY)
        canary.chmod(0o600)
        launch=[sys.executable,"-I","-S","-c",PAYLOAD,str(canary)]
        try:
            plain=subprocess.run(launch,cwd=worker,capture_output=True,text=True,timeout=8,check=True)
            isolated=subprocess.run([
                "unshare","--user","--map-root-user","--mount","--fork",
                "bash","-c",BIND_SCRIPT,"-",str(empty),str(trusted),*launch,
            ],cwd=worker,capture_output=True,text=True,timeout=12)
        except (OSError,subprocess.SubprocessError) as exc:
            return {"status":"BLOCKED_EXECUTION", "error_type":type(exc).__name__,"scientific_go":False}
        if isolated.returncode:
            return {"status":"BLOCKED_NAMESPACE_SETUP", "exit_code":isolated.returncode,"scientific_go":False}
        try:
            p=json.loads(plain.stdout)
            q=json.loads(isolated.stdout)
        except (json.JSONDecodeError,TypeError):
            return {"status":"BLOCKED_MALFORMED_RECEIPT", "scientific_go":False}
        passed=(p["direct"]=="READABLE"
                and q["direct"] in ("PermissionError","FileNotFoundError")
                and q["proc1_root"] in ("PermissionError","FileNotFoundError")
                and q["unmount_exit"]!=0
                and canary.read_bytes()==CANARY)
        return {
            "status":"LOCAL_NAMESPACE_CANARY_DENIAL_PASS" if passed else "BLOCKED_CANARY_LEAK",
            "ordinary_process_can_read":p["direct"]=="READABLE",
            "isolated_can_read":q["direct"]=="READABLE",
            "proc_alias_can_read":q["proc1_root"]=="READABLE",
            "unmount_denied":q["unmount_exit"]!=0,
            "source_unchanged":canary.read_bytes()==CANARY,
            "canary_sha256":hashlib.sha256(CANARY).hexdigest(),
            "prospective_examples_generated":0,
            "scientific_go":False,
        }


if __name__ == "__main__":
    result=check()
    print(json.dumps(result,sort_keys=True))
    sys.exit(0 if result["status"]=="LOCAL_NAMESPACE_CANARY_DENIAL_PASS" else 2)

"""F139-D: PR-only real model-free execution and *simulated* HMAC admission."""
import argparse
import hashlib
import json
from pathlib import Path
import secrets
from f139.verify_ticket import Untrusted, admit, receipt, signature

def qualified(raw, sha, rid, oslabel, checkout_head):
    key=secrets.token_hex(32)
    fields={"key":key,"ticket":"f139-pr-rehearsal-01","lane":"Qualification",
            "source_sha":sha,"epoch":"1","repository":"spoonman136668-ai/FORGE",
            "ref":"refs/heads/main","event":"workflow_dispatch","head_sha":sha,
            "run_attempt":"1","run_id":rid,"os":oslabel}
    fields["signature"]=signature(key,fields["ticket"],fields["lane"],sha,fields["epoch"])
    if admit(fields) is not True:
        raise RuntimeError("F139D_POSITIVE_ADMISSION_FAILED")
    verified=receipt(fields,raw)
    rejected=[]
    badsig="0"*64 if fields["signature"]!="0"*64 else "1"*64
    for name,changes in (
        ("wrong-hmac",{"signature":badsig}),
        ("wrong-event",{"event":"pull_request"}),
        ("wrong-branch",{"ref":"refs/heads/pr"}),
        ("wrong-source",{"head_sha":"0"*40}),
        ("rerun",{"run_attempt":"2"}),
        ("wrong-os",{"os":"bad-runner"})):
        try:
            admit({**fields,**changes})
        except Untrusted:
            rejected.append(name)
        else:
            raise RuntimeError("F139D_NEGATIVE_ADMISSION_FAILED:"+name)
    wrong=json.loads(raw)
    wrong["scientific_first_use_authorized"]=True
    try:
        receipt(fields,(json.dumps(wrong)+"\n").encode())
    except Untrusted:
        rejected.append("false-science")
    else:
        raise RuntimeError("F139D_FALSE_SCIENCE_NOT_REJECTED")
    assert len(rejected)==7
    evidence={"schema":"forge.f139d.github-hosted-rehearsal.v1",
      "source_sha":sha,"pr_checkout_head_sha":checkout_head,"github_run_id":rid,"os":oslabel,
      "execution":"ACTUAL_GITHUB_HOSTED_MODEL_FREE_GO_RUN",
      "admission":"SIMULATED_EVENT_EPHEMERAL_HMAC_NOT_LIVE_DISPATCH",
      "live_dispatch":False,"repository_secret_used":False,
      "controller_enabled":False,"scientific_first_use":False,
      "genuine_worker_custody":False,
      "advisory_sha256":hashlib.sha256(raw).hexdigest(),
      "rejections":rejected}
    return evidence,verified

def main():
    p=argparse.ArgumentParser()
    for n in ("advisory","output","source-sha","checkout-head","run-id","os"):
        p.add_argument("--"+n,required=True)
    a=p.parse_args()
    target=Path(a.output)
    if (target.exists() or len(a.source_sha)!=40 or
        any(ch not in "0123456789abcdef" for ch in a.source_sha) or
        len(a.checkout_head)!=40 or any(ch not in "0123456789abcdef" for ch in a.checkout_head) or not a.run_id.isdecimal() or int(a.run_id)<1 or
        a.os not in ("ubuntu-latest","windows-latest")):
        raise SystemExit("F139D_INPUT_INVALID")
    evidence,verified=qualified(Path(a.advisory).read_bytes(),a.source_sha,a.run_id,a.os,a.checkout_head)
    target.mkdir(parents=True)
    for name,obj in (("f139d-rehearsal.json",evidence),
                     ("f139d-synthetic-receipt.json",verified)):
        raw=(json.dumps(obj,sort_keys=True,separators=(",",":"))+"\n").encode()
        with (target/name).open("xb") as f:f.write(raw)
    print("F139D_GITHUB_HOSTED_DEVELOPMENT_EXECUTION=PASS")
    print("F139D_EPHEMERAL_TICKET_REHEARSAL=PASS")
    print("F139D_AUTHENTIC_WORKFLOW_DISPATCH=NOT_TESTED")
    print("F139D_SCIENTIFIC_FIRST_USE=FALSE")

if __name__=="__main__":main()

"""FIT-only replay of genuine original selected MiniGrid source actions into UNCHANGED native Go R3.

No MiniGrid import, reset, step, protected CHECK/DEV parser, counterfactual labels,
native model replacement, research scheduler or independent scientific first use.
"""
import argparse
import base64
import collections
import hashlib
import json
import math
import re
import subprocess
import time
import zipfile
from pathlib import Path

EXPECTED_PROVIDER_SHA = "b81858a8b3b5b21cb064271d8f4d48694f3163e85dfec98752ce2a691de83985"
FIELD_NAMES = {"X", "Y", "GoalX", "GoalY", "Direction", "FrontBlocked"}
SOURCE_ROWS = 12000
EXPECTED_FAMILIES = {"empty": 6000, "fourrooms": 6000}
FIT_KEY = b'"FIT_original_public_experiences"'
EXPECTED_SEEDS = set(range(31400, 31424))
HEX = re.compile(r"^[0-9a-f]{64}$")

def digest(b):
    return hashlib.sha256(b).hexdigest()

def public_grid(row):
    if type(row) is not dict or set(row) != FIELD_NAMES:
        raise ValueError("R3_FIT_PUBLIC_FIELDS_DRIFT")
    if any(type(row[x]) is not int or not 0 <= row[x] <= 64 for x in
           ("X", "Y", "GoalX", "GoalY")):
        raise ValueError("R3_FIT_PUBLIC_COORDINATE_DRIFT")
    if type(row["Direction"]) is not int or row["Direction"] not in range(4):
        raise ValueError("R3_FIT_PUBLIC_HEADING_DRIFT")
    if type(row["FrontBlocked"]) is not bool:
        raise ValueError("R3_FIT_PUBLIC_BLOCKED_DRIFT")
    return {k: row[x] for x,k in [
        ("X","x"),("Y","y"),("GoalX","goal_x"),("GoalY","goal_y"),
        ("Direction","direction"),("FrontBlocked","front_blocked")
    ]}

def legal_record(item):
    keys = {"family","seed","before","after","action","reward","terminal",
            "start_sha256","next_sha256"}
    if type(item) is not dict or set(item) != keys:
        raise ValueError("R3_FIT_ROLE_SHAPE_DRIFT")
    if item["family"] not in EXPECTED_FAMILIES:
        raise ValueError("R3_FIT_FOREIGN_SOURCE_FAMILY")
    if type(item["seed"]) is not int or item["seed"] not in EXPECTED_SEEDS:
        raise ValueError("R3_FIT_PROTECTED_OR_UNKNOWN_SEED")
    if type(item["action"]) is not int or item["action"] not in (0,1,2):
        raise ValueError("R3_FIT_ILLEGAL_OR_UNEXECUTED_ACTION")
    if type(item["terminal"]) is not bool:
        raise ValueError("R3_FIT_TERMINAL_TYPE_DRIFT")
    if type(item["reward"]) not in (int,float) or not math.isfinite(item["reward"]):
        raise ValueError("R3_FIT_REWARD_TYPE_DRIFT")
    if any(type(item[n]) is not str or HEX.fullmatch(item[n]) is None
           for n in ("start_sha256","next_sha256")):
        raise ValueError("R3_FIT_SOURCE_OBSERVATION_HASH_DRIFT")
    a=public_grid(item["before"]);b=public_grid(item["after"])
    if (a["goal_x"],a["goal_y"]) != (b["goal_x"],b["goal_y"]):
        raise ValueError("R3_FIT_PUBLIC_GOAL_DISCONTINUITY")
    dx=b["x"]-a["x"];dy=b["y"]-a["y"]
    if item["action"] in (0,1):
        if (dx,dy)!=(0,0) or b["direction"]!=(a["direction"]+(1 if item["action"]==1 else -1))%4:
            raise ValueError("R3_FIT_ILLEGAL_TURN_CONSEQUENCE")
    elif b["direction"]!=a["direction"] or abs(dx)+abs(dy)>1:
        raise ValueError("R3_FIT_ILLEGAL_FORWARD_CONSEQUENCE")
    return a,b

def only_original_fit(archive):
    data=Path(archive).read_bytes()
    if digest(data)!=EXPECTED_PROVIDER_SHA:
        raise ValueError("R3_FIT_ORIGINAL_PROVIDER_SHA_DRIFT")
    with zipfile.ZipFile(archive) as z:
        if z.testzip() is not None or "process-a.json" not in z.namelist():
            raise ValueError("R3_FIT_ORIGINAL_PROVIDER_ZIP_INTEGRITY")
        raw=z.read("process-a.json")
    # Important: do NOT parse the surrounding source receipt, which includes
    # consumed CHECK and DEV. Parse only the original already-consumed FIT array.
    if raw.count(FIT_KEY)!=1:
        raise ValueError("R3_FIT_ORIGINAL_ARRAY_CUSTODY")
    m=re.search(rb'"FIT_original_public_experiences"\s*:\s*',raw)
    if m is None:
        raise ValueError("R3_FIT_ORIGINAL_ROLE_MISSING")
    text=raw[m.end():].decode("utf-8")
    rows,_=json.JSONDecoder().raw_decode(text)
    if type(rows) is not list or len(rows)!=SOURCE_ROWS:
        raise ValueError("R3_FIT_ORIGINAL_RECORD_COUNT_DRIFT")
    totals=collections.Counter()
    seen=collections.defaultdict(set)
    for row in rows:
        legal_record(row)
        totals[row["family"]]+=1
        seen[row["family"]].add(row["seed"])
    if dict(totals)!=EXPECTED_FAMILIES or any(seen[f]!=EXPECTED_SEEDS for f in EXPECTED_FAMILIES):
        raise ValueError("R3_FIT_ORIGINAL_WORLD_EXPOSURE_DRIFT")
    # Canonical public FIT identity is computed from only this selected array.
    public_sha=digest(json.dumps(rows,sort_keys=True,separators=(",",":")).encode())
    return rows,public_sha

class RealGoR3:
    def __init__(self,binary):
        self.proc=subprocess.Popen([str(binary)],stdin=subprocess.PIPE,
             stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,bufsize=1)
    def op(self,op,**args):
        if self.proc.poll() is not None:
            raise ValueError("R3_ORIGINAL_GO_PROCESS_TERMINATED")
        self.proc.stdin.write(json.dumps({"op":op,**args},sort_keys=True,separators=(",",":"))+"\n")
        self.proc.stdin.flush()
        line=self.proc.stdout.readline()
        if not line:
            raise ValueError("R3_ORIGINAL_GO_REPLY_MISSING")
        response=json.loads(line)
        if response.get("ok") is not True:
            raise ValueError("R3_ORIGINAL_GO_REJECTED_"+op+":"+str(response.get("error")))
        return response
    def close(self):
        if self.proc.poll() is None:
            self.op("quit")
            self.proc.stdin.close()
            self.proc.wait(timeout=30)
        if self.proc.returncode!=0:
            raise ValueError("R3_ORIGINAL_GO_EXIT_FAILED:"+self.proc.stderr.read()[-4000:])
        self.proc.stdout.close()
        self.proc.stderr.close()

def replay(archive,binary):
    rows,fit_sha=only_original_fit(archive)
    stats={f:{"rows":0,"eligible":0,"correct":0,"fallback":0,
              "front_blocked_predicted_mismatches":0} for f in EXPECTED_FAMILIES}
    model=RealGoR3(binary)
    checkpoint=None
    start=time.process_time()
    try:
        for ix,row in enumerate(rows):
            before,after=legal_record(row)
            prediction=model.op("predict",before=before,action=row["action"])
            f=stats[row["family"]]
            f["rows"]+=1
            if prediction["reliable"]:
                f["eligible"]+=1
                p=prediction["predicted"]
                if (p["x"],p["y"],p["direction"])==(after["x"],after["y"],after["direction"]):
                    f["correct"]+=1
                if p["front_blocked"]!=after["front_blocked"]:
                    f["front_blocked_predicted_mismatches"]+=1
            else:
                f["fallback"]+=1
            learned=model.op("learn",before=before,after=after,action=row["action"],
                    reward=row["reward"],terminal=row["terminal"])
            if learned.get("updates")!=ix+1:
                raise ValueError("R3_ORIGINAL_GO_NATIVE_COUNT_CONSERVATION_AT_"+str(ix))
        state=model.op("snapshot")
        if state["updates"]!=SOURCE_ROWS:
            raise ValueError("R3_ORIGINAL_GO_POST_FIT_UPDATES")
        checkpoint=base64.b64decode(state["state"],validate=True)
        envelope=json.loads(checkpoint)
        d=envelope["data"]
        if (d["completed_events"]!=SOURCE_ROWS or
              sum(x["samples"] for x in d["learned_effects"])!=SOURCE_ROWS or
              sum(x["seen"] for x in d["public_cell_evidence"].values())!=SOURCE_ROWS):
            raise ValueError("R3_ORIGINAL_GO_CHECKPOINT_EVENT_CUSTODY")
        choice=model.op("choose",before=public_grid(rows[-1]["before"]))["action"]
        final_prediction=model.op("predict",before=public_grid(rows[-1]["before"]),
                                  action=rows[-1]["action"])
    finally:
        model.close()
    cold=RealGoR3(binary)
    try:
        response=cold.op("load",state=base64.b64encode(checkpoint).decode())
        if response["updates"]!=SOURCE_ROWS:
            raise ValueError("R3_ORIGINAL_GO_COLD_RESTORE_COUNT_DRIFT")
        if cold.op("snapshot")["state"]!=base64.b64encode(checkpoint).decode():
            raise ValueError("R3_ORIGINAL_GO_COLD_RESTORE_STATE_DRIFT")
        if cold.op("choose",before=public_grid(rows[-1]["before"]))["action"]!=choice:
            raise ValueError("R3_ORIGINAL_GO_COLD_RESTORE_ACTION_DRIFT")
        if cold.op("predict",before=public_grid(rows[-1]["before"]),
                   action=rows[-1]["action"])!=final_prediction:
            raise ValueError("R3_ORIGINAL_GO_COLD_RESTORE_PREDICTION_DRIFT")
    finally:
        cold.close()
    return {
        "gate":"O21_S13_GENUINE_ORIGINAL_SELECTED_PUBLIC_FIT_GO_ONLY",
        "protected_first_use":False,"original_environment_steps_this_gate":0,
        "model":"original_Wingless_R3_3b11363b93e61311a8e96de2546b1a7f7f62d5db",
        "original_provider_zip_sha256":EXPECTED_PROVIDER_SHA,
        "public_fit_only_canonical_sha256":fit_sha,
        "actual_genuine_selected_action_updates":SOURCE_ROWS,
        "checkpoint_bytes":len(checkpoint),
        "checkpoint_sha256":digest(checkpoint),
        "native_learned_effect_categories_with_positive_samples":sum(x["samples"]>0 for x in d["learned_effects"]),
        "native_map_cells":len(d["public_cell_evidence"]),
        "native_map_contradictions":sum(x["contradictions"] for x in d["public_cell_evidence"].values()),
        "current_process_python_cpu_seconds_excludes_go_subprocess":time.process_time()-start,
        "by_family":stats,
        "cold_os_process_original_native_restore":"PASS",
        "scientific_go":False
    }

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--original-provider-zip",type=Path,required=True)
    p.add_argument("--original-go-bridge",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    report=replay(a.original_provider_zip,a.original_go_bridge)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(report,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({k:v for k,v in report.items() if k!="by_family"},sort_keys=True))
    print("O21_S13_AUTHENTIC_ORIGINAL_PUBLIC_FIT_REAL_GO=PASS")
    print("ORIGINAL_SCIENTIFIC_FIRST_USE=FALSE")
if __name__=="__main__": main()

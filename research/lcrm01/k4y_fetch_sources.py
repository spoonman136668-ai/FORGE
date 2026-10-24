#!/usr/bin/env python3
"""K4Y source-id pinned R1 and R2 native files, not generated substitutes."""
import argparse,base64,hashlib,json,os
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request,urlopen
PIN=Path(__file__).with_name("k4y_frozen_learned_affordance.json")
NAMES=("wingless_R1","wingless_R2","yggdrasil_R1","yggdrasil_R2")
def fetch(o):
 url="https://api.github.com/repos/"+o["repo"]+"/contents/"+quote(o["file"],safe="/")+"?ref="+o["head"]
 h={"Accept":"application/vnd.github+json","X-GitHub-Api-Version":"2022-11-28","User-Agent":"K4Y-Causal-Source"}
 if os.environ.get("GH_TOKEN"):h["Authorization"]="Bearer "+os.environ["GH_TOKEN"]
 with urlopen(Request(url,headers=h),timeout=40) as rr:
  obj=json.load(rr)
 if obj.get("type")!="file" or obj.get("encoding")!="base64":
  raise ValueError("K4Y_NOT_SOURCE_FILE")
 raw=base64.b64decode(obj["content"].replace("\n",""),validate=True)
 blob=hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()
 if blob!=o["blob"] or obj["sha"]!=blob:
  raise ValueError("K4Y_ORIGINAL_SOURCE_IDENTITY_FAILED")
 return raw,blob

def main():
 q=argparse.ArgumentParser()
 for name in NAMES:q.add_argument("--"+name.replace("_","-"),required=True,type=Path)
 a=q.parse_args();p=json.loads(PIN.read_text())
 if p.get("schema")!="mass.lcrm01.k4y.frozen-learned-affordance-intervention-v1":
  raise ValueError("K4Y_PREREG_DRIFT")
 for name in NAMES:
  target=getattr(a,name)
  if target.exists() or not target.parent.is_dir():
   raise ValueError("K4Y_NONFRESH_SOURCE_DESTINATION")
  raw,blob=fetch(p["source"][name]);target.write_bytes(raw)
  print("K4Y_"+name+"_ORIGINAL_BLOB="+blob)
if __name__=="__main__":main()

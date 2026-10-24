#!/usr/bin/env python3
"""Fetch EXACT independently qualified native source; no implied source replacement."""
import argparse,base64,hashlib,json,os
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.parse import quote

FROZEN=Path(__file__).with_name("k4u_frozen_native_minigrid.json")

def read(candidate):
    url=("https://api.github.com/repos/"+candidate["repo"]+
       "/contents/"+quote(candidate["source_file"],safe="/")+"?ref="+candidate["commit"])
    h={"Accept":"application/vnd.github+json","X-GitHub-Api-Version":"2022-11-28",
      "User-Agent":"K4U-public-native-source-identity"}
    token=os.environ.get("GH_TOKEN","")
    if token:h["Authorization"]="Bearer "+token
    with urlopen(Request(url,headers=h),timeout=30) as rsp:
        data=json.load(rsp)
    if data.get("encoding")!="base64" or data.get("type")!="file":
        raise ValueError("K4U_NATIVE_ORIGINAL_SOURCE_NOT_A_FILE")
    content=base64.b64decode(data["content"].replace("\n",""),validate=True)
    blob=hashlib.sha1(b"blob "+str(len(content)).encode()+b"\0"+content).hexdigest()
    if blob!=candidate["blob"] or data.get("sha")!=blob:
        raise ValueError("K4U_NATIVE_PINNED_SOURCE_BLOB_MISMATCH:"+candidate["repo"])
    return content,blob

def main():
    a=argparse.ArgumentParser()
    a.add_argument("--wingless-out",type=Path,required=True)
    a.add_argument("--yggdrasil-out",type=Path,required=True)
    x=a.parse_args()
    p=json.loads(FROZEN.read_text())
    if p.get("schema")!="mass.lcrm01.k4u.frozen-native-learned-minigrid-transfer.v1":
        raise ValueError("K4U_UNFROZEN_SOURCE")
    for label,path in (("wingless",x.wingless_out),("yggdrasil",x.yggdrasil_out)):
        if path.exists() or not path.parent.is_dir():
            raise RuntimeError("K4U_NATIVE_OUTPUT_NOT_ISOLATED")
        content,blob=read(p["sources"][label])
        path.write_bytes(content)
        print("K4U_"+label.upper()+"_ORIGINAL_GIT_BLOB="+blob)
if __name__=="__main__":
    main()

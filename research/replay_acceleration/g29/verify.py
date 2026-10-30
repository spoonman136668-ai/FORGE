import json, subprocess, sys, hashlib
binary=sys.argv[1]
results={}
for mode in ("idle","busy","parallel"):
    samples=[]
    for _ in range(3):
        p=subprocess.run([binary,"-role=parent","-mode="+mode],capture_output=True,text=True,check=True)
        r=json.loads(p.stdout)
        assert r["schema"]=="forge.rar.g29.cooperative-meter.v1"
        assert r["peak_child_rss_bytes"]>0 and r["child_cpu_seconds"]>=0
        assert r["child_count"]==(2 if mode=="parallel" else 1)
        samples.append(r)
    assert len({x["output_sha256"] for x in samples})==1,mode
    results[mode]={"min_cpu_s":min(x["child_cpu_seconds"] for x in samples),"max_cpu_s":max(x["child_cpu_seconds"] for x in samples),"peak_child_rss_bytes":max(x["peak_child_rss_bytes"] for x in samples),"digest":samples[0]["output_sha256"]}
assert results["busy"]["min_cpu_s"]>results["idle"]["max_cpu_s"]+0.03,results
assert results["parallel"]["min_cpu_s"]>results["busy"]["min_cpu_s"],results
receipt={"schema":"forge.rar.g29.cooperative-meter-qualified.v1","os":sys.platform,"result":"SOURCE_ONLY_COOPERATIVE_CHILD_ACCOUNTING_PASS","scope":"DIRECT_CHILD_GO_PROCESSSTATE_CPU_AND_SELF_REPORTED_PEAK_RSS","tree_complete":False,"windows_job_object_measured":False,"original_world_steps":0,"native_training_executed":False,"measurements":results}
with open("rar_g29_receipt.json","w",encoding="utf-8") as f:json.dump(receipt,f,indent=2,sort_keys=True)
print(json.dumps(receipt,sort_keys=True))

import json,sys,subprocess
b=sys.argv[1];rows=[]
for i in range(2):
 p=subprocess.run([b,"-role=parent"],text=True,capture_output=True,check=True,timeout=30)
 r=json.loads(p.stdout);assert r["schema"]=="forge.rar.g32.cooperative-tree.v1"
 assert r["children"]==2 and r["total_descendant_cpu_s"]>0.2
 assert r["sum_individual_peak_rss_bytes_upper_bound_not_concurrent_peak"]>r["max_individual_peak_rss_bytes"]
 assert r["elapsed_ms"]<3500
 rows.append(r)
assert rows[0]["os"]==rows[1]["os"]
with open("rar_g32_receipt.json","w") as f:json.dump({"classification":"COOPERATIVE_NESTED_PARALLEL_WORKERS_PASS_ONLY_NOT_KERNEL_COMPLETE_TREE", "samples":rows,"physical_tree_peak_qualified":False,"new_world_episodes":0},f,indent=2)
print("RAR_G32_COOPERATIVE_NESTED_PARALLEL_PASS", rows[0]["os"])

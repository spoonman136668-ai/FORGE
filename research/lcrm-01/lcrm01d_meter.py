"""Source-only Linux complete-process CPU/RSS measurements; no accepted science."""
import json,os,subprocess,sys,hashlib,pathlib,statistics
HERE=pathlib.Path(__file__).resolve().parent
ARMS=('candidate','peer','ablation','symbolic')
rows=[]
for arm in ARMS:
 for trial in range(3):
  env=dict(os.environ,OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1')
  cmd=[sys.executable,'-B',str(HERE/'lcrm01d_trial.py'),'--arm',arm]
  # Use temporary named process stdout so no pipe holds open the child.
  out=HERE/f'.transient-{arm}-{trial}.json'
  try:
   with out.open('w') as f:
    p=subprocess.Popen(cmd,cwd=HERE,env=env,stdout=f,stderr=subprocess.DEVNULL,text=True)
    pid,status,cost=os.wait4(p.pid,0)
   if pid!=p.pid or os.waitstatus_to_exitcode(status)!=0:raise RuntimeError('original child failed: '+arm)
   row=json.loads(out.read_text()); row.update(repetition=trial,os_cpu_user_sys_ns=round((cost.ru_utime+cost.ru_stime)*1e9),os_peak_rss_bytes=cost.ru_maxrss*1024)
   rows.append(row)
  finally:
   out.unlink(missing_ok=True)
  print('FINISHED',arm,trial,flush=True)
rec={'schema':'mass.lcrm01.d.local-original-sourceonly-full-os.v1','rows':rows,'os_process_count':len(rows),'science_accepted':False,'external_firstuse':0,'host':'isolated local Linux, not independent hosted'}
path=HERE/'original_12_processes.json'
with path.open('x') as f:json.dump(rec,f,indent=2,sort_keys=True);f.write('\n')
print('SHA256',hashlib.sha256(path.read_bytes()).hexdigest(),flush=True)
for arm in ARMS:
 sub=[r for r in rows if r['arm']==arm]
 print(arm,'CV',[r['CV'] for r in sub],'cpu_median',statistics.median(r['os_cpu_user_sys_ns'] for r in sub),'rss_median',statistics.median(r['os_peak_rss_bytes'] for r in sub))

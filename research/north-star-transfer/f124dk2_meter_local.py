"""Local source-only complete Linux process resource metering; NOT hosted qualification."""
import json,os,subprocess,sys,tempfile
ARMS=('candidate','peer')
CODE='''import json,sys
import f124dk2_relational_models as m
from test_f124dk2_relational_models import analytic_fit
v=m.fit_only_diagnostics(sys.argv[1],analytic_fit()); print(json.dumps({'arm':sys.argv[1],'cv_exact':v['FIT_local_CV_exact_episodes_of_4'],'FIT_sha256':v['receipt']['FIT_sha256'],'parameters':v['receipt']['trainable_parameters'],'updates':v['receipt']['updates']}))'''
allrows=[]
for arm in ARMS:
 for trial in range(3):
  with tempfile.TemporaryFile(mode='w+t') as output,tempfile.TemporaryFile(mode='w+t') as error:
   env=dict(os.environ,OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1')
   p=subprocess.Popen([sys.executable,'-B','-c',CODE,arm],cwd=os.path.dirname(__file__),env=env,stdout=output,stderr=error,text=True)
   pid,status,cost=os.wait4(p.pid,0)
   output.seek(0);error.seek(0)
   if pid!=p.pid or os.waitstatus_to_exitcode(status)!=0:raise RuntimeError(error.read())
   row=json.loads(output.read())
   row.update(repeat=trial,cpu_ns=round((cost.ru_utime+cost.ru_stime)*1e9),peak_rss_bytes=cost.ru_maxrss*1024,source_only=True,scientific_acceptance=False)
   allrows.append(row)
print(json.dumps({'schema':'f124dk2.local-source-only-OS.v1','rows':allrows},sort_keys=True))

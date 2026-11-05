"""Real Windows byte-range contention on disposable files, never the owner."""
from pathlib import Path
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

from f139.local_controller import SingleOwner

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(os.name == 'nt', 'Windows kernel and both native PowerShell hosts')
class OriginalOwnerMutexTests(unittest.TestCase):
    def run_shells(self, root, body, csharp=""):
        helper = str(ROOT/'f139/F139OriginalOwnerMutex.cs').replace("'", "''")
        path = str(root/'original.lock').replace("'", "''")
        for shell in ('powershell.exe', 'pwsh.exe'):
            with self.subTest(shell=shell):
                exe = shutil.which(shell)
                self.assertIsNotNone(exe)
                extra=root/'test-harness.cs'; extra.write_text(csharp)
                extra_ps=str(extra).replace("'", "''")
                script = ("$ErrorActionPreference='Stop'\n"
                          "Add-Type -TypeDefinition ((Get-Content -LiteralPath '"+helper+
                          "' -Raw)+[Environment]::NewLine+(Get-Content -LiteralPath '"+extra_ps+"' -Raw))\n$p='"+path+"'\n"+body)
                ps = root/'probe.ps1'; ps.write_text(script, encoding='utf-8')
                out = subprocess.run([exe, '-NoProfile', '-NonInteractive', '-File', str(ps)],
                    cwd=ROOT, env={**os.environ, 'PYTHONPATH':str(ROOT)},
                    capture_output=True, text=True, timeout=45)
                self.assertEqual(out.returncode, 0, out.stdout+out.stderr)

    def test_waits_for_existing_filestream_lock_without_writing_bytes(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); path=root/'original.lock'; path.write_bytes(b'L-original')
            self.run_shells(root, '[F139MutexTest.ReleaseOwner]::Test($p)', r'''
namespace F139MutexTest {
using System; using System.IO; using System.Threading; using System.Diagnostics;
public static class ReleaseOwner {
 public static void Test(string path) {
  var owner=new FileStream(path,FileMode.Open,FileAccess.ReadWrite,FileShare.ReadWrite);
  owner.Lock(0,1);
  var release=new Thread(delegate(){Thread.Sleep(250);owner.Unlock(0,1);owner.Dispose();});
  release.Start();var watch=Stopwatch.StartNew();
  try {
   using(var lease=F139OriginalOwnerMutex.Acquire(path,3000)) {
    if(watch.ElapsedMilliseconds<100)throw new Exception("did not wait for the owner");
    using(var probe=new FileStream(path,FileMode.Open,FileAccess.ReadWrite,FileShare.ReadWrite)) {
     bool denied=false;try{probe.Lock(0,1);probe.Unlock(0,1);}catch(IOException){denied=true;}
     if(!denied)throw new Exception("lease does not exclude another handle");
    }
   }
  } finally {release.Join();}
  using(var probe=new FileStream(path,FileMode.Open,FileAccess.ReadWrite,FileShare.ReadWrite)) {
   probe.Lock(0,1);probe.Unlock(0,1);
  }
 }
}
}
''')
            self.assertEqual(path.read_bytes(), b'L-original')

    def test_timeout_cannot_unlock_the_original_python_owner(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); path=root/'original.lock'
            probe=root/'held_owner_probe.py'
            probe.write_text('''import sys
from pathlib import Path
from f139.local_controller import SingleOwner, F139Error
try:
    with SingleOwner(Path(sys.argv[1])): pass
except F139Error:
    pass
else:
    raise AssertionError('Original Python owner was unlocked')
''')
            py=str(Path(sys.executable)).replace("'", "''")
            probe_ps=str(probe).replace("'", "''")
            for content in (b'L', b'L-original', b'L'*8193):
                path.write_bytes(content)
                with SingleOwner(path):
                    self.run_shells(root, r'''
$denied=$false
try {$lease=[F139OriginalOwnerMutex]::Acquire($p,80);$lease.Dispose()}
catch {if($_.Exception.GetBaseException() -is [TimeoutException]){$denied=$true}else{throw}}
if(-not $denied){throw 'Original Python owner was bypassed'}
''' + "& '"+py+"' -B '"+probe_ps+"' $p\n" + r'''
if($LASTEXITCODE -ne 0){throw 'Timeout released the original Python owner'}
''')
                with SingleOwner(path):
                    pass
                self.assertEqual(path.read_bytes(), content)

    def test_disposal_and_exceptions_release_the_same_python_mutex(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); path=root/'original.lock'; path.write_bytes(b'L-original')
            probe=root/'owner_probe.py'
            probe.write_text('''import sys
from pathlib import Path
from f139.local_controller import SingleOwner, F139Error
try:
    with SingleOwner(Path(sys.argv[1])): pass
except F139Error:
    assert sys.argv[2]=='deny'
else:
    assert sys.argv[2]=='allow'
''')
            py=str(Path(sys.executable)).replace("'", "''")
            probe_ps=str(probe).replace("'", "''")
            self.run_shells(root, """
$lease=[F139OriginalOwnerMutex]::Acquire($p,3000)
try {
 & '"""+py+"""' -B '"""+probe_ps+"""' $p deny
 if($LASTEXITCODE -ne 0){throw 'Python owner exclusion failed'}
 throw 'deliberate-post-acquisition-test-exception'
}catch {
 if($_.Exception.Message -cne 'deliberate-post-acquisition-test-exception'){throw}
}finally{$lease.Dispose();$lease.Dispose()}
& '"""+py+"""' -B '"""+probe_ps+"""' $p allow
if($LASTEXITCODE -ne 0){throw 'Python owner could not resume'}
""")
            self.assertEqual(path.read_bytes(), b'L-original')

    def test_missing_file_and_invalid_deadline_never_create_a_mutex(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            self.run_shells(root, r'''
foreach($deadline in @(-1,0,900001)) {
 $denied=$false
 try {$lease=[F139OriginalOwnerMutex]::Acquire($p,$deadline);$lease.Dispose()}
 catch {if($_.Exception.GetBaseException() -is [ArgumentOutOfRangeException]){$denied=$true}else{throw}}
 if(-not $denied){throw 'Unbounded deadline accepted'}
}
$denied=$false
try {$lease=[F139OriginalOwnerMutex]::Acquire($p,100);$lease.Dispose()}
catch {if($_.Exception.GetBaseException() -is [ComponentModel.Win32Exception]){$denied=$true}else{throw}}
if(-not $denied -or (Test-Path -LiteralPath $p)){throw 'Missing mutex was created'}
''')
            self.assertFalse((root/'original.lock').exists())

    def test_cancellation_racing_owner_release_cannot_leave_a_hidden_lock(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); path=root/'original.lock'; path.write_bytes(b'L-original')
            self.run_shells(root, '[F139MutexRace.ReleaseOwner]::Test($p)', r'''
namespace F139MutexRace {
using System; using System.IO; using System.Threading;
public static class ReleaseOwner {
 public static void Test(string path) {
  for(int i=0;i<18;i++) {
   var owner=new FileStream(path,FileMode.Open,FileAccess.ReadWrite,FileShare.ReadWrite);
   owner.Lock(0,1);int delay=(i%3==0)?3:(i%3==1)?10:30;
   var release=new Thread(delegate(){Thread.Sleep(delay);owner.Unlock(0,1);owner.Dispose();});
   release.Start();
   try {using(var lease=F139OriginalOwnerMutex.Acquire(path,10)) {}}
   catch(TimeoutException) {}
   finally {release.Join();}
   using(var probe=new FileStream(path,FileMode.Open,FileAccess.ReadWrite,FileShare.ReadWrite)) {
    probe.Lock(0,1);probe.Unlock(0,1);
   }
  }
 }
}
}
''')
            self.assertEqual(path.read_bytes(), b'L-original')


if __name__ == '__main__':
    unittest.main()

"""Linux CPU sandbox control qualification; never original/signed admission.

Uses existing user-systemd cgroups and a hash-verified rootless Ubuntu
bubblewrap binary extracted into a new directory. No OS package installation,
privileged fallback, project source, model, GPU or controller operation.
"""
from __future__ import annotations
import argparse
import ctypes
import ctypes.util
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import urllib.request
from f139.private_cpu_runtime import canonical, digest, hash_file, need, verify_receipt

RUNTIME_SOURCE='c0dc5857679cfb10b32361c23a6bb1a08bed16fb'
PARENT_ENV={'PATH':'/usr/bin:/bin','LANG':'C.UTF-8'}
MEMORY='4294967296'


def package_pin(text):
    block=text.strip().split('\n\n')[0]
    fields=dict(line.split(': ',1) for line in block.splitlines() if ': ' in line and not line.startswith(' '))
    need(fields.get('Package')=='bubblewrap' and fields.get('Architecture')=='amd64','BWRAP_PACKAGE_IDENTITY')
    filename=fields.get('Filename','');sha=fields.get('SHA256','')
    need(re.fullmatch(r'pool/(main|universe)/b/bubblewrap/[A-Za-z0-9._+%-]+\.deb',filename)
         and re.fullmatch('[a-f0-9]{64}',sha)
         and fields.get('Size','').isdigit() and 0<int(fields['Size'])<=5*1024*1024,'BWRAP_PACKAGE_PIN')
    return dict(version=fields['Version'],filename=filename,sha256=sha,size=int(fields['Size']))


def seccomp_filter(path):
    """Export libseccomp policy only; bubblewrap applies it after namespace setup."""
    need(platform.system()=='Linux' and platform.machine()=='x86_64','SECCOMP_PLATFORM')
    name=ctypes.util.find_library('seccomp');need(bool(name),'EXISTING_LIBSECCOMP_REQUIRED')
    lib=ctypes.CDLL(name)
    class Compare(ctypes.Structure):
        _fields_=[('arg',ctypes.c_uint),('op',ctypes.c_int),('a',ctypes.c_uint64),('b',ctypes.c_uint64)]
    lib.seccomp_init.argtypes=[ctypes.c_uint32];lib.seccomp_init.restype=ctypes.c_void_p
    lib.seccomp_release.argtypes=[ctypes.c_void_p]
    lib.seccomp_syscall_resolve_name.argtypes=[ctypes.c_char_p];lib.seccomp_syscall_resolve_name.restype=ctypes.c_int
    lib.seccomp_rule_add_array.argtypes=[ctypes.c_void_p,ctypes.c_uint32,ctypes.c_int,ctypes.c_uint,ctypes.POINTER(Compare)]
    lib.seccomp_rule_add_array.restype=ctypes.c_int
    lib.seccomp_export_bpf.argtypes=[ctypes.c_void_p,ctypes.c_int];lib.seccomp_export_bpf.restype=ctypes.c_int
    ctx=lib.seccomp_init(0x7fff0000);need(bool(ctx),'SECCOMP_CONTEXT')
    try:
        def rule(syscall,action=0x00050001,comparison=None):
            number=lib.seccomp_syscall_resolve_name(syscall.encode());need(number>=0,'SECCOMP_SYSCALL_UNRECOGNIZED')
            array=(Compare*1)(comparison) if comparison is not None else None
            need(lib.seccomp_rule_add_array(ctx,action,number,1 if array is not None else 0,array)==0,'SECCOMP_RULE')
        for syscall in ('unshare','setns','mount','umount2','pivot_root','chroot','ptrace',
                        'bpf','keyctl','add_key','request_key','perf_event_open','userfaultfd',
                        'process_vm_readv','process_vm_writev','open_by_handle_at','name_to_handle_at',
                        'init_module','finit_module','delete_module','reboot','kexec_load',
                        'swapon','swapoff','io_uring_setup','io_uring_enter','io_uring_register'):
            rule(syscall)
        # Permit ordinary threads/processes, never new namespaces. clone3 gets
        # ENOSYS so libc can use the filtered traditional clone fallback.
        rule('clone3',0x00050026)
        for bit in (0x00020000,0x02000000,0x04000000,0x08000000,0x10000000,0x20000000,0x40000000):
            rule('clone',comparison=Compare(0,7,bit,bit))
        for family in range(64):
            if family not in (1,2,10):rule('socket',comparison=Compare(0,4,family,0))
        rule('socket',comparison=Compare(0,5,64,0))
        for command in (0x5412,0x541c):rule('ioctl',comparison=Compare(1,4,command,0))
        with Path(path).open('xb') as stream:
            need(lib.seccomp_export_bpf(ctx,stream.fileno())==0,'SECCOMP_EXPORT')
        need(0<Path(path).stat().st_size<=32768,'SECCOMP_FILTER_BUDGET')
    finally:lib.seccomp_release(ctx)
    return hash_file(path)


def sandbox_argv(binary,runtime,probe,filter_fd):
    runtime=Path(runtime).resolve();probe=Path(probe).resolve()
    need(runtime.is_absolute() and (runtime/'python/bin/python3.11').is_file()
         and probe.is_file() and type(filter_fd) is int and filter_fd>=3,'SANDBOX_INPUTS')
    args=[str(binary),'--unshare-all','--unshare-user','--disable-userns','--assert-userns-disabled',
          '--new-session','--die-with-parent','--cap-drop','ALL','--clearenv','--ro-bind','/usr','/usr']
    for name in ('/bin','/sbin','/lib','/lib64'):
        path=Path(name)
        if path.is_symlink():
            target=os.readlink(path)
            need(not target.startswith('/') and '..' not in Path(target).parts,'SYSTEM_LINK_POLICY')
            args+=['--symlink',target,name]
        elif path.exists():args+=['--ro-bind',name,name]
    args+=['--proc','/proc','--dev','/dev','--dir','/etc']
    for name in ('passwd','group'):
        need((probe.parent/name).is_file(),'SANDBOX_IDENTITY_FILE_MISSING')
        args+=['--ro-bind',str(probe.parent/name),'/etc/'+name]
    if Path('/etc/ld.so.cache').is_file():args+=['--ro-bind','/etc/ld.so.cache','/etc/ld.so.cache']
    args+=['--ro-bind',str(runtime/'python'),str(runtime/'python'),'--ro-bind',str(probe),'/probe.py',
           '--size','67108864','--tmpfs','/tmp','--size','536870912','--tmpfs','/scratch',
           '--dir','/work','--chdir','/work','--seccomp',str(filter_fd)]
    for key,value in dict(PATH=str(runtime/'python/bin')+':/usr/bin:/bin',LANG='C.UTF-8',
                          TMPDIR='/scratch',PYTHONDONTWRITEBYTECODE='1',OMP_NUM_THREADS='1',
                          OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1').items():args+=['--setenv',key,value]
    return args+['--',str(runtime/'python/bin/python3.11'),'-I','-B','/probe.py']


PROBE='''import errno, hashlib, json, os, pathlib, socket, subprocess
checks={}
for path in ('/mnt/c','/run/WSL','/init','/home','/root','/dev/dxg','/dev/nvidia0','/sys'):
    checks['hidden:'+path]=not pathlib.Path(path).exists()
status=dict(line.split(':',1) for line in pathlib.Path('/proc/self/status').read_text().splitlines())
checks['no_new_privs']=status['NoNewPrivs'].strip()=='1'
checks['capabilities_dropped']=int(status['CapEff'].strip(),16)==0
for name in os.environ:
    assert name not in ('GH_TOKEN','GITHUB_TOKEN','F139_WORKER_HMAC_KEY','OPENAI_API_KEY','F139_PRIVATE_CANARY')
checks['credential_environment_absent']=True
for entry in pathlib.Path('/proc').iterdir():
    if entry.name.isdigit():
        try: data=(entry/'environ').read_bytes()
        except (PermissionError,FileNotFoundError):continue
        assert b'F139_PRIVATE_CANARY=' not in data and b'GH_TOKEN=' not in data
checks['all_visible_process_environments_clean']=True
try: pathlib.Path(CANARY_PATH).read_bytes()
except FileNotFoundError: checks['host_canary_hidden']=True
else: checks['host_canary_hidden']=False
try: pathlib.Path(RUNTIME_PATH+'/write-probe').write_bytes(b'blocked')
except OSError as exc: checks['runtime_readonly']=exc.errno in (errno.EROFS,errno.EACCES,errno.EPERM)
else: checks['runtime_readonly']=False
try: socket.socket(40,socket.SOCK_STREAM)
except OSError as exc: checks['vsock_blocked']=exc.errno==errno.EPERM
else: checks['vsock_blocked']=False
sock=socket.socket(socket.AF_INET,socket.SOCK_STREAM);sock.settimeout(1)
try:sock.connect(('127.0.0.1',HOST_PORT))
except OSError: checks['host_network_hidden']=True
else:checks['host_network_hidden']=False
sock.close()
probe=subprocess.run(['/usr/bin/unshare','--user','/usr/bin/true'],capture_output=True,check=False,timeout=5)
checks['nested_user_namespace_blocked']=probe.returncode!=0
pathlib.Path('/scratch/write-probe').write_bytes(b'private scratch')
checks['private_scratch_writable']=True
import torch, pytest, platform
checks['python_pinned']=platform.python_version()=='3.11.11'
checks['torch_cpu_pinned']=torch.__version__=='2.5.1+cpu' and torch.version.cuda is None
checks['pytest_pinned']=pytest.__version__=='8.3.4'
checks['cpu_tensor_smoke']=torch.ones(1,device='cpu').item()==1
assert all(checks.values()),json.dumps(checks,sort_keys=True)
print(json.dumps(dict(checks=checks,sandbox_control_probe_pass=True),sort_keys=True))
'''


def qualify(runtime,root,source_sha):
    need(platform.system()=='Linux' and os.getuid()==1000,'PRIVATE_LINUX_USER_REQUIRED')
    runtime=Path(runtime).resolve();root=Path(root)
    receipt=verify_receipt(runtime);need(receipt['source_sha']==RUNTIME_SOURCE,'QUALIFIED_RUNTIME_SOURCE')
    need(re.fullmatch('[a-f0-9]{40}',source_sha) and root.is_absolute() and not root.exists()
         and not root.is_symlink(),'NEW_SANDBOX_ROOT')
    bus=Path('/run/user/1000/bus');need(bus.exists(),'EXISTING_USER_MANAGER_REQUIRED')
    memory=dict(line.split(':',1) for line in Path('/proc/meminfo').read_text().splitlines())
    need(int(memory['MemAvailable'].split()[0])>=6*1024**2,'SANDBOX_MEMORY_HEADROOM')
    root.mkdir(mode=0o700);os.nice(19)
    if hasattr(os,'sched_setaffinity'):os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
    def command(argv,timeout=30,env=None):
        p=subprocess.run([str(x) for x in argv],env=env or PARENT_ENV,cwd=root,
                         stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=timeout,check=False)
        if p.returncode:
            print('F139_PRIVATE_SANDBOX_COMMAND_FAILURE='+canonical(dict(program=Path(argv[0]).name,
                exit_code=p.returncode,stderr_tail=p.stderr.decode('utf-8','replace')[-1800:])).decode('ascii'))
        need(p.returncode==0,'SANDBOX_TRUSTED_COMMAND_FAILED')
        return p.stdout.decode('utf-8','strict')
    pin=package_pin(command(['/usr/bin/apt-cache','show','--no-all-versions','bubblewrap']))
    (root/'package-lock.json').write_bytes(canonical(pin))
    url='https://archive.ubuntu.com/ubuntu/'+pin['filename']
    with urllib.request.urlopen(url,timeout=30) as response:
        data=response.read(pin['size']+1)
    need(len(data)==pin['size'] and digest(data)==pin['sha256'],'BWRAP_PACKAGE_HASH')
    package=root/'bubblewrap.deb';package.write_bytes(data)
    command(['/usr/bin/dpkg-deb','--extract',package,root/'package'])
    binary=root/'package/usr/bin/bwrap'
    need(binary.is_file() and not binary.is_symlink() and not binary.stat().st_mode & 0o6000,'ROOTLESS_BWRAP_REQUIRED')
    helptext=command([binary,'--help'])
    need(all(x in helptext for x in ('--disable-userns','--assert-userns-disabled','--seccomp','--size')),'BWRAP_REQUIRED_FEATURES')
    policy=root/'seccomp.bpf';filter_hash=seccomp_filter(policy)
    import socket
    listener=socket.socket(socket.AF_INET,socket.SOCK_STREAM);listener.bind(('127.0.0.1',0));listener.listen(1)
    try:
        canary=root/'host-canary';canary.write_bytes(os.urandom(32))
        probe=root/'probe.py'
        text=PROBE.replace('CANARY_PATH',repr(str(canary))).replace('RUNTIME_PATH',repr(str(runtime/'python'))).replace('HOST_PORT',str(listener.getsockname()[1]))
        probe.write_text(text)
        (root/'passwd').write_text('root:x:0:0:private-worker:/scratch:/usr/sbin/nologin\n')
        (root/'group').write_text('root:x:0:\n')
        # This launcher runs INSIDE the admitted resource scope before exec.
        # It opens only the verified filter FD, then passes it to bubblewrap.
        launcher=root/'launch.py'
        argv=sandbox_argv(binary,runtime,probe,3)
        launch='''import json, os, pathlib
root=pathlib.Path(ROOT)
group=next(line.split(':',2)[2] for line in pathlib.Path('/proc/self/cgroup').read_text().splitlines() if line.startswith('0::'))
assert '..' not in group.split('/')
base=pathlib.Path('/sys/fs/cgroup')/group.lstrip('/')
values={name:(base/name).read_text().strip() for name in ('memory.max','memory.swap.max','pids.max','cpu.max')}
assert values['memory.max']=='4294967296' and values['memory.swap.max']=='0' and values['pids.max']=='64'
quota,period=map(int,values['cpu.max'].split());assert quota>0 and quota==period
fd=os.open(root/'seccomp.bpf',os.O_RDONLY)
if fd!=3:os.dup2(fd,3);os.close(fd)
os.set_inheritable(3,True)
argv=ARGV
os.execve(argv[0],argv,{'PATH':'/usr/bin:/bin','LANG':'C.UTF-8'})
'''.replace('ROOT',repr(str(root))).replace('ARGV',repr(argv))
        launcher.write_text(launch)
        env={**PARENT_ENV,'XDG_RUNTIME_DIR':'/run/user/1000','DBUS_SESSION_BUS_ADDRESS':'unix:path=/run/user/1000/bus'}
        output=command(['/usr/bin/systemd-run','--user','--scope','--quiet','--unit=f139-private-sandbox-'+root.name,
            '--property=MemoryMax='+MEMORY,'--property=MemorySwapMax=0','--property=CPUQuota=100%',
            '--property=TasksMax=64','/usr/bin/python3','-I','-B',launcher],timeout=90,env=env)
        result=json.loads(output)
        need(result.get('sandbox_control_probe_pass') is True and result.get('checks') and all(x is True for x in result['checks'].values()),'SANDBOX_CONTROL_PROBE_NOT_PASSED')
    finally:listener.close()
    need(verify_receipt(runtime)==receipt,'RUNTIME_CHANGED_DURING_SANDBOX_PROBE')
    libraries={}
    for name in ('libc.so.6','libseccomp.so.2','libcap.so.2','ld-linux-x86-64.so.2'):
        path=Path('/usr/lib/x86_64-linux-gnu')/name
        need(path.is_file(),'SYSTEM_LIBRARY_CUSTODY')
        libraries[name]=hash_file(path)
    libraries['systemd-run']=hash_file('/usr/bin/systemd-run')
    report=dict(schema='forge.f139.private-linux-cpu-sandbox-probe.v1',source_sha=source_sha,
        kernel_release=platform.release(),libc_identity=list(platform.libc_ver()),system_libraries_sha256=libraries,
        runtime_source_sha=RUNTIME_SOURCE,runtime_tree_sha256=receipt['runtime_tree_sha256'],
        wheel_lock_sha256=receipt['wheel_lock_sha256'],bubblewrap_package=pin,
        bubblewrap_binary_sha256=hash_file(binary),seccomp_filter_sha256=filter_hash,
        recipe_sha256=digest(canonical(argv)),checks=result['checks'],
        sandbox_control_probe_pass=True,complete_tree_memory_max=int(MEMORY),cpu_count=1,pids_max=64,
        private_project_code_executed=False,model_training=False,gpu_used=False,
        original_owner_mutations=0,signed_worker_qualified=False,scientific_first_use=False)
    (root/'sandbox-probe-receipt.json').write_bytes(canonical(report))
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--runtime',type=Path,required=True);p.add_argument('--root',type=Path,required=True)
    p.add_argument('--source-sha',required=True);a=p.parse_args()
    print('F139_PRIVATE_CPU_SANDBOX='+canonical(qualify(a.runtime,a.root,a.source_sha)).decode('ascii'))

if __name__=='__main__':main()

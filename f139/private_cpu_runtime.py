"""Private CPU runtime custody only; never candidate execution or owner authority.

Installs into a new dedicated directory, without altering system Python, users,
services, GPU, original owner or research checkout. Open-source dependencies
are downloaded once, hashed into an offline lock BEFORE installation, then the
complete runtime is sealed. This is NOT an isolated/signed worker receipt.
"""
from __future__ import annotations
import argparse
import email.parser
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import posixpath
import re
import shutil
import stat
import subprocess
import sys
import tarfile
import urllib.parse
import urllib.request
import zipfile

PYTHON_VERSION = '3.11.11'
TORCH_VERSION = '2.5.1+cpu'
PYTEST_VERSION = '8.3.4'
ARTIFACT = 'cpython-3.11.11%2B20241219-x86_64-unknown-linux-gnu-install_only.tar.gz'
ARTIFACT_URL = 'https://github.com/astral-sh/python-build-standalone/releases/download/20241219/'+ARTIFACT
SCHEMA = 'forge.f139.private-cpu-runtime-custody.v1'
MAX_ARCHIVE = 64*1024*1024
MAX_WHEELS = 512*1024*1024
MAX_EXPANDED = 2*1024*1024*1024

class RuntimeDenied(ValueError):
    pass

def need(value, reason):
    if not value: raise RuntimeDenied('F139_PRIVATE_CPU_RUNTIME_'+reason)

def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode('ascii')

def digest(data): return hashlib.sha256(data).hexdigest()

def hash_file(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()

def safe_relative(name):
    need(type(name) is str and name and '\\' not in name and '\x00' not in name and ':' not in name,
         'UNSAFE_ARTIFACT_PATH')
    p=PurePosixPath(name)
    need(not p.is_absolute() and all(x not in ('','.','..') for x in name.split('/')),
         'UNSAFE_ARTIFACT_PATH')
    return p

def archive_plan(members):
    """Validate every tar path/link before extraction; links are created last."""
    rows=[];seen=set();expanded=0
    need(0<len(members)<=100000,'ARCHIVE_MEMBER_BUDGET')
    for member in members:
        path=safe_relative(member.name.rstrip('/'))
        need(path.parts[0]=='python' and str(path) not in seen,'ARCHIVE_SCOPE_OR_DUPLICATE')
        seen.add(str(path))
        need(not member.mode & 0o6000,'PRIVILEGED_ARCHIVE_MODE')
        need(member.isdir() or member.isfile() or member.issym() or member.islnk(), 'ARCHIVE_SPECIAL_FILE')
        expanded+=member.size
        need(expanded<=MAX_EXPANDED,'EXPANDED_ARCHIVE_BUDGET')
        if member.issym() or member.islnk():
            target=member.linkname
            need(target and not target.startswith('/') and '\\' not in target,'UNSAFE_ARCHIVE_LINK')
            resolved=posixpath.normpath(posixpath.join(str(path.parent),target) if member.issym() else target)
            need(resolved=='python' or resolved.startswith('python/'),'UNSAFE_ARCHIVE_LINK')
            safe_relative(resolved)
        rows.append(member)
    need(rows and 'python/bin/python3.11' in seen,'PYTHON_EXECUTABLE_MISSING')
    links={m.name.rstrip('/') for m in rows if m.issym() or m.islnk()}
    for m in rows:
        need(not any(str(p) in links for p in PurePosixPath(m.name.rstrip('/')).parents),
             'ARCHIVE_LINK_PARENT')
    return rows

def extract_python(archive, root):
    root=Path(root)
    need(root.is_dir() and not root.is_symlink() and not (root/'python').exists(), 'EXTRACTION_TARGET_COLLISION')
    with tarfile.open(archive,'r:gz') as source:
        rows=archive_plan(source.getmembers())
        for m in rows:
            if m.issym() or m.islnk():continue
            path=root/m.name.rstrip('/')
            path.parent.mkdir(parents=True,exist_ok=True)
            if m.isdir():path.mkdir(exist_ok=True)
            else:
                with source.extractfile(m) as incoming,path.open('xb') as output:
                    shutil.copyfileobj(incoming,output,1024*1024)
                path.chmod(m.mode & 0o755)
        for m in rows:
            if m.issym():
                destination=root/m.name
                destination.parent.mkdir(parents=True,exist_ok=True)
                destination.symlink_to(m.linkname)
        for m in rows:
            if m.islnk():
                target=root/posixpath.normpath(m.linkname)
                need(target.is_file() and not target.is_symlink(),'HARDLINK_TARGET_NOT_REGULAR')
                destination=root/m.name
                destination.parent.mkdir(parents=True,exist_ok=True)
                os.link(target,destination)

def freeze_wheels(folder):
    rows=[];names=set();total=0
    paths=sorted(Path(folder).iterdir())
    need(0<len(paths)<=64,'WHEEL_COUNT_BUDGET')
    for path in paths:
        need(path.is_file() and not path.is_symlink() and path.suffix=='.whl','WHEELHOUSE_UNEXPECTED_FILE')
        safe_relative(path.name)
        total+=path.stat().st_size
        need(total<=MAX_WHEELS,'WHEEL_DOWNLOAD_BUDGET')
        with zipfile.ZipFile(path) as wheel:
            expanded=0;metadata=[]
            need(len(wheel.infolist())<=100000,'WHEEL_MEMBER_BUDGET')
            for item in wheel.infolist():
                safe_relative(item.filename.rstrip('/'))
                need(not stat.S_ISLNK(item.external_attr>>16),'WHEEL_SYMLINK')
                expanded+=item.file_size
                need(expanded<=MAX_EXPANDED,'WHEEL_EXPANSION_BUDGET')
                if item.filename.endswith('.dist-info/METADATA'):metadata.append(item)
            need(len(metadata)==1 and metadata[0].file_size<=2_000_000,'WHEEL_METADATA_AMBIGUOUS')
            doc=email.parser.BytesParser().parsebytes(wheel.read(metadata[0]))
        name=re.sub('[-_.]+','-',doc.get('Name','')).lower();version=doc.get('Version','')
        need(re.fullmatch('[a-z0-9]+(?:-[a-z0-9]+)*',name) and name not in names,
             'WHEEL_NAME_OR_DUPLICATE')
        need(re.fullmatch('[A-Za-z0-9.+!_-]{1,100}',version) and not name.startswith('nvidia-'),
             'WHEEL_VERSION_OR_GPU_DEPENDENCY')
        names.add(name)
        rows.append(dict(name=name,version=version,filename=path.name,sha256=hash_file(path)))
    versions={r['name']:r['version'] for r in rows}
    need(versions.get('torch')==TORCH_VERSION and versions.get('pytest')==PYTEST_VERSION,
         'PINNED_CPU_DEPENDENCIES_MISSING')
    return sorted(rows,key=lambda r:r['name'])

def lock_text(rows):
    return ''.join(r['name']+'=='+r['version']+' --hash=sha256:'+r['sha256']+'\n' for r in rows)

def tree_manifest(root):
    root=Path(root).resolve();result={}
    need(root.is_dir(),'RUNTIME_TREE_MISSING')
    for p in sorted(root.rglob('*')):
        relative=p.relative_to(root).as_posix();safe_relative(relative)
        if p.is_symlink():
            need(p.resolve().is_relative_to(root) and p.exists(),'RUNTIME_SYMLINK_ESCAPE')
            result[relative]={'symlink':os.readlink(p)}
        elif p.is_file():result[relative]={'sha256':hash_file(p),'mode':stat.S_IMODE(p.stat().st_mode)}
        else:need(p.is_dir(),'RUNTIME_SPECIAL_FILE')
    need(result,'EMPTY_RUNTIME_TREE')
    return result

def verify_receipt(root):
    root=Path(root)
    receipt=json.loads((root/'runtime-receipt.json').read_bytes())
    need(type(receipt) is dict and set(receipt)=={'schema','source_sha','python_version','python_archive_sha256',
         'python_archive_url','wheels','wheel_lock_sha256','runtime_tree_sha256','runtime_provisioned',
         'worker_execution_authorized','signed_worker_qualified','scientific_first_use'},'RECEIPT_FIELDS')
    need(receipt['schema']==SCHEMA and receipt['python_version']==PYTHON_VERSION
         and re.fullmatch('[a-f0-9]{40}',receipt['source_sha'])
         and receipt['python_archive_url']==ARTIFACT_URL
         and re.fullmatch('[a-f0-9]{64}',receipt['python_archive_sha256'])
         and receipt['runtime_provisioned'] is True
         and all(receipt[k] is False for k in ('worker_execution_authorized','signed_worker_qualified','scientific_first_use')),
         'RECEIPT_IDENTITY_OR_AUTHORITY')
    need(hash_file(root/'python.tar.gz')==receipt['python_archive_sha256']
         and (root/'upstream.sha256').read_text().strip()==receipt['python_archive_sha256'],
         'PYTHON_ARTIFACT_CUSTODY_DRIFT')
    need(json.loads((root/'input-lock.json').read_bytes())==dict(source_sha=receipt['source_sha'],
         python_version=PYTHON_VERSION,python_archive_url=ARTIFACT_URL,
         python_archive_sha256=receipt['python_archive_sha256'],torch=TORCH_VERSION,pytest=PYTEST_VERSION),
         'FROZEN_INPUT_LOCK_DRIFT')
    need(freeze_wheels(root/'wheelhouse')==receipt['wheels'],'WHEEL_CUSTODY_DRIFT')
    need((root/'requirements.lock').read_text()==lock_text(receipt['wheels'])
         and hash_file(root/'requirements.lock')==receipt['wheel_lock_sha256'],'WHEEL_LOCK_DRIFT')
    need(digest(canonical(tree_manifest(root/'python')))==receipt['runtime_tree_sha256'], 'RUNTIME_TREE_DRIFT')
    return receipt

def download(url,path,limit):
    need(url.startswith('https://github.com/astral-sh/python-build-standalone/releases/download/20241219/'),
         'ARTIFACT_ORIGIN_DENIED')
    with urllib.request.urlopen(url,timeout=60) as response,Path(path).open('xb') as output:
        need(urllib.parse.urlsplit(response.url).scheme=='https' and
             urllib.parse.urlsplit(response.url).hostname in {'github.com','release-assets.githubusercontent.com','objects.githubusercontent.com'},
             'ARTIFACT_REDIRECT_ORIGIN_DENIED')
        total=0
        while True:
            chunk=response.read(1024*1024)
            if not chunk:break
            total+=len(chunk);need(total<=limit,'ARTIFACT_DOWNLOAD_BUDGET');output.write(chunk)

def run(args, *, cwd, timeout=600):
    # Trusted provisioning only. No inherited project/API/HMAC variables.
    allowed={'PATH','LANG','LC_ALL','SYSTEMROOT','WINDIR','TEMP','TMP','TMPDIR'}
    env={k:v for k,v in os.environ.items() if k.upper() in allowed}
    env.update(PYTHONDONTWRITEBYTECODE='1',PIP_CONFIG_FILE=os.devnull,
               PIP_DISABLE_PIP_VERSION_CHECK='1',NETRC=os.devnull,OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1')
    p=subprocess.run([str(a) for a in args],cwd=cwd,env=env,stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=False,timeout=timeout)
    need(p.returncode==0,'TRUSTED_PROVISION_COMMAND_FAILED')
    return p.stdout.decode('utf-8','strict').strip()

def provision(root,source_sha):
    need(sys.platform=='linux' and os.getuid()!=0,'UNPRIVILEGED_LINUX_REQUIRED')
    need(re.fullmatch('[a-f0-9]{40}',source_sha),'QUALIFIED_SOURCE_REQUIRED')
    root=Path(root)
    need(root.is_absolute() and not root.exists() and not root.is_symlink(),'NEW_RUNTIME_ROOT_REQUIRED')
    need(shutil.disk_usage(root.parent).free>=8*1024**3,'DISK_HEADROOM_REQUIRED')
    memory=dict(line.split(':',1) for line in Path('/proc/meminfo').read_text().splitlines())
    need(int(memory['MemAvailable'].split()[0])>=6*1024**2,'MEMORY_HEADROOM_REQUIRED')
    root.mkdir(mode=0o700)
    os.nice(19)
    if hasattr(os,'sched_setaffinity'):
        os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
    download(ARTIFACT_URL+'.sha256',root/'upstream.sha256',200)
    expected=(root/'upstream.sha256').read_text().strip()
    need(re.fullmatch('[a-f0-9]{64}',expected),'UPSTREAM_HASH_INVALID')
    (root/'input-lock.json').write_bytes(canonical(dict(source_sha=source_sha,python_version=PYTHON_VERSION,
        python_archive_url=ARTIFACT_URL,python_archive_sha256=expected,
        torch=TORCH_VERSION,pytest=PYTEST_VERSION)))
    download(ARTIFACT_URL,root/'python.tar.gz',MAX_ARCHIVE)
    need(hash_file(root/'python.tar.gz')==expected,'PYTHON_ARCHIVE_HASH_DRIFT')
    extract_python(root/'python.tar.gz',root)
    python=root/'python/bin/python3.11'
    need(run([python,'-I','-B','-c','import platform;print(platform.python_version())'],cwd=root)==PYTHON_VERSION,
         'OBSERVED_PYTHON_VERSION_DRIFT')
    wheels=root/'wheelhouse';wheels.mkdir()
    run([python,'-I','-B','-m','pip','--isolated','--disable-pip-version-check','--keyring-provider','disabled','download','--quiet','--no-cache-dir','--only-binary=:all:',
         '--dest',wheels,'--index-url','https://download.pytorch.org/whl/cpu',
         '--extra-index-url','https://pypi.org/simple','torch=='+TORCH_VERSION,'pytest=='+PYTEST_VERSION],cwd=root)
    rows=freeze_wheels(wheels)
    (root/'requirements.lock').write_text(lock_text(rows))
    run([python,'-I','-B','-m','pip','--isolated','--disable-pip-version-check','--keyring-provider','disabled','install','--quiet','--no-cache-dir','--no-compile','--no-deps','--no-index',
         '--find-links',wheels,'--require-hashes','-r',root/'requirements.lock'],cwd=root)
    run([python,'-I','-B','-m','pip','--isolated','--disable-pip-version-check','check'],cwd=root)
    observed=json.loads(run([python,'-I','-B','-c',
        'import importlib.metadata as m,json;print(json.dumps({k:m.version(k) for k in ("torch","pytest")}))'],cwd=root))
    need(observed=={'torch':TORCH_VERSION,'pytest':PYTEST_VERSION},'OBSERVED_PACKAGE_VERSION_DRIFT')
    receipt=dict(schema=SCHEMA,source_sha=source_sha,python_version=PYTHON_VERSION,
        python_archive_sha256=expected,python_archive_url=ARTIFACT_URL,wheels=rows,
        wheel_lock_sha256=hash_file(root/'requirements.lock'),
        runtime_tree_sha256=digest(canonical(tree_manifest(root/'python'))),runtime_provisioned=True,
        worker_execution_authorized=False,signed_worker_qualified=False,scientific_first_use=False)
    (root/'runtime-receipt.json').write_bytes(canonical(receipt))
    return verify_receipt(root)

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,required=True)
    p.add_argument('--source-sha',required=True);p.add_argument('--verify-only',action='store_true');a=p.parse_args()
    result=verify_receipt(a.root) if a.verify_only else provision(a.root,a.source_sha)
    need(result['source_sha']==a.source_sha,'RECEIPT_SOURCE_DRIFT')
    print('F139_PRIVATE_CPU_RUNTIME='+canonical(result).decode('ascii'))

if __name__=='__main__':main()

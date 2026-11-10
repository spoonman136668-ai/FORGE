"""Runtime artifact custody; fixtures never authorize an execution worker."""
import copy
import io
import json
import os
from pathlib import Path
import stat
import tarfile
import tempfile
import unittest
from unittest.mock import patch
import zipfile
from f139 import private_cpu_runtime as r


def wheel(folder,name,version,*,extra=None):
    path=folder/(name+'-'+version+'-py3-none-any.whl')
    with zipfile.ZipFile(path,'w') as out:
        out.writestr(name+'-'+version+'.dist-info/METADATA',
                     'Metadata-Version: 2.1\nName: '+name+'\nVersion: '+version+'\n')
        if extra is not None:out.writestr(extra,b'payload')
    return path


def member(name,kind=tarfile.REGTYPE,link='',size=0,mode=0o644):
    t=tarfile.TarInfo(name);t.type=kind;t.linkname=link;t.size=size;t.mode=mode
    return t


class RuntimeArtifacts(unittest.TestCase):
    def test_tar_validation_precedes_all_extraction_and_rejects_escape_and_specials(self):
        good=member('python/bin/python3.11')
        self.assertEqual(r.archive_plan([good]),[good])
        for bad in (member('../escape'),member('/absolute'),member('C:/drive'),
                    member('python/../escape'),member('python/bad\\path'),
                    member('elsewhere/file'),member('python/device',tarfile.CHRTYPE),
                    member('python/bin/tool',mode=0o4755),
                    member('python/link',tarfile.SYMTYPE,'../../outside'),
                    member('python/link',tarfile.SYMTYPE,'/outside'),
                    member('python/link',tarfile.LNKTYPE,'outside'),
                    member('python/giant',size=r.MAX_EXPANDED+1)):
            with self.subTest(name=bad.name),self.assertRaises(r.RuntimeDenied):r.archive_plan([good,bad])
        with self.assertRaises(r.RuntimeDenied):r.archive_plan([good,good])
        with self.assertRaises(r.RuntimeDenied):
            r.archive_plan([good,member('python/link',tarfile.SYMTYPE,'bin'),member('python/link/injected')])

    def test_tar_safe_internal_link_and_real_regular_extraction(self):
        rows=[member('python/bin/python3.11'),member('python/bin/python3',tarfile.SYMTYPE,'python3.11')]
        self.assertEqual(len(r.archive_plan(rows)),2)
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);archive=root/'python.tgz'
            with tarfile.open(archive,'w:gz') as out:
                t=member('python/bin/python3.11',size=3,mode=0o755);out.addfile(t,io.BytesIO(b'bin'))
            r.extract_python(archive,root)
            self.assertEqual((root/'python/bin/python3.11').read_bytes(),b'bin')
            with self.assertRaises(r.RuntimeDenied):r.extract_python(archive,root)

    def test_tar_bad_link_cannot_leave_a_partially_extracted_python(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);archive=root/'python.tgz'
            with tarfile.open(archive,'w:gz') as out:
                t=member('python/bin/python3.11',size=3);out.addfile(t,io.BytesIO(b'bin'))
                out.addfile(member('python/escape',tarfile.SYMTYPE,'/outside'))
            with self.assertRaises(r.RuntimeDenied):r.extract_python(archive,root)
            self.assertFalse((root/'python').exists())

    def test_freeze_all_wheel_hashes_before_offline_install(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);wheel(root,'torch',r.TORCH_VERSION);wheel(root,'pytest',r.PYTEST_VERSION)
            rows=r.freeze_wheels(root)
            self.assertEqual([x['name'] for x in rows],['pytest','torch'])
            self.assertTrue(all(len(x['sha256'])==64 for x in rows))
            self.assertEqual(r.lock_text(rows).count('--hash=sha256:'),2)
            wheel(root,'filelock','3.16.1')
            self.assertEqual(len(r.freeze_wheels(root)),3)

    def test_missing_pin_gpu_dependency_unexpected_file_and_wheel_path_denied(self):
        for mode in ('missing','gpu','unexpected','traversal','drive','duplicate','badversion'):
            with self.subTest(mode=mode),tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp);wheel(root,'torch',r.TORCH_VERSION)
                if mode!='missing':wheel(root,'pytest',r.PYTEST_VERSION)
                if mode=='gpu':wheel(root,'nvidia-cuda-runtime-cu12','12.4')
                if mode=='unexpected':(root/'untracked.txt').write_text('unqualified')
                if mode=='traversal':wheel(root,'extra','1',extra='../escape')
                if mode=='drive':wheel(root,'extra','1',extra='C:/escape')
                if mode=='duplicate':wheel(root,'pytest','9')
                if mode=='badversion':wheel(root,'extra','1 --index-url other')
                with self.assertRaises(r.RuntimeDenied):r.freeze_wheels(root)

    def bundle(self,root):
        (root/'python/bin').mkdir(parents=True);(root/'python/bin/python3.11').write_bytes(b'fixture binary')
        (root/'wheelhouse').mkdir();wheel(root/'wheelhouse','torch',r.TORCH_VERSION);wheel(root/'wheelhouse','pytest',r.PYTEST_VERSION)
        (root/'python.tar.gz').write_bytes(b'fixture upstream bytes')
        sha=r.hash_file(root/'python.tar.gz');(root/'upstream.sha256').write_text(sha+'\n')
        rows=r.freeze_wheels(root/'wheelhouse');(root/'requirements.lock').write_text(r.lock_text(rows))
        doc=dict(schema=r.SCHEMA,source_sha='a'*40,python_version=r.PYTHON_VERSION,
            python_archive_sha256=sha,python_archive_url=r.ARTIFACT_URL,wheels=rows,
            wheel_lock_sha256=r.hash_file(root/'requirements.lock'),
            runtime_tree_sha256=r.digest(r.canonical(r.tree_manifest(root/'python'))),
            runtime_provisioned=True,worker_execution_authorized=False,
            signed_worker_qualified=False,scientific_first_use=False)
        (root/'input-lock.json').write_bytes(r.canonical(dict(source_sha='a'*40,python_version=r.PYTHON_VERSION,
            python_archive_url=r.ARTIFACT_URL,python_archive_sha256=sha,torch=r.TORCH_VERSION,pytest=r.PYTEST_VERSION)))
        (root/'runtime-receipt.json').write_bytes(r.canonical(doc));return doc

    def test_cold_custody_receipt_has_no_execution_or_scientific_authority(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);doc=self.bundle(root);self.assertEqual(r.verify_receipt(root),doc)
            for key in ('worker_execution_authorized','signed_worker_qualified','scientific_first_use'):
                bad={**doc,key:True};(root/'runtime-receipt.json').write_bytes(r.canonical(bad))
                with self.subTest(key=key),self.assertRaises(r.RuntimeDenied):r.verify_receipt(root)
            (root/'runtime-receipt.json').write_bytes(r.canonical({**doc,'extra':False}))
            with self.assertRaises(r.RuntimeDenied):r.verify_receipt(root)

    def test_cold_receipt_rejects_each_artifact_runtime_and_lock_drift(self):
        for path in ('python/bin/python3.11','python.tar.gz','upstream.sha256','requirements.lock','input-lock.json'):
            with self.subTest(path=path),tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp);self.bundle(root);(root/path).write_bytes(b'changed')
                with self.assertRaises((r.RuntimeDenied,ValueError)):r.verify_receipt(root)
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);self.bundle(root);wheel(root/'wheelhouse','unqualified','1')
            with self.assertRaises(r.RuntimeDenied):r.verify_receipt(root)

    def test_tree_seal_rejects_new_files_and_symlink_escape(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);self.bundle(root);(root/'python/new.py').write_text('changed')
            with self.assertRaises(r.RuntimeDenied):r.verify_receipt(root)
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'inside').mkdir();(root/'outside').write_text('private')
            try:(root/'inside/link').symlink_to(root/'outside')
            except OSError:self.skipTest('Native symlink permission unavailable')
            with self.assertRaises(r.RuntimeDenied):r.tree_manifest(root/'inside')

    def test_download_refuses_arbitrary_network_and_mutation_origins(self):
        for url in ('http://github.com/anything','https://foreign.invalid/payload','file:///secret'):
            with patch.object(r.urllib.request,'urlopen') as network,self.assertRaises(r.RuntimeDenied):
                r.download(url,'unused',1)
            network.assert_not_called()

    def test_provision_subprocess_receives_no_api_or_hmac_environment(self):
        with tempfile.TemporaryDirectory() as tmp,patch.dict(os.environ,
                {'GH_TOKEN':'not-real-credential','F139_WORKER_HMAC_KEY':'not-real-owner-key','OPENAI_API_KEY':'not-real-key'}):
            result=type('Result',(),dict(returncode=0,stdout=b'ok',stderr=b''))()
            with patch.object(r.subprocess,'run',return_value=result) as process:
                self.assertEqual(r.run(['python','--version'],cwd=tmp),'ok')
                env=process.call_args.kwargs['env']
                self.assertFalse(any(k in env for k in ('GH_TOKEN','GITHUB_TOKEN','F139_WORKER_HMAC_KEY','OPENAI_API_KEY')))
                self.assertEqual(env['NETRC'],os.devnull)
                self.assertIs(process.call_args.kwargs['stdin'],r.subprocess.DEVNULL)
                self.assertFalse(process.call_args.kwargs.get('shell',False))

    def test_system_python_and_existing_directories_are_never_modified(self):
        with patch.object(r.sys,'platform','win32'),patch.object(r,'download') as download:
            with self.assertRaises(r.RuntimeDenied):r.provision(Path('/unqualified'),'a'*40)
            download.assert_not_called()
        if r.sys.platform=='linux':
            with tempfile.TemporaryDirectory() as tmp,patch.object(r.os,'getuid',return_value=1000),patch.object(r,'download') as download:
                with self.assertRaises(r.RuntimeDenied):r.provision(Path(tmp),'a'*40)
                download.assert_not_called()

if __name__=='__main__':unittest.main()

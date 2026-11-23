"""No candidate is executed by these policy/custody negative controls."""
import json
import os
from pathlib import Path
import platform
import tempfile
import unittest
from unittest.mock import patch
from f139 import private_cpu_sandbox as s
from f139.private_cpu_runtime import RuntimeDenied


class PrivateSandboxControls(unittest.TestCase):
    def pin(self,**edits):
        fields=dict(Package='bubblewrap',Version='0.9.0-1ubuntu0.1',Architecture='amd64',
            Filename='pool/main/b/bubblewrap/bubblewrap_0.9.0-1ubuntu0.1_amd64.deb',
            Size='100000',SHA256='a'*64)
        fields.update(edits)
        return '\n'.join(k+': '+v for k,v in fields.items())

    def test_exact_existing_ubuntu_package_pin_only(self):
        pin=s.package_pin(self.pin())
        self.assertEqual(pin['size'],100000);self.assertEqual(pin['sha256'],'a'*64)
        for changes in (dict(Package='foreign'),dict(Architecture='arm64'),dict(Filename='../elsewhere'),
                        dict(Filename='https://foreign/file.deb'),dict(SHA256='bad'),dict(Size='99999999'),
                        dict(Size='-1'),dict(Size='0')):
            with self.subTest(changes=changes),self.assertRaises(RuntimeDenied):s.package_pin(self.pin(**changes))

    def setup_policy(self,root):
        runtime=root/'runtime';(runtime/'python/bin').mkdir(parents=True)
        (runtime/'python/bin/python3.11').write_bytes(b'fixture only')
        probe=root/'probe.py';probe.write_text('pass')
        for name in ('passwd','group'):(root/name).write_text('fixture identity')
        # Windows temporary paths can use 8.3 aliases; the recipe deliberately
        # canonicalizes inputs before constructing its mount/command inventory.
        return runtime.resolve(),probe.resolve()

    def test_recipe_has_no_host_home_windows_gpu_secret_or_writable_runtime_bind(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);runtime,probe=self.setup_policy(root)
            args=s.sandbox_argv('/qualified/bwrap',runtime,probe,3)
            for flag in ('--unshare-all','--unshare-user','--disable-userns','--assert-userns-disabled',
                         '--new-session','--die-with-parent','--clearenv','--seccomp'):
                self.assertIn(flag,args)
            self.assertEqual(args[args.index('--cap-drop')+1],'ALL')
            self.assertNotIn('--bind',args);self.assertNotIn('--dev-bind',args)
            self.assertNotIn('--share-net',args);self.assertNotIn('--not-a-security-boundary',args)
            self.assertNotIn('--unshare-user-try',args)
            for forbidden in ('/mnt/c','/home','/root','/run/user/1000/bus','/dev/dxg','GH_TOKEN','GITHUB_TOKEN','F139_WORKER_HMAC_KEY'):
                self.assertNotIn(forbidden,args)
            self.assertEqual(args[-4:],[str(runtime/'python/bin/python3.11'),'-I','-B','/probe.py'])
            self.assertIn(str(runtime/'python'),args)
            self.assertEqual(args.count('--tmpfs'),2)

    def test_recipe_requires_valid_inputs_and_identity_maps(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);runtime,probe=self.setup_policy(root)
            for fd in (-1,0,2,True):
                with self.subTest(fd=fd),self.assertRaises(RuntimeDenied):s.sandbox_argv('/bwrap',runtime,probe,fd)
            (root/'passwd').unlink()
            with self.assertRaises(RuntimeDenied):s.sandbox_argv('/bwrap',runtime,probe,3)

    def test_sysroot_external_symlink_is_never_silently_shared(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);runtime,probe=self.setup_policy(root)
            with patch.object(s.os,'readlink',return_value='../../host-private'):
                if any(Path(x).is_symlink() for x in ('/bin','/sbin','/lib','/lib64')):
                    with self.assertRaises(RuntimeDenied):s.sandbox_argv('/bwrap',runtime,probe,3)

    @unittest.skipUnless(platform.system()=='Linux' and platform.machine()=='x86_64','Linux filter export only')
    def test_real_libseccomp_filter_exports_without_loading_or_executing_it(self):
        if not s.ctypes.util.find_library('seccomp'):self.skipTest('Native libseccomp unavailable')
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'policy.bpf'
            sha=s.seccomp_filter(path)
            self.assertEqual(len(sha),64)
            self.assertGreater(path.stat().st_size,0)
            self.assertLessEqual(path.stat().st_size,32768)
            with self.assertRaises(FileExistsError):s.seccomp_filter(path)

    def test_unsupported_filter_platform_rejected_before_loading_library(self):
        with patch.object(s.platform,'system',return_value='Windows'),patch.object(s.ctypes,'CDLL') as load:
            with self.assertRaises(RuntimeDenied):s.seccomp_filter('unused')
            load.assert_not_called()

    def test_native_qualification_cannot_elevate_or_skip_custody(self):
        with patch.object(s.platform,'system',return_value='Windows'),patch.object(s,'verify_receipt') as verify:
            with self.assertRaises(RuntimeDenied):s.qualify(Path('/runtime'),Path('/sandbox'),'a'*40)
            verify.assert_not_called()
        if platform.system()=='Linux':
            with patch.object(s.os,'getuid',return_value=0),patch.object(s,'verify_receipt') as verify:
                with self.assertRaises(RuntimeDenied):s.qualify(Path('/runtime'),Path('/sandbox'),'a'*40)
                verify.assert_not_called()

    def test_static_probe_is_valid_and_checks_real_boundary_conditions(self):
        import ast
        script=s.PROBE.replace('CANARY_PATH',repr('/unmounted-canary')).replace('RUNTIME_PATH',repr('/runtime')).replace('HOST_PORT','9')
        ast.parse(script)
        for required in ('CapEff','NoNewPrivs','/dev/dxg','socket.socket(40','/proc','unshare','torch.version.cuda'):
            self.assertIn(required,script)
        self.assertNotIn('requests',script)
        self.assertNotIn('torch.cuda.is_available',script)

if __name__=='__main__':unittest.main()

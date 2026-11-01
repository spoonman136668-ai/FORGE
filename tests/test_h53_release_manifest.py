import unittest
import hashlib
import pathlib
import tempfile
import shutil
import subprocess
import sys
from f139 import h53_release_manifest as m

class ManifestTests(unittest.TestCase):
    def test_staged_template_and_runtime_tampering(self):
        source = pathlib.Path(__file__).resolve().parents[1]
        self.assertFalse(m.verify_template(source)["release_authorized"])
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            names = m.REQUIRED - {m.WORKFLOW}
            template = ".github/audit-templates/f139-h53-one-shot-workflow.inactive.yml"
            for name in sorted(names | {template}):
                target = root / name
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source / name, target)
            m.verify_template(root)
            text = (root / template).read_text(encoding="utf-8")
            block = text.split("        shell: python\n        run: |\n", 1)[1].split("      - name:", 1)[0]
            code = "\n".join(line[10:] for line in block.splitlines())
            executable = root / m.WORKFLOW
            executable.parent.mkdir(parents=True, exist_ok=True)
            executable.write_text(text, encoding="utf-8")
            result = subprocess.run([sys.executable, "-c", code], cwd=root, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            executable.unlink()
            for name in sorted(names):
                path = root / name
                original = path.read_bytes()
                path.write_bytes(original + b"# tampered\n")
                with self.assertRaisesRegex(RuntimeError, "TEMPLATE_RUNTIME_DRIFT"):
                    m.verify_template(root)
                executable.write_text(text, encoding="utf-8")
                result = subprocess.run([sys.executable, "-c", code], cwd=root, capture_output=True, text=True)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("F139_H53_RUNTIME_CONTENT_DRIFT", result.stderr)
                executable.unlink()
                path.write_bytes(original)
            path = root / m.WORKFLOW
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("unexpected executable workflow")
            with self.assertRaisesRegex(RuntimeError, "TEMPLATE_ALREADY_ACTIVE"):
                m.verify_template(root)

    def test_exact_release_allowlist_and_pins(self):
        changed=sorted(m.REQUIRED)
        hashes={k:"a"*64 for k in changed}
        kwargs=dict(parent=m.g.SOURCE,source_hashes=hashes,expected_hashes=hashes)
        self.assertFalse(m.verify_release_manifest(changed,**kwargs)["release_authorized"])
        for bad in [changed[:-1],changed+[".github/workflows/other.yml"],changed+[changed[0]]]:
            with self.assertRaisesRegex(RuntimeError,"RELEASE_MANIFEST"):
                m.verify_release_manifest(bad,**kwargs)
        with self.assertRaisesRegex(RuntimeError,"RELEASE_PARENT"):
            m.verify_release_manifest(changed,**{**kwargs,"parent":"bad"})
        with self.assertRaisesRegex(RuntimeError,"RELEASE_CONTENT_DRIFT"):
            m.verify_release_manifest(changed,**{**kwargs,"source_hashes":{**hashes,changed[0]:"b"*64}})
    def test_actual_bytes_must_match_pins(self):
        changed=sorted(m.REQUIRED)
        files={k:(k+"\\n").encode() for k in changed}
        pins={k:hashlib.sha256(v).hexdigest() for k,v in files.items()}
        m.verify_release_bytes(changed,parent=m.g.SOURCE,files=files,expected_hashes=pins)
        altered={**files,changed[0]:b"tampered"}
        with self.assertRaisesRegex(RuntimeError,"RELEASE_CONTENT_DRIFT"):
            m.verify_release_bytes(changed,parent=m.g.SOURCE,files=altered,expected_hashes=pins)
if __name__=="__main__":
    unittest.main()

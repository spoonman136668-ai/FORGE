"""Adversarial controls for the one four-file FORGE engineering recipe."""
import base64
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

from f139 import self_qualification_candidate as candidate
from f139.check_test_discovery_inventory import (
    collect, compare_physical_coverage, fixture_normalized_ast,
)


class CandidateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Read immutable Git objects, so the controls also run in the generated
        # proposal checkout whose working-tree fixture imports intentionally differ.
        cls.files={p:subprocess.check_output(['git','show','HEAD:'+p]) for p in candidate.RULES}

    def proposal(self):
        return candidate.propose(self.files,source_sha='a'*40,source_tree='b'*40)

    def test_native_generator_is_deterministic_and_only_preserves_test_semantics(self):
        first=self.proposal()
        self.assertEqual(first,self.proposal())
        after=candidate.inspect_proposal(first,self.files,source_sha='a'*40,source_tree='b'*40)
        self.assertEqual(set(after),set(candidate.RULES))
        for path,raw in after.items():
            self.assertNotEqual(raw,self.files[path])
            self.assertEqual(fixture_normalized_ast(raw.decode()),
                             fixture_normalized_ast(self.files[path].decode()))
        doc=json.loads(first)
        self.assertFalse(doc['live_owner_authorized'])
        self.assertFalse(doc['dispatch_authorized'])
        self.assertFalse(doc['scientific_first_use'])

    def test_extra_missing_or_controller_path_is_denied(self):
        for files in ({k:v for k,v in self.files.items() if k!=next(iter(self.files))},
                      {**self.files,'f139/local_controller.py':b'unsafe'},
                      {'../outside.py':b'unsafe'}):
            with self.assertRaises(ValueError):
                candidate.propose(files,source_sha='a'*40,source_tree='b'*40)

    def test_before_identity_drift_even_comment_only_is_denied(self):
        files=dict(self.files)
        files[next(iter(files))]+=b'\n# unreviewed\n'
        with self.assertRaises(ValueError):
            candidate.propose(files,source_sha='a'*40,source_tree='b'*40)

    def test_self_consistent_patch_hash_cannot_authorize_an_extra_edit(self):
        doc=json.loads(self.proposal())
        row=doc['changes'][0]
        raw=base64.b64decode(row['after_base64'])+b'\n# extra caller patch\n'
        row['after_base64']=base64.b64encode(raw).decode()
        row['after_sha256']=hashlib.sha256(raw).hexdigest()
        with self.assertRaises(ValueError):
            candidate.inspect_proposal(candidate.canonical(doc),self.files,
                                       source_sha='a'*40,source_tree='b'*40)

    def test_claimed_authority_foreign_repository_and_threshold_drift_are_denied(self):
        for key,value in [('live_owner_authorized',True),('dispatch_authorized',True),
                          ('scientific_first_use',True),('repository','foreign/repo'),
                          ('minimum_speedup',1.0),('optimizer_reward',True)]:
            doc=json.loads(self.proposal());doc[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):
                candidate.inspect_proposal(candidate.canonical(doc),self.files,
                                           source_sha='a'*40,source_tree='b'*40)

    def test_duplicate_key_and_independent_source_drift_are_denied(self):
        raw=self.proposal()
        with self.assertRaises(ValueError):
            candidate.inspect_proposal(b'{"schema":"forged",'+raw[1:],self.files,
                                       source_sha='a'*40,source_tree='b'*40)
        with self.assertRaises(ValueError):
            candidate.inspect_proposal(raw,self.files,source_sha='c'*40,source_tree='b'*40)

    def test_physical_coverage_denies_lost_tests_new_skips_or_false_repetition(self):
        before=dict(ids=['flat','package','other'],physical=['same','same','other'],skipped_physical=[])
        after=dict(ids=['flat','other'],physical=['same','other'],skipped_physical=[])
        compare_physical_coverage(before,after,1)
        for changed in (dict(ids=['flat'],physical=['same'],skipped_physical=[]),
                        {**after,'skipped_physical':['other']},
                        {**after,'physical':['same','same']}):
            with self.assertRaises(ValueError):
                compare_physical_coverage(before,changed,1)

    def test_real_discovery_distinguishes_namespace_repetition_from_unique_source(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);package=root/'f139';package.mkdir()
            (package/'__init__.py').write_text('',encoding='utf-8')
            (package/'test_source.py').write_text(
                'import unittest\nclass Case(unittest.TestCase):\n'
                ' def test_one(self): self.assertTrue(True)\n',encoding='utf-8')
            consumer=package/'test_consumer.py'
            consumer.write_text('from f139.test_source import Case\n',encoding='utf-8')
            before=collect(root)
            consumer.write_text('import f139.test_source as fixture_module\n',encoding='utf-8')
            after=collect(root)
            self.assertEqual(len(before['ids']),2)
            self.assertEqual(len(set(before['physical'])),1)
            compare_physical_coverage(before,after,1)

    def test_frozen_timing_threshold_denies_a_regressing_pair_or_small_gain(self):
        def runs(values):
            return [dict(arm=arm,seconds=value) for arm,value in zip(
                ['baseline','proposal','proposal','baseline'],values)]
        self.assertTrue(candidate.assess_times(runs([110,100,100,110]))['development_threshold_met'])
        self.assertFalse(candidate.assess_times(runs([130,100,100,99]))['development_threshold_met'])
        self.assertFalse(candidate.assess_times(runs([102,100,100,102]))['development_threshold_met'])
        for values in ([110,0,100,110],[110,float('nan'),100,110]):
            with self.assertRaises(ValueError):
                candidate.assess_times(runs(values))

    def test_windows_checkout_newlines_retain_raw_identity_and_same_canonical_patch(self):
        crlf={p:raw.replace(b'\n',b'\r\n') for p,raw in self.files.items()}
        windows=candidate.propose(crlf,source_sha='a'*40,source_tree='b'*40)
        after=candidate.inspect_proposal(windows,crlf,source_sha='a'*40,source_tree='b'*40)
        posix=json.loads(self.proposal())
        for row, original in zip(json.loads(windows)['changes'],posix['changes']):
            self.assertEqual(row['after_canonical_sha256'],original['after_canonical_sha256'])
            self.assertEqual(row['before_sha256'],hashlib.sha256(crlf[row['path']]).hexdigest())
            self.assertEqual(after[row['path']].replace(b'\r\n',b'\n'),
                             base64.b64decode(original['after_base64']))


if __name__=='__main__':
    unittest.main()

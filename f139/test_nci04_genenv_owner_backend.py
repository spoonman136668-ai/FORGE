"""Owner-path fixtures; these tests do not authenticate the live owner."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from f139 import nci04_genenv_owner_backend as backend
from f139 import nci04_genenv_source as compiler
from f139 import nci04_model_free_search as search
from f139.nci04_native_contract import canonical, digest
from f139 import test_nci04_model_free_search as fixtures

BEFORE = fixtures.BEFORE


class SourceUseRequestTests(unittest.TestCase):
    def test_v38_binary_custody_accepts_only_cold_verified_known_source_schema(self):
        import sqlite3
        with tempfile.TemporaryDirectory() as temp:
            source = 'a'*40
            raw = b'development-only-byte-custody-fixture-not-executed'
            binary = Path(temp)/'genenv-source'/source/'f139-genenv-source.exe'
            binary.parent.mkdir(parents=True); binary.write_bytes(raw)
            conn = sqlite3.connect(':memory:');self.addCleanup(conn.close);conn.row_factory=sqlite3.Row
            conn.execute('CREATE TABLE events(seq INTEGER,kind TEXT,payload TEXT)')
            verified=[]
            db=SimpleNamespace(conn=conn,filename=Path(temp)/'state.sqlite',
                verify=lambda:verified.append(True),meta=lambda:{'source_sha':source})
            for schema, accepted in (('v32',True),('v33',True),('v34',False)):
                conn.execute('DELETE FROM events')
                doc=dict(schema='forge.f139.source-transition.'+schema,
                         to_source_sha=source,genenv_executable_sha256=digest(raw),
                         generation_mechanism_sha256=digest(backend.generation_mechanism()))
                conn.execute('INSERT INTO events VALUES(?,?,?)',(1,'SOURCE_TRANSITION_ADMITTED',json.dumps(doc)))
                if accepted:
                    self.assertEqual(backend.executable_custody(db,source),(binary,digest(raw)))
                    backend.typed_generation_custody(db,source,digest(backend.generation_mechanism()))
                else:
                    with self.assertRaisesRegex(backend.BackendUnavailable,'RELEASE_NOT_BOUND'):
                        backend.executable_custody(db,source)
                    with self.assertRaisesRegex(backend.BackendUnavailable,'TYPED_RELEASE_NOT_BOUND'):
                        backend.typed_generation_custody(db,source,digest(backend.generation_mechanism()))
            self.assertEqual(len(verified),6)
            doc['schema']='forge.f139.source-transition.v33'
            conn.execute('UPDATE events SET payload=?',(json.dumps(doc),))
            with self.assertRaisesRegex(backend.BackendUnavailable,'TYPED_MECHANISM_DRIFT'):
                backend.typed_generation_custody(db,source,'f'*64)
            with self.assertRaisesRegex(backend.BackendUnavailable,'TYPED_RELEASE_NOT_BOUND'):
                backend.typed_generation_custody(db,'b'*40,digest(backend.generation_mechanism()))
            binary.write_bytes(b'changed bytes')
            with self.assertRaisesRegex(backend.BackendUnavailable,'EXECUTABLE_DRIFT'):
                backend.executable_custody(db,source)
    def consumed(self):
        return {digest(x[1]) for x in search.candidates(BEFORE)}

    def test_plan_is_deterministic_and_only_contains_unconsumed_compositions(self):
        a = backend.build_request(BEFORE, self.consumed(), set(), "a"*64)
        self.assertEqual(a, backend.build_request(BEFORE, self.consumed(), set(), "a"*64))
        self.assertEqual(len(a["history"]["records"]), 3)
        self.assertEqual(len(a["frozen"]["requests"]), 4)
        self.assertEqual(a["frozen"]["max_operations"], 9)
        self.assertTrue(all(r["classification"] == "CONSUMED_INDETERMINATE"
                            for r in a["history"]["records"]))

    def test_no_replay_reset_when_the_composition_space_is_consumed(self):
        consumed = {digest(compiler.source_for_vector(BEFORE, v)[0])
                    for v in ((0,0,1),(0,1,0),(1,0,0),(0,1,1),(1,0,1),(1,1,0),(1,1,1))}
        self.assertIsNone(backend.build_request(BEFORE, consumed, set(), "a"*64))

    def test_requires_standalone_exhaustion_before_invocation(self):
        with self.assertRaisesRegex(backend.BackendUnavailable, "NOT_EXHAUSTED"):
            backend.build_request(BEFORE, set(), set(), "a"*64)

    def test_history_pin_changes_when_original_negative_custody_changes(self):
        a = backend.build_request(BEFORE, self.consumed(), set(), "a"*64)
        b = backend.build_request(BEFORE, self.consumed(), set(), "b"*64)
        self.assertNotEqual(a["history_sha256"], b["history_sha256"])
        self.assertNotEqual(a["frozen_sha256"], b["frozen_sha256"])

    def test_unpinned_executable_never_runs(self):
        with patch.object(backend.subprocess, "run", side_effect=AssertionError("must not run")):
            with self.assertRaises((OSError, backend.BackendUnavailable)):
                backend.invoke(Path("missing-genenv-binary.exe"), "a"*64, {})

    def test_utility_cannot_inherit_owner_or_model_credentials_and_timeout_is_typed(self):
        with tempfile.TemporaryDirectory() as temp:
            binary = Path(temp)/"fixture.exe"
            binary.write_bytes(b"fixture-only-not-executable")
            expected = digest(binary.read_bytes())
            with patch.dict(os.environ, {"F139_WORKER_HMAC_KEY":"secret-fixture",
                    "GH_TOKEN":"secret-fixture", "OPENROUTER_API_KEY":"secret-fixture"}), \
                    patch.object(backend.subprocess,"run", return_value=SimpleNamespace(
                        returncode=0,stdout=b"{}",stderr=b"")) as run:
                self.assertEqual(backend.invoke(binary,expected,{}),b"{}")
                self.assertTrue(set(run.call_args.kwargs["env"]) <= {"SystemRoot","WINDIR","TEMP","TMP"})
                self.assertEqual(run.call_args.kwargs["timeout"],15)
            with patch.object(backend.subprocess,"run",side_effect=subprocess.TimeoutExpired("fixture",15)):
                with self.assertRaisesRegex(backend.BackendUnavailable,"UTILITY_UNAVAILABLE"):
                    backend.invoke(binary,expected,{})

    def test_utility_modified_during_call_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            binary = Path(temp)/"fixture.exe"
            binary.write_bytes(b"fixture-only-not-executable")
            expected = digest(binary.read_bytes())
            def mutate(*args,**kwargs):
                binary.write_bytes(b"changed")
                return SimpleNamespace(returncode=0,stdout=b"{}",stderr=b"")
            with patch.object(backend.subprocess,"run",side_effect=mutate):
                with self.assertRaisesRegex(backend.BackendUnavailable,"EXECUTABLE_CHANGED"):
                    backend.invoke(binary,expected,{})


class OriginalPublisherConnectionTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.ModelFreeOwnerPublicationTests("test_exhausted_search_is_read_only_and_never_calls_provider")
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.db = self.fixture.db
        self.prepared = search.owner_request(self.db, self.fixture.owner.get,
            self.fixture.steering.get, source_sha=self.fixture.owner.source,
            lane="Yggdrasil", target_commit=self.fixture.owner.parent,
            path=search.PATH, owner_witness=lambda: True)
        self.prepared["consumed_after_hashes"].update(
            digest(x[1]) for x in search.candidates(BEFORE))
        change = patch.object(compiler, "PARENT", self.fixture.owner.parent)
        change.start()
        self.addCleanup(change.stop)

    def utility_fixture(self, binary, binary_sha, request):
        # Only the ABI/publication plumbing is mocked. Actual GenEnv is
        # separately invoked by the two-OS cross-language CI qualification.
        candidates = []
        for recipe in request["frozen"]["requests"]:
            vector = [0, 0, 0]
            for op in recipe["changes"]:
                vector[op["index"]] += op["delta"]
            candidates.append(dict(vector=vector, classification="UNTESTED_PROPOSAL"))
        return canonical(dict(schema="forge.f139.genenv-source-output.v1",
            source_sha=self.fixture.owner.parent, result=dict(
                schema="forge.genenvironment.advisory.v1", lane="Yggdrasil",
                frozen_sha256=request["frozen_sha256"], history_sha256=request["history_sha256"],
                candidates=candidates, scientific_accepted=False,
                dispatch_authorized=False, sealed_holdout_consumed=False)))

    def test_original_exhausted_tick_reaches_the_existing_journaled_publisher(self):
        with patch.object(search, "owner_request", return_value=self.prepared), \
                patch.object(backend, "executable_custody", return_value=(Path("unused"), "c"*64)), \
                patch.object(backend, "invoke", side_effect=self.utility_fixture):
            result = self.fixture.publish()
        self.assertEqual(result["disposition"], "MODEL_DRAFT_AUTHENTICATED")
        self.assertEqual(result["generator"], "GENENV_NATIVE_SOURCE_COMPILER")
        self.assertEqual(result["model_calls"], 0)
        self.assertNotIn(result["source_after_sha256"], self.prepared["consumed_after_hashes"])
        self.assertEqual(self.db.conn.execute(
            "SELECT COUNT(*) FROM events WHERE kind='MODEL_DRAFT_ATTEMPTED'").fetchone()[0], 1)
        self.db.verify()

    def test_missing_release_custody_remains_read_only(self):
        original = self.db.meta().copy()
        with patch.object(search, "owner_request", return_value=self.prepared), \
                patch.object(backend, "invoke", side_effect=AssertionError("must not run")):
            result = self.fixture.publish()
        self.assertEqual(result["disposition"], "MODEL_FREE_SEARCH_EXHAUSTED_NO_FRESH_CANDIDATE")
        self.assertIn("RELEASE_NOT_BOUND", result["source_backend_blocked"])
        self.assertEqual(self.db.meta(), original)
        self.assertEqual(self.fixture.owner.write_calls, [])

    def test_utility_failure_cannot_consume_or_publish_a_candidate(self):
        original = self.db.meta().copy()
        with patch.object(search, "owner_request", return_value=self.prepared), \
                patch.object(backend, "executable_custody", return_value=(Path("unused"), "c"*64)), \
                patch.object(backend, "invoke", side_effect=backend.BackendUnavailable("utility failed")):
            with self.assertRaises(backend.BackendUnavailable):
                self.fixture.publish()
        self.assertEqual(self.db.meta(), original)
        self.assertEqual(self.fixture.owner.write_calls, [])

    def test_lost_publication_ack_remains_sticky_before_another_utility_call(self):
        self.fixture.owner.fail_after_reference = True
        with patch.object(search, "owner_request", return_value=self.prepared), \
                patch.object(backend, "executable_custody", return_value=(Path("unused"), "c"*64)), \
                patch.object(backend, "invoke", side_effect=self.utility_fixture) as invoke:
            first = self.fixture.publish()
            second = self.fixture.publish()
        self.assertEqual(first["disposition"], "MODEL_DRAFT_REMOTE_AMBIGUOUS_NO_RETRY")
        self.assertEqual(second["disposition"], "MODEL_DRAFT_UNRESOLVED_NO_REPLAY")
        self.assertEqual(invoke.call_count, 1)

    def test_pin_drift_is_a_blocker_not_silent_catalog_exhaustion(self):
        original = self.db.meta().copy()
        with patch.object(search, "owner_request", return_value=self.prepared), \
                patch.object(backend, "executable_custody", side_effect=backend.BackendUnavailable(
                    "F139_GENENV_EXECUTABLE_DRIFT")):
            with self.assertRaisesRegex(backend.BackendUnavailable, "EXECUTABLE_DRIFT"):
                self.fixture.publish()
        self.assertEqual(self.db.meta(), original)
        self.assertEqual(self.fixture.owner.write_calls, [])


class TypedOriginalPublisherConnectionTests(unittest.TestCase):
    def setUp(self):
        OriginalPublisherConnectionTests.setUp(self)
        self.prepared["consumed_after_hashes"].update(
            digest(compiler.source_for_vector(BEFORE,v)[0])
            for v in ((0,0,1),(0,1,0),(1,0,0),(0,1,1),(1,0,1),(1,1,0),(1,1,1)))

    def utility_fixture(self,binary,binary_sha,request):
        from f139.test_nci04_prompt_source import output_fixture
        frozen=request["promptbreeder"]["frozen"]
        doc=output_fixture(frozen)
        doc["result"]["operations_used"]=len(frozen["operations"])
        return canonical(doc)

    def test_original_publisher_authenticates_typed_candidate_after_all_seven(self):
        with patch.object(search,"owner_request",return_value=self.prepared), \
                patch.object(backend,"executable_custody",return_value=(Path("unused"),"c"*64)), \
                patch.object(backend,"typed_generation_custody"), \
                patch.object(backend,"invoke",side_effect=self.utility_fixture), \
                patch.object(search,"publish_model_once",wraps=search.publish_model_once) as publish:
            result=self.fixture.publish()
        self.assertEqual(result["disposition"],"MODEL_DRAFT_AUTHENTICATED")
        self.assertEqual(result["generator"],"PROMPTBREEDER_TYPED_SOURCE_COMPILER")
        self.assertEqual(result["model_calls"],0)
        self.assertNotIn(result["source_after_sha256"],self.prepared["consumed_after_hashes"])
        doc=json.loads(publish.call_args.kwargs["raw_response"])
        self.assertLessEqual(len(doc["hypothesis"]),600)
        marker=" provenance-prompt-v1="
        self.assertIn(marker,doc["hypothesis"])
        pins=json.loads(doc["hypothesis"].split(marker)[1])
        self.assertEqual(set(pins),set("rfhome"))
        self.assertTrue(all(len(v)==64 for v in pins.values()))
        self.assertEqual(pins["h"],result["provenance"]["source_bindings_sha256"])
        self.db.verify()

    def test_typed_missing_release_or_mechanism_drift_cannot_invoke_or_publish(self):
        original=self.db.meta().copy()
        with patch.object(search,"owner_request",return_value=self.prepared), \
                patch.object(backend,"executable_custody",return_value=(Path("unused"),"c"*64)), \
                patch.object(backend,"invoke",side_effect=AssertionError("must not run")):
            result=self.fixture.publish()
            self.assertEqual(result["disposition"],"GENENV_COMPOSITION_SPACE_EXHAUSTED")
            self.assertIn("TYPED_RELEASE_NOT_BOUND",result["source_backend_blocked"])
            with patch.object(backend,"typed_generation_custody",
                    side_effect=backend.BackendUnavailable("F139_GENENV_TYPED_MECHANISM_DRIFT")):
                with self.assertRaisesRegex(backend.BackendUnavailable,"TYPED_MECHANISM_DRIFT"):
                    self.fixture.publish()
        self.assertEqual(self.db.meta(),original)
        self.assertEqual(self.fixture.owner.write_calls,[])

    def test_typed_publication_ambiguity_remains_sticky(self):
        self.fixture.owner.fail_after_reference=True
        with patch.object(search,"owner_request",return_value=self.prepared), \
                patch.object(backend,"executable_custody",return_value=(Path("unused"),"c"*64)), \
                patch.object(backend,"typed_generation_custody"), \
                patch.object(backend,"invoke",side_effect=self.utility_fixture) as invoke:
            first=self.fixture.publish()
            second=self.fixture.publish()
        self.assertEqual(first["disposition"],"MODEL_DRAFT_REMOTE_AMBIGUOUS_NO_RETRY")
        self.assertEqual(second["disposition"],"MODEL_DRAFT_UNRESOLVED_NO_REPLAY")
        self.assertEqual(invoke.call_count,1)

    def test_typed_mechanism_changed_during_utility_is_read_only(self):
        original=self.db.meta().copy()
        mechanism=backend.generation_mechanism()
        with patch.object(search,"owner_request",return_value=self.prepared), \
                patch.object(backend,"executable_custody",return_value=(Path("unused"),"c"*64)), \
                patch.object(backend,"typed_generation_custody"), \
                patch.object(backend,"generation_mechanism",side_effect=[mechanism,mechanism+b"drift"]), \
                patch.object(backend,"invoke",side_effect=self.utility_fixture):
            with self.assertRaisesRegex(backend.BackendUnavailable,"TYPED_MECHANISM_CHANGED"):
                self.fixture.publish()
        self.assertEqual(self.db.meta(),original)
        self.assertEqual(self.fixture.owner.write_calls,[])

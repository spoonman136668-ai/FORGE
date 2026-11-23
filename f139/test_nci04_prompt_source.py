"""Negative source-binding tests; real Go invocation is a separate CI check."""
import copy
from dataclasses import replace
import json
import unittest

from f139.check_prompt_source_integration import fixture, check
from f139.nci04_portfolio_source_boundary import PortfolioSourceRejected, _sha
from f139.nci04_prompt_source import bindings_digest, compile_prompt_sources, encoded, frozen_digest


def output_fixture(frozen):
    pin = frozen_digest(frozen)
    parent = _sha(("FORGE-PROMPTLINEAGE-PARENT-V1\nYggdrasil\n"+frozen["source_sha"]+"\n"+
                   frozen["parent"]).encode())
    entries = []
    for i, op in enumerate(frozen["operations"]):
        words = frozen["parent"].split(" ")
        words[op["position"]] = op["replacement"]
        prompt = " ".join(words)
        child = _sha(("FORGE-PROMPTLINEAGE-CHILD-V1\n"+pin+"\n"+parent+"\n"+
                      str(i)+"\n"+prompt).encode())
        entries.append(dict(parent_sha256=parent, candidate_sha256=child, prompt=prompt,
                            operation=op, classification="UNTESTED"))
    return dict(schema="forge.f139.prompt-source-output.v1", source_sha=frozen["source_sha"],
        result=dict(schema="forge.promptlineage.advisory.v1", lane="Yggdrasil",
            frozen_sha256=pin, parent_sha256=parent, operations_used=2, candidates=entries,
            scientific_accepted=False, dispatch_authorized=False, sealed_evaluation_consumed=False))


class SourceBindingTests(unittest.TestCase):
    def setUp(self):
        before, frozen, mechanism, bindings = fixture()
        self.doc = output_fixture(frozen)
        self.args = dict(frozen=frozen, frozen_sha256=frozen_digest(frozen), bindings=bindings,
            bindings_sha256=bindings_digest(bindings), mechanism=mechanism,
            mechanism_sha256=_sha(mechanism), lane="Yggdrasil", path=bindings[0].source.path,
            parent_sha=frozen["source_sha"], before=before,
            historical_sha256=frozenset(), historical_ast_sha256=frozenset())

    def compile(self, doc=None, **overrides):
        raw = encoded(self.doc if doc is None else doc)
        return compile_prompt_sources(raw, **{**self.args, "result_sha256":_sha(raw), **overrides})

    def test_complete_bindings_preserve_all_independent_pins(self):
        result = self.compile()
        self.assertEqual(len(result.candidates), 2)
        self.assertEqual(result.bindings_sha256, self.args["bindings_sha256"])
        self.assertEqual(result.frozen_sha256, self.args["frozen_sha256"])
        self.assertTrue(check(encoded(self.doc))["complete_seven_consumed_replay_rejected"])

    def test_advisory_json_without_source_bindings_is_not_executable(self):
        with self.assertRaisesRegex(PortfolioSourceRejected, "BINDINGS_BOUND"):
            self.compile(bindings=())
        with self.assertRaisesRegex(PortfolioSourceRejected, "SOURCE_BINDING_REQUIRED"):
            bindings_digest((self.doc["result"]["candidates"][0],))

    def test_missing_extra_or_duplicate_binding_rejects_entire_population(self):
        bindings = self.args["bindings"]
        for changed in (bindings[:1], bindings+(bindings[0],), (bindings[0], bindings[0])):
            with self.subTest(size=len(changed)), self.assertRaises(PortfolioSourceRejected):
                self.compile(bindings=changed, bindings_sha256=bindings_digest(changed))

    def test_no_cherry_picking_missing_reordered_or_replayed_outputs(self):
        for kind in ("drop", "reorder", "repeat"):
            doc = copy.deepcopy(self.doc)
            entries = doc["result"]["candidates"]
            if kind == "drop":
                entries.pop()
            elif kind == "reorder":
                entries.reverse()
            else:
                entries[1] = entries[0]
            with self.subTest(kind=kind), self.assertRaises(PortfolioSourceRejected):
                self.compile(doc)

    def test_source_artifact_manifest_and_mechanism_drift_fail_closed(self):
        b = self.args["bindings"][0]
        cases = [dict(mechanism=b"changed"), dict(bindings_sha256="0"*64),
                 dict(frozen_sha256="0"*64), dict(result_sha256="0"*64),
                 dict(bindings=(replace(b,source=replace(b.source,after=b"x=3\n")),
                                self.args["bindings"][1]))]
        for overrides in cases:
            with self.subTest(keys=list(overrides)), self.assertRaises(PortfolioSourceRejected):
                self.compile(**overrides)

    def test_rebound_source_wrong_lane_parent_or_generator_is_denied(self):
        b = self.args["bindings"][0]
        for field, value in (("lane","Wingless"), ("parent_sha","b"*40),
                             ("generator","dgm_genenv"), ("path","other.py")):
            changed = (replace(b,source=replace(b.source,**{field:value})), self.args["bindings"][1])
            with self.subTest(field=field), self.assertRaises(PortfolioSourceRejected):
                self.compile(bindings=changed, bindings_sha256=bindings_digest(changed))

    def test_historical_negative_byte_and_ast_replays_cannot_be_relabeled(self):
        b = self.args["bindings"][0]
        from f139.nci04_model_free_search import normalized
        for keys in (dict(historical_sha256=frozenset({_sha(b.source.after)})),
                     dict(historical_ast_sha256=frozenset({normalized(b.source.after)}))):
            with self.assertRaisesRegex(PortfolioSourceRejected,"HISTORICAL_REPLAY"):
                self.compile(**keys)

    def test_forged_mutation_hash_identity_and_authority_are_rejected(self):
        edits = [("result", "dispatch_authorized", True),
                 ("result", "sealed_evaluation_consumed", True),
                 ("result", "scientific_accepted", True),
                 ("result", "frozen_sha256", "b"*64),
                 (None,"source_sha","b"*40)]
        for group,key,value in edits:
            doc = copy.deepcopy(self.doc)
            (doc[group] if group else doc)[key] = value
            with self.subTest(key=key), self.assertRaises(PortfolioSourceRejected):
                self.compile(doc)
        for key,value in (("classification","SUPPORTED"), ("candidate_sha256","b"*64),
                          ("operation",{}), ("prompt","invented executable")):
            doc = copy.deepcopy(self.doc)
            doc["result"]["candidates"][0][key] = value
            with self.subTest(key=key), self.assertRaises(PortfolioSourceRejected):
                self.compile(doc)

    def test_wrong_frozen_budget_source_and_boolean_epoch_are_denied(self):
        for key,value in (("max_operations",1), ("epoch",True), ("source_sha","0"*40)):
            f = copy.deepcopy(self.args["frozen"])
            f[key] = value
            with self.subTest(key=key), self.assertRaises(PortfolioSourceRejected):
                self.compile(frozen=f)

    def test_source_is_parsed_never_executed(self):
        bindings = tuple(replace(b,source=replace(b.source,
            after=b"raise RuntimeError('must not execute')\nx="+str(i).encode()+b"\n",
            after_sha256=_sha(b"raise RuntimeError('must not execute')\nx="+str(i).encode()+b"\n")))
            for i,b in enumerate(self.args["bindings"]))
        self.assertEqual(len(self.compile(bindings=bindings,
            bindings_sha256=bindings_digest(bindings)).candidates),2)

    def test_duplicate_json_keys_and_boolean_operation_position_are_denied(self):
        raw = encoded(self.doc).replace(b'"dispatch_authorized":false',
            b'"dispatch_authorized":true,"dispatch_authorized":false')
        with self.assertRaisesRegex(PortfolioSourceRejected,"DUPLICATE_JSON_FIELD"):
            compile_prompt_sources(raw, **self.args, result_sha256=_sha(raw))
        doc = copy.deepcopy(self.doc)
        doc["result"]["candidates"][0]["operation"]["position"] = True
        with self.assertRaisesRegex(PortfolioSourceRejected,"OUTPUT_BINDING_MISMATCH"):
            self.compile(doc)

    def test_wrongly_bound_source_text_and_duplicate_semantics_are_denied(self):
        b = self.args["bindings"][0]
        other = self.args["bindings"][1]
        changed = (b, replace(other,source=b.source))
        with self.assertRaisesRegex(PortfolioSourceRejected,"HISTORICAL_REPLAY"):
            self.compile(bindings=changed, bindings_sha256=bindings_digest(changed))
        changed = (b, replace(other,prompt="unbound words"))
        with self.assertRaisesRegex(PortfolioSourceRejected,"OUTPUT_BINDING_MISMATCH"):
            self.compile(bindings=changed, bindings_sha256=bindings_digest(changed))


if __name__ == "__main__":
    unittest.main()

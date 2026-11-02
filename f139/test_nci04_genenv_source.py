import json
from pathlib import Path
import unittest

from f139.check_genenv_source_integration import check
from f139.nci04_genenv_source import compile_operator_vectors
from f139.nci04_portfolio_source_boundary import PortfolioSourceRejected, _sha


class GenEnvSourceTests(unittest.TestCase):
    def result(self):
        result = dict(schema="forge.genenvironment.advisory.v1", lane="Yggdrasil",
                    frozen_sha256="a" * 64, history_sha256="b" * 64,
                    scientific_accepted=False, dispatch_authorized=False,
                    sealed_holdout_consumed=False, candidates=[dict(
                        classification="UNTESTED_PROPOSAL", vector=v)
                        for v in ([1,1,0], [1,0,1], [0,1,1], [1,1,1])])
        return dict(schema="forge.f139.genenv-source-output.v1",
                    source_sha="992ef142aaa551156749a1de484a971b9a0c092f", result=result)

    def compile(self, result, **overrides):
        raw = json.dumps(result).encode()
        options = dict(result_sha256=_sha(raw), frozen_sha256="a" * 64,
                       history_sha256="b" * 64, mechanism=b"mechanism",
                       mechanism_sha256=_sha(b"mechanism"), before=Path(
                           "f139/fixtures/model_free_yggdrasil_992ef.py").read_bytes(),
                       historical_sha256=frozenset(), historical_ast_sha256=frozenset())
        options.update(overrides)
        return compile_operator_vectors(raw, **options)

    def test_four_real_source_compositions_after_fixture_exhaustion(self):
        self.assertEqual(check(json.dumps(self.result()).encode())["fresh_source_candidates"],4)

    def test_wrong_lane_and_authority_rejected(self):
        for key, value in (("lane","Wingless"),("dispatch_authorized",True),
                           ("scientific_accepted",True),("sealed_holdout_consumed",True)):
            result = self.result()
            result["result"][key] = value
            with self.assertRaisesRegex(PortfolioSourceRejected,"CONTRACT"):
                self.compile(result)

    def test_nonrecipe_vector_and_prompt_cannot_become_source(self):
        for vector in ([1,2,0], [True,0,1], [0,0,0], "choose a better rule"):
            result = self.result()
            result["result"]["candidates"][0]["vector"] = vector
            with self.assertRaisesRegex(PortfolioSourceRejected,"SOURCE_RECIPE"):
                self.compile(result)

    def test_result_pin_and_consumed_composition_rejected(self):
        with self.assertRaisesRegex(PortfolioSourceRejected,"RESULT_DRIFT"):
            self.compile(self.result(),result_sha256="0"*64)
        receipts = self.compile(self.result()).candidates
        with self.assertRaisesRegex(PortfolioSourceRejected,"HISTORICAL_REPLAY"):
            self.compile(self.result(), historical_sha256=frozenset({receipts[0][0].after_sha256}))


    def test_foreign_source_identity_rejected(self):
        result = self.result()
        result["source_sha"] = "f" * 40
        with self.assertRaisesRegex(PortfolioSourceRejected,"SOURCE_IDENTITY"):
            self.compile(result)

    def test_upstream_result_and_training_pins_survive_compilation(self):
        result = self.result()
        batch = self.compile(result)
        self.assertEqual(batch.generator_result_sha256, _sha(json.dumps(result).encode()))
        self.assertEqual(batch.frozen_sha256, "a" * 64)
        self.assertEqual(batch.history_sha256, "b" * 64)
        self.assertEqual(batch.mechanism_sha256, _sha(b"mechanism"))
        self.assertEqual(batch.source_sha, result["source_sha"])

"""L10-C8 controlled in-process semantic mapping leak falsification.

Development-only safety diagnostic. Demonstrates a current source-custody
limitation; DOES NOT score any heldout, fit a learner, prove a secure sandbox,
or authorize scientific first use. A future protected evaluation must isolate
untrusted model execution from source truth at an actual host/filesystem level.
"""
import unittest

import l10_dev_source_custody as source
import l10_dev_matched_controls as controls
import l10_semantic_dev_oracle as oracle


def illicit_inprocess_candidate(model_input):
    """A negative control intentionally using nonpublic SOURCE MODULE state.

    The callback receives only the claimed public ModelInput, but in-process
    Python imports expose the semantic lexicon stored in the same repository.
    This must never be admitted as a protected or unseen-language method.
    """
    assert model_input.information_regime == "WITHHELD_MAPPING"
    assert model_input.public_lexicon == ()
    from l10_dev_source_custody import PREDICATE_LEXICON
    stolen = dict(PREDICATE_LEXICON)
    lines = []
    for record in model_input.observed:
        lines.append(
            f"{record.subject} :: {stolen[record.relation_code]} :: "
            f"{record.object} :: {'+' if record.polarity == 1 else '-'}"
        )
    return "; ".join(lines)


class InProcessMappingLeakFalsification(unittest.TestCase):
    def test_withheld_public_interface_does_not_prevent_source_import(self):
        # One manually specified SOURCE-FREE diagnostic, not DEV_CHECK/heldout.
        inp = source.ModelInput(
            (source.Observed("Aster", "P0", "Boreal", 1),),
            (),
            "WITHHELD_MAPPING",
        )
        self.assertEqual(controls.allowed(inp), {})
        self.assertIsNone(controls.canonical_facts(inp))
        self.assertEqual(inp.public_lexicon, ())
        stolen_output = illicit_inprocess_candidate(inp)
        parsed = oracle.parse(stolen_output)
        self.assertEqual(
            parsed.claims,
            (oracle.Claim("Aster", "located_in", "Boreal", 1),),
        )
        self.assertEqual(parsed.unparseable_clauses, 0)
        self.assertFalse(parsed.abstention)

    def test_inprocess_candidate_registration_has_no_independent_isolation(self):
        # A callable is accepted without any process boundary, even when it
        # can import forbidden source mappings. Do NOT score any source cohort.
        self.assertTrue(callable(illicit_inprocess_candidate))
        self.assertEqual(controls.ARMS[-1], "candidate-interface")
        self.assertEqual(
            controls.OBS,
            "DEVELOPMENT_ONLY_NOT_PROSPECTIVE_SCIENTIFIC_EVIDENCE",
        )
        self.assertFalse(hasattr(controls, "evaluate_prospective"))

    def test_no_hidden_cohorts_or_firstuse_generated(self):
        self.assertFalse(hasattr(source, "PROSPECTIVE_SEED"))
        self.assertFalse(hasattr(source, "generate_prospective"))
        self.assertEqual(source.PROSPECTIVE_ROLE, "L10_PROSPECTIVE_NEW_SOURCE_FAMILY")


if __name__ == "__main__":
    unittest.main()

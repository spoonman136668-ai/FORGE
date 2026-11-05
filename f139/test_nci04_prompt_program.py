"""Typed-program compiler falsification; candidate execution is test-only."""
from fractions import Fraction
import itertools
from pathlib import Path
import unittest

from f139 import nci04_model_free_search as search
from f139.nci04_genenv_source import source_for_vector
from f139.nci04_native_contract import digest
from f139.nci04_prompt_program import (
    BRANCHES,MARKER,SEED,ProgramRejected,build_plan,recover_program,
    public_rate_preflight,source_for_program,
)
from f139.nci04_prompt_source import frozen_digest

BEFORE = Path(__file__).with_name("fixtures").joinpath("model_free_yggdrasil_992ef.py").read_bytes()
LEGACY = tuple(source_for_vector(BEFORE,v)[0] for v in itertools.product((0,1),repeat=3) if any(v))


def plan(sources=LEGACY,**overrides):
    args = dict(history_sources=sources,consumed_sha256={digest(x) for x in sources},
        historical_ast_sha256={search.normalized(x) for x in sources},
        history_sha256="a"*64,mechanism_sha256="b"*64)
    return build_plan(BEFORE,**{**args,**overrides})


def oracle(program,counts):
    """Independent rational oracle over the original unsimplified grammar."""
    words = program.split(" ")
    def value(pos,success,failure):
        token = words[pos]
        if pos not in BRANCHES:
            return dict(success=success,failure=failure,total=success+failure,
                        zero=0,one=1,two=2)[token],pos+1
        a,pos = value(pos+1,success,failure)
        b,pos = value(pos,success,failure)
        return {"add":lambda:a+b,"mul":lambda:a*b,"min":lambda:min(a,b),
                "max":lambda:max(a,b)}[token](),pos
    rates = []
    for failure,success in counts:
        if failure+success == 0:
            return None
        n,pos = value(1,success,failure)
        d,pos = value(pos,success,failure)
        if d <= 0:
            return None
        rates.append(Fraction(n,d))
    return None if rates[0] == rates[1] else 0 if rates[0] > rates[1] else 1


class TypedProgramTests(unittest.TestCase):
    def test_all_seven_consumed_sources_leave_a_fresh_bounded_population(self):
        p = plan()
        self.assertGreater(len(p.bindings),0)
        self.assertLessEqual(len(p.bindings),16)
        self.assertEqual(len(p.bindings),len(p.frozen["operations"]))
        self.assertEqual(len(p.frozen["parent"].split(" ")),20)
        self.assertEqual(len({search.normalized(b.source.after) for b in p.bindings}),len(p.bindings))
        self.assertTrue(all(b.source.after_sha256 not in {digest(x) for x in LEGACY}
                            for b in p.bindings))

    def test_recovered_generated_sources_continue_without_resetting_negatives(self):
        sources = LEGACY
        consumed = {digest(x) for x in sources}
        for _ in range(12):
            p = plan(sources)
            self.assertIsNotNone(p)
            child = p.bindings[0].source.after
            self.assertNotIn(digest(child),consumed)
            self.assertIsNotNone(recover_program(BEFORE,child))
            consumed.add(digest(child))
            sources += (child,)
        self.assertEqual(len(consumed),19)
        self.assertTrue({digest(x) for x in LEGACY} <= consumed)

    def test_public_rate_preflight_rejects_real_v36_negatives_but_keeps_history(self):
        # Exact public-counter programs from original V36 task negatives
        # i1483 (tautological tie) and i1484 (failure-rate inversion).
        negatives = (
            "rate min max success total add total zero add add total zero add zero zero",
            "rate min min failure total add total zero add add total zero add zero zero",
            "rate add add failure zero add zero zero add add total zero add zero zero",
        )
        for program in negatives:
            with self.subTest(program=program):
                self.assertFalse(public_rate_preflight(program))
                # Existing source identities stay reconstructible for custody.
                # Historical decoding is never requalified by this new filter.
                historical = source_for_program(BEFORE, program)
                reconstructed = recover_program(BEFORE, historical)
                self.assertIsNotNone(reconstructed)
                self.assertEqual(source_for_program(BEFORE, reconstructed), historical)
        self.assertTrue(public_rate_preflight(SEED))
        laplace = "rate add add success one add zero zero add add total two add zero zero"
        self.assertTrue(public_rate_preflight(laplace))

    def test_new_proposals_preserve_public_matched_exposure_order(self):
        proposal = plan()
        self.assertIsNotNone(proposal)
        self.assertGreater(len(proposal.bindings), 0)
        self.assertTrue(all(public_rate_preflight(
            binding.prompt.split(" history ", 1)[0])
            for binding in proposal.bindings))
        # Negative candidates remain consumed, never eligible as parents.
        negatives = (
            source_for_program(BEFORE,
                "rate min max success total add total zero add add total zero add zero zero"),
            source_for_program(BEFORE,
                "rate min min failure total add total zero add add total zero add zero zero"),
        )
        later = plan(LEGACY + negatives, eligible_parent_sha256=set())
        self.assertIsNotNone(later)
        self.assertEqual(later.parent_program, SEED)
        self.assertTrue({digest(x) for x in negatives}.isdisjoint(
            {b.source.after_sha256 for b in later.bindings}))

    def test_generated_arithmetic_matches_independent_fraction_oracle_and_keeps_memory(self):
        for binding in plan().bindings:
            source = binding.source.after
            namespace = {}
            exec(compile(source,"qualified-development-fixture","exec"),namespace)
            cls = namespace["PublicCausalCells"]
            program = recover_program(BEFORE,source)
            for index in range(96):
                counts = ((index%7,(index*3+1)%7),((index*5+2)%7,(index*2+3)%7))
                cells = cls()
                cells._counts[0] = [list(x) for x in counts]
                before = cells.snapshot()
                self.assertEqual(cells.choose(0),oracle(program,counts))
                self.assertEqual(cells.snapshot(),before)
                self.assertEqual(len(before),164)
                self.assertEqual(cells.LEARNED_BYTES,128)
                cells._counts[0].reverse()
                swapped = cells.choose(0)
                expected = oracle(program,counts)
                self.assertEqual(swapped,None if expected is None else 1-expected)
                self.assertIsNone(cells.choose(0,retained=True))

    def test_sources_preserve_all_original_methods_except_choice(self):
        import ast
        def methods(raw):
            cls = next(x for x in ast.parse(raw).body if isinstance(x,ast.ClassDef))
            return {x.name:ast.dump(x,include_attributes=False) for x in cls.body
                    if isinstance(x,ast.FunctionDef) and x.name != "choose"}
        expected = methods(BEFORE)
        self.assertTrue(all(methods(b.source.after) == expected for b in plan().bindings))

    def test_baseline_affine_replays_and_original_laplace_share_original_identities(self):
        self.assertEqual(source_for_program(BEFORE,SEED),BEFORE)
        doubled = SEED.replace("success zero","success success",1)
        self.assertEqual(source_for_program(BEFORE,doubled),BEFORE)
        laplace = "rate add add success one add zero zero add add total two add zero zero"
        self.assertEqual(source_for_program(BEFORE,laplace),LEGACY[3])
        scaled = "rate mul add success one add one one add add total two add zero zero"
        self.assertEqual(source_for_program(BEFORE,scaled),LEGACY[3])

    def test_history_is_bound_in_actual_prompt_plan_without_source_nonce_replays(self):
        a,b = plan(),plan(history_sha256="c"*64)
        self.assertNotEqual(frozen_digest(a.frozen),frozen_digest(b.frozen))
        self.assertEqual([x.source.after_sha256 for x in a.bindings],
                         [x.source.after_sha256 for x in b.bindings])
        self.assertIn(" history "+" ".join(["a"*16]*4),a.frozen["parent"])

    def test_raw_and_ast_negative_sets_are_both_used_for_preflight(self):
        p = plan()
        child = p.bindings[0].source
        for overrides in (dict(consumed_sha256={child.after_sha256}),
                          dict(historical_ast_sha256={search.normalized(child.after)})):
            new = plan(**overrides)
            self.assertNotIn(child.after_sha256,[b.source.after_sha256 for b in new.bindings])

    def test_marker_is_only_a_lookup_hint_not_source_provenance(self):
        child = plan().bindings[0].source.after
        with self.assertRaisesRegex(ProgramRejected,"HISTORY_SOURCE_DRIFT"):
            recover_program(BEFORE,child+b"\nx=1\n")
        forged = BEFORE+MARKER.encode()+SEED.encode()+b"\n"
        with self.assertRaises(ProgramRejected):
            recover_program(BEFORE,forged)

    def test_equivalent_tokens_cannot_change_source_identity_before_native_intake(self):
        child = plan().bindings[0].source.after
        canonical = recover_program(BEFORE,child)
        alias = canonical.replace("failure zero","zero failure",1)
        self.assertNotEqual(alias,canonical)
        self.assertEqual(source_for_program(BEFORE,alias),child)
        # Original publication custody has the raw hash before native intake.
        # The new source's AST is deliberately absent from this fixture.
        new = plan(consumed_sha256={digest(child)},historical_ast_sha256=set())
        self.assertNotIn(search.normalized(child),
                         [search.normalized(b.source.after) for b in new.bindings])

    def test_untyped_tokens_capacity_growth_and_invalid_context_fail_closed(self):
        for invalid in (SEED+" zero",SEED.replace("add","__import__",1),
                        SEED.replace("success","42",1),SEED.replace("rate","eval",1)):
            with self.subTest(program=invalid),self.assertRaises(ProgramRejected):
                source_for_program(BEFORE,invalid)
        for overrides in (dict(max_candidates=17),dict(max_candidates=True),
                          dict(history_sha256="wrong"),dict(history_sources=LEGACY*600)):
            with self.subTest(keys=list(overrides)),self.assertRaises(ProgramRejected):
                plan(**overrides)
        with self.assertRaisesRegex(ValueError,"FROZEN_SOURCE_DRIFT"):
            source_for_program(BEFORE+b"\n",SEED)


if __name__ == "__main__":
    unittest.main()

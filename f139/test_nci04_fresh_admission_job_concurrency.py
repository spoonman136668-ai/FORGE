"""Negative controls: fresh admission cannot consume another owner workflow's queue."""
from pathlib import Path
import unittest

WORKFLOW = (Path(__file__).resolve().parents[1] / ".github" / "workflows" /
            "f139-fresh-original-owner-admission.yml")


def qualify(source: str) -> None:
    """Static contract; does not execute GitHub Actions or admit a ticket."""
    def need(ok: bool) -> None:
        if not ok:
            raise ValueError("F139_FRESH_ADMISSION_CONCURRENCY_SCOPE_INVALID")
    need(source.count("on:\n  issue_comment:\n    types: [created]\n") == 1
         and "\n  schedule:" not in source)
    need(source.count("\njobs:\n  fresh-one-ready:\n    if: >-\n") == 1
         and source.count("    runs-on: [self-hosted, Windows, forge-codex-isolated]\n") == 1)
    # Top-level workflow concurrency reserves a shared slot BEFORE job-level
    # owner/issue checks, even when every job ultimately skips.
    need("\nconcurrency:\n" not in source)
    need(source.count(
        "    concurrency:\n"
        "      group: forge-f139-fresh-owner-admission\n"
        "      cancel-in-progress: false\n") == 1)
    need("group: forge-f139-v54-original-owner" not in source)
    for owner_bound in (
        "github.actor == 'spoonman136668-ai'",
        "github.event.issue.number == 1830",
        "github.event.comment.author_association == 'OWNER'",
        "startsWith(github.event.comment.body, 'F139-FRESH-DEV-ADMIT ')",
        "RUNNER_NAME -cne 'FORGE-CODEX-REMOTE'",
        "python -B -m f139.nci04_fresh_original_owner_admission_cli",
        "F139_WORKER_DISPATCH_AUTHORIZED=FALSE",
        "F139_SCIENTIFIC_FIRST_USE=FALSE",
    ):
        need(source.count(owner_bound) == 1)


class FreshOwnerJobConcurrencyTests(unittest.TestCase):
    def test_real_workflow_scope(self):
        qualify(WORKFLOW.read_text(encoding="utf-8"))

    def test_unrelated_comment_must_not_claim_original_owner_group(self):
        source = WORKFLOW.read_text(encoding="utf-8")
        original = ("    concurrency:\n"
                    "      group: forge-f139-fresh-owner-admission\n"
                    "      cancel-in-progress: false\n")
        unsafe = ("concurrency:\n"
                  "  group: forge-f139-v54-original-owner\n"
                  "  cancel-in-progress: false\n")
        for mutant in (
            source.replace(original, unsafe),
            source.replace("forge-f139-fresh-owner-admission",
                           "forge-f139-v54-original-owner"),
            source.replace(original, ""),
            source.replace(original, original + original),
            source.replace("github.event.issue.number == 1830",
                           "github.event.issue.number == 807"),
            source.replace("github.actor == 'spoonman136668-ai'",
                           "github.actor == 'anyone'"),
            source.replace("RUNNER_NAME -cne 'FORGE-CODEX-REMOTE'",
                           "RUNNER_NAME -cne 'other'"),
        ):
            with self.subTest(mutant_hash=hash(mutant)):
                with self.assertRaises(ValueError):
                    qualify(mutant)


    def test_exact_owner_pr_ci_exception_is_narrow(self):
        from scripts.check_rar_g145_pr_scope import (
            FRESH_CONCURRENCY_BASE, FRESH_CONCURRENCY_BLOB,
            FRESH_CONCURRENCY_BRANCH, FRESH_CONCURRENCY_FILES,
            FRESH_CONCURRENCY_TREE, FRESH_CONCURRENCY_WORKFLOW,
            admit_fresh_admission_job_concurrency, generic_paths_safe,
        )
        head = "b" * 40
        base = FRESH_CONCURRENCY_BASE
        pr = {
            "number": 1846,
            "author_association": "OWNER",
            "user": {"login": "spoonman136668-ai"},
            "head": {"sha": head, "ref": FRESH_CONCURRENCY_BRANCH,
                     "repo": {"full_name": "spoonman136668-ai/FORGE"}},
            "base": {"sha": base, "ref": "main",
                     "repo": {"full_name": "spoonman136668-ai/FORGE"}},
        }
        files = sorted(FRESH_CONCURRENCY_FILES)
        answers = {
            ("merge-base", base, head): base,
            ("rev-parse", base + "^{tree}"): FRESH_CONCURRENCY_TREE,
            ("rev-parse", head + ":" + FRESH_CONCURRENCY_WORKFLOW):
                FRESH_CONCURRENCY_BLOB,
            ("diff", "--no-renames", "--name-only", base, head):
                "\n".join(files),
        }
        git = lambda *args: answers[args]
        self.assertFalse(generic_paths_safe(files))
        self.assertEqual(
            admit_fresh_admission_job_concurrency(head, base, pr, git),
            "EXACT_PR1846_FRESH_ADMISSION_JOB_CONCURRENCY_CI_ONLY")
        for wrong in (
            dict(pr, number=1845),
            dict(pr, user={"login": "other"}),
            dict(pr, author_association="CONTRIBUTOR"),
            dict(pr, head=dict(pr["head"], ref="other")),
            dict(pr, base=dict(pr["base"], sha="c" * 40)),
        ):
            with self.subTest(keys=repr(wrong)):
                with self.assertRaises(ValueError):
                    admit_fresh_admission_job_concurrency(head, base, wrong, git)
        for key, bad_value in (
            (("rev-parse", base + "^{tree}"), "0" * 40),
            (("rev-parse", head + ":" + FRESH_CONCURRENCY_WORKFLOW), "0" * 40),
            (("diff", "--no-renames", "--name-only", base, head),
             "\n".join(files) + "\n.github/workflows/unrelated.yml"),
        ):
            with self.subTest(key=key):
                wrong_answers = dict(answers, **{})
                wrong_answers[key] = bad_value
                with self.assertRaisesRegex(ValueError, "EXACT_SCOPE_DENIED"):
                    admit_fresh_admission_job_concurrency(
                        head, base, pr, lambda *args: wrong_answers[args])


if __name__ == "__main__":
    unittest.main()

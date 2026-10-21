"""F139-NCI04-A3 dual-HMAC admission/receipt tests (never dispatch)."""
import base64
import hashlib
import json
import unittest

from f139.nci04_native_contract import SCHEMA, digest, canonical
from f139.nci04_signed_native import (
    admit_native_intent, receipt_from_report, sign_native_intent)
from f139.nci04_native_worker import COMMANDS
from f139.verify_ticket import signature as sign_controller, Untrusted

MAIN = "a" * 40
TARGET = "b" * 40
TREE = "c" * 40
KEY = "nci04-ephemeral-integration-test-key-not-real-0123456"
SOURCE = b"package cognition\n\n// test native source boundary\n"
BODY = "d" * 64


def intent(lane="Wingless"):
    return {
        "schema": SCHEMA, "controller_source_sha": MAIN, "lane": lane,
        "target_repository": ("spoonman136668-ai/Wingless" if lane == "Wingless"
                              else "spoonman136668-ai/Yggdrasil"),
        "target_commit": TARGET, "target_tree_sha": TREE,
        "dependency_sha256": "d" * 64,
        "qualification_harness_sha256": "e" * 64,
        "training_config_sha256": "f" * 64,
        "toolchain_identity": ("go1.25.0" if lane == "Wingless" else "python3.11"),
        "suite_identity_sha256": "1" * 64,
        "path": ("cognition/native_state.go" if lane == "Wingless"
                 else "yggdrasil/native_state.py"),
        "before_sha256": digest(b""), "after_sha256": digest(SOURCE),
        "after_base64": base64.b64encode(SOURCE).decode("ascii"),
        "worker_mode": "isolated-candidate-only",
        "scientific_first_use": False, "paid_api_calls": 0,
        "accepted_ref_mutations": 0, "optimizer_policy_mutations": 0,
        "protected_holdouts_accessed": 0,
    }


def fixture(lane="Wingless"):
    body = canonical(intent(lane))
    from f139.nci04_native_contract import parse_intent
    candidate = parse_intent(body, protected_main=MAIN, target_commit=TARGET,
                             target_tree_sha=TREE)
    ticket = "f139-nci04-i689-" + MAIN[:12] + "-" + candidate.intent_sha256[:8]
    inputs = {
        "key": KEY, "ticket": ticket, "lane": lane,
        "source_sha": MAIN, "epoch": "1", "repository": "spoonman136668-ai/FORGE",
        "ref": "refs/heads/main", "event": "workflow_dispatch",
        "head_sha": MAIN, "run_attempt": "1", "run_id": "39500123999",
        "os": "windows-latest",
    }
    inputs["signature"] = sign_controller(
        KEY, inputs["ticket"], lane, MAIN, inputs["epoch"])
    sig = sign_native_intent(inputs, candidate, issue_number="689", issue_id="123456",
                             issue_body_sha256=BODY)
    return inputs, body, sig


def admit(inputs, body, sig, **overrides):
    return admit_native_intent(
        inputs, body, native_signature=sig,
        issue_number=overrides.get("issue_number", "689"),
        issue_id=overrides.get("issue_id", "123456"),
        issue_body_sha256=overrides.get("issue_body_sha256", BODY),
        authenticated_main_sha=overrides.get("authenticated_main_sha", MAIN),
        authenticated_target_commit=overrides.get("authenticated_target_commit", TARGET),
        authenticated_target_tree=overrides.get("authenticated_target_tree", TREE),
    )


def report(admission, fail=False):
    commands = []
    for i, argv in enumerate(COMMANDS[admission.lane]):
        if fail and i:
            break
        output = b"focused test failed" if fail else b"test passed"
        commands.append({
            "command": list(argv), "outcome": "TEST_FAILURE" if fail else "PASS",
            "returncode": 1 if fail else 0, "elapsed_ms": 17,
            "output_sha256": digest(output), "output_bytes": len(output),
            "excerpt": output.decode(),
        })
    c = admission.intent
    return {
        "schema": "forge.f139.nci04.native-development-diagnostic.v1",
        "intent_sha256": c.intent_sha256, "qualification_key": c.qualification_key,
        "target_commit": c.target_commit, "target_tree_sha": c.target_tree_sha,
        "candidate_file": c.path, "candidate_sha256": c.after_sha256,
        "lane": admission.lane, "qualification_complete": not fail,
        "real_code_changed_in_isolated_copy": True, "commands": commands,
        "child_peak_rss_bytes": None, "scientific_first_use": False,
        "protected_holdouts_accessed": 0, "accepted_ref_mutations": 0,
        "paid_model_calls": 0, "durable_controller_custody_verified": False,
        "unattended_controller_dispatch_verified": False,
    }


class NCI04SignedNativeTests(unittest.TestCase):
    def test_both_lanes_compose_real_F139_HMAC_with_native_signature(self):
        for lane in ("Wingless", "Yggdrasil"):
            with self.subTest(lane=lane):
                inp, body, sig = fixture(lane)
                admitted = admit(inp, body, sig)
                self.assertEqual(admitted.ticket, inp["ticket"])
                self.assertEqual(admitted.issue_number, 689)
                self.assertEqual(len(admitted.authorization_sha256), 64)
                proof = receipt_from_report(admitted, report(admitted))
                self.assertTrue(proof["native_qualified"])
                self.assertFalse(proof["controller_unattended_verified"])
                self.assertFalse(proof["local_custody_verified"])
                self.assertEqual(proof["native_intent_sha256"],
                                 admitted.intent.intent_sha256)

    def test_fails_closed_on_old_D2K_and_historical_ticket(self):
        inp, body, sig = fixture()
        for name in ("f139-d2k-i689-" + MAIN[:12] + "-" + BODY[:8],
                     "f139-d2j-wingless-" + MAIN[:12]):
            with self.subTest(name=name):
                changed = dict(inp, ticket=name)
                d2k_fields = ({"issue_number":"689", "issue_id":"123456",
                               "body_sha256":BODY, "target_package":"./planner"}
                              if name.startswith("f139-d2k-") else {})
                changed.update(d2k_fields)
                changed["signature"] = sign_controller(KEY, name, "Wingless", MAIN, "1",
                                                        **d2k_fields)
                with self.assertRaisesRegex(Untrusted, "NATIVE_TICKET_REQUIRED"):
                    admit(changed, body, sig)

    def test_requires_original_controller_HMAC(self):
        inp, body, sig = fixture()
        inp["signature"] = "0" * 64
        with self.assertRaisesRegex(Untrusted, "TICKET_SIGNATURE_REJECTED"):
            admit(inp, body, sig)

    def test_rejects_second_wrong_or_absent_signature(self):
        inp, body, sig = fixture()
        for s in ("0" * 64, "", "wrong"):
            with self.subTest(signature=s):
                with self.assertRaises(Untrusted):
                    admit(inp, body, s)

    def test_source_identity_run_retry_and_os_tamper_rejected(self):
        inp, body, sig = fixture()
        for change in ({"head_sha": "9" * 40}, {"run_attempt": "2"},
                       {"ref": "refs/heads/evil"}, {"os": "untrusted"}):
            with self.subTest(change=change):
                with self.assertRaises(Untrusted):
                    admit({**inp, **change}, body, sig)
        with self.assertRaisesRegex(ValueError, "CONTROLLER_IDENTITY_DRIFT"):
            admit(inp, body, sig, authenticated_main_sha="9" * 40)
        with self.assertRaisesRegex(ValueError, "TARGET_TREE_DRIFT"):
            admit(inp, body, sig, authenticated_target_tree="9" * 40)

    def test_issue_binding_and_no_ticket_recycling(self):
        inp, body, sig = fixture()
        for field, v in (("issue_number","690"), ("issue_id","654321"),
                         ("issue_body_sha256","e"*64)):
            with self.subTest(field=field):
                with self.assertRaises(Untrusted):
                    admit(inp, body, sig, **{field:v})
        modified = json.loads(body)
        modified["training_config_sha256"] = "9" * 64
        mutated = canonical(modified)
        with self.assertRaisesRegex(Untrusted, "NATIVE_TICKET_IDENTITY_DRIFT"):
            admit(inp, mutated, sig)

    def test_negative_result_retained_but_not_promoted(self):
        inp, body, sig = fixture()
        admitted = admit(inp, body, sig)
        negative = receipt_from_report(admitted, report(admitted, True))
        self.assertFalse(negative["native_qualified"])
        self.assertFalse(negative["scientific_first_use_authorized"])
        self.assertFalse(negative["local_custody_verified"])

    def test_no_false_success_or_arbitrary_commands(self):
        inp, body, sig = fixture()
        admitted = admit(inp, body, sig)
        r = report(admitted, True)
        r["qualification_complete"] = True
        with self.assertRaisesRegex(Untrusted, "FALSE_QUALIFICATION_CLAIM"):
            receipt_from_report(admitted, r)
        r = report(admitted)
        r["commands"][0]["command"] = ["sh", "-c", "do anything"]
        with self.assertRaisesRegex(Untrusted, "COMMAND_EVIDENCE_INVALID"):
            receipt_from_report(admitted, r)
        r = report(admitted)
        r["scientific_first_use"] = True
        with self.assertRaisesRegex(Untrusted, "REPORT_AUTHORITY_OR_SOURCE_INVALID"):
            receipt_from_report(admitted, r)
        r = report(admitted)
        r["durable_controller_custody_verified"] = True
        with self.assertRaisesRegex(Untrusted, "REPORT_AUTHORITY_OR_SOURCE_INVALID"):
            receipt_from_report(admitted, r)

    def test_receipt_binding_rejects_wrong_candidate(self):
        inp, body, sig = fixture()
        admitted = admit(inp, body, sig)
        for name, new in (("candidate_sha256", "1"*64),
                          ("qualification_key", "2"*64),
                          ("target_commit", "3"*40)):
            with self.subTest(field=name):
                r = report(admitted)
                r[name] = new
                with self.assertRaisesRegex(Untrusted, "REPORT_AUTHORITY_OR_SOURCE_INVALID"):
                    receipt_from_report(admitted, r)


    def test_authenticated_intent_reaches_isolated_native_worker_and_receipt(self):
        """One in-process credential-ephemeral qualification, NOT live dispatch."""
        import subprocess
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from f139.nci04_native_contract import parse_intent
        from f139.nci04_native_worker import stage_candidate, verify_fixed_commands
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source"
            source.mkdir()
            (source / "cognition").mkdir()
            def git(*args):
                p = subprocess.run(["git", "-C", str(source), *args],
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   timeout=15, check=True)
                return p.stdout.decode().strip()
            git("init", "-q")
            git("config", "user.name", "nci04-test")
            git("config", "user.email", "nci04@example.invalid")
            (source / "cognition" / "base.go").write_bytes(b"package cognition\n")
            git("add", ".")
            git("commit", "-qm", "sealed source fixture")
            commit, tree = git("rev-parse", "HEAD"), git("rev-parse", "HEAD^{tree}")
            blob = canonical({**intent(), "target_commit": commit, "target_tree_sha": tree})
            candidate = parse_intent(blob, protected_main=MAIN,
                                     target_commit=commit, target_tree_sha=tree)
            ticket = "f139-nci04-i689-" + MAIN[:12] + "-" + candidate.intent_sha256[:8]
            inp = {
                "key": KEY, "ticket": ticket, "lane": "Wingless",
                "source_sha": MAIN, "epoch": "1",
                "repository": "spoonman136668-ai/FORGE",
                "ref": "refs/heads/main", "event": "workflow_dispatch",
                "head_sha": MAIN, "run_attempt": "1", "run_id": "39500123999",
                "os": "ubuntu-latest",
            }
            inp["signature"] = sign_controller(KEY, ticket, "Wingless", MAIN, "1")
            sig = sign_native_intent(inp, candidate, issue_number="689",
                                     issue_id="123456", issue_body_sha256=BODY)
            accepted = admit_native_intent(
                inp, blob, native_signature=sig, issue_number="689",
                issue_id="123456", issue_body_sha256=BODY,
                authenticated_main_sha=MAIN, authenticated_target_commit=commit,
                authenticated_target_tree=tree)
            sandbox = root / "sandbox"
            sandbox.mkdir()
            staged = stage_candidate(accepted.intent, source, sandbox)
            newfile = staged / "checkout" / "cognition" / "native_state.go"
            self.assertEqual(newfile.read_bytes(), SOURCE)
            self.assertFalse((source / "cognition" / "native_state.go").exists())
            calls = []
            def mock_native_test(argv, **kwargs):
                calls.append(tuple(argv))
                self.assertNotIn("F139_WORKER_HMAC_KEY", kwargs["env"])
                return subprocess.CompletedProcess(argv, 0, b"qualified\n")
            proof = verify_fixed_commands(accepted.intent, staged, runner=mock_native_test)
            self.assertEqual(calls, list(COMMANDS["Wingless"]))
            self.assertTrue(proof["qualification_complete"])
            receipt = receipt_from_report(accepted, proof)
            self.assertEqual(receipt["native_authorization_sha256"],
                             accepted.authorization_sha256)
            self.assertTrue(receipt["native_qualified"])
            self.assertFalse(receipt["controller_unattended_verified"])
            self.assertEqual(git("status", "--porcelain"), "")


if __name__ == "__main__":
    unittest.main()

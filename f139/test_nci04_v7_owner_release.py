"""G39: one-source, no-science original V7 approval negatives.

Deliberately no original-owner DB writes and no repeated full-suite test.
"""
import unittest
from f139.nci04_v7_owner_release import (
    OLD,SCHEMA,FIELDS,V7OwnerDenied,validate_v7_original_owner,
    original_owner_database_source,
)
from f139.local_controller import Database


class G39OriginalReleaseTests(unittest.TestCase):
    def test_actual_python_module_entrypoint_class_is_owner_source(self):
        from f139.local_controller import Database
        import runpy
        self.assertTrue(original_owner_database_source(object.__new__(Database)))
        # Re-execute the SAME source as a second module, modeling -m's
        # __main__.Database identity without invoking the live CLI.
        alt = runpy.run_module(
            "f139.local_controller", run_name="__f139_g41_alias__")
        duplicate = alt["Database"]
        self.assertIsNot(duplicate, Database)
        self.assertTrue(original_owner_database_source(
            object.__new__(duplicate)))
        self.assertFalse(original_owner_database_source(object()))

    def test_old_protected_source_is_frozen(self):
        self.assertEqual(OLD,"b2079282fed03df2203807de09b4f3e82bdfe05a")
        self.assertIn("v6_terminal_event_sha256",FIELDS)
        self.assertIn("original_quarantined_tickets_sha256",FIELDS)

    def test_never_accept_missing_or_forged_original_database(self):
        with self.assertRaises(V7OwnerDenied):
            validate_v7_original_owner(None,{})
        with self.assertRaises(V7OwnerDenied):
            validate_v7_original_owner(None,dict.fromkeys(FIELDS))

    def test_v7_cannot_authorize_science_or_unattested_dispatch(self):
        from pathlib import Path
        source=Path(__file__).resolve().parent/"nci04_v7_owner_release.py"
        raw=source.read_text()
        self.assertIn('approval.get("v2_production_dispatch_authorized") is False',raw)
        self.assertIn('approval.get("scientific_first_use") is False',raw)
        self.assertIn('approval.get("new_controller") is False',raw)
        self.assertIn('approval["paid_api_calls"] == 0',raw)

    def test_v7_requires_separate_manual_owner_cli(self):
        import inspect
        from f139.local_controller import cli
        s=inspect.getsource(cli)
        self.assertIn('transition-qualified-native-v7',s)
        self.assertIn('allow_certified_negative=True,allow_v7=True',s)
        self.assertIn('SingleOwner(args.db.with_suffix(".lock"))',s)


if __name__=="__main__":
    unittest.main()

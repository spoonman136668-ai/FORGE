"""Synthetic source-free positive and adversarial checks; never execute a model."""
from __future__ import annotations
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

from nativeevidence import component_checkpoint_artifact as c

SOURCE = "a" * 40

def archive(path, items):
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        for name, data in items.items():
            z.writestr(name, data)
    return path

def wing_fixture():
    before, after = b"fixture-prefix-v1", b"fixture-learned-v2"
    e = {
        "schema": c.WING, "project": "Wingless", "source_commit_sha": SOURCE,
        "independent_process_continuation": True, "source_free_generated_fixture": True,
        "stale_checkpoint_rejected": True, "scientific_accepted": False,
        "promotion_authority": False,
        "accepted_model_or_portable_state_former": False,
        "independent_source_first_use": False,
        "matched_baseline_superiority": "UNVERIFIED", "unfamiliar_transfer": "UNVERIFIED",
        "learned_observations": 2, "source_probe_sha256": "b" * 64,
        "prefix_checkpoint_sha256": c.sha(before),
        "uninterrupted_checkpoint_sha256": c.sha(after),
        "continued_checkpoint_sha256": c.sha(after),
    }
    return {"evidence.json": c.canonical(e), "prefix.snapshot": before,
            "full/final.snapshot": after, "resumed/final.snapshot": after,
            "full/go.mod": b"module wingless.nci04g5.privateprobe\\n\\ngo 1.20\\n",
            "resumed/go.mod": b"module wingless.nci04g5.privateprobe\\n\\ngo 1.20\\n",
            "full/probe.go": b"package fixture", "resumed/probe.go": b"package fixture"}

def make_journal(episode, checkpoint_sha):
    events = [
        {"kind": "header", "schema": c.JOURNAL, "source_sha256": c.FIXTURE,
         "episode": f"ep-{episode:06d}", "max_steps": 2,
         "role": "OWNER_PUBLIC_FIT_DEVELOPMENT_ONLY"},
        {"kind": "reset_intent"},
        {"kind": "reset_result", "observation": "docked_MRV"},
        {"kind": "step_intent", "action": "Backup", "index": 0},
        {"kind": "step_result", "observation": "Nothing", "reward": 0,
         "terminal": False, "truncated": False},
        {"kind": "step_intent", "action": "Backup", "index": 1},
        {"kind": "step_result", "observation": "Nothing", "reward": 0,
         "terminal": False, "truncated": True},
        {"kind": "checkpoint_intent", "sha256": checkpoint_sha},
        {"kind": "checkpoint_result", "sha256": checkpoint_sha}
    ]
    previous = "0" * 64
    lines = []
    for n, event in enumerate(events):
        record = {"seq": n, "prev": previous, "event": event}
        h = c.sha(c.canonical(record))
        lines.append(c.canonical(dict(record, digest=h)))
        previous = h
    return b"\n".join(lines) + b"\n", previous

def ygg_fixture():
    files, rows = {}, []
    for n in range(1, 4):
        body = {"schema": c.NATIVE, "transitions": 2*n, "observation": None,
                "frozen_native_sha256": None, "weights": [n, 2*n]}
        checkpoint = c.canonical({"body": body, "sha256": c.sha(c.canonical(body))})
        journal, head = make_journal(n, c.sha(checkpoint))
        path = f"cohort/episode-{n:06d}/"
        files[path + "learned-checkpoint.bin"] = checkpoint
        files[path + "public-events.jsonl"] = journal
        rows.append({"episode": n, "steps": 2,
                     "checkpoint_bytes": len(checkpoint),
                     "checkpoint_sha256": c.sha(checkpoint),
                     "journal_sha256": c.sha(journal), "journal_head": head,
                     "native_model_identities": {"native": str(n)*64,
                                                 "memory": "b"*64}})
    p = {"schema": c.PREFIX, "source_commit_sha": SOURCE,
         "project": "Yggdrasil", "source_free_fixture_sha256": c.FIXTURE,
         "scientific_first_use": False, "promotion_authority": False,
         "checkpoints": rows[:2],
         "native_model_identities": rows[1]["native_model_identities"]}
    e = {"schema": c.YGG, "source_commit_sha": SOURCE,
         "project": "Yggdrasil", "source_free_fixture_sha256": c.FIXTURE,
         "source_authentication": "SELF_DECLARED_FIXTURE_ONLY",
         "independent_process_continuation": True,
         "previous_episodes_skipped_without_replay": 2,
         "native_source_selected_actions": 6,
         "actual_original_world_executed": False,
         "scientific_first_use": False, "scientific_accepted": False,
         "successor_authority": False, "promotion_authority": False,
         "portable_16_slot_accepted_model": False,
         "retention_vs_fresh_control": "UNVERIFIED",
         "unfamiliar_transfer": "UNVERIFIED",
         "parent_checkpoint_sha256": rows[1]["checkpoint_sha256"],
         "child_checkpoint_sha256": rows[2]["checkpoint_sha256"],
         "checkpoint_history": rows,
         "native_model_identities": rows[2]["native_model_identities"]}
    cohort = {"schema": c.COHORT, "episodes": 3, "max_steps": 2,
              "protected_first_use": False,
              "role": "OWNER_PUBLIC_FIT_DEVELOPMENT_ONLY",
              "source_sha256": c.FIXTURE}
    files.update({"evidence.json": c.canonical(e),
                  "prefix-evidence.json": c.canonical(p),
                  "cohort/cohort.json": c.canonical(cohort)})
    return files

class ComponentArchiveTests(unittest.TestCase):
    def verify(self, files, project, source=SOURCE):
        with tempfile.TemporaryDirectory() as td:
            return c.inspect(archive(Path(td)/"fixture.zip", files),
                             project=project, source_sha=source)

    def rejected(self, files, project, reason):
        with self.assertRaises(c.Rejected) as out:
            self.verify(files, project)
        self.assertIn(reason, str(out.exception))

    def test_supported_sourcefree_shapes_never_promote(self):
        for project, creator in (("Wingless", wing_fixture),
                                 ("Yggdrasil", ygg_fixture)):
            with self.subTest(project=project):
                report = self.verify(creator(), project)
                self.assertEqual(report["internal_archive_integrity"], "PASS")
                self.assertEqual(report["learning_gain"], "UNVERIFIED")
                self.assertFalse(report["optimizer_reward"])
                self.assertFalse(report["model_promotion"])
                self.assertFalse(report["portable_model_accepted"])

    def test_wrong_source_pin_and_project_rejected(self):
        for source in ("f"*40, "bad", ""):
            with self.subTest(source=source), self.assertRaises(c.Rejected):
                self.verify(wing_fixture(), "Wingless", source=source)
        with self.assertRaises(c.Rejected):
            self.verify(wing_fixture(), "Yggdrasil")

    def test_wing_corrupt_raw_checkpoint_and_authority(self):
        f = wing_fixture()
        f["resumed/final.snapshot"] += b"tamper"
        self.rejected(f, "Wingless", "WING_CHECKPOINT_HASH")
        f = wing_fixture()
        d = c.decode(f["evidence.json"])
        d["promotion_authority"] = True
        f["evidence.json"] = c.canonical(d)
        self.rejected(f, "Wingless", "WING_RECEIPT")
        f = wing_fixture()
        d = c.decode(f["evidence.json"])
        d["matched_baseline_superiority"] = "PASS"
        f["evidence.json"] = c.canonical(d)
        self.rejected(f, "Wingless", "WING_RECEIPT")

    def test_wing_substituted_probe_and_module_rejected(self):
        for name in ("full/probe.go", "resumed/probe.go",
                     "full/go.mod", "resumed/go.mod"):
            with self.subTest(path=name):
                f = wing_fixture()
                f[name] += b"tampered"
                self.rejected(f, "Wingless",
                              "WING_PROBE_HASH" if name.endswith("probe.go")
                              else "WING_MODULE_SOURCE")
        f = wing_fixture()
        f["resumed/probe.go"] = f["full/probe.go"] + b"changed"
        d = c.decode(f["evidence.json"])
        d["source_probe_sha256"] = c.sha(f["full/probe.go"])
        f["evidence.json"] = c.canonical(d)
        self.rejected(f, "Wingless", "WING_PROBE_HASH")

    def test_ygg_corrupt_checkpoint_journal_and_lineage(self):
        f = ygg_fixture()
        f["cohort/episode-000002/learned-checkpoint.bin"] += b"tamper"
        self.rejected(f, "Yggdrasil", "YGG_CONTENT_HASH")
        f = ygg_fixture()
        path = "cohort/episode-000002/public-events.jsonl"
        f[path] = f[path].replace(b"Backup", b"Move", 1)
        self.rejected(f, "Yggdrasil", "YGG_CONTENT_HASH")
        f = ygg_fixture()
        d = c.decode(f["evidence.json"])
        d["child_checkpoint_sha256"] = "f"*64
        f["evidence.json"] = c.canonical(d)
        self.rejected(f, "Yggdrasil", "YGG_PARENT_CHILD_IDENTITY")
        f = ygg_fixture()
        d = c.decode(f["evidence.json"])
        d["scientific_accepted"] = True
        f["evidence.json"] = c.canonical(d)
        self.rejected(f, "Yggdrasil", "YGG_RECEIPT")

    def test_zip_duplicates_missing_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td)/"x.zip"
            f = wing_fixture()
            del f["prefix.snapshot"]
            archive(path, f)
            with self.assertRaises(c.Rejected):
                c.inspect(path, project="Wingless", source_sha=SOURCE)
            with zipfile.ZipFile(path, "w") as z:
                for name, payload in wing_fixture().items():
                    z.writestr(name, payload)
                z.writestr("evidence.json", b"{}")
            with self.assertRaises(c.Rejected):
                c.inspect(path, project="Wingless", source_sha=SOURCE)
            with zipfile.ZipFile(path, "w") as z:
                for name, payload in wing_fixture().items():
                    info = zipfile.ZipInfo(name)
                    if name == "prefix.snapshot":
                        info.create_system = 3
                        info.external_attr = 0o120777 << 16
                    z.writestr(info, payload)
            with self.assertRaises(c.Rejected):
                c.inspect(path, project="Wingless", source_sha=SOURCE)

    def test_duplicate_json_fields_and_nonfinite_rejected(self):
        f = wing_fixture()
        f["evidence.json"] = b'{"schema":"a","schema":"b"}'
        self.rejected(f, "Wingless", "DUPLICATE_JSON_KEY")
        f = wing_fixture()
        f["evidence.json"] = b'{"x":NaN}'
        self.rejected(f, "Wingless", "NONFINITE_JSON")

if __name__ == "__main__":
    unittest.main()

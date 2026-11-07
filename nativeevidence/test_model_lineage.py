"""Source-free, offline model-lineage integrity and falsification tests."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from nativeevidence import model_lineage as m

def fixture(root, project, name, *, parent=None, changed=True):
    root = Path(root)
    files = {
        "model/weights.bin": b"learned-v2" if changed else b"learned-v1",
        "state/resume.json": b'{"step":2}',
        "replay/input.json": b'{"input":1}',
        "replay/output.json": b'{"output":1}',
    }
    records = []
    for path, raw in files.items():
        dst = root / "files" / path
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(raw)
        role = ("learned_parameters" if path.startswith("model/") else
                "resumable_state" if path.startswith("state/") else
                "replay_input" if path == "replay/input.json" else "replay_output")
        records.append(dict(path=path, role=role, size_bytes=len(raw), sha256=m.sha256(raw)))
    by_path = {r["path"]: r for r in records}
    if project == "Wingless":
        interface = dict(signature="state_former(raw_input, history) -> fixed_size_state",
                         fixed_state_dimension=8, fixed_readout_capacity=4,
                         capacity_growth=False)
    else:
        interface = dict(signature="cognition_consumer(retained_state, local_state) -> decision_state",
                         total_slots=16, active_slots=7, retained_slots=9,
                         hidden_persistent_memory_growth=False, addressing_change=False,
                         capacity_growth=False)
    payload = dict(schema=m.SCHEMA, project=project, mechanism_id="synthetic-control",
                   qualification_identity=dict(source_commit_sha="a"*40,
                        source_tree_sha="b"*40, source_schema_sha256="c"*64,
                        qualification_contract_sha256="d"*64, toolchain_id="python3.12"),
                   lineage=dict(experiment_id=name, parent_checkpoint_sha256=parent),
                   interface=interface,
                   resource_envelope=dict(comparison="equal-or-lower-than-baseline",
                        baseline_id="synthetic-control", max_parameters=128,
                        max_context_bytes=256, max_model_calls=0),
                   files=records,
                   replay=dict(vectors=[dict(id="test",input_path="replay/input.json",
                        output_path="replay/output.json",
                        input_sha256=by_path["replay/input.json"]["sha256"],
                        output_sha256=by_path["replay/output.json"]["sha256"])],
                        runtime_replay_required_before_promotion=True),
                   portability=dict(retraining_required=False, restore_supported=True,
                        requalification_required_before_promotion=True),
                   authority=dict(m.NO_AUTHORITY),scientific_classification=None)
    payload["checkpoint_content_sha256"] = m.sha256(m.canonical(payload))
    (root / "manifest.json").write_text(json.dumps(payload,sort_keys=True),encoding="utf8")
    return payload

def rewrite(root, update):
    path=Path(root)/"manifest.json"
    data=json.loads(path.read_text())
    update(data)
    data.pop("checkpoint_content_sha256",None)
    data["checkpoint_content_sha256"]=m.sha256(m.canonical(data))
    path.write_text(json.dumps(data,sort_keys=True))
    return data

class ModelLineageTests(unittest.TestCase):
    def test_two_projects_verify_bytes_but_never_claim_learning(self):
        for project in ("Wingless","Yggdrasil"):
            with self.subTest(project=project),tempfile.TemporaryDirectory() as td:
                a=Path(td)/"a";b=Path(td)/"b"
                x=fixture(a,project,"generation-one",changed=False)
                y=fixture(b,project,"generation-two",
                          parent=x["checkpoint_content_sha256"])
                out=m.compare(a,b,parent_pin=x["checkpoint_content_sha256"],
                              child_pin=y["checkpoint_content_sha256"])
                self.assertEqual(out["artifact_integrity"],"PASS")
                self.assertTrue(out["parameters_changed"])
                self.assertEqual(out["continued_training"],"UNVERIFIED")
                self.assertEqual(out["independent_cold_process_restore"],"UNVERIFIED")
                self.assertEqual(out["matched_control_improvement"],"UNVERIFIED")
                self.assertFalse(out["optimizer_update_authorized"])
    def test_wrong_parent_and_project_swaps_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            a=Path(td)/"a";b=Path(td)/"b"
            x=fixture(a,"Wingless","one",changed=False)
            y=fixture(b,"Yggdrasil","two",parent=x["checkpoint_content_sha256"])
            with self.assertRaises(m.Rejected):
                m.compare(a,b,parent_pin=x["checkpoint_content_sha256"],
                          child_pin=y["checkpoint_content_sha256"])
            y=rewrite(b,lambda p:p["lineage"].update(parent_checkpoint_sha256="0"*64))
            with self.assertRaises(m.Rejected):
                m.compare(a,b,parent_pin=x["checkpoint_content_sha256"],
                          child_pin=y["checkpoint_content_sha256"])
    def test_tampering_manifest_and_bytes_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            a=Path(td)/"a";b=Path(td)/"b"
            x=fixture(a,"Yggdrasil","one",changed=False)
            y=fixture(b,"Yggdrasil","two",parent=x["checkpoint_content_sha256"])
            (b/"files/model/weights.bin").write_bytes(b"malicious")
            with self.assertRaises(m.Rejected):
                m.compare(a,b,parent_pin=x["checkpoint_content_sha256"],
                          child_pin=y["checkpoint_content_sha256"])
            (b/"files/model/weights.bin").write_bytes(b"learned-v2")
            (b/"manifest.json").write_text((b/"manifest.json").read_text().replace(
                '"scientific_classification": null', '"scientific_classification": "PASS"'))
            with self.assertRaises(m.Rejected):
                m.compare(a,b,parent_pin=x["checkpoint_content_sha256"],
                          child_pin=y["checkpoint_content_sha256"])
    def test_spoofed_authority_invalid_interface_and_changed_pin_rejected(self):
        for fault in ("authority","interface","source","pin"):
            with self.subTest(fault=fault),tempfile.TemporaryDirectory() as td:
                a=Path(td)/"a";b=Path(td)/"b"
                x=fixture(a,"Yggdrasil","one",changed=False)
                y=fixture(b,"Yggdrasil","two",parent=x["checkpoint_content_sha256"])
                if fault=="authority":
                    y=rewrite(b,lambda p:p["authority"].update(promotion_authority=True))
                elif fault=="interface":
                    y=rewrite(b,lambda p:p["interface"].update(total_slots=17))
                elif fault=="source":
                    y=rewrite(b,lambda p:p["qualification_identity"].update(source_commit_sha="z"*40))
                with self.assertRaises(m.Rejected):
                    m.compare(a,b,parent_pin=x["checkpoint_content_sha256"],
                              child_pin="f"*64 if fault=="pin" else y["checkpoint_content_sha256"])
    def test_duplicate_keys_and_directory_traversal_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            a=Path(td)/"a"
            fixture(a,"Wingless","one",changed=False)
            doc=(a/"manifest.json")
            doc.write_text('{"schema":"x","schema":"y"}')
            with self.assertRaises(m.Rejected):m._read_manifest(a)
            fixture(a,"Wingless","one",changed=False)
            rewrite(a,lambda p:p["files"][0].update(path="../escape"))
            with self.assertRaises(m.Rejected):m._read_manifest(a)

if __name__=="__main__":
    unittest.main()

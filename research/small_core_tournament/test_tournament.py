from collections import Counter
from dataclasses import replace
from pathlib import Path
import random
import subprocess
import sys

import pytest
import torch

import tournament as t

CPU = torch.device("cpu")
TINY = t.Profile(16, 32, 12, 4, 6, 3)


def setup_module():
    torch.set_num_threads(1)
    t.set_seed(42)


def oracle(rows):
    query, *records = rows
    key, encoded_depth, _, task = query
    records = {record[0]: record for record in records}
    if task == t.GRAPH:
        depth = next(hops for hops, token in t.DEPTH_TOKEN.items() if token == encoded_depth)
        for _ in range(depth):
            key = records[key][1]
        return key

    def reduce(entity):
        _, parent, raw, op = records[entity]
        value = raw - t.ENTITIES
        if op == t.BASE:
            return value
        prev = reduce(parent)
        return {t.ADD: prev + value, t.SUB: prev - value, t.MUL: prev * value}[op] % t.MODULUS

    return t.ENTITIES + reduce(key)


@pytest.mark.parametrize("task", [t.GRAPH, t.ARITH])
def test_ood_depth_substitution_and_split_integrity(task):
    rng = random.Random(542)
    split_signatures = []
    for stage in (1, 2, 3):
        for split, depth in (("train", None), ("search", None), ("eval", 8), ("eval", 12)):
            raw, gold, swapped, swapped_gold, permutations, signatures = t.draw(
                rng, stage, split, depth, 32, task, CPU
            )
            split_signatures.append(((stage, split), set(signatures)))
            assert [oracle(rows) for rows in raw.tolist()] == gold.tolist()
            assert [oracle(rows) for rows in swapped.tolist()] == swapped_gold.tolist()
            seen_depth = set(raw[:, 0, 1].tolist())
            assert seen_depth <= {t.DEPTH_TOKEN[d] for d in ((2, 3, 4) if depth is None else (depth,))}
            for i, permutation in enumerate(permutations):
                assert all(index != renamed for index, renamed in enumerate(permutation))
                restored, restored_gold = t.apply_permutation(
                    swapped[i], swapped_gold[i], torch.tensor(permutation).argsort()
                )
                assert torch.equal(raw[i], restored)
                assert torch.equal(gold[i], restored_gold)
    for owner, partition in split_signatures:
        for other, competing in split_signatures:
            if owner != other:
                assert not partition & competing


def test_depth_encoding_uses_one_trained_marker_for_all_hop_counts():
    depths = (*t.TRAIN_DEPTHS, *t.OOD_DEPTHS)
    rows = torch.full((len(depths), t.ROWS, 4), t.PAD)
    rows[:, 0, 1] = torch.tensor([t.DEPTH_TOKEN[hops] for hops in depths])
    model = t.Model(TINY, "dense")
    expected = model.embedding(rows.clamp(max=t.DEPTH)).detach().clone()
    expected[:, 0, 1, 0] += torch.tensor(depths) / max(t.TRAIN_DEPTHS)
    torch.testing.assert_close(model.embed_rows(rows), expected.flatten(-2), rtol=0, atol=0)


@pytest.mark.parametrize("profile", [t.CPU, t.GPU])
def test_exact_train_and_inference_parameter_parity(profile):
    baseline = t.Model(profile, "dense")
    assert baseline.counts() == (baseline.target, baseline.target)
    assert (250_000 if profile == t.CPU else 5_000_000) <= baseline.target
    assert baseline.target <= (500_000 if profile == t.CPU else 25_000_000)
    combinations = [f"{left}+{right}" for left in t.OPTIMIZATION for right in t.ANTI_MEMORIZATION]
    for method in (*t.METHODS, *combinations):
        model = t.Model(profile, method)
        peak, active = model.counts()
        assert active == baseline.target, method
        assert peak - active == (2 * profile.width**2 if "scaffold" in method else 0), method


def test_same_seed_matches_stream_and_dense_training():
    first = t.build_data(TINY, 1729, 1, CPU)
    again = t.build_data(TINY, 1729, 1, CPU)
    different = t.build_data(TINY, 1730, 1, CPU)
    assert first[3] == again[3] != different[3]
    assert torch.equal(first[0][0], again[0][0])
    budget = t.common_budget(TINY, t.METHODS)
    runs = [t.run_arm(TINY, "dense", 1729, CPU, datasets, budget, 1) for datasets in (first, again)]
    for result in runs:
        for field in ("train_seconds", "evaluation_seconds", "training_host_cpu_seconds"):
            result.pop(field)
    assert runs[0] == runs[1]


def test_scaffold_fades_and_core_matches_same_seed_baseline():
    t.set_seed(73)
    dense = t.Model(TINY, "dense")
    t.set_seed(73)
    model = t.Model(TINY, "scaffold")
    for name, parameter in dense.named_parameters():
        assert torch.equal(parameter, dict(model.named_parameters())[name]), name
    rows = t.build_data(TINY, 7, 1, CPU)[0][0][0]
    torch.testing.assert_close(dense(rows)[0], model(rows, step_fraction=1.0)[0])
    assert not torch.allclose(dense(rows)[0], model(rows, step_fraction=0.0)[0])
    model.eval()
    torch.testing.assert_close(dense(rows)[0], model(rows, step_fraction=0.0)[0])
    assert t.fraction_at(8, 12) < 1 == t.fraction_at(9, 12)


def test_adaptive_halting_uses_shared_blocks_and_changes_sweeps():
    rows = t.build_data(TINY, 7, 1, CPU)[0][0][0]
    model = t.Model(TINY, "loops").eval()
    with torch.no_grad():
        model.halt.bias.fill_(10)
        assert model(rows)[2].item() == 1
        model.halt.bias.fill_(-10)
        assert model(rows)[2].item() == 3
    model.train()
    model.halt.bias.data.zero_()
    logits, _, sweeps = model(rows)
    (logits[logits.isfinite()].square().mean() + 0.01 * sweeps).backward()
    assert model.halt.weight.grad.abs().sum().item() > 0
    assert len(model.blocks) == 2


def test_spectral_basis_is_orthogonal():
    block = t.Model(TINY, "spectral").blocks[0]
    torch.testing.assert_close(block.basis @ block.basis.T, torch.eye(TINY.width))
    shifts = [block.basis.roll(i * TINY.width // 4, -1) @ block.basis.T for i in range(4)]
    gram = torch.stack([operator.flatten() for operator in shifts])
    torch.testing.assert_close(gram @ gram.T, TINY.width * torch.eye(4), atol=2e-6, rtol=1e-5)


def test_pointer_reads_context_without_persistent_fact_state():
    rows = t.build_data(TINY, 7, 1, CPU)[0][0][0]
    model = t.Model(TINY, "pointer").eval()
    changed = rows.clone()
    changed[:, 1:, 1] = t.PAD
    assert not torch.allclose(model(rows)[0], model(changed)[0])
    assert model.scratch_key is not None
    assert all(isinstance(block, t.PointerBlock) and not block.values.nonlinear for block in model.blocks)


def test_all_eight_arms_smoke_and_share_budgets():
    receipt = t.make_receipt(1, TINY, t.METHODS, (1729,), CPU)
    runs = receipt["runs"]
    assert len(runs) == 8
    assert len({run["inference_parameters"] for run in runs}) == 1
    assert len({run["training_contraction_flops_cap"] for run in runs}) == 1
    for run in runs:
        assert run["failure_mode"] is None
        assert run["steps"] == TINY.steps
        assert run["training_examples"] == TINY.batch * TINY.steps
        assert 0 < run["charged_training_contraction_flops"] <= run["training_contraction_flops_cap"]
        assert len(run["buckets"]) == 6
    population = runs[-1]["population_search"]
    assert Counter(member["generation"] for member in population) == {0: 3, 1: 3}
    assert runs[-1]["winning_topology_seed"] in {member["topology_seed"] for member in population}


@pytest.mark.parametrize("method", ["scaffold+scramble", "loops+pointer", "evolution+pointer", "spectral+stability"])
def test_synthesis_arms_smoke(method):
    data = t.build_data(TINY, 19, 3, CPU)
    budget = t.common_budget(TINY, ("dense", method))
    result = t.run_arm(TINY, method, 19, CPU, data, budget, 3)
    assert result["failure_mode"] is None
    assert result["steps"] == TINY.steps
    assert len(result["buckets"]) == 12


def test_round_two_prunes_half_and_measures_distractors():
    profile = replace(TINY, steps=8)
    datasets = t.build_data(profile, 23, 2, CPU)
    run = t.run_arm(profile, "scaffold", 23, CPU, datasets, t.common_budget(profile, ("scaffold",)), 2)
    assert run["pruned_parameters"] == run["random_pruned_parameters"] == run["inference_parameters"] // 2
    for key in ("summary", "pruned_summary", "random_pruned_summary"):
        assert 0 <= run[key]["noisy_ood"] <= 1


def score(method, ood, drop, *, seconds=1.0, seed=1729):
    return {"method": method, "seed": seed, "train_seconds": seconds, "failure_mode": None,
            "summary": {"id": 0.50, "ood": ood, "drop": drop}}


def test_hard_gate_handles_ties_overhead_and_missing_synthesis_family():
    runs = [score("dense", 0.40, 0.10), score("scaffold", 0.40, 0.02),
            score("scramble", 0.60, 0.10), score("spectral", 0.60, 0.02, seconds=2.1),
            score("loops", 0.55, 0.01), score("pointer", 0.65, 0.01)]
    decisions, finalists = t.classify(runs, [row["method"] for row in runs], 1)
    assert decisions["scaffold"]["verdict"] == decisions["scramble"]["verdict"] == "ELIMINATED"
    assert "proportional" in decisions["spectral"]["reasons"][0]
    assert finalists == ["loops", "pointer"]
    assert t.synthesis_arms(finalists) == ("dense", "loops", "pointer", "loops+pointer")
    assert not t.synthesis_arms(["scaffold", "loops"])


def test_synthesis_requires_gain_over_each_single_arm():
    methods = ("dense", "loops", "pointer", "loops+pointer")
    runs = [score(method, ood, drop, seed=seed)
            for seed in t.GPU_SEEDS
            for method, ood, drop in zip(methods, (0.3, 0.4, 0.5, 0.6), (0.2, 0.15, 0.10, 0.05))]
    assert t.synthesis_comparison(runs, methods)["beats_all_comparators"]
    runs[-1]["summary"]["ood"] = 0.49
    assert not t.synthesis_comparison(runs, methods)["beats_all_comparators"]


def test_receipt_rejects_drift_and_never_overwrites(tmp_path):
    rows = [score(method, 0.4, 0.10) for method in t.METHODS]
    decisions, finalists = t.classify(rows, t.METHODS, 1)
    receipt = {
        "schema": t.SCHEMA, "round": 1, "configuration": t.asdict(t.CPU), "source": t.source_info(),
        "methods": list(t.METHODS), "seeds": [1729], "runs": rows, "decisions": decisions,
        "finalists": finalists,
    }
    path = tmp_path / "receipt.json.gz"
    t.save_receipt(path, {**receipt, "receipt_sha256": t.digest(receipt)})
    assert t.read_previous(path, 1)["finalists"] == []
    with pytest.raises(FileExistsError):
        t.save_receipt(path, {})
    with pytest.raises(ValueError, match="round mismatch"):
        t.read_previous(path, 2)
    receipt["source"]["script_sha256"] = "0" * 64
    drift = tmp_path / "drift.json"
    t.save_receipt(drift, {**receipt, "receipt_sha256": t.digest(receipt)})
    with pytest.raises(ValueError, match="source"):
        t.read_previous(drift, 1)


def test_cli_gpu_round_requires_owner_reference_and_input(tmp_path):
    target = tmp_path / "no-receipt.json"
    result = subprocess.run(
        [sys.executable, str(Path(t.__file__)), "--round", "2", "--output", str(target)],
        check=False, capture_output=True, text=True,
    )
    assert result.returncode == 2
    assert "owner review reference" in result.stderr
    assert not target.exists()

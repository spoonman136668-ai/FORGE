"""F124-DK-2 source-neutral trainable compositional binding prototype.

Experimental engineering only, not original scientific first-use. Both arms
consume identical public FIT trajectories and the same Adam update budget.
No source law, prospective sources, CHECK, or HELDOUT are imported by learners.
"""
from __future__ import annotations
import hashlib
import json
from typing import Any

import torch
from torch import nn

ROLES = ("alpha", "beta", "gamma")
STEPS = 8
FIT = 24
TRAIN_FIT = 20
FEATURES = 20
PARAMETERS = 180
UPDATES = 240
SEED = 3117
LEARNING_RATE = 0.027


def digest(item: Any) -> str:
    return hashlib.sha256(json.dumps(item, sort_keys=True,
                          separators=(",", ":")).encode()).hexdigest()


def encode(v: tuple[int, ...]) -> list[float]:
    if len(v) != 5 or any(type(x) is not int or not 0 <= x < 16 for x in v):
        raise ValueError("PUBLIC_FIVE_NIBBLE_INPUT")
    return [1.0 if x & (1 << bit) else -1.0 for x in v for bit in range(4)]


def fit_rows(episodes: list[dict]) -> tuple[torch.Tensor, torch.Tensor]:
    if not isinstance(episodes, list) or len(episodes) not in (TRAIN_FIT, FIT):
        raise ValueError("FIT_LOCAL_20_OR_24_EPISODES")
    rows, labels = [], []
    for episode in episodes:
        if set(episode) != {"initial", "events"} or set(episode["initial"]) != set(ROLES) or len(episode["events"]) != STEPS:
            raise ValueError("PUBLIC_EPISODE_CONTRACT")
        state = {role: list(episode["initial"][role]) for role in ROLES}
        if any(len(s) != 2 or any(type(v) is not int or not 0 <= v < 16 for v in s) for s in state.values()):
            raise ValueError("PUBLIC_INITIAL_STATE")
        for event in episode["events"]:
            if set(event) != {"target", "source", "event", "observed"}:
                raise ValueError("EVENT_FIELDS")
            target, source = event["target"], event["source"]
            ev, y = event["event"], event["observed"]
            if target not in ROLES or source not in ROLES or target == source or any(type(v) is not int or not 0 <= v < 16 for v in (ev, y)):
                raise ValueError("PUBLIC_EVENT_VALUES")
            own, other = state[target], state[source]
            rows.append(encode((own[0], own[1], other[0], other[1], ev)))
            labels.append([(y >> b) & 1 for b in range(4)])
            state[target] = [y, own[0]]
    return torch.tensor(rows, dtype=torch.float32), torch.tensor(labels, dtype=torch.float32)


class LearnedRelation(nn.Module):
    """Generic learned bilinear role/bit interactions, no supplied symmetry."""
    def __init__(self):
        super().__init__()
        self.a = nn.Parameter(torch.empty(5, 4, 4))
        self.b = nn.Parameter(torch.empty(5, 4, 4))
        self.out = nn.Parameter(torch.empty(4, 4))
        self.bias = nn.Parameter(torch.zeros(4))
        with torch.no_grad():
            self.a.uniform_(-.11, .11)
            self.b.uniform_(-.11, .11)
            self.out.uniform_(-.3, .3)

    def forward(self, x: torch.Tensor, *, ablate: bool = False) -> torch.Tensor:
        v = x.reshape(-1, 5, 4)
        a = torch.einsum('bsi,sih->bh', v, self.a)
        b = torch.einsum('bsi,sih->bh', v, self.b.roll(1, 0) if ablate else self.b)
        return (torch.tanh(a) * torch.tanh(b)) @ self.out.T + self.bias


class IndependentSequencePeer(nn.Module):
    """Separate fully trained 7-unit dense control (179 + scalar gain)."""
    def __init__(self):
        super().__init__()
        self.project = nn.Linear(20, 7)
        self.readout = nn.Linear(7, 4)
        self.gain = nn.Parameter(torch.ones(()))

    def forward(self, x: torch.Tensor, *, ablate: bool = False) -> torch.Tensor:
        if ablate:
            raise ValueError("ABLATION_ONLY_FOR_LEARNED_RELATION")
        return self.readout(torch.tanh(self.project(x))) * self.gain


def new_model(arm: str):
    if arm not in ("candidate", "peer"):
        raise ValueError("UNKNOWN_ARM")
    torch.manual_seed(SEED)
    model = LearnedRelation() if arm == "candidate" else IndependentSequencePeer()
    if sum(p.numel() for p in model.parameters()) != PARAMETERS:
        raise AssertionError("UNMATCHED_PARAMETER_BUDGET")
    return model


def fit_model(arm: str, fit_episodes: list[dict]) -> tuple[nn.Module, dict]:
    x, y = fit_rows(fit_episodes)
    torch.set_num_threads(1)
    model = new_model(arm)
    optimizer = torch.optim.Adam(model.parameters(), lr=LEARNING_RATE)
    for _ in range(UPDATES):
        optimizer.zero_grad(set_to_none=True)
        loss = nn.functional.binary_cross_entropy_with_logits(model(x), y)
        loss.backward()
        optimizer.step()
    return model, {"arm":arm,"FIT_episodes":len(fit_episodes),"training_rows":len(x),
                  "updates":UPDATES,"trainable_parameters":PARAMETERS,
                  "FIT_sha256":digest(fit_episodes), "extra_oracle_answers":0,
                  "CHECK_or_HELDOUT_training":False,"scientific_acceptance":False}


def rollout(model: nn.Module, episode: dict, *, ablate: bool = False) -> tuple[int, ...]:
    # No event[observed] reads; self-predicted state across all 8 events.
    if set(episode) != {"initial", "events"} or set(episode["initial"]) != set(ROLES) or len(episode["events"]) != STEPS:
        raise ValueError("PUBLIC_ROLLOUT_CONTRACT")
    state = {r: list(episode["initial"][r]) for r in ROLES}
    outputs = []
    model.eval()
    with torch.no_grad():
        for e in episode["events"]:
            if set(e) != {"target", "source", "event", "observed"} or e["target"] not in ROLES or e["source"] not in ROLES or e["target"] == e["source"]:
                raise ValueError("PUBLIC_ROLLOUT_EVENT")
            t, s = e["target"], e["source"]
            own, other = state[t], state[s]
            x = torch.tensor([encode((own[0], own[1], other[0], other[1], e["event"]))])
            logits = model(x, ablate=ablate)[0]
            output = sum(int(logits[bit] >= 0) << bit for bit in range(4))
            outputs.append(output)
            state[t] = [output, own[0]]
    return tuple(outputs)


def fit_only_diagnostics(arm: str, fit_episodes: list[dict]) -> dict:
    if len(fit_episodes) != FIT:
        raise ValueError("FROZEN_FIT_COUNT")
    cv_model, cv_receipt = fit_model(arm, fit_episodes[:TRAIN_FIT])
    validation = fit_episodes[TRAIN_FIT:]
    cv_predictions = [rollout(cv_model, ep) for ep in validation]
    cv_correct = sum(preds == tuple(e["observed"] for e in ep["events"])
                     for preds, ep in zip(cv_predictions, validation))
    full_model, receipt = fit_model(arm, fit_episodes)
    return {"model": full_model, "receipt":receipt, "cv_receipt":cv_receipt,
            "FIT_local_CV_exact_episodes_of_4":cv_correct,
            "used_CHECK_or_HELDOUT":False}

"""Full-public-information source-free conventional occupancy predictors."""
from __future__ import annotations
from collections import defaultdict
from change_memory import _cell, _tick


class LastObserved:
    def __init__(self): self.memory = {}
    def predict(self, t, cell):
        _tick(t); k = _cell(cell)
        return float(self.memory[k]) if k in self.memory else 0.5
    def observe(self, t, cell, blocked):
        _tick(t); k = _cell(cell)
        if type(blocked) is not bool: raise ValueError("CONTROL_BAD_BOOL")
        self.memory[k] = blocked


class LaplaceHistory:
    def __init__(self): self.count = defaultdict(lambda: [0, 0])
    def predict(self, t, cell):
        _tick(t); yes, no = self.count[_cell(cell)]
        return (yes + 1) / (yes + no + 2)
    def observe(self, t, cell, blocked):
        _tick(t); k = _cell(cell)
        if type(blocked) is not bool: raise ValueError("CONTROL_BAD_BOOL")
        self.count[k][0 if blocked else 1] += 1


class MarkovLaplace:
    """Each cell has an unconstrained fitted binary transition model.

    This is an important stronger conventional reference, not a straw man;
    transition counts do not claim to resolve unobserved intermediate flips.
    """
    def __init__(self):
        self.last = {}
        self.transitions = defaultdict(lambda: [[0, 0], [0, 0]])
    def predict(self, t, cell):
        _tick(t); k = _cell(cell)
        if k not in self.last: return 0.5
        prev = int(self.last[k]); row = self.transitions[k][prev]
        return (row[1] + 1) / (sum(row) + 2)
    def observe(self, t, cell, blocked):
        _tick(t); k = _cell(cell)
        if type(blocked) is not bool: raise ValueError("CONTROL_BAD_BOOL")
        if k in self.last:
            self.transitions[k][int(self.last[k])][int(blocked)] += 1
        self.last[k] = blocked


class NoMemory:
    def predict(self, t, cell):
        _tick(t); _cell(cell)
        return 0.5
    def observe(self, t, cell, blocked):
        _tick(t); _cell(cell)
        if type(blocked) is not bool: raise ValueError("CONTROL_BAD_BOOL")

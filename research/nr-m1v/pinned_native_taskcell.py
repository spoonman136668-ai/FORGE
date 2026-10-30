"""Literal frozen Yggdrasil TaskCell class, copied without edits from
Yggdrasil PR #700 commit 8a1bf9c961a1c9b66080885d4d48106836638b5e,
file research/native/itd02/mg40/task_cells.py, Git blob
fdccd7a601adfacf4a4f8533279e66280cf16d99.
Not a live native import, original-world execution, or independent science.
"""
class TaskCell:
    def __init__(self):
        self.count=[0]*7
        self.effect=[0]*7
    def record(self,selected,effect):
        if type(selected) is not int or selected not in range(7):
            raise ValueError("NRM1Q_INVALID_SOURCE_ACTION")
        if self.count[selected]>=MAX_COUNT:
            raise ValueError("NRM1Q_COUNT_CAP")
        self.count[selected]+=1
        if effect:
            self.effect[selected]+=1
    def propose(self,parent):
        if type(parent) is not int or parent not in range(7):
            raise ValueError("NRM1Q_BAD_NATIVE_PARENT")
        if self.count[parent]<2:
            return parent,False
        base=10000*(self.effect[parent]+1)//(self.count[parent]+2)
        best=parent
        best_score=0
        # Only observed source-selected pickup and door-toggle evidence matters.
        for action in (3,5):
            if action==parent or self.count[action]<2 or self.effect[action]==0:
                continue
            score=10000*(self.effect[action]+1)//(self.count[action]+2)
            if score>=5000 and score>=base+1000 and score>best_score:
                best=action
                best_score=score
        return best,best!=parent


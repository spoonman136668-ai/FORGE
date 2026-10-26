"""Independent conventional conditional Beta(1,1) source-public turn estimator.

Reference estimator only. Does not claim parity with native R8 route selection.
"""
class ConditionalBeta:
    def __init__(self):
        self.bins=[[[0,0] for _ in range(2)] for _ in range(8)]
        self.previous=0
        self.samples=0

    def begin_episode(self):
        self.previous=0

    def observe(self,front_blocked,action,next_front_blocked):
        if type(action) is not int or action not in (0,1,2):
            raise ValueError("BETA_INVALID_SELECTED_ACTION")
        context=int(bool(front_blocked))*4+self.previous
        if action in (0,1):
            counts=self.bins[context][action]
            counts[int(bool(next_front_blocked))]+=1
            self.samples+=1
        self.previous=action+1

    def risks(self,front_blocked):
        context=int(bool(front_blocked))*4+self.previous
        counts=self.bins[context]
        risk=tuple((x[1]+1)/(sum(x)+2) for x in counts)
        eligible=all(sum(x)>=4 for x in counts)
        return risk,eligible

    def turn_choice(self,front_blocked):
        if not front_blocked:
            return None
        (left,right),eligible=self.risks(front_blocked)
        if not eligible:return None
        if left-right>=0.25:return 1
        if left-right<=-0.25:return 0
        return None

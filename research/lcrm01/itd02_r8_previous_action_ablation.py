"""R8 previous-action ablation: collapse all prior-action contexts.

The original native R8 learner is not modified. This is a separate matched
conditional-Beta control with previous-action information removed.
"""
from itd02_r8_conditional_beta import ConditionalBeta

class PreviousActionAblatedBeta(ConditionalBeta):
    def observe(self,front_blocked,action,next_front_blocked):
        self.previous=0
        super().observe(front_blocked,action,next_front_blocked)
        self.previous=0

    def risks(self,front_blocked):
        self.previous=0
        return super().risks(front_blocked)

    def begin_episode(self):
        self.previous=0

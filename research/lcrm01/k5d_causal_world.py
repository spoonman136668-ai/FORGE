"""K5D original constructed six-bit causal intervention micro-world.

This is an authored deterministic, auditable micro-world, not external physics.
The latent operator mappings are private simulator state. Candidate and
conventional models receive the SAME executed public before/op/after effects.
"""
import random

BITS=6
INPUTS=(0,1,2,4,8,16,32)
OPS=(0,1,2)
class CausalSixBitWorld:
 def __init__(self,seed):
  if type(seed)is not int or not 0<seed<1_000_000:
   raise ValueError("K5D_WORLD_SEED_INVALID")
  rng=random.Random(seed)
  self._rules=[]
  for op in OPS:
   perm=list(range(BITS))
   rng.shuffle(perm)
   self._rules.append((tuple(perm),rng.randrange(64)))
  self._state=None
  self.seed=seed
  self.steps=0

 def reset(self,public_state):
  if type(public_state)is not int or not 0<=public_state<64:
   raise ValueError("K5D_PUBLIC_INITIAL_STATE_INVALID")
  self._state=public_state
  self.steps=0
  return self._state

 def step(self,action):
  if self._state is None or type(action)is not int or action not in OPS:
   raise ValueError("K5D_UNLAWFUL_PUBLIC_INTERVENTION")
  before=self._state
  perm,mask=self._rules[action]
  after=mask
  for output_bit,input_bit in enumerate(perm):
   after^=((before>>input_bit)&1)<<output_bit
  self._state=after
  self.steps+=1
  return before,action,after

 def current(self):
  if self._state is None:raise ValueError("K5D_WORLD_NOT_RESET")
  return self._state

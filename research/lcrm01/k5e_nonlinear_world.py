"""K5E original seeded non-affine unknown causal-parent micro-world.

For each of 3 actions and 8 output bits, 3 distinct unknown input parents
and a randomly generated 8-entry nonlinear Boolean truth table. Only actual
public before/action/after is exposed. This is a CONSTRUCTED world, not
external hardware, robotics, or a standard benchmark.
"""
import random

def depends_on_all_three(table):
 for bit in range(3):
  if not any(table[idx]!=table[idx^(1<<bit)] for idx in range(8)):
   return False
 return True

class NonlinearParentWorld:
 def __init__(self,seed):
  if type(seed)is not int or not 0<seed<1000000:
   raise ValueError("K5E_BAD_WORLD_SEED")
  rng=random.Random(seed)
  rules={}
  for action in range(3):
   output=[]
   for bit in range(8):
    parents=tuple(sorted(rng.sample(range(8),3)))
    while True:
     table=[rng.randrange(2) for _ in range(8)]
     if depends_on_all_three(table):break
    output.append((parents,tuple(table)))
   rules[action]=tuple(output)
  self.__rules=rules
  self.__current=None
  self.seed=seed
  self.steps=0

 def reset(self,state):
  if type(state)is not int or not 0<=state<256:
   raise ValueError("K5E_UNLAWFUL_PUBLIC_STATE")
  self.__current=state;self.steps=0
  return state

 def step(self,action):
  if self.__current is None or type(action)is not int or action not in (0,1,2):
   raise ValueError("K5E_UNLAWFUL_CAUSAL_ACTION")
  before=self.__current
  after=0
  for bit,(parents,table) in enumerate(self.__rules[action]):
   b=(before>>parents[0]&1)|((before>>parents[1]&1)<<1)|((before>>parents[2]&1)<<2)
   after|=table[b]<<bit
  self.__current=after;self.steps+=1
  return before,action,after

 def current(self):
  if self.__current is None:raise ValueError("K5E_WORLD_UNINITIALIZED")
  return self.__current

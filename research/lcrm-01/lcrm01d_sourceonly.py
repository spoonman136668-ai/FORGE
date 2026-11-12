"""A single local, explicit diagnostic fixture; never scientific first-use."""
import random,copy
from lcrm01d_public import ROLES

def fixture():
    rng=random.Random(23017)
    episodes=[]
    for _ in range(24):
      state={role:[rng.randrange(16),rng.randrange(16)] for role in ROLES}
      first=copy.deepcopy(state); events=[]
      for step in range(8):
         t,s=rng.sample(ROLES,2)
         ev=rng.randrange(16)
         y=state[s][0]  # source-only toy: public source value copied to target
         events.append({'target':t,'source':s,'event':ev,'observed':y})
         state[t]=[y,state[t][0]]
      episodes.append({'initial':first,'events':events})
    return episodes

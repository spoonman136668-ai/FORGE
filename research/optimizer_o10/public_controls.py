"""O8 equally informed trained public-history conventional predictors.

The episodic table and logistic competitor are intentionally strong but
have explicitly engineered initial-cue and action-parity memory features.
Their learned Bernoulli heads are fitted only to O8_PUBLIC_TRAIN query
targets. These feature extractors are NOT learned and should not be
misrepresented as equal-parameter recurrent architectures.
"""
import math
from public_source import canonical, query_info
from recurrent_memory import sigmoid


class PublicQueryCounts:
    def __init__(self, memory):
        if memory not in ("CURRENT_QUERY", "FULL_PUBLIC_EPISODIC"):
            raise ValueError("O8_UNKNOWN_COUNTS")
        self.memory = memory
        self.table = {}
        self.updates = 0

    def key(self, episode):
        q = query_info(episode)
        if self.memory == "CURRENT_QUERY":
            return (q["query_observation"], 2, int(q["query_t"] == 18))
        return (q["cue"], q["parity"])

    def fit(self, episodes):
        for ep in episodes:
            key = self.key(ep)
            counts = self.table.setdefault(key, [0,0])
            counts[query_info(ep)["target"]] += 1
            self.updates += 1

    def predict(self, episode):
        negative, positive = self.table.get(self.key(episode), (0,0))
        return (positive+1)/(negative+positive+2)

    def checkpoint(self):
        return canonical({
            "model":self.memory,
            "stored_counts":[{"feature":list(k),"outcomes":v}
                             for k,v in sorted(self.table.items())],
            "updates":self.updates,
            "hand_engineered_memory_features":self.memory == "FULL_PUBLIC_EPISODIC",
        })


class PublicMemoryLogistic:
    def __init__(self):
        self.w=[0.0]*6
        self.updates=0

    def features(self, ep):
        q=query_info(ep)
        cue, parity = q["cue"],q["parity"]
        return (1.0,float(cue),float(parity),float(cue*parity),
                float(q["query_t"] == 18),float(q["query_observation"]))

    def fit(self, episodes):
        n=len(episodes)
        if n == 0:
            raise ValueError("O8_EMPTY_FIT")
        for _ in range(50):
            gradients=[0.0]*6
            for ep in episodes:
                x=self.features(ep)
                p=sigmoid(sum(w*v for w,v in zip(self.w,x)))
                delta=p-query_info(ep)["target"]
                for k in range(6):
                    gradients[k]+=delta*x[k]
            for k in range(6):
                penalty=0.0 if k==0 else 0.001*self.w[k]
                self.w[k]-=0.3*(gradients[k]/n+penalty)
            self.updates+=n

    def predict(self, episode):
        x=self.features(episode)
        return sigmoid(sum(w*v for w,v in zip(self.w,x)))

    def checkpoint(self):
        return canonical({
            "model":"PUBLIC_LOGISTIC_MEMORY",
            "weights":self.w,"updates":self.updates,
            "hand_engineered_cue_parity_features":True,
        })

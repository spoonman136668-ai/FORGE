"""O10 trained fully informed PUBLIC counts and memory ability witnesses.

Engineered action parity is an explicit PUBLIC information witness, not a
blinded equally-capable learned comparator. It never reads generator state.
"""
from public_source import canonical,query_info


class PublicCountControl:
    def __init__(self,variant):
        if variant not in ("PUBLIC_ENGINEERED_EPISODIC","CURRENT_ONLY_COUNTS"):
            raise ValueError("O10_BAD_CONTROL")
        self.variant=variant
        self.table={}
        self.updates=0

    def key(self,ep):
        q=query_info(ep)
        if self.variant=="CURRENT_ONLY_COUNTS":
            return (q["query_observation"],q["query_t"])
        return (q["cue"],q["cue4"],q["selector"],q["parity"])

    def fit(self,episodes):
        for ep in episodes:
            key=self.key(ep)
            counts=self.table.setdefault(key,[0,0])
            counts[query_info(ep)["target"]]+=1
            self.updates+=1

    def predict(self,ep):
        neg,pos=self.table.get(self.key(ep),(0,0))
        return (pos+1)/(neg+pos+2)

    def checkpoint(self):
        return canonical({
            "model":self.variant,
            "counts":[[list(k),counts] for k,counts in sorted(self.table.items())],
            "updates":self.updates,
            "hand_engineered_parity":self.variant=="PUBLIC_ENGINEERED_EPISODIC",
            "stored_public_history_event_count":0,
            "public_retained_cue_and_action_parity_scalars":4,
        })

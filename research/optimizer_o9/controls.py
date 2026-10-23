"""O9 fully fitted PUBLIC history count comparators.

The episodic control's public cue/selector/parity features are hand-specified
and deliberately advantaged as an information-availability witness. They are
NOT learned latent features or matched in parameter capacity to attention.
"""
from public_source import canonical,query_info


class PublicCounts:
    def __init__(self, kind):
        if kind not in ("PUBLIC_EPISODIC_TABLE","CURRENT_QUERY_COUNTS"):
            raise ValueError("O9_UNREGISTERED_CONTROL")
        self.kind=kind
        self.counts={}
        self.updates=0

    def key(self, ep):
        q=query_info(ep)
        if self.kind=="CURRENT_QUERY_COUNTS":
            return (q["query_observation"],q["query_t"])
        return (q["cue"],q["cue4"],q["selector"],q["parity"])

    def fit(self, batch):
        for ep in batch:
            key=self.key(ep)
            row=self.counts.setdefault(key,[0,0])
            row[query_info(ep)["target"]]+=1
            self.updates+=1

    def predict(self, ep):
        negative,positive=self.counts.get(self.key(ep),(0,0))
        return (positive+1)/(positive+negative+2)

    def checkpoint(self):
        return canonical({
            "model":self.kind,
            "fitted_counts":[{"public_key":list(k),"targets":v}
                             for k,v in sorted(self.counts.items())],
            "updates":self.updates,
            "engineered_public_cue_action_features":self.kind=="PUBLIC_EPISODIC_TABLE",
        })

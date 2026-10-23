"""O9 fully fitted PUBLIC history count comparators.

The episodic control's public cue/selector/parity features are hand-specified
and deliberately advantaged as an information-availability witness. They are
NOT learned latent features or matched in parameter capacity to attention.
"""
from public_source import canonical,query_info,FAMILIES


class PublicCounts:
    def __init__(self, kind, family):
        if kind not in ("PUBLIC_EPISODIC_TABLE","CURRENT_QUERY_COUNTS"):
            raise ValueError("O9_UNREGISTERED_CONTROL")
        if family not in FAMILIES:
            raise ValueError("O9_CONTROL_FAMILY_NOT_FROZEN")
        self.kind=kind
        self.family=family
        self.counts={}
        self.updates=0

    def key(self, ep):
        q=query_info(ep)
        if self.kind=="CURRENT_QUERY_COUNTS":
            return (q["query_observation"],q["query_t"])
        # Source-specific engineered ability witness, intentionally NOT a
        # blinded comparator: freeze exact PUBLIC history sufficiency key.
        if self.family=="A_ONE_CUE_RECALL":
            return (q["cue"],)
        if self.family=="B_SELECT_TWO_CUES":
            return (q["cue"],q["cue4"],q["selector"])
        return (q["cue"],q["parity"])

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
            "model":self.kind, "family_specific_hand_engineered_key":self.family,
            "fitted_counts":[{"public_key":list(k),"targets":v}
                             for k,v in sorted(self.counts.items())],
            "updates":self.updates,
            "engineered_public_cue_action_features":self.kind=="PUBLIC_EPISODIC_TABLE",
        })

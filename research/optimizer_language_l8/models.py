"""L8 explicit attribution of the EXACT frozen L7 learned patterns.

No new learning algorithm is invented or tuned against spent L7 public DEV.
Calls the original trained L7 realizer and independently reconstructs its
deterministic candidate route. If parity fails, it FAILS CLOSED instead
of accepting a changed fallback rule. New no-fallback control ABSTAINS.
"""
from l7_models_original import (
    PublicLanguageRealizer,PLACEHOLDER,similarity,contains_value
)
from source import canonical

ARMS=(
    "REFERENCE_RETRIEVAL","DELEX_TEMPLATE","CONSTRAINED_TEMPLATE",
    "CANONICAL_FACTS","NO_FALLBACK_CONSTRAINED",
)
AUDIT_KEYS=("name","near","food","area","eattype")


def canonical_facts(mr):
    return "; ".join(k+" is "+v for k,v in sorted(mr.items()))


def trace_delex(model,mr):
    candidates=model.fit.candidates(mr)
    for _,row in candidates:
        if set(PLACEHOLDER.findall(row["template"])).issubset(mr):
            result=model.fit.render(row["template"],mr)
            return result,"learned_pattern",len(candidates),None
    return candidates[0][1]["ref"],"reference_fallback",len(candidates),None


def trace_constrained(model,mr):
    candidates=model.fit.candidates(mr)
    eligible=[]
    for _,row in candidates[:32]:
        placeholders=set(PLACEHOLDER.findall(row["template"]))
        if not placeholders.issubset(mr):
            continue
        rendered=model.fit.render(row["template"],mr)
        literal,_=model.fit.source_slot_coverage(rendered,mr)
        halluc=model.fit.unsupported_name_near(rendered,mr)
        eligible.append((literal,-halluc,similarity(row["mr"],mr),rendered))
    if eligible:
        chosen=max(eligible,key=lambda x:(x[0],x[1],x[2]))
        return chosen[3],"learned_pattern",len(candidates)+len(eligible),len(eligible)
    return canonical_facts(mr),"canonical_fallback",len(candidates)+32,0


class AttributionRealizer:
    def __init__(self,arm,train,shared_constrained=None):
        if arm not in ARMS:
            raise ValueError("L8_UNKNOWN_FROZEN_ARM")
        self.arm=arm
        self.model=(shared_constrained
                    if arm=="NO_FALLBACK_CONSTRAINED"
                    else PublicLanguageRealizer(arm,train))
        if self.model is None:
            raise ValueError("L8_MISSING_SHARED_FROZEN_CONSTRAINED_MODEL")
        if arm=="NO_FALLBACK_CONSTRAINED" and \
                self.model.arm!="CONSTRAINED_TEMPLATE":
            raise ValueError("L8_INVALID_SHARED_MODEL")

    def predict(self,mr):
        if not isinstance(mr,dict) or not mr:
            raise ValueError("L8_NONPUBLIC_MEANING")
        if self.arm in ("CONSTRAINED_TEMPLATE","NO_FALLBACK_CONSTRAINED"):
            mirror,route,work,eligible=trace_constrained(self.model,mr)
            orig,_=self.model.generate(mr)
            if orig!=mirror:
                raise ValueError("L8_ORIGINAL_L7_CONSTRAINED_OUTPUT_CHANGED")
            if self.arm=="NO_FALLBACK_CONSTRAINED" and route=="canonical_fallback":
                return None,{"route":"abstained","original_route":route,
                             "candidate_count":eligible,"operations":work}
            return orig,{"route":route,"original_route":route,
                         "candidate_count":eligible,"operations":work}
        output,work=self.model.generate(mr)
        if self.arm=="DELEX_TEMPLATE":
            expected,route,_,_=trace_delex(self.model,mr)
            if output!=expected:
                raise ValueError("L8_ORIGINAL_L7_DELEX_OUTPUT_CHANGED")
        else:
            route=("canonical_direct" if self.arm=="CANONICAL_FACTS"
                   else "raw_reference")
        return output,{"route":route,"original_route":route,
                       "candidate_count":None,"operations":work}

    def checkpoint(self):
        return self.model.checkpoint()

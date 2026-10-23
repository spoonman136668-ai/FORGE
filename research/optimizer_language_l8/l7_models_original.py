"""L7 train-only learned delexicalized MR-to-human-language patterns.

A learned phrase-template mechanism is NOT a discovered cognitive state:
all MR key/value pairs are furnished at runtime; training text is
human-authored E2E NLG; no private first use or pretrained model.
"""
import re
from source import canonical

KEYS=("name","near","food","area","eattype")
PLACEHOLDER=re.compile(r"\{\{([a-z]+)\}\}")


def contains_value(text,value):
    if not value:
        return False
    return re.search(r"(?<!\w)"+re.escape(value)+r"(?!\w)",
                     text,flags=re.IGNORECASE) is not None


def delex(text,mr):
    output=text
    for key,value in sorted(mr.items(),key=lambda kv:(-len(kv[1]),kv[0])):
        if len(value)<2:
            continue
        output=re.sub(r"(?<!\w)"+re.escape(value)+r"(?!\w)",
                      lambda match:"{{"+key+"}}",output,flags=re.IGNORECASE)
    return output


def similarity(left,right):
    shared=set(left)&set(right)
    exact=sum(left[k].casefold()==right[k].casefold() for k in shared)
    mismatched=len(shared)-exact
    extra=len(set(left)^set(right))
    return 3*exact+len(shared)-2*mismatched-2*extra


class LearnedPatterns:
    def __init__(self,train):
        if not train:
            raise ValueError("L7_EMPTY_REAL_TEXT_TRAIN")
        self.rows=tuple({"mr":dict(r["mr"]),"ref":r["ref"],
                         "template":delex(r["ref"],r["mr"])}
                        for r in train)
        self.patterns=sum(bool(PLACEHOLDER.search(r["template"]))
                          for r in self.rows)
        # The inventory is solely TRAIN-visible word values, never DEV.
        self.name_near_inventory={
            key:{r["mr"][key] for r in self.rows if key in r["mr"]}
            for key in ("name","near")
        }

    def candidates(self,meaning):
        return sorted(enumerate(self.rows),key=lambda item:(
            -similarity(item[1]["mr"],meaning),
            -sum(k in meaning for k in PLACEHOLDER.findall(
                item[1]["template"])),
            item[0]
        ))

    @staticmethod
    def render(template,meaning):
        def repl(m):
            return meaning.get(m.group(1),"{{"+m.group(1)+"}}")
        return PLACEHOLDER.sub(repl,template)

    def source_slot_coverage(self,output,meaning):
        eligible=[k for k in KEYS if k in meaning]
        if not eligible:
            return 0.,0
        covered=sum(contains_value(output,meaning[k]) for k in eligible)
        return covered/len(eligible),len(eligible)

    def unsupported_name_near(self,output,meaning):
        unsupported=0
        for key,vocab in self.name_near_inventory.items():
            expected=meaning.get(key)
            for candidate in vocab:
                if candidate!=expected and len(candidate)>=5 and \
                        contains_value(output,candidate):
                    unsupported+=1
        return unsupported


class PublicLanguageRealizer:
    def __init__(self,arm,train):
        names=("REFERENCE_RETRIEVAL","DELEX_TEMPLATE",
               "CONSTRAINED_TEMPLATE","CANONICAL_FACTS")
        if arm not in names:
            raise ValueError("L7_UNREGISTERED_MEANING_REALIZER")
        self.arm=arm
        self.fit=LearnedPatterns(train) if arm!="CANONICAL_FACTS" else None
        self.seen_examples=len(train)

    def generate(self,meaning):
        if not isinstance(meaning,dict) or not meaning:
            raise ValueError("L7_INVALID_PUBLIC_MR")
        if self.arm=="CANONICAL_FACTS":
            # Lossless but deliberately NOT a natural English fluency model.
            return "; ".join(k+" is "+v for k,v in sorted(meaning.items())),len(meaning)
        candidates=self.fit.candidates(meaning)
        if self.arm=="REFERENCE_RETRIEVAL":
            return candidates[0][1]["ref"],len(candidates)
        if self.arm=="DELEX_TEMPLATE":
            for _,row in candidates:
                present=set(PLACEHOLDER.findall(row["template"]))
                if present.issubset(meaning):
                    return self.fit.render(row["template"],meaning),len(candidates)
            return candidates[0][1]["ref"],len(candidates)
        # A constrained REALIZER screens no more than 32 candidate patterns.
        # All constraints reference TRAIN-inventory and the requested MR.
        # The same selection is applied to SELECT and DEV; no post-DEV fixes.
        possible=[]
        for _,row in candidates[:32]:
            placeholders=set(PLACEHOLDER.findall(row["template"]))
            if not placeholders.issubset(meaning):
                continue
            output=self.fit.render(row["template"],meaning)
            literal,_=self.fit.source_slot_coverage(output,meaning)
            halluc=self.fit.unsupported_name_near(output,meaning)
            possible.append((literal,-halluc,
                             similarity(row["mr"],meaning),output))
        if possible:
            chosen=max(possible,key=lambda x:(x[0],x[1],x[2]))
            return chosen[3],len(candidates)+len(possible)
        # Never claim fallback is a fitted fluent language generator.
        return "; ".join(k+" is "+v for k,v in sorted(meaning.items())),len(candidates)+32

    def checkpoint(self):
        return canonical({
            "schema":"forge.optimizer.language.l7.structured-realizer.v1",
            "arm":self.arm,"train_count":self.seen_examples,
            "learned":self.fit.rows if self.fit is not None else [],
            "delex_train_patterns":self.fit.patterns if self.fit else 0,
            "source_inventory":self.fit.name_near_inventory if False else (
                {k:sorted(v) for k,v in self.fit.name_near_inventory.items()}
                if self.fit else {}),
        })

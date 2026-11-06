"""Typed source compiler for the existing Promptbreeder word mutator.

The grammar is fixed-capacity integer arithmetic over one cell's public
observations. Generation uses promptlineage.Generate, not a second optimizer.
All candidate execution remains in the original isolated native worker.
"""
from dataclasses import dataclass
import re

from f139 import nci04_model_free_search as search
from f139.nci04_native_contract import digest
from f139.nci04_portfolio_source_boundary import SourceCandidate
from f139.nci04_prompt_source import SourceBinding, bindings_digest, frozen_digest

SEED = "rate add add success zero add zero zero add add total zero add zero zero"
OPERATIONS = ("add", "mul", "min", "max")
TERMINALS = ("success", "failure", "total", "zero", "one", "two")
BRANCHES = frozenset((1, 2, 5, 8, 9, 12))
MARKER = "        # F139_TYPED_RATE_PROGRAM="
MAX_PARENTS = 4096


class ProgramRejected(ValueError):
    pass


def need(ok, reason):
    if not ok:
        raise ProgramRejected("F139_PROMPT_PROGRAM_" + reason)


def simplify(kind, left, right):
    """Canonicalize safe identities; this is not a behavioral novelty proof."""
    left, right = sorted((left, right), key=repr)
    if left[0] == right[0] == "constant":
        a, b = left[1], right[1]
        return ("constant", {"add":lambda:a+b, "mul":lambda:a*b,
                             "min":lambda:min(a,b), "max":lambda:max(a,b)}[kind]())
    zero, one = ("constant",0), ("constant",1)
    if kind == "add" and zero in (left,right):
        return right if left == zero else left
    if kind == "mul":
        if zero in (left,right):
            return zero
        if one in (left,right):
            return right if left == one else left
    if kind == "min" and zero in (left,right):
        return zero
    if kind == "max" and zero in (left,right):
        return right if left == zero else left
    if kind in ("min","max") and left == right:
        return left
    return (kind,left,right)


def parse(program):
    need(type(program) is str, "TEXT_REQUIRED")
    words = program.split(" ")
    need(len(words) == 15 and words[0] == "rate", "FIXED_CAPACITY_GRAMMAR")
    for pos, word in enumerate(words[1:],1):
        need(word in (OPERATIONS if pos in BRANCHES else TERMINALS), "TYPED_TOKEN")

    def node(pos):
        word = words[pos]
        if pos not in BRANCHES:
            value = {"zero":0,"one":1,"two":2}.get(word)
            return (("constant",value) if value is not None else ("observed",word)), pos+1
        left, pos = node(pos+1)
        right, pos = node(pos)
        return simplify(word,left,right), pos

    numerator, offset = node(1)
    denominator, offset = node(offset)
    need(offset == 15 and numerator != denominator and numerator != ("constant",0)
         and denominator != ("constant",0)
         and not (numerator[0] == denominator[0] == "constant"), "DEGENERATE_RATE")
    return numerator, denominator


def render(term, arm):
    if term[0] == "constant":
        return str(term[1])
    if term[0] == "observed":
        return {"success":"one", "failure":"zero", "total":"trials"}[term[1]]+str(arm)
    kind, left, right = term
    a,b = render(left,arm),render(right,arm)
    if kind in ("min","max"):
        return kind+"("+a+", "+b+")"
    return "("+a+(" + " if kind == "add" else " * ")+b+")"


def positive(term):
    """A sufficient proof of positivity given both arms' existing evidence."""
    if term[0] == "constant":
        return term[1] > 0
    if term[0] == "observed":
        return term[1] == "total"
    a,b = positive(term[1]),positive(term[2])
    return a and b if term[0] in ("mul","min") else a or b


def polynomial(term, arm):
    """Trusted symbolic arithmetic only; never evaluate candidate Python."""
    if term[0] == "constant":
        return {(0,0,0,0):term[1]} if term[1] else {}
    if term[0] == "observed":
        result = {}
        for index in ((arm*2,) if term[1] == "success" else
                      (arm*2+1,) if term[1] == "failure" else (arm*2,arm*2+1)):
            powers = [0,0,0,0]
            powers[index] = 1
            result[tuple(powers)] = 1
        return result
    if term[0] not in ("add","mul"):
        return None  # No unproved equivalence claim for piecewise expressions.
    a,b = polynomial(term[1],arm),polynomial(term[2],arm)
    if a is None or b is None:
        return None
    return poly_add(a,b) if term[0] == "add" else poly_multiply(a,b)


def poly_add(a,b,sign=1):
    out = dict(a)
    for powers,coefficient in b.items():
        out[powers] = out.get(powers,0)+sign*coefficient
    return {p:c for p,c in out.items() if c}


def poly_multiply(a,b):
    out = {}
    for ap,ac in a.items():
        for bp,bc in b.items():
            powers = tuple(x+y for x,y in zip(ap,bp))
            out[powers] = out.get(powers,0)+ac*bc
    return {p:c for p,c in out.items() if c}


def choice_polynomial(numerator,denominator):
    if not positive(denominator):
        return None  # A zero denominator can introduce new abstention.
    n0,n1 = polynomial(numerator,0),polynomial(numerator,1)
    d0,d1 = polynomial(denominator,0),polynomial(denominator,1)
    if any(x is None for x in (n0,n1,d0,d1)):
        return None
    return poly_add(poly_multiply(n0,d1),poly_multiply(n1,d0),-1)


def same_ordering(a,b):
    if a is None or b is None or not a or set(a) != set(b):
        return False
    powers = next(iter(b))
    numerator,denominator = a[powers],b[powers]
    return numerator*denominator > 0 and all(
        a[p]*denominator == b[p]*numerator for p in b)



def _public_counter_value(term, success, failure):
    """Evaluate trusted integer grammar nodes, never candidate Python."""
    if term[0] == "constant":
        return term[1]
    if term[0] == "observed":
        return {"success": success, "failure": failure,
                "total": success + failure}[term[1]]
    left = _public_counter_value(term[1], success, failure)
    right = _public_counter_value(term[2], success, failure)
    return {"add": lambda: left + right, "mul": lambda: left * right,
            "min": lambda: min(left, right),
            "max": lambda: max(left, right)}[term[0]]()


def _public_domain_leq(left, right):
    """Sufficient integer inequalities for one arm AFTER both arms have trials.

    The frozen public counters are nonnegative, success/failure <= total and
    total >= 1 when choose() compares rates. Never assume an upper sample
    bound, a hidden outcome, or a floating-point approximation.
    """
    if left == right or left == ("constant", 0):
        return True
    if (right == ("observed", "total")
            and left in (("observed", "success"),
                         ("observed", "failure"), ("constant", 1))):
        return True
    if right[0] == "mul":
        # x <= x * total, provided x >= 0 and total >= 1.
        return (left in right[1:]
                and ("observed", "total") in right[1:])
    return False


def _public_domain_reduce(term):
    """Conservatively prove equal expressions; historical bytes stay frozen."""
    if term[0] in ("constant", "observed"):
        return term
    kind, a, b = term
    reduced = simplify(kind, _public_domain_reduce(a), _public_domain_reduce(b))
    if reduced[0] not in ("min", "max"):
        return reduced
    kind, a, b = reduced
    if _public_domain_leq(a, b):
        return a if kind == "min" else b
    if _public_domain_leq(b, a):
        return b if kind == "min" else a
    return reduced


def _same_baseline_public_choice(numerator, denominator):
    """Prove, not sample, an identical baseline choice over all valid counts.

    Pointwise rewrites use only genuine public-counter invariants. Once reduced,
    the existing exact symbolic cross-product certificate proves the two arms
    have identical ordering and ties. Unknown min/max forms stay candidates.
    """
    gap = choice_polynomial(_public_domain_reduce(numerator),
                            _public_domain_reduce(denominator))
    baseline = choice_polynomial(("observed", "success"),
                                 ("observed", "total"))
    return same_ordering(gap, baseline)


def public_rate_preflight(program):
    """Development-only public-evidence control for NEW proposed programs.

    Equal arm exposure must preserve the ordering of observed success rates,
    including both directions and explicit abstention checks. This prevents
    tautological rate ties and reversed failure-rate choices before a worker
    is dispatched. It does NOT certify unequal exposure, learning or science.
    Historic source decoding deliberately does not call this preflight.
    """
    numerator, denominator = parse(program)
    # Target only min/max proposals that the historical polynomial guard
    # could not prove equivalent. Preserve the legacy SEED preflight result;
    # source_for_program already maps ordinary polynomial aliases to before.
    # Historical source reconstruction and SHA custody remain untouched.
    if (("min" in program.split(" ") or "max" in program.split(" "))
            and _same_baseline_public_choice(numerator, denominator)):
        return False
    for trials in (2, 4, 8):
        for success0 in range(trials + 1):
            for success1 in range(trials + 1):
                if success0 == success1:
                    continue
                numerator0 = _public_counter_value(
                    numerator, success0, trials - success0)
                numerator1 = _public_counter_value(
                    numerator, success1, trials - success1)
                denominator0 = _public_counter_value(
                    denominator, success0, trials - success0)
                denominator1 = _public_counter_value(
                    denominator, success1, trials - success1)
                if denominator0 <= 0 or denominator1 <= 0:
                    return False
                difference = numerator0 * denominator1 - numerator1 * denominator0
                if difference == 0 or (difference > 0) != (success0 > success1):
                    return False
    return True


def constant_forms(height):
    """Unique fixed-shape spellings of the tiny compile-time constant domain."""
    need(type(height) is int and 0 <= height <= 2, "TYPED_EMBEDDING")
    if height == 0:
        return {0:"zero",1:"one",2:"two"}
    children = constant_forms(height-1)
    out = {}
    for kind in OPERATIONS:
        for a in sorted(children):
            for b in sorted(children):
                value = simplify(kind,("constant",a),("constant",b))[1]
                out.setdefault(value,kind+" "+children[a]+" "+children[b])
    return out


def embed(term,height):
    """Recover a canonical mutation parent without a source-identity nonce."""
    if term[0] == "constant":
        forms = constant_forms(height)
        need(term[1] in forms, "CONSTANT_CAPACITY")
        return forms[term[1]]
    if term[0] == "observed":
        return term[1] if height == 0 else "add "+embed(term,height-1)+" "+embed(("constant",0),height-1)
    need(height > 0, "TYPED_EMBEDDING")
    return term[0]+" "+embed(term[1],height-1)+" "+embed(term[2],height-1)


def source_for_program(before, program):
    # Reuse exact original source and anchor custody; never execute Python.
    tuple(search.candidates(before))
    numerator, denominator = parse(program)
    gap = choice_polynomial(numerator,denominator)
    baseline = choice_polynomial(("observed","success"),("observed","total"))
    if same_ordering(gap,baseline):
        return before  # identity is explicitly filtered, never a fresh draft
    need(gap is None or bool(gap), "CONSTANT_CHOICE")
    # Preserve the exact existing shrinkage source identity, not a relabeled
    # implementation of its mathematical rule.
    laplace = (simplify("add",("observed","success"),("constant",1)),
               simplify("add",("observed","total"),("constant",2)))
    if same_ordering(gap,choice_polynomial(*laplace)):
        return tuple(search.candidates(before))[0][1]
    # Canonical source comments are essential while a publication is not yet
    # admitted: its raw source hash is already consumed, but the older owner
    # ledger does not yet hold its AST identity. Equivalent token spellings
    # must therefore produce the very same bytes, including the parent hint.
    canonical_program = "rate "+embed(numerator,2)+" "+embed(denominator,2)
    code = MARKER+canonical_program+"\n"
    code += "        numerator0 = "+render(numerator,0)+"\n"
    code += "        numerator1 = "+render(numerator,1)+"\n"
    code += "        denominator0 = "+render(denominator,0)+"\n"
    code += "        denominator1 = "+render(denominator,1)+"\n"
    code += ("        if denominator0 <= 0 or denominator1 <= 0:\n"
             "            return None\n"
             "        lhs = numerator0 * denominator1\n"
             "        rhs = numerator1 * denominator0\n")
    after = before.decode("utf-8").replace(search.RATE,code,1).encode("utf-8")
    search.normalized(after)
    return after


def recover_program(before, source):
    """A comment is only a lookup hint; require exact reconstructed bytes."""
    if type(source) is not bytes or not 0 < len(source) <= 256_000:
        raise ProgramRejected("F139_PROMPT_PROGRAM_HISTORY_BYTES")
    matches = re.findall(rb"^"+MARKER.encode()+rb"([^\r\n]+)$", source, re.MULTILINE)
    if not matches:
        return None
    need(len(matches) == 1, "AMBIGUOUS_HISTORY_MARKER")
    try:
        program = matches[0].decode("ascii")
        need(source_for_program(before,program) == source, "HISTORY_SOURCE_DRIFT")
    except (UnicodeError,ValueError) as exc:
        raise ProgramRejected("F139_PROMPT_PROGRAM_HISTORY_SOURCE_DRIFT") from exc
    return program


@dataclass(frozen=True)
class ProgramPlan:
    frozen: dict
    bindings: tuple
    history_sha256: str
    parent_program: str

    def request(self):
        return dict(promptbreeder=dict(frozen=self.frozen,
                                      frozen_sha256=frozen_digest(self.frozen)))

    @property
    def source_bindings_sha256(self):
        return bindings_digest(self.bindings)


def build_plan(before, *, history_sources, consumed_sha256, historical_ast_sha256,
               history_sha256, mechanism_sha256, max_candidates=16,
               eligible_parent_sha256=None):
    """Build one complete, bounded mutation plan from retained original history.

    The caller authenticates complete history outside this pure adapter. It
    must include negative, invalid and consumed/indeterminate source identities.
    Live callers supply the engineering-qualified parent identities separately.
    All sources still enter the consumed sets before parent filtering. The None
    default preserves historical pure-adapter rehearsal; the original-owner
    backend always passes its explicit verified-ledger eligibility set.
    Parent qualification is not a task-quality reward or scientific selection.
    """
    need(type(history_sources) is tuple and len(history_sources) <= MAX_PARENTS,
         "HISTORY_SOURCE_BUDGET")
    need(type(max_candidates) is int and 1 <= max_candidates <= 16, "POPULATION_BUDGET")
    need(all(type(x) is str and re.fullmatch(r"[0-9a-f]{64}",x)
             for x in (history_sha256,mechanism_sha256)), "CONTEXT_PINS")
    need(all(type(values) in (set,frozenset) and all(type(x) is str
             and re.fullmatch(r"[0-9a-f]{64}",x) for x in values)
             for values in (consumed_sha256,historical_ast_sha256)), "CONSUMED_IDENTITIES")
    need(eligible_parent_sha256 is None or (
        type(eligible_parent_sha256) in (set, frozenset)
        and all(type(x) is str and re.fullmatch(r"[0-9a-f]{64}", x)
                for x in eligible_parent_sha256)), "PARENT_ELIGIBILITY")
    tuple(search.candidates(before))
    raw_seen, ast_seen = set(consumed_sha256), set(historical_ast_sha256)
    # Never omit a historical negative just because it is not this grammar.
    # Opaque/invalid sources remain consumed by raw identity.
    parents = [SEED]
    for source in history_sources:
        need(type(source) is bytes, "HISTORY_BYTES")
        raw_seen.add(digest(source))
        try:
            ast_seen.add(search.normalized(source))
        except ValueError:
            pass  # Original caller separately verifies invalid-negative custody.
        if eligible_parent_sha256 is not None and digest(source) not in eligible_parent_sha256:
            continue
        program = recover_program(before,source)
        if program is not None and program not in parents:
            parents.append(program)
    trailer = " history "+" ".join(history_sha256[i:i+16] for i in range(0,64,16))
    for parent in reversed(parents):
        operations, bindings = [], []
        words = parent.split(" ")
        local_raw, local_ast = set(raw_seen), set(ast_seen)
        for pos in range(1,15):
            vocabulary = OPERATIONS if pos in BRANCHES else TERMINALS
            for replacement in vocabulary:
                if replacement == words[pos]:
                    continue
                changed = words.copy()
                changed[pos] = replacement
                program = " ".join(changed)
                try:
                    if not public_rate_preflight(program):
                        continue
                    after = source_for_program(before,program)
                except ProgramRejected:
                    continue
                after_id, ast_id = digest(after), search.normalized(after)
                if after == before or after_id in local_raw or ast_id in local_ast:
                    continue
                local_raw.add(after_id)
                local_ast.add(ast_id)
                operations.append(dict(kind="replace",position=pos,replacement=replacement))
                bindings.append(SourceBinding(program+trailer, SourceCandidate(
                    generator="promptbreeder", lane="Yggdrasil", path=search.PATH,
                    parent_sha=search.PARENT, before_sha256=digest(before), after_sha256=after_id,
                    mechanism_sha256=mechanism_sha256, after=after,
                    question="Does this typed public-counter rate program preserve native decision learning?",
                    hypothesis="Fixed-capacity typed arithmetic exploration; retain every negative, "
                        "unchanged-parent, checkpoint, arm-symmetry and unfamiliar-transfer controls.")))
                if len(operations) == max_candidates:
                    break
            if len(operations) == max_candidates:
                break
        if operations:
            frozen = dict(schema="forge.promptlineage.frozen.v1",lane="Yggdrasil",
                epoch=len(raw_seen)+1,source_sha=search.PARENT,parent=parent+trailer,
                vocabulary=list(OPERATIONS+TERMINALS),max_operations=len(operations),operations=operations)
            return ProgramPlan(frozen,tuple(bindings),history_sha256,parent)
    return None  # Honest finite-grammar exhaustion, never a quota/history reset.

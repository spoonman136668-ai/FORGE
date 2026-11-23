// Package researchsteer previews one source-pinned Mind-Palace governance
// contract. It has NO scheduling, execution, admission or acceptance methods.
package researchsteer

import (
    "context"
    "crypto/sha256"
    "encoding/hex"
    "encoding/json"
    "errors"
    "io"
    "strings"
)

const PolicyPath = "governance/unified-final-authority.v1.json"
const maxPolicyBytes = 32768

// Source matches FORGE's existing mindcontext.Source. The private GitHub
// transport is shared and read-only, not a new authentication mechanism.
type Source interface {
    ResolveMain(context.Context) (string, error)
    ReadAt(context.Context, string, string) ([]byte, error)
}

// Preview is deliberately incapable of authorizing changes to any research
// worker, task, scientific verdict or protected repository reference.
type Preview struct {
    Schema string `json:"schema"`
    PolicyID string `json:"policy_id"`
    Revision int `json:"revision"`
    SourceCommit string `json:"source_commit"`
    SourceSHA256 string `json:"source_sha256"`
    AdvisoryOnly bool `json:"advisory_only"`
    MayChangeResearchState bool `json:"may_change_research_state"`
}

func fail() error { return errors.New("FORGE_NORTH_STAR_POLICY_UNQUALIFIED") }
func hex40(s string) bool {
    if len(s) != 40 { return false }
    for _, c := range s { if (c<'0'||c>'9')&&(c<'a'||c>'f') { return false } }
    return true
}
func obj(x any) map[string]any { m, _ := x.(map[string]any); return m }
func eq(m map[string]any, key string, value any) bool { return m[key] == value }
func trueAt(m map[string]any, key string) bool { return eq(m,key,true) }
func falseAt(m map[string]any, key string) bool { return eq(m,key,false) }

// ReadPreview consumes one exact revision and validates authority boundaries.
// Even an accepted policy is only a read-only PREVIEW until a separately
// qualified, existing FORGE planning point is explicitly wired to consume it.
func ReadPreview(ctx context.Context, source Source) (Preview, error) {
    var zero Preview
    if ctx == nil || source == nil { return zero, fail() }
    pin, err := source.ResolveMain(ctx)
    if err != nil || !hex40(pin) { return zero, fail() }
    raw, err := source.ReadAt(ctx,pin,PolicyPath)
    if err != nil || len(raw)<1 || len(raw)>maxPolicyBytes { return zero, fail() }
    dec := json.NewDecoder(strings.NewReader(string(raw)))
    dec.UseNumber()
    var generic any
    if err=dec.Decode(&generic); err != nil { return zero, fail() }
    var extra any
    if err=dec.Decode(&extra); err != io.EOF { return zero, fail() }
    m := obj(generic)
    if !eq(m,"schema","mind-palace.unified-final-authority.v1") ||
       !eq(m,"policy_id","NSTAR-ONE-FINAL-AUTHORITY") ||
       !eq(m,"scope","program_wide_governance_only") { return zero,fail() }
    rev,ok:=m["revision"].(json.Number)
    if !ok { return zero,fail() }
    revision,err:=rev.Int64()
    if err!=nil || revision<1 || revision>1000000 { return zero,fail() }
    owner:=obj(m["final_authority"])
    if !eq(owner,"role","human_operator") ||
       !eq(owner,"authority_type","ultimate_program_decision") ||
       !trueAt(owner,"cannot_delegate_without_explicit_owner_decision") { return zero,fail() }
    gov:=obj(m["canonical_governance"])
    if !eq(gov,"repository","spoonman136668-ai/Mind-Palace") ||
       !eq(gov,"file",PolicyPath) || !trueAt(gov,"one_current_revision") { return zero,fail() }
    guards:=obj(m["nondelegable_guards"])
    for _,k:=range []string{
        "independent_scientific_first_use","frozen_protocols_and_sealed_holdouts",
        "no_cross_link_FORGE_CKB_plane","no_new_controller_scheduler_queue",
        "read_only_Mind_Palace_consumption","no_automatic_protected_ref_promotion",
        "no_automatic_live_broker_approval","avoid_paid_API_without_permission",
        "retain_negative_evidence","do_not_rewrite_in_flight_work",
        "measurable_north_star_improvement_required","no_progression_regression",
        "do_not_pause_cancel_or_restart_qualified_active_work",
        "no_unauthorized_reprioritization_of_frozen_experiments",
        "no_unqualified_change_to_existing_worker_dispatch",
        "no_silent_memory_or_governance_fallback",
        "no_unqualified_FORGE_scientific_ownership_claims",
        "preserve_independent_research_lanes","do_not_retroactively_reassign_source_authority",
    } { if !trueAt(guards,k) { return zero,fail() } }
    research:=obj(m["research_organization"])
    if !eq(research,"design","one_shared_memory_one_FORGE_research_operations_hub_independent_native_learners") ||
       !eq(research,"strategic_owner","human_operator") ||
       !falseAt(research,"actual_runtime_steering_qualified") ||
       !falseAt(research,"automatic_cross_chat_updates") ||
       !eq(research,"transition","additive_prospective_only_no_auto_migration_or_preemption") { return zero,fail() }
    memory:=obj(research["shared_memory"])
    if !eq(memory,"system","Mind-Palace") || !falseAt(memory,"scientific_authority") ||
       !falseAt(memory,"execution_controller") {return zero,fail()}
    operations:=obj(research["research_operations"])
    if !eq(operations,"system","FORGE") || !trueAt(operations,"native_controller_only") ||
       !trueAt(operations,"requires_qualified_existing_FORGE_intake_and_FSA") ||
       !trueAt(operations,"may_execute_only_authorized_eligible_work") ||
       !falseAt(operations,"ckb_plane_dependency") { return zero,fail() }
    science:=obj(research["scientific_authority"])
    if !eq(science,"system","FORGE Scientific Authority") ||
       !eq(science,"scope","new_prospectively_admitted_intelligence_research_only_after_FSA_qualification") ||
       !trueAt(science,"does_not_rewrite_historical_accepted_results") ||
       !trueAt(science,"does_not_override_independent_review_or_human_approval") {return zero,fail()}
    lanes,ok:=research["independent_research_lanes"].([]any)
    allowed:=[]string{"Wingless","Yggdrasil","Optimizer Work","BIO","Mass Research","Language Research"}
    if !ok || len(lanes)!=len(allowed) {return zero,fail()}
    for i, lane := range allowed { if lanes[i]!=lane { return zero,fail() } }
    if !eq(m,"effect","advisory_contract_only") {return zero,fail()}
    consumers,ok:=m["declared_active_consumers"].([]any)
    if !ok||len(consumers)!=0 {return zero,fail()}
    sum:=sha256.Sum256(raw)
    return Preview{Schema:"forge.north-star-preview.v1",PolicyID:"NSTAR-ONE-FINAL-AUTHORITY",
       Revision:int(revision),SourceCommit:pin,SourceSHA256:hex.EncodeToString(sum[:]),
       AdvisoryOnly:true,MayChangeResearchState:false},nil
}

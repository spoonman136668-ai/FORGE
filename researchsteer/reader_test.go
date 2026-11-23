package researchsteer

import (
 "context"
 "encoding/json"
 "errors"
 "strings"
 "testing"
)

type fakeSource struct{ pin string; raw []byte; gotPath,gotPin string; err error }
func (f *fakeSource) ResolveMain(context.Context)(string,error){return f.pin,f.err}
func (f *fakeSource) ReadAt(_ context.Context,pin,path string)([]byte,error){f.gotPath=path;f.gotPin=pin;return f.raw,f.err}
func fixture() map[string]any {
 return map[string]any{
 "schema":"mind-palace.unified-final-authority.v1", "policy_id":"NSTAR-ONE-FINAL-AUTHORITY",
 "scope":"program_wide_governance_only", "revision":1, "effect":"advisory_contract_only",
 "declared_active_consumers":[]string{},
 "final_authority":map[string]any{"role":"human_operator","authority_type":"ultimate_program_decision","cannot_delegate_without_explicit_owner_decision":true},
 "canonical_governance":map[string]any{"repository":"spoonman136668-ai/Mind-Palace","file":PolicyPath,"one_current_revision":true},
 "nondelegable_guards":map[string]any{
 "independent_scientific_first_use":true,"frozen_protocols_and_sealed_holdouts":true,
 "no_cross_link_FORGE_CKB_plane":true,"no_new_controller_scheduler_queue":true,
 "read_only_Mind_Palace_consumption":true,"no_automatic_protected_ref_promotion":true,
 "no_automatic_live_broker_approval":true,"avoid_paid_API_without_permission":true,
 "retain_negative_evidence":true,"do_not_rewrite_in_flight_work":true,
 "measurable_north_star_improvement_required":true,"no_progression_regression":true,
 "do_not_pause_cancel_or_restart_qualified_active_work":true,
 "no_unauthorized_reprioritization_of_frozen_experiments":true,
 "no_unqualified_change_to_existing_worker_dispatch":true,
 "no_silent_memory_or_governance_fallback":true,
 "no_unqualified_FORGE_scientific_ownership_claims":true,
 "preserve_independent_research_lanes":true,"do_not_retroactively_reassign_source_authority":true,
 },
 "research_organization":map[string]any{
 "design":"one_shared_memory_one_FORGE_research_operations_hub_independent_native_learners",
 "strategic_owner":"human_operator","actual_runtime_steering_qualified":false,
 "automatic_cross_chat_updates":false,
 "transition":"additive_prospective_only_no_auto_migration_or_preemption",
 "shared_memory":map[string]any{"system":"Mind-Palace","scientific_authority":false,"execution_controller":false},
 "research_operations":map[string]any{"system":"FORGE","native_controller_only":true,"requires_qualified_existing_FORGE_intake_and_FSA":true,"may_execute_only_authorized_eligible_work":true,"ckb_plane_dependency":false},
 "scientific_authority":map[string]any{"system":"FORGE Scientific Authority","scope":"new_prospectively_admitted_intelligence_research_only_after_FSA_qualification","does_not_rewrite_historical_accepted_results":true,"does_not_override_independent_review_or_human_approval":true},
 "independent_research_lanes":[]string{"Wingless","Yggdrasil","Optimizer Work","BIO","Mass Research","Language Research"},
 },
 }
}
func raw(m map[string]any)[]byte{b,e:=json.Marshal(m);if e!=nil{panic(e)};return b}
func reader(m map[string]any)*fakeSource{return &fakeSource{pin:strings.Repeat("a",40),raw:raw(m)}}
func TestAdvisoryReadPinnedAndNonExecuting(t *testing.T){s:=reader(fixture());p,e:=ReadPreview(context.Background(),s);if e!=nil{t.Fatal(e)};if !p.AdvisoryOnly||p.MayChangeResearchState||p.Revision!=1||p.SourceCommit!=s.pin||len(p.SourceSHA256)!=64||s.gotPath!=PolicyPath||s.gotPin!=s.pin{t.Fatalf("unsafe or unpinned preview: %#v",p)}}
func TestMissingOwnerRejected(t *testing.T){m:=fixture();m["final_authority"].(map[string]any)["role"]="FORGE";if _,e:=ReadPreview(context.Background(),reader(m));e==nil{t.Fatal("admitted competing authority")}}
func TestCKBDependencyRejected(t *testing.T){m:=fixture();m["research_organization"].(map[string]any)["research_operations"].(map[string]any)["ckb_plane_dependency"]=true;if _,e:=ReadPreview(context.Background(),reader(m));e==nil{t.Fatal("admitted forbidden dependency")}}
func TestFrozenProgressionGuardRejected(t *testing.T){m:=fixture();m["nondelegable_guards"].(map[string]any)["do_not_pause_cancel_or_restart_qualified_active_work"]=false;if _,e:=ReadPreview(context.Background(),reader(m));e==nil{t.Fatal("accepted disruption")}}
func TestIndependentLaneRejected(t *testing.T){m:=fixture();m["research_organization"].(map[string]any)["independent_research_lanes"]=[]string{"Wingless"};if _,e:=ReadPreview(context.Background(),reader(m));e==nil{t.Fatal("removed independent lanes")}}
func TestUnqualifiedSteeringFalse(t *testing.T){m:=fixture();m["research_organization"].(map[string]any)["actual_runtime_steering_qualified"]=true;if _,e:=ReadPreview(context.Background(),reader(m));e==nil{t.Fatal("false live steering")}}
func TestPinnedCommitRejected(t *testing.T){s:=reader(fixture());s.pin="main";if _,e:=ReadPreview(context.Background(),s);e==nil{t.Fatal("mutable pin accepted")}}
func TestReadFailureRejected(t *testing.T){s:=reader(fixture());s.err=errors.New("access denied");if _,e:=ReadPreview(context.Background(),s);e==nil{t.Fatal("read failure silently accepted")}}
func TestUnauthorizedPathNeverUsed(t *testing.T){s:=reader(fixture());_,_=ReadPreview(context.Background(),s);if s.gotPath!=PolicyPath{t.Fatal("arbitrary file retrieval")}}
func TestTrailingJSONRejected(t *testing.T){s:=reader(fixture());s.raw=append(s.raw,[]byte(` {"accepted":true}`)...);if _,e:=ReadPreview(context.Background(),s);e==nil{t.Fatal("trailing JSON accepted")}}

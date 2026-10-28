package branchpolicy

import (
	"os"
	"strings"
	"testing"
)

// The reviewed administrative handoff must not become a CI dispatch, an
// original-owner task mutation, or an unrestricted settings operation.
func TestF139ReleaseRulesetInstallerNoSideEffectsWithoutApply(t *testing.T) {
	raw, err := os.ReadFile("../scripts/Install-F139V18ReleaseRuleset.ps1")
	if err != nil { t.Fatal(err) }
	s := strings.ReplaceAll(string(raw), "\r\n", "\n")
	require := []string{
		"param([switch]$Apply)",
		"if(-not $Apply)",
		"F139_V18_ADMIN_LOCK=NOT_INSTALLED_READONLY",
		"F139_V18_ADMIN_LOCK_DENIED_",
		"RULESET_NEGATIVE_TESTS_NOT_PASSING",
		"ORIGINAL_MAIN_RELEASE_OR_OWNER_POLICY_DRIFT",
		"RULESET_INVENTORY_UNEXPECTED",
		"--method POST",
		"repos/$repo/rulesets",
		"ACTIVE_RULESET_NOT_UNIQUE",
		"SERVER_ENFORCEMENT_OR_BYPASS_DRIFT",
		"RELEASE_BRANCH_NOT_PROTECTED_OR_MAIN_DRIFT",
		"F139_V18_OWNER_CUTOVER_AUTHORIZED=FALSE",
		"F139_V18_SCIENTIFIC_FIRST_USE=FALSE",
		"@($detail.bypass_actors).Count -ne 0",
		"$lock[0] -cne 'deletion'",
		"$lock[1] -cne 'update'",
		"f139-owner-release-$target",
		"ownerPolicy.source_sha -cne $oldMain",
		"ownerPolicy.scientific_first_use -ne $false",
		"ownerPolicy.paid_model_calls -ne 0",
	}
	for _, token := range require {
		if !strings.Contains(s, token) {t.Errorf("missing admin safety guard %q",token)}
	}
	if strings.Index(s,"if(-not $Apply)") > strings.Index(s,"--method POST") {
		t.Error("admin operation reachable before read-only default")
	}
	for _, forbidden := range []string{
		"Disable-ScheduledTask",
		"Stop-ScheduledTask",
		"Start-ScheduledTask",
		"Stop-Process",
		"Set-ScheduledTask",
		"transition-qualified-native-v18",
		"F139-V18-OWNER-CUTOVER ",
		"gh workflow run",
		"gh pr merge",
		"--method PATCH",
		"gh auth login",
		"GH_TOKEN=",
		"GITHUB_TOKEN=",
	} {
		if strings.Contains(s, forbidden) {
			t.Errorf("admin handoff contains forbidden operation %q",forbidden)
		}
	}
}

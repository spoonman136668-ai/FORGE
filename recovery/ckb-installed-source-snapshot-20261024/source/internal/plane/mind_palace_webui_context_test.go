package plane

import "testing"

func mindPalaceContextTestOperation(scriptSHA256 string) LocalOperation {
	return LocalOperation{
		ID:             mindPalaceWebUIContextOperationID,
		Class:          "diagnostic",
		Script:         "operations/Read-MindPalaceContext.ps1",
		ScriptSHA256:   scriptSHA256,
		TimeoutSeconds: 60,
		Arguments: []LocalOperationArgument{
			{Name: "Query", Type: "string", Required: true, Pattern: mindPalaceWebUIContextQueryPattern, MaxLength: 256},
			{Name: "Project", Type: "string", Required: false, Pattern: mindPalaceWebUIContextProjectPattern, MaxLength: 80},
		},
	}
}

func mindPalaceContextTestRegistry(scriptSHA256 string) *LocalOperationRegistry {
	return &LocalOperationRegistry{byID: map[string]LocalOperation{
		mindPalaceWebUIContextOperationID: mindPalaceContextTestOperation(scriptSHA256),
	}}
}

func TestMindPalaceWebUIContextDescriptorUsesRuntimeRegisteredHash(t *testing.T) {
	oldHash := "a5828e635d8ae755183a23fc96355db0a095cb3402fa916b5892b2afaf30fe9b"
	newHash := "ddea39482b225d0d83810a5c2a417716e20d876eff2e7b2362115df65446e68f"

	for _, hash := range []string{oldHash, newHash} {
		registry := mindPalaceContextTestRegistry(hash)
		if !mindPalaceWebUIContextAvailable(registry) {
			t.Fatalf("valid registered operation %s was not advertised", hash)
		}
		gotHash := mindPalaceWebUIContextRegisteredSHA256(registry)
		if gotHash != hash {
			t.Fatalf("registered hash=%q, want %q", gotHash, hash)
		}
		d := mindPalaceWebUIContextDescriptor(gotHash)
		if d == nil {
			t.Fatalf("descriptor unexpectedly nil for %s", hash)
		}
		if got := d["input_sha256"]; got != hash {
			t.Fatalf("descriptor input_sha256=%v, want %s", got, hash)
		}
	}
}

func TestMindPalaceWebUIContextDescriptorContract(t *testing.T) {
	hash := "ddea39482b225d0d83810a5c2a417716e20d876eff2e7b2362115df65446e68f"
	d := mindPalaceWebUIContextDescriptor(hash)
	checks := map[string]any{
		"provider":              "mind-palace",
		"mode":                  "on-demand",
		"action":                "local-exec",
		"operation_id":          mindPalaceWebUIContextOperationID,
		"input_sha256":          hash,
		"generation_required":   true,
		"context_schema":        "ckb-plane.mind-palace-context.v1",
		"query_max_length":      256,
		"query_pattern":         mindPalaceWebUIContextQueryPattern,
		"project_optional":      true,
		"project_pattern":       mindPalaceWebUIContextProjectPattern,
		"advisory_only":         true,
		"authorizes_execution":  false,
		"authorizes_acceptance": false,
	}
	for key, want := range checks {
		if got, ok := d[key]; !ok || got != want {
			t.Fatalf("descriptor[%q]=%v, want %v", key, got, want)
		}
	}
	for _, key := range []string{"usage_policy", "query_policy"} {
		if value, ok := d[key].(string); !ok || value == "" {
			t.Fatalf("%s missing or empty: %v", key, d[key])
		}
	}
}

func TestMindPalaceWebUIContextAvailabilityRejectsMalformedOrMutatedOperation(t *testing.T) {
	validHash := "ddea39482b225d0d83810a5c2a417716e20d876eff2e7b2362115df65446e68f"
	if mindPalaceWebUIContextAvailable(nil) {
		t.Fatal("nil registry reported Mind-Palace context available")
	}

	for _, hash := range []string{
		"",
		"abc",
		"DDEA39482B225D0D83810A5C2A417716E20D876EFF2E7B2362115DF65446E68F",
		"gdea39482b225d0d83810a5c2a417716e20d876eff2e7b2362115df65446e68f",
	} {
		registry := mindPalaceContextTestRegistry(hash)
		if mindPalaceWebUIContextAvailable(registry) {
			t.Fatalf("malformed hash %q was advertised", hash)
		}
		if got := mindPalaceWebUIContextRegisteredSHA256(registry); got != "" {
			t.Fatalf("malformed hash %q returned registered hash %q", hash, got)
		}
		if d := mindPalaceWebUIContextDescriptor(hash); d != nil {
			t.Fatalf("malformed hash %q produced descriptor", hash)
		}
	}

	mutated := mindPalaceContextTestOperation(validHash)
	mutated.Arguments = append([]LocalOperationArgument(nil), mutated.Arguments...)
	mutated.Arguments[0].MaxLength = 255
	registry := &LocalOperationRegistry{byID: map[string]LocalOperation{mindPalaceWebUIContextOperationID: mutated}}
	if mindPalaceWebUIContextAvailable(registry) {
		t.Fatal("argument-contract-mismatched operation was advertised")
	}

	mutated = mindPalaceContextTestOperation(validHash)
	mutated.Script = "operations/Other.ps1"
	registry.byID[mindPalaceWebUIContextOperationID] = mutated
	if mindPalaceWebUIContextAvailable(registry) {
		t.Fatal("script-contract-mismatched operation was advertised")
	}
}

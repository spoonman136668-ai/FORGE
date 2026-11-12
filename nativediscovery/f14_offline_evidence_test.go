package nativediscovery

import (
	"bytes"
	"encoding/json"
	"os"
	"path/filepath"
	"testing"
)

func TestF14EndToEndOfflineCycleEvidenceDoesNotAdmitNegativeScience(t *testing.T) {
	cp, err := F8Development()
	if err != nil {
		t.Fatal("F8 cold checkpoint not available", err)
	}
	benefit, err := F10Development()
	if err != nil {
		t.Fatal("F10 strongest-control review not available", err)
	}
	drift, err := F13Development()
	if err != nil {
		t.Fatal("F13 changed-world review not available", err)
	}
	raw, sha, err := F14Export(cp, benefit, drift)
	if err != nil || len(sha) != 64 {
		t.Fatal("F14 failed to bind real source reports", err)
	}
	path := filepath.Join(t.TempDir(), "eureka-offline-cycle.json")
	if err := os.WriteFile(path, raw, 0600); err != nil {
		t.Fatal(err)
	}
	cold, err := os.ReadFile(path)
	if err != nil || !bytes.Equal(raw, cold) {
		t.Fatal("offline bytes changed", err)
	}
	v, err := F14Import(cold, sha)
	if err != nil {
		t.Fatal("independent file readback failed", err)
	}
	if v.F8CheckpointSHA256 != cp.CheckpointSHA256 ||
		v.F10.DigestSHA256 != benefit.DigestSHA256 ||
		v.F13.DigestSHA256 != drift.DigestSHA256 ||
		v.Classification != F14NO_GO || v.OwnerEligible ||
		v.ScientificAccepted || v.DispatchAuthorized {
		t.Fatal("negative science was promoted or parent lineage lost")
	}
	if _, err := F14Import(cold, ""); err == nil {
		t.Fatal("unanchored artifact accepted")
	}
	modified := append([]byte(nil), cold...)
	modified[len(modified)-2] ^= 1
	if _, err := F14Import(modified, sha); err == nil {
		t.Fatal("tampering accepted")
	}
	if _, err := F14Import(append(append([]byte(nil), cold...), '\n'), f3Hash(append(append([]byte(nil), cold...), '\n'))); err == nil {
		t.Fatal("noncanonical trailing bytes accepted")
	}
	// Even an attacker who supplies a new matching outer digest cannot forge
	// scientific/owner claims, omit the original negative, or swap a checkpoint.
	for _, mutate := range []func(*F14Evidence){
		func(x *F14Evidence) { x.ScientificAccepted = true },
		func(x *F14Evidence) { x.OwnerEligible = true },
		func(x *F14Evidence) { x.DispatchAuthorized = true },
		func(x *F14Evidence) { x.F13.Classification = F13Signal },
		func(x *F14Evidence) { x.F13.Arms[0].Rounds[1].ChangedCorrect[0]++ },
		func(x *F14Evidence) { x.F10.ParentF8CheckpointSHA256 = x.F13.DigestSHA256 },
		func(x *F14Evidence) { x.F8Artifact[3] ^= 1 },
	} {
		var forged F14Evidence
		if err := json.Unmarshal(raw, &forged); err != nil {
			t.Fatal(err)
		}
		mutate(&forged)
		bytesNew, err := json.Marshal(forged)
		if err != nil {
			t.Fatal(err)
		}
		bytesNew = append(bytesNew, '\n')
		if _, err := F14Import(bytesNew, f3Hash(bytesNew)); err == nil {
			t.Fatal("rehashed forged bundle accepted")
		}
	}
	t.Logf("F14_OFFLINE_EVIDENCE=PASS F8=%s F10=%s F13=%s classification=%s owner=false science=false", cp.CheckpointSHA256, benefit.DigestSHA256, drift.DigestSHA256, v.Classification)
}

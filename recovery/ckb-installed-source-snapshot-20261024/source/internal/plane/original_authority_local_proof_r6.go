package plane

import (
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"time"
)

type originalAuthorityInactiveProofR6 struct {
	Schema                     string    `json:"schema"`
	CreatedAtUTC               time.Time `json:"created_at_utc"`
	ExpiresAtUTC               time.Time `json:"expires_at_utc"`
	Authority                  string    `json:"authority"`
	Repository                 string    `json:"repository"`
	WorkOrderID                string    `json:"work_order_id"`
	RunnerService              string    `json:"runner_service"`
	RunnerServiceStatus        string    `json:"runner_service_status"`
	AcceptedRefMutationAllowed bool      `json:"accepted_ref_mutation_allowed"`
	RuntimeLaunchAllowed       bool      `json:"runtime_launch_allowed"`
	LocalOriginalAuthorityOnly bool      `json:"local_original_authority_only"`
}

func originalAuthorityInactiveLocalProofR6() error {
	root, err := originalAuthorityPlaneRootR6()
	if err != nil {
		return errors.New("ORIGINAL_AUTHORITY_VERIFICATION_UNAVAILABLE")
	}
	path := filepath.Join(root, "state", "original-authority-inactive-r6.json")
	raw, err := os.ReadFile(path)
	if err != nil {
		return errors.New("ORIGINAL_AUTHORITY_VERIFICATION_UNAVAILABLE")
	}
	var proof originalAuthorityInactiveProofR6
	if err := json.Unmarshal(raw, &proof); err != nil {
		return fmt.Errorf("ORIGINAL_AUTHORITY_VERIFICATION_UNAVAILABLE: malformed local proof")
	}
	now := time.Now().UTC()
	if proof.Schema != "ckb-plane.original-authority-inactive.v1" {
		return errors.New("ORIGINAL_AUTHORITY_VERIFICATION_UNAVAILABLE")
	}
	if !strings.EqualFold(proof.Authority, "plane") {
		return errors.New("ORIGINAL_AUTHORITY_VERIFICATION_UNAVAILABLE")
	}
	if !strings.EqualFold(proof.RunnerServiceStatus, "Stopped") {
		return errors.New("ORIGINAL_AUTHORITY_VERIFICATION_UNAVAILABLE")
	}
	if proof.AcceptedRefMutationAllowed || proof.RuntimeLaunchAllowed {
		return errors.New("ORIGINAL_AUTHORITY_VERIFICATION_UNAVAILABLE")
	}
	if !proof.LocalOriginalAuthorityOnly {
		return errors.New("ORIGINAL_AUTHORITY_VERIFICATION_UNAVAILABLE")
	}
	if proof.CreatedAtUTC.IsZero() || proof.ExpiresAtUTC.IsZero() || now.After(proof.ExpiresAtUTC) {
		return errors.New("ORIGINAL_AUTHORITY_VERIFICATION_UNAVAILABLE")
	}
	return nil
}

func originalAuthorityInactiveLocalProofBoolR6() (bool, error) {
	if err := originalAuthorityInactiveLocalProofR6(); err != nil {
		return false, err
	}
	return true, nil
}

func originalAuthorityPlaneRootR6() (string, error) {
	wd, err := os.Getwd()
	if err != nil {
		return "", err
	}
	dir := wd
	for i := 0; i < 8; i++ {
		if fileExistsR6(filepath.Join(dir, "config", "autonomy.yaml")) || fileExistsR6(filepath.Join(dir, "bin", "ckb-plane.exe")) {
			return dir, nil
		}
		next := filepath.Dir(dir)
		if next == dir {
			break
		}
		dir = next
	}
	return "", errors.New("plane root not found")
}

func fileExistsR6(path string) bool {
	info, err := os.Stat(path)
	return err == nil && !info.IsDir()
}

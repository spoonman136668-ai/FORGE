package plane

import (
	"encoding/json"
	"strings"
	"testing"
)

const preflightOrderYAML = `id: V11110_STAGE_TEST_PREFLIGHT_R1
title: preflight contract proof
repo: ckb
baseline:
  ref: local-candidate/V11110_STAGE_BASELINE_R1
  sha: "1111111111111111111111111111111111111111"
worker:
  branch: codex/v1.11.10-stage-test-preflight-r1
  preferred: codex
scope:
  allowed_paths:
    - pkg/web/app.js
    - pkg/web/strategy.html
    - pkg/preflight_test.go
  forbidden_paths: []
instructions:
  - prove contract validation
preserve:
  - custom chart and candle behavior
  - Stage DZB coherent market and timeframe switching
required_paths:
  - pkg/web/app.js
  - pkg/web/strategy.html
  - pkg/preflight_test.go
required_tests:
  focused_go:
    - ^TestPreflightCandidate$
  go_packages:
    - ./pkg
  powershell_scripts: []
context_files: []
acceptance:
  run_go_test_all: false
  run_playwright: true
  protect_accepted_refs: true
  require_clean_baseline: true
ui:
  root: pkg/web
  pages:
    - path: strategy.html
      critical_ids:
        - priceCanvas
      chart_id: priceCanvas
  markers:
    custom chart and candle behavior:
      - priceCanvas
forbidden:
  - runtime launch
`

func TestWorkOrderPreflightRejectsMissingPreserveMarkerAtQueueParse(t *testing.T) {
	q := QueueOrder{
		Schema:        queueSchema,
		ID:            "V11110_STAGE_TEST_PREFLIGHT_R1",
		LogicalStage:  "V11110_STAGE_TEST_PREFLIGHT_R1",
		Kind:          "source",
		WorkOrderYAML: preflightOrderYAML,
	}
	raw, err := json.Marshal(q)
	if err != nil {
		t.Fatal(err)
	}
	_, err = (&Engine{}).parseQueue(raw, q.ID)
	if err == nil || !strings.Contains(err.Error(), "UI_CONTRACT_INVALID: missing explicit markers for Stage DZB coherent market and timeframe switching") {
		t.Fatalf("expected deterministic UI preflight rejection, got %v", err)
	}
}

func TestWorkOrderPreflightDoesNotRetroactivelyInvalidatePersistedOrder(t *testing.T) {
	if _, err := ParseOrder([]byte(preflightOrderYAML)); err != nil {
		t.Fatalf("persisted legacy order must remain readable; queue ingress owns the new preflight: %v", err)
	}
}

func TestWorkOrderPreflightAcceptsCompletePreserveMarkersAtQueueParse(t *testing.T) {
	complete := strings.Replace(
		preflightOrderYAML,
		"    custom chart and candle behavior:\n      - priceCanvas\n",
		"    custom chart and candle behavior:\n      - priceCanvas\n    Stage DZB coherent market and timeframe switching:\n      - selectionGeneration\n",
		1,
	)
	q := QueueOrder{
		Schema:        queueSchema,
		ID:            "V11110_STAGE_TEST_PREFLIGHT_R1",
		LogicalStage:  "V11110_STAGE_TEST_PREFLIGHT_R1",
		Kind:          "source",
		WorkOrderYAML: complete,
	}
	raw, err := json.Marshal(q)
	if err != nil {
		t.Fatal(err)
	}
	if _, err = (&Engine{}).parseQueue(raw, q.ID); err != nil {
		t.Fatalf("complete preservation contract rejected: %v", err)
	}
}

func TestWorkOrderPreflightRejectsEmptyMarker(t *testing.T) {
	var w WorkOrder
	w.Preserve = []string{"state parity"}
	w.Acceptance.Browser = true
	w.UI.Root = "pkg/web"
	w.UI.Pages = []UIPage{{Path: "strategy.html", CriticalIDs: []string{"priceCanvas"}}}
	w.UI.Markers = map[string][]string{"state parity": {""}}
	if err := validateWorkOrderPreflight(w); err == nil || !strings.Contains(err.Error(), "empty marker") {
		t.Fatalf("expected empty marker rejection, got %v", err)
	}
}

func TestWorkOrderPreflightAllowsNonUIWorkOrder(t *testing.T) {
	if err := validateWorkOrderPreflight(WorkOrder{}); err != nil {
		t.Fatalf("non-UI work order should not require UI contract: %v", err)
	}
}

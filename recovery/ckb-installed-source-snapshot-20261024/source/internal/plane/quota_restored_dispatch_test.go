package plane

import (
	"context"
	"testing"
)

func containsCapability(v any, want string) bool {
	items, ok := v.([]string)
	if !ok {
		return false
	}
	for _, item := range items {
		if item == want {
			return true
		}
	}
	return false
}

func TestQuotaRestoredBridgeDispatchAndCapability(t *testing.T) {
	p, w, _ := prepareCodexQuotaRearmFixture(t)
	p.Config.Autonomy.RemoteControl = true
	if err := p.setSetting("autonomy_generation", "1"); err != nil {
		t.Fatal(err)
	}
	b := &WebUIBridge{Config: BridgeConfig{ControlEnabled: true}}
	p.AttachBridge(b)

	ping, err := b.snapshot(context.Background(), BridgeCommand{Action: "ping"})
	if err != nil {
		t.Fatal(err)
	}
	projection, ok := ping.(map[string]any)
	if !ok || !containsCapability(projection["capabilities"], "quota-restored") {
		t.Fatalf("quota-restored not advertised: %#v", ping)
	}

	result, err := p.controlRequest(context.Background(), BridgeCommand{
		ID:          "quota-restored-dispatch-test",
		Action:      "quota-restored",
		WorkOrderID: w.ID,
		Generation:  1,
	})
	if err != nil {
		t.Fatal(err)
	}
	response := result.(map[string]any)
	if response["succeeded"] != true {
		t.Fatalf("quota-restored bridge dispatch failed: %#v", response)
	}
	var state string
	if err = p.Store.DB.QueryRow("SELECT state FROM queue_items WHERE id=?", w.ID).Scan(&state); err != nil {
		t.Fatal(err)
	}
	if state != "QUEUED" {
		t.Fatalf("bridge dispatch did not rearm queue: %s", state)
	}
}

func TestQuotaRestoredNativeDispatch(t *testing.T) {
	p, w, _ := prepareCodexQuotaRearmFixture(t)
	result, err := p.HandleNative(context.Background(), NativeRequest{Action: "quota-restored", ID: w.ID})
	if err != nil {
		t.Fatal(err)
	}
	got := result.(map[string]any)
	if got["queue_state_after"] != "QUEUED" || got["work_order_state_after"] != "DRAFT" {
		t.Fatalf("unexpected native quota-restored result: %#v", got)
	}
}

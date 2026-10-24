package plane

import (
	"context"
	"errors"
	"testing"
	"time"
)

func TestBlockerResolverModeControlRequiresPausedAuthority(t *testing.T) {
	p, _ := setup(t)
	testAuthority(p)

	if blockerResolverMode(p) != blockerResolverModeOff {
		t.Fatal("resolver must default off")
	}
	if _, err := p.SetBlockerResolverMode(context.Background(), blockerResolverModeShadow); err == nil ||
		err.Error() != "BLOCKER_RESOLVER_SHADOW_REQUIRES_PAUSED_CONTROLLER" {
		t.Fatalf("unpaused shadow enable: %v", err)
	}
	if blockerResolverMode(p) != blockerResolverModeOff {
		t.Fatal("failed enable changed resolver mode")
	}

	if err := p.Store.Pause(true); err != nil {
		t.Fatal(err)
	}
	out, err := p.SetBlockerResolverMode(context.Background(), blockerResolverModeShadow)
	if err != nil {
		t.Fatal(err)
	}
	if blockerResolverMode(p) != blockerResolverModeShadow || out["mode"] != blockerResolverModeShadow ||
		out["production_accepted"] != false || out["resume_authorized"] != false {
		t.Fatalf("unexpected shadow result: %+v mode=%s", out, blockerResolverMode(p))
	}

	p.authorityVerifier = func(context.Context) error { return errors.New("AUTHORITY_LOST") }
	if _, err = p.SetBlockerResolverMode(context.Background(), blockerResolverModeShadow); err == nil ||
		err.Error() != "AUTHORITY_LOST" {
		t.Fatalf("lost authority accepted: %v", err)
	}

	out, err = p.SetBlockerResolverMode(context.Background(), blockerResolverModeOff)
	if err != nil {
		t.Fatal(err)
	}
	if blockerResolverMode(p) != blockerResolverModeOff || out["mode"] != blockerResolverModeOff {
		t.Fatalf("off failed: %+v mode=%s", out, blockerResolverMode(p))
	}
	if _, err = p.SetBlockerResolverMode(context.Background(), "live"); err == nil ||
		err.Error() != "BLOCKER_RESOLVER_MODE_INVALID" {
		t.Fatalf("invalid mode accepted: %v", err)
	}
}

func TestBlockerResolverBridgeCommandIsGenerationBoundAndNarrow(t *testing.T) {
	at := time.Now().UTC()
	cfg := BridgeConfig{PlaneID: "plane", MailboxID: "mailbox", ControlEnabled: true}
	cmd := BridgeCommand{
		Schema: bridgeCommandSchema, ID: "blocker-resolver-shadow", PlaneID: cfg.PlaneID, MailboxID: cfg.MailboxID,
		CreatedAt: at, ExpiresAt: at.Add(time.Hour), Action: "blocker-resolver", Generation: 1, Mode: blockerResolverModeShadow,
	}
	if err := cmd.validate(cfg, at); err != nil {
		t.Fatal(err)
	}
	cmd.Mode = "live"
	if err := cmd.validate(cfg, at); err == nil || err.Error() != "CONTROL_ARGUMENTS_INVALID" {
		t.Fatalf("invalid mode accepted: %v", err)
	}
	cmd.Mode = blockerResolverModeShadow
	cmd.WorkOrderID = "DEMO"
	if err := cmd.validate(cfg, at); err == nil || err.Error() != "CONTROL_ARGUMENTS_INVALID" {
		t.Fatalf("work-order argument accepted: %v", err)
	}
}

func TestBlockerResolverMailboxControlUsesExistingAuthorityGeneration(t *testing.T) {
	p, _ := setup(t)
	testAuthority(p)
	if err := p.Store.Pause(true); err != nil {
		t.Fatal(err)
	}
	p.Config.Autonomy.RemoteControl = true
	p.bridge = &WebUIBridge{Config: BridgeConfig{ControlEnabled: true}}
	cmd := BridgeCommand{
		ID: "blocker-resolver-control", Action: "blocker-resolver", Generation: 1, Mode: blockerResolverModeShadow,
	}
	v, err := p.controlRequest(context.Background(), cmd)
	if err != nil {
		t.Fatal(err)
	}
	response, ok := v.(map[string]any)
	if !ok || response["succeeded"] != true || blockerResolverMode(p) != blockerResolverModeShadow {
		t.Fatalf("unexpected control result: %#v mode=%s", v, blockerResolverMode(p))
	}
	status, err := p.AutonomyStatus()
	if err != nil {
		t.Fatal(err)
	}
	if status["blocker_resolver_mode"] != blockerResolverModeShadow || status["blocker_resolver_status"] != "MODE_SHADOW" {
		t.Fatalf("resolver status not projected: %#v", status)
	}
}

func TestBlockerResolverActiveModeRequiresPausedAuthority(t *testing.T) {
	p, _ := setup(t)
	testAuthority(p)
	if _, err := p.SetBlockerResolverMode(context.Background(), blockerResolverModeActive); err == nil ||
		err.Error() != "BLOCKER_RESOLVER_ACTIVE_REQUIRES_PAUSED_CONTROLLER" {
		t.Fatalf("unpaused active enable: %v", err)
	}
	if err := p.Store.Pause(true); err != nil {
		t.Fatal(err)
	}
	out, err := p.SetBlockerResolverMode(context.Background(), blockerResolverModeActive)
	if err != nil {
		t.Fatal(err)
	}
	if blockerResolverMode(p) != blockerResolverModeActive || out["mode"] != blockerResolverModeActive ||
		out["production_accepted"] != false || out["resume_authorized"] != false {
		t.Fatalf("unexpected active result: %+v mode=%s", out, blockerResolverMode(p))
	}
}

func TestBlockerResolverBridgeCommandAcceptsBoundedActiveMode(t *testing.T) {
	at := time.Now().UTC()
	cfg := BridgeConfig{PlaneID: "plane", MailboxID: "mailbox", ControlEnabled: true}
	cmd := BridgeCommand{
		Schema: bridgeCommandSchema, ID: "blocker-resolver-active", PlaneID: cfg.PlaneID, MailboxID: cfg.MailboxID,
		CreatedAt: at, ExpiresAt: at.Add(time.Hour), Action: "blocker-resolver", Generation: 1, Mode: blockerResolverModeActive,
	}
	if err := cmd.validate(cfg, at); err != nil {
		t.Fatal(err)
	}
}

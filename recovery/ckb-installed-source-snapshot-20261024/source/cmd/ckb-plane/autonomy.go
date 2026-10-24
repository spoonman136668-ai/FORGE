package main

import (
	"ckb-plane/internal/plane"
	"context"
	"encoding/json"
	"errors"
	"flag"
	"fmt"
	"os"
	"path/filepath"
	"strings"
)

func runAutonomy(args []string) error {
	if len(args) < 2 {
		return errors.New("use workorders list-pending|validate|enqueue|run-pending|retry|export, or controller configure|run|status|authority|pause|resume|acknowledge|verify-evidence|qualify|tooling|handoff-check|stop")
	}
	family, sub := args[0], args[1]
	rest := args[2:]
	pos := ""
	if len(rest) > 0 && !strings.HasPrefix(rest[0], "-") {
		pos = rest[0]
		rest = rest[1:]
	}
	fs := flag.NewFlagSet(family+" "+sub, flag.ContinueOnError)
	config := fs.String("config", "config/autonomy.yaml", "autonomy configuration")
	file := fs.String("file", "", "queue envelope or configuration input")
	id := fs.String("id", pos, "exact work order id")
	auth := fs.String("authorization", "none", "none, test, operator")
	mode := fs.String("mode", "dry-run", "dry-run, controlled-proof, source")
	consume := fs.Bool("consume-on-refusal", false, "explicitly fail a refused proof item")
	owner := fs.String("owner", "original", "original, test, plane")
	bridge := fs.String("bridge-config", "", "optional WebUI mailbox configuration")
	source := fs.String("source", "", "clean CKB seed repository")
	remote := fs.Bool("remote-control", false, "enable structured remote actions after mailbox setup")
	home := fs.String("codex-home", "", "dedicated Codex profile")
	if e := fs.Parse(rest); e != nil {
		return e
	}
	if fs.NArg() != 0 {
		return errors.New("unexpected arguments")
	}
	emit := func(v any) error {
		b, e := json.MarshalIndent(v, "", "  ")
		if e == nil {
			fmt.Println(string(b))
		}
		return e
	}
	if family == "controller" && sub == "configure" {
		return plane.ConfigureAutonomy(*config, *file, *source, *home, *remote)
	}
	c, e := plane.LoadConfig(*config)
	if e != nil {
		return e
	}
	if !c.Autonomy.Enabled {
		return errors.New("AUTONOMY_CONFIG_REQUIRED")
	}
	root, e := filepath.Abs(filepath.Join(filepath.Dir(*config), ".."))
	if e != nil {
		return e
	}
	p, e := plane.NewEngine(c, root)
	if e != nil {
		return e
	}
	defer p.Store.DB.Close()
	ctx := context.Background()
	if family == "controller" && sub == "run" {
		if *bridge != "" {
			bc, er := plane.LoadBridgeConfig(*bridge)
			if er != nil {
				return er
			}
			b, er := plane.NewWebUIBridge(root, c.State.SQLitePath, bc)
			if er != nil {
				return er
			}
			defer b.Close()
			p.AttachBridge(b)
		}
		fmt.Println("CKB-plane native controller: local status at http://127.0.0.1:8791; dispatch follows recorded authority and authorization.")
		return p.RunController()
	}
	if family == "controller" && sub == "status" {
		s, e := p.AutonomyStatus()
		if e != nil {
			return e
		}
		return emit(s)
	}
	if family == "workorders" && sub == "list-pending" {
		s, e := p.QueueList()
		if e != nil {
			return e
		}
		return emit(s)
	}
	if family == "workorders" && sub == "validate" {
		q, e := p.QueueValidate(*id)
		if e != nil {
			return e
		}
		return emit(map[string]any{"valid": true, "id": q.ID, "kind": q.Kind, "source_authorized": false})
	}
	// Mutating CLI actions coordinate with the service using its local API.
	// Offline proof actions take the same controller lock, so they cannot race it.
	if family == "controller" {
		switch sub {
		case "tooling":
			return emit(c.Tools)
		case "proof-check":
			return p.CheckR4c1Proof()
		case "handoff-check":
			return p.CheckAutonomyHandoff(ctx)
		case "qualify":
			v, e := p.QualifyAutonomy(ctx)
			_ = emit(v)
			return e
		case "authority":
			return p.ChangeAuthorityOffline(ctx, *owner)
		case "stop":
			v, e := p.StopLocalController(ctx)
			if e != nil {
				return e
			}
			return emit(v)
		case "quota-restored":
			v, e := p.RearmCodexQuotaRestoredOffline(ctx, *id)
			if e != nil {
				return e
			}
			return emit(v)
		case "pause", "resume", "acknowledge":
			v, e := p.LocalControl(ctx, sub, *id)
			if e != nil {
				return e
			}
			return emit(v)
		case "acceptance-replay":
			v, e := p.AcceptanceReplayOffline(ctx, *id)
			if e != nil {
				return e
			}
			return emit(v)
		case "verify-evidence":
			j, e := p.Store.Get(*id)
			if e != nil {
				return e
			}
			if e = p.VerifyEvidence(j); e != nil {
				return e
			}
			return emit(map[string]any{"id": j.ID, "verified": true})
		}
	}
	if family == "workorders" {
		switch sub {
		case "retry":
			v, e := p.RetryQueueOffline(ctx, *id, *auth, *mode)
			if e != nil {
				return e
			}
			return emit(v)
		case "enqueue":
			b, e := os.ReadFile(*file)
			if e != nil {
				return e
			}
			return p.SubmitOffline(b)
		case "run-pending":
			if *id == "" {
				*id = "V11110_STAGE_CT_POST_ACCEPTANCE_QUEUE_CONSUMPTION_R1"
			}
			r, e := p.RunQueueOffline(ctx, *id, *auth, *mode, *consume)
			_ = emit(r)
			return e
		case "export":
			v, e := p.ExportCandidateOffline(ctx, *id)
			if e != nil {
				return e
			}
			return emit(v)
		}
	}
	return errors.New("unknown autonomy command")
}

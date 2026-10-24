package main

import (
	"bytes"
	"ckb-plane/internal/plane"
	"context"
	"encoding/json"
	"flag"
	"fmt"
	"io"
	"net/http"
	"os"
	"path/filepath"
	"strings"
	"time"
)

func main() {
	if len(os.Args) == 2 && os.Args[1] == "__plane-host" {
		os.Exit(plane.HostMain())
	}
	if e := run(os.Args[1:]); e != nil {
		fmt.Fprintln(os.Stderr, e)
		os.Exit(1)
	}
}
func run(args []string) error {
	if len(args) > 0 && args[0] == "advisory" {
		return runOpenCodeAdvisory(args[1:])
	}
	if len(args) > 0 && args[0] == "bridge" {
		return runWebUIBridge(args[1:])
	}
	if len(args) == 0 {
		fmt.Println("ckb-plane: controller configure/run/status/qualify/authority | workorders list-pending/validate/enqueue/run-pending/export | advisory run | bridge | legacy: init/doctor/serve/status/profile/workorder/authorize/dispatch/accept/retry/demo-init")
		return nil
	}
	if args[0] == "workorders" || args[0] == "controller" {
		return runAutonomy(args)
	}
	command := args[0]
	args = args[1:]
	sub := ""
	if command == "workorder" || command == "profile" {
		if len(args) == 0 {
			return fmt.Errorf("%s requires a subcommand", command)
		}
		sub = args[0]
		args = args[1:]
	}
	fs := flag.NewFlagSet(command, flag.ContinueOnError)
	config := fs.String("config", "config/local.yaml", "local configuration")
	file := fs.String("file", "", "work order YAML")
	id := fs.String("id", "", "exact work order ID")
	jsonOut := fs.Bool("json", false, "JSON output")
	dir := fs.String("dir", "demo", "new demo directory")
	profileName := fs.String("profile", "", "repo-neutral dispatch profile name")
	stateDB := fs.String("state-db", "", "override SQLite state path")
	if e := fs.Parse(args); e != nil {
		return e
	}
	if fs.NArg() != 0 {
		return fmt.Errorf("unexpected arguments")
	}
	if command == "demo-init" {
		return plane.DemoInit(*dir)
	}
	if command == "workorder" && sub == "validate" {
		b, e := os.ReadFile(*file)
		if e != nil {
			return e
		}
		w, e := plane.ParseOrder(b)
		if e != nil {
			return e
		}
		fmt.Println("PASS:", w.ID)
		return nil
	}
	c, e := plane.LoadConfig(*config)
	if e != nil {
		return e
	}
	if *stateDB != "" {
		c.State.SQLitePath = *stateDB
	}
	if *profileName != "" {
		c.Profile.Name = *profileName
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
	printJSON := func(v any) error {
		b, e := json.MarshalIndent(v, "", "  ")
		if e == nil {
			fmt.Println(string(b))
		}
		return e
	}
	switch command {
	case "profile":
		switch sub {
		case "preflight":
			ev, e := p.PreflightSelectedProfile(context.Background())
			if e != nil {
				return e
			}
			if *jsonOut {
				return printJSON(ev)
			}
			fmt.Printf("[PlaneProfile] %s -> %s\n", ev.ProfileName, ev.Status)
			fmt.Println("[PlaneProfile] evidence:", ev.EvidencePath)
			return nil
		case "replay":
			ev, e := p.ReplaySelectedProfile(context.Background(), filepath.Join(p.Root, "artifacts", "r2f"))
			if *jsonOut {
				_ = printJSON(ev)
			} else if ev.ProfileName != "" {
				fmt.Printf("[PlaneProfile] %s replay -> %s\n", ev.ProfileName, ev.FinalState)
				if ev.ReplayEvidencePath != "" {
					fmt.Println("[PlaneProfile] replay evidence:", ev.ReplayEvidencePath)
				}
				if ev.Evidence != "" {
					fmt.Println("[PlaneProfile] acceptance evidence:", ev.Evidence)
				}
			}
			return e
		case "workspace-dry-run":
			ev, e := p.WorkspaceDryRunSelectedProfile(context.Background(), filepath.Join(p.Root, "artifacts", "r3b"))
			if *jsonOut {
				_ = printJSON(ev)
			} else if ev.ProfileName != "" {
				fmt.Printf("[PlaneProfile] %s workspace-dry-run -> %s\n", ev.ProfileName, ev.Status)
				if ev.EvidencePath != "" {
					fmt.Println("[PlaneProfile] workspace evidence:", ev.EvidencePath)
				}
				if ev.WorkspacePlan.WorkspaceRoot != "" {
					fmt.Println("[PlaneProfile] workspace plan:", ev.WorkspacePlan.WorkspaceRoot)
				}
			}
			return e
		case "worker-proof":
			ev, e := p.WorkerProofSelectedProfile(context.Background(), filepath.Join(p.Root, "artifacts", "r4a"))
			if *jsonOut {
				_ = printJSON(ev)
			} else if ev.ProfileName != "" {
				fmt.Printf("[PlaneProfile] %s worker-proof -> %s\n", ev.ProfileName, ev.FinalState)
				if ev.WorkerProofEvidencePath != "" {
					fmt.Println("[PlaneProfile] worker-proof evidence:", ev.WorkerProofEvidencePath)
				}
				if ev.AcceptanceEvidence != "" {
					fmt.Println("[PlaneProfile] acceptance evidence:", ev.AcceptanceEvidence)
				}
			}
			return e
		case "workspace-materialize-readonly":
			ev, e := p.MaterializeReadonlyWorkspaceSelectedProfile(context.Background(), filepath.Join(p.Root, "artifacts", "r3c"))
			if *jsonOut {
				_ = printJSON(ev)
			} else if ev.ProfileName != "" {
				fmt.Printf("[PlaneProfile] %s workspace-materialize-readonly -> %s\n", ev.ProfileName, ev.Status)
				if ev.EvidencePath != "" {
					fmt.Println("[PlaneProfile] workspace evidence:", ev.EvidencePath)
				}
				if ev.Workspace.WorkspaceRoot != "" {
					fmt.Println("[PlaneProfile] materialized workspace:", ev.Workspace.WorkspaceRoot)
				}
			}
			return e
		default:
			return fmt.Errorf("unknown profile subcommand")
		}
	case "init":
		if _, e = p.Token(); e != nil {
			return e
		}
		fmt.Println("Initialized. Operator token file: " + filepath.Join(root, "state", "operator.token"))
		return nil
	case "doctor":
		h := p.Doctor()
		if *jsonOut {
			return printJSON(h)
		}
		for _, v := range h {
			fmt.Printf("%-10s %-27s %s\n", v.Status, v.Name, v.Detail)
		}
		return nil
	case "serve":
		fmt.Printf("CKB Plane local demo service: http://%s:%d\n", c.Server.Bind, c.Server.Port)
		return p.Serve()
	case "status":
		jobs, e := p.Store.List()
		if e != nil {
			return e
		}
		return printJSON(map[string]any{"why": p.Why(), "jobs": jobs})
	case "workorder":
		if sub != "load" {
			return fmt.Errorf("unknown workorder command")
		}
		b, e := os.ReadFile(*file)
		if e != nil {
			return e
		}
		if e = p.Store.Load(b); e != nil {
			return e
		}
		fmt.Println("Loaded as DRAFT")
		return nil
	case "authorize":
		if e = p.Authorize(*id); e != nil {
			return e
		}
		return p.Ready(*id)
	case "dispatch", "accept", "retry", "cancel":
		if *id == "" {
			return fmt.Errorf("--id required")
		}
		token, e := p.Token()
		if e != nil {
			return e
		}
		url := fmt.Sprintf("http://%s:%d/api/workorders/%s/%s", c.Server.Bind, c.Server.Port, *id, command)
		req, e := http.NewRequest("POST", url, bytes.NewReader(nil))
		if e != nil {
			return e
		}
		req.Header.Set("Authorization", "Bearer "+token)
		client := http.Client{Timeout: 3 * time.Minute}
		res, e := client.Do(req)
		if e != nil {
			return fmt.Errorf("local service required: %w", e)
		}
		defer res.Body.Close()
		b, e := io.ReadAll(io.LimitReader(res.Body, 1<<20))
		if e != nil {
			return e
		}
		fmt.Println(strings.TrimSpace(string(b)))
		if res.StatusCode != 200 {
			return fmt.Errorf("action rejected")
		}
		return nil
	}
	return fmt.Errorf("unknown command: %s", command)
}


func runOpenCodeAdvisory(args []string) error {
	if len(args) == 0 || args[0] != "run" {
		return fmt.Errorf("advisory requires run")
	}
	fs := flag.NewFlagSet("advisory run", flag.ContinueOnError)
	config := fs.String("config", "config/autonomy.yaml", "plane configuration")
	file := fs.String("file", "", "bounded OpenCode advisory packet JSON")
	jsonOut := fs.Bool("json", false, "emit invocation metadata and transient model output as JSON")
	if err := fs.Parse(args[1:]); err != nil {
		return err
	}
	if fs.NArg() != 0 {
		return fmt.Errorf("unexpected arguments")
	}
	if strings.TrimSpace(*file) == "" {
		return fmt.Errorf("--file required")
	}

	input, err := os.Open(*file)
	if err != nil {
		return err
	}
	raw, readErr := io.ReadAll(io.LimitReader(input, 2<<20+1))
	closeErr := input.Close()
	if readErr != nil {
		return readErr
	}
	if closeErr != nil {
		return closeErr
	}
	if len(raw) > 2<<20 {
		return fmt.Errorf("OPENCODE_ADVISORY_PACKET_SIZE_INVALID")
	}
	packet, err := plane.ParseOpenCodeAdvisoryPacket(raw)
	if err != nil {
		return err
	}
	cfg, err := plane.LoadConfig(*config)
	if err != nil {
		return err
	}
	root, err := filepath.Abs(filepath.Join(filepath.Dir(*config), ".."))
	if err != nil {
		return err
	}
	service := plane.NewOpenCodeAdvisoryService(root, cfg)
	var stdout, stderr bytes.Buffer
	invocation, runErr := service.Run(context.Background(), packet, &stdout, &stderr)

	if *jsonOut {
		payload := map[string]any{
			"invocation": invocation,
			"stdout":     stdout.String(),
			"stderr":     stderr.String(),
		}
		if runErr != nil {
			payload["error"] = runErr.Error()
		}
		encoded, marshalErr := json.MarshalIndent(payload, "", "  ")
		if marshalErr != nil {
			return marshalErr
		}
		fmt.Println(string(encoded))
	} else {
		if _, err = os.Stdout.Write(stdout.Bytes()); err != nil {
			return err
		}
		if _, err = os.Stderr.Write(stderr.Bytes()); err != nil {
			return err
		}
		if invocation.EvidencePath != "" {
			fmt.Fprintln(os.Stderr, "[OpenCodeAdvisor] evidence:", invocation.EvidencePath)
		}
	}
	return runErr
}

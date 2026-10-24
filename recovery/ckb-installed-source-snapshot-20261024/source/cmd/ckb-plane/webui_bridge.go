package main

import (
	"ckb-plane/internal/plane"
	"context"
	"flag"
	"fmt"
	"os"
	"os/signal"
	"path/filepath"
)

func runWebUIBridge(args []string) error {
	if len(args) == 0 {
		return fmt.Errorf("bridge requires check-config, once, or watch")
	}
	sub := args[0]
	if sub != "check-config" && sub != "once" && sub != "watch" && sub != "enable-control" && sub != "disable-control" {
		return fmt.Errorf("unknown bridge subcommand")
	}
	fs := flag.NewFlagSet("bridge "+sub, flag.ContinueOnError)
	config := fs.String("config", "config/local.yaml", "plane configuration (read only)")
	bridgeConfig := fs.String("bridge-config", "config/webui-bridge.json", "local GitHub mailbox configuration")
	if e := fs.Parse(args[1:]); e != nil {
		return e
	}
	if fs.NArg() != 0 {
		return fmt.Errorf("unexpected bridge arguments")
	}
	if sub == "enable-control" || sub == "disable-control" {
		return plane.EnableBridgeControl(context.Background(), *bridgeConfig, sub == "enable-control")
	}
	bc, e := plane.LoadBridgeConfig(*bridgeConfig)
	if e != nil {
		return e
	}
	c, e := plane.LoadConfig(*config)
	if e != nil {
		return e
	}
	if sub == "check-config" {
		fmt.Println("PASS: read-only bridge configuration; connectivity and Windows acceptance not checked")
		return nil
	}
	if bc.ControlEnabled {
		return fmt.Errorf("Control-enabled bridge requires controller run --bridge-config; standalone bridge remains read-only")
	}
	root, e := filepath.Abs(filepath.Join(filepath.Dir(*config), ".."))
	if e != nil {
		return e
	}
	b, e := plane.NewWebUIBridge(root, c.State.SQLitePath, bc)
	if e != nil {
		return e
	}
	defer b.Close()
	ctx, cancel := signal.NotifyContext(context.Background(), os.Interrupt)
	defer cancel()
	if sub == "once" {
		if e = b.Once(ctx); e != nil {
			return e
		}
		fmt.Println("PASS: mailbox cycle completed; no worker or queue actions permitted")
		return nil
	}
	fmt.Println("Read-only WebUI bridge listening through GitHub; Ctrl+C stops it. Worker and queue actions are disabled.")
	return b.Watch(ctx, func(e error) { fmt.Fprintln(os.Stderr, e) })
}

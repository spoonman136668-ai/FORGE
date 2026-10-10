// Command replay inspects a bounded shadow journal. It never contacts GitHub,
// schedules a workflow, executes science, or modifies CKB state.
package main

import (
	"github.com/spoonman136668-ai/forge"
	"encoding/json"
	"flag"
	"fmt"
	"os"
)

func main() {
	file := flag.String("journal", "", "read-only NDJSON journal path; '-' for stdin")
	flag.Parse()
	if *file == "" || flag.NArg() != 0 {
		fmt.Fprintln(os.Stderr, "usage: replay -journal <file|->")
		os.Exit(2)
	}
	input := os.Stdin
	if *file != "-" {
		var err error
		input, err = os.Open(*file)
		if err != nil {
			fmt.Fprintln(os.Stderr, err)
			os.Exit(1)
		}
		defer input.Close()
	}
	state, err := progression.Replay(input)
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
	output := struct {
		Schema             string               `json:"schema"`
		AdvisoryOnly       bool                 `json:"advisory_only"`
		DispatchAuthorized bool                 `json:"dispatch_authorized"`
		State              progression.State    `json:"state"`
		Intents            []progression.Intent `json:"intents"`
	}{Schema: "ckb.research.shadow-replay-output.v2", AdvisoryOnly: true, DispatchAuthorized: false, State: state, Intents: progression.Advisory(state)}
	enc := json.NewEncoder(os.Stdout)
	enc.SetIndent("", "  ")
	if err := enc.Encode(output); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
}

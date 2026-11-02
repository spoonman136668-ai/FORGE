// Bounded stdin/stdout adapter for the existing GenEnv implementation.
// No controller, network, source execution, publication or authority.
package main

import (
 "encoding/json"
 "fmt"
 "io"
 "os"

 "github.com/spoonman136668-ai/forge/genenv"
)

type request struct {
 Frozen genenv.Frozen `json:"frozen"`
 FrozenSHA256 string `json:"frozen_sha256"`
 History genenv.History `json:"history"`
 HistorySHA256 string `json:"history_sha256"`
}

func generate(input io.Reader, output io.Writer) error {
 limited := &io.LimitedReader{R: input, N: 256001}
 decoder := json.NewDecoder(limited)
 decoder.DisallowUnknownFields()
 var req request
 if err := decoder.Decode(&req); err != nil { return err }
 var trailing any
 if err := decoder.Decode(&trailing); err != io.EOF { return fmt.Errorf("GENENV_TRAILING_INPUT") }
 if limited.N == 0 { return fmt.Errorf("GENENV_INPUT_SIZE") }
 result, err := genenv.Generate(req.Frozen, req.FrozenSHA256, req.History, req.HistorySHA256)
 if err != nil { return err }
 return json.NewEncoder(output).Encode(result)
}

func main() {
 if err := generate(os.Stdin, os.Stdout); err != nil {
  fmt.Fprintln(os.Stderr, err)
  os.Exit(1)
 }
}

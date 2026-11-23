// Bounded stdin/stdout adapter for the existing GenEnv implementation.
// No controller, network, source execution, publication or authority.
package main

import (
 "encoding/json"
 "fmt"
 "io"
 "os"
 "reflect"

 "github.com/spoonman136668-ai/forge/genenv"
 "github.com/spoonman136668-ai/forge/promptlineage"
)

type request struct {
 Frozen genenv.Frozen `json:"frozen"`
 FrozenSHA256 string `json:"frozen_sha256"`
 History genenv.History `json:"history"`
 HistorySHA256 string `json:"history_sha256"`
 Promptbreeder *promptRequest `json:"promptbreeder,omitempty"`
}

type promptRequest struct {
 Frozen promptlineage.Frozen `json:"frozen"`
 FrozenSHA256 string `json:"frozen_sha256"`
}

type promptOutput struct {
 Schema string `json:"schema"`
 SourceSHA string `json:"source_sha"`
 Result promptlineage.Result `json:"result"`
}

type sourceOutput struct {
 Schema string `json:"schema"`
 SourceSHA string `json:"source_sha"`
 Result genenv.Result `json:"result"`
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
 if req.Promptbreeder != nil {
  // Two explicitly disjoint request forms share the same bounded utility.
  // A prompt is advisory text; executable source is validated separately.
  if !reflect.DeepEqual(req.Frozen, genenv.Frozen{}) ||
   !reflect.DeepEqual(req.History, genenv.History{}) ||
   req.FrozenSHA256 != "" || req.HistorySHA256 != "" {
   return fmt.Errorf("PROMPT_SOURCE_MIXED_REQUEST")
  }
  p := req.Promptbreeder
  result, err := promptlineage.Generate(p.Frozen, p.FrozenSHA256)
  if err != nil { return err }
  return json.NewEncoder(output).Encode(promptOutput{
   Schema: "forge.f139.prompt-source-output.v1", SourceSHA: p.Frozen.SourceSHA, Result: result})
 }
 result, err := genenv.Generate(req.Frozen, req.FrozenSHA256, req.History, req.HistorySHA256)
 if err != nil { return err }
 return json.NewEncoder(output).Encode(sourceOutput{Schema: "forge.f139.genenv-source-output.v1", SourceSHA: req.Frozen.SourceSHA, Result: result})
}

func main() {
 if err := generate(os.Stdin, os.Stdout); err != nil {
  fmt.Fprintln(os.Stderr, err)
  os.Exit(1)
 }
}

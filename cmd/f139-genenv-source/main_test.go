package main

import (
 "bytes"
 "encoding/json"
 "os/exec"
 "path/filepath"
 "strings"
 "testing"

 "github.com/spoonman136668-ai/forge/genenv"
)

func sourceFixture() request {
 h := genenv.History{Schema: genenv.HistorySchema, Lane: "Yggdrasil",
  SourceSHA: "992ef142aaa551156749a1de484a971b9a0c092f"}
 for i := 0; i < 3; i++ {
  vector := []int64{0, 0, 0}
  vector[i] = 1
  h.Records = append(h.Records, genenv.Record{Sequence: i+1,
   EvidenceSHA256: strings.Repeat(string(rune('a'+i)), 64), TrainingOnly: true,
   Classification: "CONSUMED_INDETERMINATE", Vector: vector})
 }
 f := genenv.Frozen{Schema: genenv.FrozenSchema, Lane: h.Lane, SourceSHA: h.SourceSHA,
  Epoch: 1, HistorySHA256: genenv.HistoryDigest(h), Base: []int64{0,0,0},
  MaxLevel: 1, MaxCandidates: 4, MaxOperations: 9,
  Requests: []genenv.Request{
   {ID: "shrinkage-abstention", Changes: []genenv.Change{{Index:0,Delta:1},{Index:1,Delta:1}}},
   {ID: "shrinkage-recency", Changes: []genenv.Change{{Index:0,Delta:1},{Index:2,Delta:1}}},
   {ID: "abstention-recency", Changes: []genenv.Change{{Index:1,Delta:1},{Index:2,Delta:1}}},
   {ID: "all-three", Changes: []genenv.Change{{Index:0,Delta:1},{Index:1,Delta:1},{Index:2,Delta:1}}},
  }}
 return request{Frozen:f, FrozenSHA256:genenv.FrozenDigest(f), History:h, HistorySHA256:genenv.HistoryDigest(h)}
}

func TestRealGenEnvCompilesFreshSourceAfterFixtureCatalogExhaustion(t *testing.T) {
 req := sourceFixture()
 raw, err := json.Marshal(req)
 if err != nil { t.Fatal(err) }
 var result bytes.Buffer
 if err = generate(bytes.NewReader(raw), &result); err != nil { t.Fatal(err) }
 python, err := exec.LookPath("python")
 if err != nil { t.Fatal("Python integration runtime required:", err) }
 cmd := exec.Command(python, "-B", "-m", "f139.check_genenv_source_integration")
 cmd.Dir = filepath.Join("..", "..")
 cmd.Stdin = bytes.NewReader(result.Bytes())
 output, err := cmd.CombinedOutput()
 if err != nil { t.Fatalf("source compilation failed: %v\n%s", err, output) }
 if !bytes.Contains(output, []byte(`"fresh_source_candidates": 4`)) { t.Fatalf("missing proof: %s",output) }
 t.Log(string(output))
}

func TestGeneratorAdapterRejectsPinDriftAndTrailingInput(t *testing.T) {
 req := sourceFixture()
 req.FrozenSHA256 = strings.Repeat("0",64)
 raw, _ := json.Marshal(req)
 var output bytes.Buffer
 if generate(bytes.NewReader(raw), &output) == nil || output.Len() != 0 { t.Fatal("accepted drift") }
 req = sourceFixture()
 raw, _ = json.Marshal(req)
 if generate(strings.NewReader(string(raw)+` {}`), &output) == nil { t.Fatal("accepted trailing JSON") }
}

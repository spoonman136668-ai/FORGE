package main

import (
 "bytes"
 "encoding/json"
 "strings"
 "testing"

 "github.com/spoonman136668-ai/forge/genenv"
 "github.com/spoonman136668-ai/forge/promptlineage"
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

func TestRealPromptbreederAndDisjointRequest(t *testing.T) {
 f := promptlineage.Frozen{Schema:promptlineage.Schema, Lane:"Yggdrasil",
  SourceSHA:"992ef142aaa551156749a1de484a971b9a0c092f", Epoch:1,
  Parent:"shrinkage standalone", Vocabulary:[]string{"abstention","recency"},
  MaxOperations:2, Operations:[]promptlineage.Operation{
   {Kind:"replace",Position:1,Replacement:"abstention"},
   {Kind:"replace",Position:1,Replacement:"recency"}}}
 req := request{Promptbreeder:&promptRequest{Frozen:f,FrozenSHA256:promptlineage.Digest(f)}}
 raw, _ := json.Marshal(req)
 var output bytes.Buffer
 if err := generate(bytes.NewReader(raw),&output); err != nil {t.Fatal(err)}
 var result promptOutput
 if err := json.Unmarshal(output.Bytes(),&result); err != nil {t.Fatal(err)}
 if result.Schema != "forge.f139.prompt-source-output.v1" || len(result.Result.Candidates)!=2 ||
  result.Result.Candidates[0].Prompt!="shrinkage abstention" ||
  result.Result.ScientificAccepted || result.Result.DispatchAuthorized {t.Fatal("bad prompt export")}
 req.Frozen = sourceFixture().Frozen
 raw, _ = json.Marshal(req)
 output.Reset()
 if generate(bytes.NewReader(raw),&output)==nil || output.Len()!=0 {t.Fatal("accepted mixed request")}
 req.Frozen = genenv.Frozen{}
 req.Promptbreeder.FrozenSHA256 = strings.Repeat("0",64)
 raw, _ = json.Marshal(req)
 if generate(bytes.NewReader(raw),&output)==nil || output.Len()!=0 {t.Fatal("accepted prompt pin drift")}
}

func TestRealGenEnvRecipeExport(t *testing.T) {
 req := sourceFixture()
 raw, err := json.Marshal(req)
 if err != nil { t.Fatal(err) }
 var result bytes.Buffer
 if err = generate(bytes.NewReader(raw), &result); err != nil { t.Fatal(err) }
 var decoded sourceOutput
 if err := json.Unmarshal(result.Bytes(), &decoded); err != nil { t.Fatal(err) }
 if len(decoded.Result.Candidates) != 4 { t.Fatal("missing generated recipes") }
 t.Log("F139_GENENV_RESULT=" + strings.TrimSpace(result.String()))
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

package researcharchive

// Source-only R20 observation tests. A Git blob identity is not first-use custody.
import (
 "bytes"
 "encoding/json"
 "errors"
 "io"
 "os"
 "strings"
 "testing"
)

type r20SourcePin struct {
 Lane string `json:"lane"`
 Experiment string `json:"experiment"`
 Repository string `json:"repository"`
 SourceHeadSHA string `json:"source_head_sha"`
 PreregPath string `json:"prereg_path"`
 PreregGitBlobSHA string `json:"prereg_git_blob_sha"`
 IndependentSourceBirthProven bool `json:"independent_source_birth_proven"`
 CompleteFirstUseReconciled bool `json:"complete_first_use_reconciled"`
 ScientificAccepted bool `json:"scientific_accepted"`
}
type r20Snapshot struct {
 Schema string `json:"schema"`
 Mode string `json:"mode"`
 Entries []r20SourcePin `json:"entries"`
}
var errR20=errors.New("R20_SOURCE_BLOB_OBSERVATION_NOT_SCIENTIFIC_CUSTODY")

var r20ExactGitBlobs = []struct{ Experiment, Path, Blob string }{
 {"W-R24","research/contrib/chatgpt/20261013-w-r24-missingness/pre.json","b31bf89b5f0e4300a36592ffacc97a6dac5a5edc"},
 {"W-R25","research/contrib/chatgpt/20261013-w-r25-alignment/prereg.json","0b430e6f701f939ca13e1899c8d937418c21a262"},
 {"W-R26","research/contrib/chatgpt/20261013-w-r26-next-prediction/prereg.json","708e05de6725d9a0fe6ab3f69eced46b9de5790b"},
 {"Y037","research/contrib/chatgpt/20261013-y037-diversity/pre.json","538f0e70a0be350f71b73ab9f5106679cf27fb5f"},
 {"Y038","research/contrib/chatgpt/20261013-y038-retention-capacity/prereg.json","e6ee97bef29ce53bfe30f20ddccac3e61fc910af"},
 {"Y039","research/contrib/chatgpt/20261013-y039-interrupt/prereg.json","cfeffae76c60f08d9781fbba4904b4d69ea461f5"},
}


func inspectR20(raw []byte, m Manifest) error {
 if len(raw)==0 || len(raw)>16384 || len(m.Entries)!=6 || !unambiguousJSON(raw){return errR20}
 var x r20Snapshot
 d:=json.NewDecoder(bytes.NewReader(raw))
 d.DisallowUnknownFields()
 if d.Decode(&x)!=nil || d.Decode(new(any))!=io.EOF{return errR20}
 if x.Schema!="forge.research-archive.r20-source-prereg-observations.v1" ||
  x.Mode!="GITHUB_IMMUTABLE_BLOBS_ONLY_NOT_INDEPENDENT_CUSTODY" ||
  len(x.Entries)!=len(m.Entries) || len(r20ExactGitBlobs)!=len(m.Entries){return errR20}
 seen:=map[string]bool{}
 for i,p:=range x.Entries {
  e:=m.Entries[i]
  exact:=r20ExactGitBlobs[i]
  if p.Experiment!=exact.Experiment || p.PreregPath!=exact.Path ||
   p.PreregGitBlobSHA!=exact.Blob || p.Lane!=e.Lane || p.Experiment!=e.Experiment ||
   p.Repository!=e.Repository || p.SourceHeadSHA!=e.HeadSHA ||
   !goodHex(p.PreregGitBlobSHA,40) ||
   !strings.HasPrefix(p.PreregPath,"research/contrib/chatgpt/20261013-") ||
   !(strings.HasSuffix(p.PreregPath,"/prereg.json")||strings.HasSuffix(p.PreregPath,"/pre.json")) ||
   strings.Contains(p.PreregPath,"..") || strings.Contains(p.PreregPath,"\\") ||
   p.IndependentSourceBirthProven || p.CompleteFirstUseReconciled ||
   p.ScientificAccepted || seen[p.Lane+":"+p.Experiment] {return errR20}
  seen[p.Lane+":"+p.Experiment]=true
 }
 return nil
}
func TestR20HistoricalBlobObservationsRemainUnqualified(t *testing.T) {
 manifestRaw,err:=os.ReadFile("../reference/research-originals/20261013-six-recent-archive-cohort.json")
 if err!=nil{t.Fatal(err)}
 m,err:=LoadManifest(manifestRaw)
 if err!=nil{t.Fatal(err)}
 raw,err:=os.ReadFile("../reference/research-originals/20261015-r20-prereg-source-observations.json")
 if err!=nil{t.Fatal(err)}
 if err:=inspectR20(raw,m);err!=nil{t.Fatal(err)}
 var original r20Snapshot
 if err:=json.Unmarshal(raw,&original);err!=nil{t.Fatal(err)}
 cases:=map[string]func(*r20Snapshot){
  "false_scientific_acceptance":func(x *r20Snapshot){x.Entries[0].ScientificAccepted=true},
  "false_first_use":func(x *r20Snapshot){x.Entries[0].CompleteFirstUseReconciled=true},
  "false_independent_birth":func(x *r20Snapshot){x.Entries[0].IndependentSourceBirthProven=true},
  "source_drift":func(x *r20Snapshot){x.Entries[0].SourceHeadSHA=strings.Repeat("a",40)},
  "wrong_prereg_blob":func(x *r20Snapshot){x.Entries[0].PreregGitBlobSHA="invalid"},
  "valid_length_prereg_blob_drift":func(x *r20Snapshot){x.Entries[0].PreregGitBlobSHA=strings.Repeat("a",40)},
  "valid_shape_prereg_path_drift":func(x *r20Snapshot){x.Entries[0].PreregPath="research/contrib/chatgpt/20261013-untrusted/pre.json"},
  "cross_lane":func(x *r20Snapshot){x.Entries[0].Lane="Yggdrasil"},
  "missing_original":func(x *r20Snapshot){x.Entries=x.Entries[1:]},
  "wrong_path":func(x *r20Snapshot){x.Entries[0].PreregPath="../private"},
 }
 for name,change:=range cases {
  t.Run(name,func(t *testing.T){
   copy:=original
   copy.Entries=append([]r20SourcePin(nil),original.Entries...)
   change(&copy)
   bad,err:=json.Marshal(copy)
   if err!=nil{t.Fatal(err)}
   if inspectR20(bad,m)==nil{t.Fatal("invalid R20 observation accepted")}
  })
 }
 if inspectR20(append(bytes.TrimSpace(raw),[]byte(" {}")...),m)==nil {
  t.Fatal("trailing JSON accepted")
 }
 if inspectR20(bytes.Replace(raw,[]byte(`"scientific_accepted":false`),
  []byte(`"scientific_accepted":false,"scientific_accepted":true`),1),m)==nil {
  t.Fatal("duplicate authority key accepted")
 }
}

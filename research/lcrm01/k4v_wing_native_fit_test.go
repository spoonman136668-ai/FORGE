package r1
import (
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "errors"
 "fmt"
 "os"
 "os/exec"
 "strconv"
 "strings"
 "testing"
)
type k4vRow struct {
 Before PublicGrid `json:"before"`
 Action int `json:"action"`
 After PublicGrid `json:"after"`
 Reward float64 `json:"reward"`
 Terminal bool `json:"terminal"`
}
type k4vEvidence struct {
 Schema string `json:"schema"`
 Replayed int `json:"replayed"`
 ActionCounts [3]int `json:"action_counts"`
 ChoiceCounts [3]int `json:"choice_counts"`
 Updates uint64 `json:"updates"`
 ColdRestored bool `json:"cold_restored"`
 CheckpointSHA string `json:"checkpoint_sha256"`
 LastAction int `json:"last_action"`
}
func k4vReadRows(t *testing.T) []k4vRow {
 t.Helper()
 raw,e:=os.ReadFile(os.Getenv("K4V_INPUT"));if e!=nil{t.Fatal(e)}
 var rows []k4vRow
 if e=json.Unmarshal(raw,&rows);e!=nil{t.Fatal(e)}
 if len(rows)!=5955{t.Fatalf("wrong FIT rows %d",len(rows))}
 return rows
}
func TestK4VActualFITReplay(t *testing.T){
 rows:=k4vReadRows(t)
 p:=New()
 var actions,choices [3]int
 for idx,r:=range rows{
   if r.Action<0||r.Action>2{t.Fatalf("illegal original action at %d",idx)}
   selected,e:=p.Choose(r.Before)
   if e!=nil||selected<0||selected>2{t.Fatalf("cannot choose at %d: %v",idx,e)}
   choices[selected]++;actions[r.Action]++
   if e=p.Observe(r.Before,r.Action,r.After,r.Reward,r.Terminal);e!=nil{t.Fatalf("FIT observed event %d failed: %v",idx,e)}
 }
 if p.Updates!=uint64(len(rows)){t.Fatalf("state missed FIT updates %d",p.Updates)}
 if actions[2]==0||actions[0]==0||actions[1]==0{t.Fatal("FIT missing legal actions")}
 checkpoint,e:=p.Snapshot();if e!=nil{t.Fatal(e)}
 clone,e:=Restore(checkpoint);if e!=nil{t.Fatal(e)}
 sentinel:=rows[len(rows)-1].After
 orig,e:=p.Choose(sentinel);if e!=nil{t.Fatal(e)}
 restored,e:=clone.Choose(sentinel);if e!=nil||orig!=restored{t.Fatal("snapshot changed FIT policy")}
 sbytes,e:=json.Marshal(sentinel);if e!=nil{t.Fatal(e)}
 sum:=sha256.Sum256(checkpoint)
 if e=os.WriteFile(os.Getenv("K4V_SNAPSHOT"),checkpoint,0600);e!=nil{t.Fatal(e)}
 if e=os.WriteFile(os.Getenv("K4V_SENTINEL"),sbytes,0600);e!=nil{t.Fatal(e)}
 command:=exec.Command(os.Args[0],"-test.run=^TestK4VColdChild$","-test.v")
 command.Env=append(os.Environ(),"K4V_CHILD=1","K4V_EXPECT="+strconv.Itoa(orig))
 output,e:=command.CombinedOutput()
 if e!=nil||!strings.Contains(string(output),"K4V_REAL_FIT_COLD_PASS"){t.Fatalf("cold process failed: %v %s",e,string(output))}
 receipt:=k4vEvidence{"mass.lcrm01.k4v.wingless-actual-fit-replay.v1",len(rows),actions,choices,p.Updates,true,hex.EncodeToString(sum[:]),orig}
 report,e:=json.Marshal(receipt);if e!=nil{t.Fatal(e)}
 if e=os.WriteFile(os.Getenv("K4V_OUTPUT"),report,0600);e!=nil{t.Fatal(e)}
 fmt.Printf("K4V_WINGLESS_FIT_REPLAY=PASS replayed=%d input_actions=%v choices=%v checkpoint=%s\n",len(rows),actions,choices,receipt.CheckpointSHA)
}
func TestK4VColdChild(t *testing.T){
 if os.Getenv("K4V_CHILD")!="1"{t.Skip("child process test only")}
 raw,e:=os.ReadFile(os.Getenv("K4V_SNAPSHOT"));if e!=nil{t.Fatal(e)}
 p,e:=Restore(raw);if e!=nil{t.Fatal(e)}
 sensorBytes,e:=os.ReadFile(os.Getenv("K4V_SENTINEL"));if e!=nil{t.Fatal(e)}
 var sensor PublicGrid
 if e=json.Unmarshal(sensorBytes,&sensor);e!=nil{t.Fatal(e)}
 action,e:=p.Choose(sensor);if e!=nil{t.Fatal(e)}
 expected,e:=strconv.Atoi(os.Getenv("K4V_EXPECT"));if e!=nil{t.Fatal(e)}
 if action!=expected{t.Fatal(errors.New("cold restored action diverged"))}
 fmt.Println("K4V_REAL_FIT_COLD_PASS")
}

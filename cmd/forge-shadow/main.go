// forge-shadow is an inactive research observer: no worker, reservation,
// accepted-ref write or scientific authority is available in this process.
package main
import(
 "context"
 "encoding/json"
 "flag"
 "fmt"
 "os"
 "os/signal"
 "time"
 "github.com/spoonman136668-ai/forge/researchstate"
 "github.com/spoonman136668-ai/forge/shadowcore"
)
func run(args []string)error{
 f:=flag.NewFlagSet("forge-shadow",flag.ContinueOnError)
 root:=f.String("archive","","existing offline journal directory")
 watch:=f.Bool("watch",false,"periodically observe the inactive archive")
 seconds:=f.Int("interval-seconds",30,"shadow observation interval, 1..300")
 if err:=f.Parse(args);err!=nil{return err}
 if *root==""||f.NArg()!=0{return fmt.Errorf("FORGE_SHADOW_ARCHIVE_REQUIRED")}
 if *watch{
  if *seconds<1||*seconds>300{return fmt.Errorf("FORGE_SHADOW_INTERVAL_INVALID")}
  ctx,stop:=signal.NotifyContext(context.Background(),os.Interrupt)
  defer stop()
  enc:=json.NewEncoder(os.Stdout)
  return shadowcore.Run(ctx,shadowcore.ArchiveObserver{Root:*root},time.Duration(*seconds)*time.Second,func(s shadowcore.Sample)error{return enc.Encode(s)})
 }
 journal,err:=researchstate.LoadArchive(*root)
 if err!=nil{return err}
 snapshot,err:=shadowcore.Observe(journal);if err!=nil{return err}
 encoder:=json.NewEncoder(os.Stdout)
 encoder.SetIndent("","  ")
 return encoder.Encode(snapshot)
}
func main(){if err:=run(os.Args[1:]);err!=nil{fmt.Fprintln(os.Stderr,err);os.Exit(1)}}

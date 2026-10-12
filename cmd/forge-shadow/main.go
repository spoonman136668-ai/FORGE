// forge-shadow is an inactive, read-only integration command. It cannot
// start workers, reserve cohorts, transfer authority, or mutate accepted refs.
package main
import(
 "encoding/json"
 "flag"
 "fmt"
 "os"
 "github.com/spoonman136668-ai/forge/researchstate"
 "github.com/spoonman136668-ai/forge/shadowcore"
)
func run(args []string)error{
 f:=flag.NewFlagSet("forge-shadow",flag.ContinueOnError)
 root:=f.String("archive","","existing offline journal directory")
 if err:=f.Parse(args);err!=nil{return err}
 if *root==""||f.NArg()!=0{return fmt.Errorf("FORGE_SHADOW_ARCHIVE_REQUIRED")}
 journal,err:=researchstate.LoadArchive(*root)
 if err!=nil{return err}
 snapshot,err:=shadowcore.Observe(journal);if err!=nil{return err}
 encoder:=json.NewEncoder(os.Stdout)
 encoder.SetIndent("","  ")
 return encoder.Encode(snapshot)
}
func main(){if err:=run(os.Args[1:]);err!=nil{fmt.Fprintln(os.Stderr,err);os.Exit(1)}}

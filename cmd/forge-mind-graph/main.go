package main

import (
 "context"
 "errors"
 "flag"
 "fmt"
 "os"
 "path/filepath"
 "strings"
 "time"

 "github.com/spoonman136668-ai/forge/mindcontext"
 "github.com/spoonman136668-ai/forge/mindgraph"
)
func run()error{
 var out string
 var projects string
 var max int
 flag.StringVar(&out,"out","","new absolute path for PRIVATE .ice graph and Obsidian vault (must not exist)")
 flag.StringVar(&projects,"projects","Wingless,Yggdrasil,Research","strict, read-only research projects")
 flag.IntVar(&max,"max",24,"maximum bounded Mind-Palace advisory records")
 flag.Parse()
 if out==""||max<1||max>mindcontext.MaxRecords{
  return errors.New("FORGE_MIND_GRAPH_OUTPUT_OR_BUDGET_MISSING")
 }
 // A public FORGE checkout is never a permissible destination for private
 // records, even when the output path is new and gitignored.
 work,err:=os.Getwd()
 if err!=nil{return errors.New("FORGE_MIND_GRAPH_WORKSPACE_IDENTITY_MISSING")}
 if !filepath.IsAbs(out){return errors.New("FORGE_MIND_GRAPH_ABSOLUTE_DESTINATION_REQUIRED")}
 rel,relErr:=filepath.Rel(work,filepath.Clean(out))
 if relErr==nil&&(rel=="."||rel!=".."&&!strings.HasPrefix(rel,".."+string(os.PathSeparator))){
  return errors.New("FORGE_MIND_GRAPH_PRIVATE_DESTINATION_INSIDE_PUBLIC_WORKTREE")
 }
 list:=strings.Split(projects,",")
 if len(list)<1||len(list)>3{return errors.New("FORGE_MIND_GRAPH_PROJECT_BOUNDS")}
 used:=map[string]bool{}
 for _,p:=range list{
  if used[p]||p!="Wingless"&&p!="Yggdrasil"&&p!="Research"{
   return errors.New("FORGE_MIND_GRAPH_UNAUTHORIZED_PROJECT")
  }
  used[p]=true
 }
 token:=os.Getenv("FORGE_MIND_PALACE_READ_TOKEN")
 if token==""{
  return errors.New("FORGE_MIND_GRAPH_READ_ONLY_PRIVATE_TOKEN_REQUIRED")
 }
 source,err:=mindcontext.NewGitHub(token,nil)
 if err!=nil{return err}
 ctx,cancel:=context.WithTimeout(context.Background(),60*time.Second)
 defer cancel()
 result,err:=(mindcontext.Reader{Source:source}).Read(ctx,list,max)
 if err!=nil{return fmt.Errorf("FORGE_MIND_GRAPH_PRIVATE_ICE_READ_BLOCKED: %w",err)}
 bundle,err:=mindgraph.Build(result)
 if err!=nil{return err}
 if err:=mindgraph.WriteNew(out,bundle);err!=nil{return err}
 // Neither untrusted source statements nor credentials are printed.
 fmt.Printf("FORGE_PRIVATE_ICE_GRAPH_OBSIDIAN_READY=PASS records=%d sources=%d\n",
  bundle.RecordCount,bundle.SourceCount)
 fmt.Println("FORGE_GRAPHIFY_INPUT_LOCAL_ONLY=READY")
 fmt.Println("FORGE_MIND_GRAPH_SCIENTIFIC_AUTHORITY=NONE")
 return nil
}
func main(){
 if err:=run();err!=nil{
  fmt.Fprintln(os.Stderr,err)
  os.Exit(1)
 }
}

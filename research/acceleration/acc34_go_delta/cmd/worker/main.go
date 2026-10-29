package main
import("encoding/json";"flag";"fmt";"os";a "example.org/acc34delta/isolated_core")
func main(){
 mode:=flag.String("mode","","mode")
 scenario:=flag.String("scenario","","scenario")
 seed:=flag.Int("seed",0,"paired development seed")
 events:=flag.Int("events",a.Events,"fixed source-free event count")
 flag.Parse()
 out,e:=a.Run(*mode,*scenario,*seed,*events)
 if e!=nil{fmt.Fprintln(os.Stderr,e);os.Exit(2)}
 if e=json.NewEncoder(os.Stdout).Encode(out);e!=nil{fmt.Fprintln(os.Stderr,e);os.Exit(3)}
}

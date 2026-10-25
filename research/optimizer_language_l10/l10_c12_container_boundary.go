package main

// L10-C12: source-free, invented canary boundary diagnostic.
// This is a trusted probe binary, NOT a sandbox for arbitrary model code or
// a protected scientific experiment. A successful probe has NO science permit.
import (
  "encoding/json"
  "fmt"
  "net"
  "os"
  "strings"
  "time"
)
type Receipt struct {
  Schema string `json:"schema"`
  HostCanaryReadable bool `json:"host_canary_readable"`
  ProcHostCanaryReadable bool `json:"proc_host_canary_readable"`
  NetworkEgressConnected bool `json:"network_egress_connected"`
  DockerSocketPresent bool `json:"docker_socket_present"`
  GitHubAuthEnvPresent bool `json:"github_auth_env_present"`
  CapabilitiesZero bool `json:"capabilities_zero"`
  ReadOnlyRoot bool `json:"read_only_root"`
  SourceFree bool `json:"source_free"`
  ProspectiveExamplesGenerated int `json:"prospective_examples_generated"`
  ScientificGo bool `json:"scientific_go"`
  Status string `json:"status"`
}
func canRead(path string) bool {
  _,err:=os.ReadFile(path)
  return err==nil
}
func noCaps() bool {
  data,err:=os.ReadFile("/proc/self/status")
  if err!=nil {return false}
  for _,line:=range strings.Split(string(data),"\n") {
    if strings.HasPrefix(line,"CapEff:") {
      return strings.TrimSpace(strings.TrimPrefix(line,"CapEff:"))=="0000000000000000"
    }
  }
  return false
}
func main() {
  if len(os.Args)!=2 || !strings.HasPrefix(os.Args[1],"/") {
    fmt.Fprintln(os.Stderr,"invalid canary path")
    os.Exit(2)
  }
  c,err:=net.DialTimeout("tcp","1.1.1.1:443",500*time.Millisecond)
  connected:=err==nil
  if c!=nil {_=c.Close()}
  canary:=os.Args[1]
  auth:=false
  for _,key:=range []string{"GITHUB_TOKEN","GH_TOKEN","ACTIONS_RUNTIME_TOKEN","ACTIONS_ID_TOKEN_REQUEST_TOKEN","ACTIONS_RUNTIME_URL"} {
    if os.Getenv(key)!="" {auth=true}
  }
  // This path must be unreachable because the container's rootfs is readonly.
  writeErr:=os.WriteFile("/l10-c12-rootfs-canary",[]byte("should-not-write"),0600)
  readOnly:=writeErr!=nil
  receipt:=Receipt{
    Schema:"forge.l10.c12.code-only-container-boundary-v1",
    HostCanaryReadable:canRead(canary),
    ProcHostCanaryReadable:canRead("/proc/1/root"+canary),
    NetworkEgressConnected:connected,
    DockerSocketPresent:canRead("/var/run/docker.sock"),
    GitHubAuthEnvPresent:auth,
    CapabilitiesZero:noCaps(),
    ReadOnlyRoot:readOnly,
    SourceFree:true,
    ProspectiveExamplesGenerated:0,
    ScientificGo:false,
  }
  if !receipt.HostCanaryReadable && !receipt.ProcHostCanaryReadable &&
     !receipt.NetworkEgressConnected && !receipt.DockerSocketPresent &&
     !receipt.GitHubAuthEnvPresent && receipt.CapabilitiesZero &&
     receipt.ReadOnlyRoot {
    receipt.Status="SOURCE_FREE_CONTAINER_CANARY_PASS"
  } else {
    receipt.Status="BLOCKED_CONTAINER_BOUNDARY_FAILURE"
  }
  _=json.NewEncoder(os.Stdout).Encode(receipt)
  if receipt.Status!="SOURCE_FREE_CONTAINER_CANARY_PASS" {os.Exit(2)}
}

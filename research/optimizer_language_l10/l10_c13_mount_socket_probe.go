package main

// L10-C13 source-free host-containment diagnostic (NOT arbitrary-code sandbox
// qualification, NOT a scientific-first-use or protected source permit).
// Runs only against an invented canary; no L9/L10 protected sample is accessed.
import (
 "encoding/json"
 "fmt"
 "net"
 "os"
 "path/filepath"
 "strings"
 "time"
)

func rootIsReadOnly(mountInfo string) bool {
 count := 0
 readOnly := false
 for _, line := range strings.Split(mountInfo, "\n") {
  fields := strings.Fields(line)
  if len(fields) < 7 || fields[4] != "/" { continue }
  count++
  ro, rw := false, false
  for _, opt := range strings.Split(fields[5], ",") {
   if opt == "ro" { ro = true }
   if opt == "rw" { rw = true }
  }
  readOnly = ro && !rw
 }
 return count == 1 && readOnly
}
func socketPathAbsentAndDenied(path string) (bool, bool) {
 _, statErr := os.Lstat(path) // Unlike ReadFile, detects Unix sockets and symlinks.
 pathAbsent := os.IsNotExist(statErr)
 conn, dialErr := net.DialTimeout("unix",path,200*time.Millisecond)
 if conn != nil { _ = conn.Close() }
 return pathAbsent, dialErr != nil
}
func fileDenied(path string) bool {
 _, err := os.ReadFile(path)
 return err != nil
}
func selfTest() bool {
 cases := []struct { data string; want bool }{
  {"100 1 0:23 / / ro,relatime - overlay overlay rw\n",true},
  {"100 1 0:23 / / rw,relatime - overlay overlay rw\n",false},
  {"100 1 0:23 / / ro,rw - overlay overlay rw\n",false},
  {"100 1 0:23 / / ro - overlay overlay rw\n101 1 0:23 / / ro - overlay overlay rw\n",false},
  {"100 1 0:23 / /home ro - overlay overlay rw\n",false},
 }
 for _, t := range cases { if rootIsReadOnly(t.data)!=t.want { return false } }
 tmp,err:=os.MkdirTemp("","l10-c13-synthetic-socket-")
 if err!=nil { return false }
 defer os.RemoveAll(tmp)
 p:=filepath.Join(tmp,"decoy.sock")
 absent,denied:=socketPathAbsentAndDenied(p)
 if !absent || !denied { return false }
 listener,err:=net.Listen("unix",p)
 if err!=nil { return false }
 defer listener.Close()
 absent,denied=socketPathAbsentAndDenied(p)
 if absent || denied { return false }
 return true
}
func main() {
 if len(os.Args)==2 && os.Args[1]=="--self-test" {
  if !selfTest() {fmt.Fprintln(os.Stderr,"C13_SELFTEST_FAIL");os.Exit(2)}
  fmt.Println("C13_PARSER_AND_SOCKET_NEGATIVE_CONTROLS_PASS")
  return
 }
 if len(os.Args)!=2 || !strings.HasPrefix(os.Args[1],"/") {
  fmt.Fprintln(os.Stderr,"C13_CANARY_PATH_REQUIRED"); os.Exit(2)
 }
 canary:=os.Args[1]
 mounts,err:=os.ReadFile("/proc/self/mountinfo")
 rootRO:=err==nil && rootIsReadOnly(string(mounts))
 // Root mount flag check is independent of the effective UID.
 rootWriteErr:=os.WriteFile("/l10-c13-unauthorized-root-write",[]byte("FAIL"),0600)
 rootWriteDenied:=rootWriteErr!=nil
 paths:=[]string{"/var/run/docker.sock","/run/docker.sock"}
 socketsAbsent,socketDialDenied:=true,true
 for _,p:=range paths {
  absent,denied:=socketPathAbsentAndDenied(p)
  socketsAbsent=socketsAbsent && absent
  socketDialDenied=socketDialDenied && denied
 }
 tcp,netErr:=net.DialTimeout("tcp","1.1.1.1:443",500*time.Millisecond)
 if tcp!=nil { _=tcp.Close() }
 credsAbsent:=true
 for _,name:=range []string{"GITHUB_TOKEN","GH_TOKEN","ACTIONS_RUNTIME_TOKEN","ACTIONS_ID_TOKEN_REQUEST_TOKEN"} {
  if os.Getenv(name)!="" {credsAbsent=false}
 }
 report:=map[string]interface{}{
  "schema":"forge.l10.c13.source-free-mount-socket-qualified-v1",
  "root_mount_flag_read_only":rootRO,
  "root_write_denied":rootWriteDenied,
  "docker_socket_paths_absent":socketsAbsent,
  "docker_socket_connect_denied":socketDialDenied,
  "invented_host_canary_read_denied":fileDenied(canary),
  "invented_proc_root_canary_read_denied":fileDenied("/proc/1/root"+canary),
  "network_tcp_probe_denied":netErr!=nil,
  "selected_github_auth_env_absent":credsAbsent,
  "prospective_samples_generated":0,
  "scientific_go":false,
 }
 ok:=rootRO && rootWriteDenied && socketsAbsent && socketDialDenied &&
   report["invented_host_canary_read_denied"].(bool) &&
   report["invented_proc_root_canary_read_denied"].(bool) &&
   netErr!=nil && credsAbsent
 if ok {report["status"]="C13_SCOPED_SOURCE_FREE_BOUNDARY_PASS"} else {
  report["status"]="C13_FAIL_CLOSED_BOUNDARY_NOT_QUALIFIED"
 }
 _=json.NewEncoder(os.Stdout).Encode(report)
 if !ok {os.Exit(2)}
}

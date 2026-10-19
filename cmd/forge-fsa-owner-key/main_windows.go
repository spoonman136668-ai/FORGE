//go:build windows

// forge-fsa-owner-key creates one operator-owned Ed25519 identity in the
// existing Windows profile. This is not a scientific start signer or an FSA
// service. A separate witness/ledger and backup still must be admitted.
package main

import (
 "crypto/ed25519"
 "crypto/rand"
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "errors"
 "fmt"
 "os"
 "path/filepath"
 "runtime"
 "syscall"
 "unsafe"
)

const (
 stateDir = "FORGE-FSA"
 stateFile = "owner-ed25519.dpapi"
 domain = "FORGE-FSA-OPERATOR-KEY-POSSESSION-NO-SCIENCE-AUTHORITY-V1\n"
 blobMagic = "FORGE-FSA-DPAPI-V1\x00"
)

type dataBlob struct { size uint32; data *byte }

var (
 crypt32 = syscall.NewLazyDLL("crypt32.dll")
 kernel32 = syscall.NewLazyDLL("kernel32.dll")
 protectProc = crypt32.NewProc("CryptProtectData")
 unprotectProc = crypt32.NewProc("CryptUnprotectData")
 localFreeProc = kernel32.NewProc("LocalFree")
)

func dpapi(data []byte, protect bool) ([]byte,error) {
 if len(data)==0 || len(data)>4096 {return nil, errors.New("invalid key length")}
 src := dataBlob{size:uint32(len(data)), data:&data[0]}
 var dst dataBlob
 proc:=unprotectProc
 if protect {proc=protectProc}
 ok, _, err:=proc.Call(
    uintptr(unsafe.Pointer(&src)), 0, 0, 0, 0, 1,
    uintptr(unsafe.Pointer(&dst))) // CRYPTPROTECT_UI_FORBIDDEN
 runtime.KeepAlive(data)
 if ok==0 {
     if err!=nil && err!=syscall.Errno(0) {return nil,fmt.Errorf("Windows DPAPI unavailable: %w",err)}
     return nil,errors.New("Windows DPAPI unavailable")
 }
 if dst.data==nil || dst.size==0 || dst.size>16384 {return nil,errors.New("Windows DPAPI returned invalid length")}
 defer localFreeProc.Call(uintptr(unsafe.Pointer(dst.data)))
 return append([]byte(nil), unsafe.Slice(dst.data,int(dst.size))...),nil
}

func keyPath() (string,error) {
 base:=os.Getenv("LOCALAPPDATA")
 if base=="" || !filepath.IsAbs(base) {return "",errors.New("LOCALAPPDATA must be a native absolute Windows path")}
 return filepath.Join(base,stateDir,stateFile),nil
}

func loadSeed(path string) ([]byte,error) {
 data,err:=os.ReadFile(path)
 if err!=nil {return nil,err}
 if len(data)<=len(blobMagic) || string(data[:len(blobMagic)])!=blobMagic {
     return nil,errors.New("unknown protected key format")
 }
 seed,err:=dpapi(data[len(blobMagic):],false)
 if err!=nil {return nil,err}
 if len(seed)!=ed25519.SeedSize {return nil,errors.New("protected seed length drift")}
 return seed,nil
}

func bootstrap(path string) error {
 root:=filepath.Dir(path)
 if err:=os.MkdirAll(root,0700);err!=nil {return err}
 st,err:=os.Lstat(root)
 if err!=nil || !st.IsDir() || st.Mode()&os.ModeSymlink!=0 {return errors.New("FSA owner state directory invalid")}
 if _,probeErr:=os.Lstat(path);probeErr==nil {return errors.New("FSA owner identity already exists: refusing overwrite")} else if !os.IsNotExist(probeErr) {return probeErr}
 seed:=make([]byte,ed25519.SeedSize)
 if _,err:=rand.Read(seed);err!=nil {return err}
 defer func(){for i:=range seed {seed[i]=0}}()
 ciphertext,err:=dpapi(seed,true)
 if err!=nil {return err}
 f,err:=os.OpenFile(path,os.O_WRONLY|os.O_CREATE|os.O_EXCL,0600)
 if err!=nil {return err}
 data:=append([]byte(blobMagic),ciphertext...)
 _,writeErr:=f.Write(data)
 syncErr:=f.Sync()
 closeErr:=f.Close()
 if writeErr!=nil || syncErr!=nil || closeErr!=nil {return errors.New("FSA key persistence failed, state requires operator inspection")}
 return nil
}

type report struct {
 Schema string `json:"schema"`
 PublicKeyEd25519Hex string `json:"public_key_ed25519_hex"`
 PublicKeySHA256 string `json:"public_key_sha256"`
 PossessionSignatureHex string `json:"possession_signature_hex"`
 State string `json:"state"`
 ExternalWitnessVerified bool `json:"external_witness_verified"`
 ScientificStartAuthorized bool `json:"scientific_start_authorized"`
 IndependentlyRecoverable bool `json:"independently_recoverable"`
}

func show(path string) error {
 seed,err:=loadSeed(path)
 if err!=nil {return err}
 private:=ed25519.NewKeyFromSeed(seed)
 for i:=range seed {seed[i]=0}
 defer func(){for i:=range private {private[i]=0}}()
 public:=private.Public().(ed25519.PublicKey)
 challenge:=[]byte(domain+hex.EncodeToString(public)+"\n")
 proof:=ed25519.Sign(private,challenge)
 if !ed25519.Verify(public,challenge,proof) {return errors.New("FSA possession proof invalid")}
 fingerprint:=sha256.Sum256(public)
 return json.NewEncoder(os.Stdout).Encode(report{
    Schema:"forge.fsa.local-operator-public-pin.v1",
    PublicKeyEd25519Hex:hex.EncodeToString(public),
    PublicKeySHA256:hex.EncodeToString(fingerprint[:]),
    PossessionSignatureHex:hex.EncodeToString(proof),
    State:"LOCAL_OPERATOR_POSSESSION_ONLY",
    ExternalWitnessVerified:false,
    ScientificStartAuthorized:false,
    IndependentlyRecoverable:false,
 })
}

func main() {
 if len(os.Args)!=2 || (os.Args[1]!="init" && os.Args[1]!="prove") {
     fmt.Fprintln(os.Stderr,"usage: forge-fsa-owner-key init|prove (Windows CurrentUser DPAPI; no science permit)")
     os.Exit(2)
 }
 path,err:=keyPath()
 if err==nil && os.Args[1]=="init" {err=bootstrap(path)}
 if err==nil {err=show(path)}
 if err!=nil {fmt.Fprintln(os.Stderr,"FSA_OWNER_KEY_STOP:",err);os.Exit(1)}
}

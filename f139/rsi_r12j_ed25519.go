// R12-J: verify Ed25519 only. The signing private key is never accepted.
// go run FILE --public-key <base64-32> --signature <base64-64> < message
package main

import (
    "bytes"
    "crypto/ed25519"
    "encoding/base64"
    "flag"
    "fmt"
    "io"
    "os"
)

func main() {
    pubArg := flag.String("public-key", "", "pinned Ed25519 key, base64")
    sigArg := flag.String("signature", "", "detached signature, base64")
    flag.Parse()
    if flag.NArg() != 0 {
        os.Exit(2)
    }
    pub, err := base64.StdEncoding.Strict().DecodeString(*pubArg)
    if err != nil || len(pub) != ed25519.PublicKeySize ||
        base64.StdEncoding.EncodeToString(pub) != *pubArg {
        os.Exit(2)
    }
    sig, err := base64.StdEncoding.Strict().DecodeString(*sigArg)
    if err != nil || len(sig) != ed25519.SignatureSize ||
        base64.StdEncoding.EncodeToString(sig) != *sigArg {
        os.Exit(2)
    }
    payload, err := io.ReadAll(io.LimitReader(os.Stdin, 8193))
    if err != nil || len(payload) == 0 || len(payload) > 8192 ||
        !bytes.HasPrefix(payload,
            []byte("FORGE-F139-RSI-ORIGINAL-PREEXECUTION-V1\n")) {
        os.Exit(2)
    }
    if !ed25519.Verify(ed25519.PublicKey(pub), payload, sig) {
        os.Exit(1)
    }
    fmt.Println("F139_RSI_R12J_ED25519_VERIFIED")
}

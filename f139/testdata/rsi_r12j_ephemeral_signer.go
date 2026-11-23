// R12-J test fixture only: ephemeral Ed25519 signer, NO persistence.
// The private key never leaves process memory. NOT original-owner custody.
package main
import (
    "crypto/ed25519"
    "crypto/rand"
    "encoding/base64"
    "encoding/json"
    "io"
    "os"
)
func main() {
    pub, priv, err := ed25519.GenerateKey(rand.Reader)
    if err != nil { os.Exit(2) }
    body, err := io.ReadAll(io.LimitReader(os.Stdin, 8193))
    if err != nil || len(body) == 0 || len(body) > 8192 { os.Exit(2) }
    proof := map[string]string{
        "public_key_b64":base64.StdEncoding.EncodeToString(pub),
        "signature_b64":base64.StdEncoding.EncodeToString(
            ed25519.Sign(priv, body)),
    }
    if json.NewEncoder(os.Stdout).Encode(proof) != nil { os.Exit(2) }
}

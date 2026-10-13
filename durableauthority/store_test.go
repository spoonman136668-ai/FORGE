package durableauthority

import (
	"crypto/ed25519"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func fixture(t *testing.T) (ed25519.PublicKey, ed25519.PrivateKey) {
	t.Helper()
	seed := sha256.Sum256([]byte("TEST ONLY: independent shadow custody signer"))
	key := ed25519.NewKeyFromSeed(seed[:])
	return key.Public().(ed25519.PublicKey), key
}
func signed(t *testing.T, priv ed25519.PrivateKey, lane, id, head string, epoch uint64) Grant {
	t.Helper()
	g := Grant{Schema: GrantSchema, Lane: lane, OriginalID: id,
		FrozenSHA256: strings.Repeat("a", 64), IntentSHA256: strings.Repeat("b", 64),
		OwnerID: "shadow_owner", OwnerEpoch: epoch, ExpectedHeadSHA256: head}
	b, err := grantPayload(g)
	if err != nil {t.Fatal(err)}
	g.SignatureHex = hex.EncodeToString(ed25519.Sign(priv, append([]byte(grantDomain), b...)))
	return g
}
func TestOriginalFirstUseDurablyConsumedAcrossRestartAndBothLanes(t *testing.T) {
	pub, priv := fixture(t)
	dir := t.TempDir()
	a, err := OpenShadow(dir, pub)
	if err != nil {t.Fatal(err)}
	if _, err := OpenShadow(dir, pub); !errors.Is(err, ErrBlocked) {t.Fatal("duplicate writer opened")}
	g := signed(t, priv, "Wingless", "original_w1", zeroSHA, 7)
	wHead, err := a.Reserve(g)
	if err != nil {t.Fatal(err)}
	if _, err := a.Reserve(g); !errors.Is(err, ErrConsumed) {t.Fatal("replay did not fail consumed", err)}
	y := signed(t, priv, "Yggdrasil", "original_y1", wHead, 13)
	yHead, err := a.Reserve(y)
	if err != nil {t.Fatal(err)}
	if wHead == yHead {t.Fatal("different records share hash")}
	if err := a.Close(); err != nil {t.Fatal(err)}
	after, err := OpenShadow(dir, pub)
	if err != nil {t.Fatal(err)}
	if _, err := after.Reserve(signed(t, priv, "Wingless", "original_w1", yHead, 14)); !errors.Is(err, ErrConsumed) {t.Fatal("restarted owner replayed first use")}
	if _, err := after.Reserve(signed(t, priv, "Wingless", "original_w2", wHead, 14)); !errors.Is(err, ErrBlocked) {t.Fatal("stale head accepted")}
	if _, err := after.Reserve(signed(t, priv, "Yggdrasil", "original_y2", yHead, 12)); !errors.Is(err, ErrBlocked) {t.Fatal("old owner epoch accepted")}
	if err := after.Close(); err != nil {t.Fatal(err)}
	snapshot, err := Load(dir, pub)
	if err != nil || len(snapshot.Entries) != 2 || !snapshot.ReservedOriginals["Wingless:original_w1"] || !snapshot.ReservedOriginals["Yggdrasil:original_y1"] {t.Fatal(snapshot, err)}
}
func TestGrantNotSelfAuthorizingAndIntegrityRejection(t *testing.T) {
	pub, priv := fixture(t)
	dir := t.TempDir()
	a, err := OpenShadow(dir, pub)
	if err != nil {t.Fatal(err)}
	g := signed(t, priv, "Wingless", "original_w1", zeroSHA, 1)
	g.IntentSHA256 = strings.Repeat("f", 64)
	if _, err := a.Reserve(g); !errors.Is(err, ErrBlocked) {t.Fatal("tampered grant accepted")}
	g = signed(t, priv, "Wingless", "original_w1", zeroSHA, 1)
	if _, err := a.Reserve(g); err != nil {t.Fatal(err)}
	if err := a.Close(); err != nil {t.Fatal(err)}
	path := filepath.Join(dir, fileName(1))
	original, err := os.ReadFile(path)
	if err != nil {t.Fatal(err)}
	var r Record
	if err := json.Unmarshal(original, &r); err != nil {t.Fatal(err)}
	// Recomputing a checksum does not counterfeit signed reservation custody.
	r.FrozenSHA256 = strings.Repeat("f", 64)
	r.RecordSHA256, err = recordHash(r)
	if err != nil {t.Fatal(err)}
	forged, err := json.Marshal(r)
	if err != nil {t.Fatal(err)}
	if err := os.WriteFile(path, append(forged, '\n'), 0600); err != nil {t.Fatal(err)}
	if _, err := Load(dir, pub); !errors.Is(err, ErrBlocked) {t.Fatal("forged custody accepted", err)}
	if _, err := OpenShadow(dir, pub); !errors.Is(err, ErrBlocked) {t.Fatal("corrupt custody opened")}
}
func TestCrashLockAndTornWriteNeverAutoRecover(t *testing.T) {
	pub, priv := fixture(t)
	dir := t.TempDir()
	a, err := OpenShadow(dir, pub)
	if err != nil {t.Fatal(err)}
	if _, err := a.Reserve(signed(t, priv, "Wingless", "original_w1", zeroSHA, 1)); err != nil {t.Fatal(err)}
	// Simulate process crash: no graceful Close() / lock release.
	if err := a.guard.Close(); err != nil {t.Fatal(err)}
	a.closed = true
	if _, err := OpenShadow(dir, pub); !errors.Is(err, ErrBlocked) {t.Fatal("stale crash lock stolen")}
	snap, err := Load(dir, pub)
	if err != nil || !snap.ReservedOriginals["Wingless:original_w1"] {t.Fatal("crash lost consumed original", err)}
	if err := os.WriteFile(filepath.Join(dir, fileName(1)), []byte("{torn"), 0600); err != nil {t.Fatal(err)}
	if _, err := Load(dir, pub); !errors.Is(err, ErrBlocked) {t.Fatal("torn original treated as unused")}
}
func TestUnknownFilesAndGapFailClosed(t *testing.T) {
	pub, priv := fixture(t)
	for _, mode := range []string{"unexpected", "gap"} {
		t.Run(mode, func(t *testing.T) {
			dir := t.TempDir()
			a, err := OpenShadow(dir, pub)
			if err != nil {t.Fatal(err)}
			if _, err := a.Reserve(signed(t, priv, "Yggdrasil", "original_y", zeroSHA, 3)); err != nil {t.Fatal(err)}
			if err := a.Close(); err != nil {t.Fatal(err)}
			if mode == "unexpected" {err = os.WriteFile(filepath.Join(dir, "untrusted"), []byte("x"), 0600)} else {
				err = os.Rename(filepath.Join(dir, fileName(1)), filepath.Join(dir, fileName(2)))
			}
			if err != nil {t.Fatal(err)}
			if _, err := Load(dir, pub); !errors.Is(err, ErrBlocked) {t.Fatal("invalid journal admitted", err)}
		})
	}
}

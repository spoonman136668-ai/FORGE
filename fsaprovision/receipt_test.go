package fsaprovision

import (
	"bytes"
	"crypto/ed25519"
	"encoding/hex"
	"encoding/json"
	"errors"
	"strings"
	"testing"
)

func testKeys()([3]ed25519.PrivateKey) {
	var out [3]ed25519.PrivateKey
	for i:=0;i<3;i++ {out[i]=ed25519.NewKeyFromSeed(bytes.Repeat([]byte{byte(i+1)},32))}
	return out
}
func signed(s Statement,k ed25519.PrivateKey)SignedStatement {
	raw,_:=json.Marshal(s)
	return SignedStatement{Statement:s,SignatureHex:hex.EncodeToString(ed25519.Sign(k,append([]byte(statementDomain),raw...)))}
}
func fixture(t *testing.T)(Pin,Bundle,[3]ed25519.PrivateKey) {
	t.Helper()
	keys:=testKeys()
	pin:=Pin{
		ArchiveID:strings.Repeat("a",64),BindingSHA256:strings.Repeat("b",64),
		AuthorityEpoch:4,ProvisioningEpoch:2,
		AuthorityAttestor:keys[0].Public().(ed25519.PublicKey),
		WitnessAttestor:keys[1].Public().(ed25519.PublicKey),
		FloorAttestor:keys[2].Public().(ed25519.PublicKey),
	}
	bundle:=Bundle{Schema:Schema}
	rows:=make([]SignedStatement,3)
	for i,role:=range []string{RoleAuthority,RoleWitness,RoleFloor} {
		s:=Statement{Schema:Schema,Role:role,ArchiveID:pin.ArchiveID,
			BindingSHA256:pin.BindingSHA256,AuthorityEpoch:pin.AuthorityEpoch,
			ProvisioningEpoch:pin.ProvisioningEpoch,
			HostIdentitySHA256:strings.Repeat(string('c'+rune(i)),64),
			StorageIdentitySHA256:strings.Repeat(string('3'+rune(i)),64),
			FailureDomainID:[]string{"dc-a","dc-b","dc-c"}[i],
			ServiceSPKISHA256:strings.Repeat(string('1'+rune(i)),64),
			ExternalEvidenceSHA256:strings.Repeat(string('7'+rune(i)),64),
		}
		rows[i]=signed(s,keys[i])
	}
	bundle.Authority,bundle.Witness,bundle.Floor=rows[0],rows[1],rows[2]
	pin.BundleSHA256,_=BundleDigest(bundle)
	return pin,bundle,keys
}
func resign(t *testing.T,p *Pin,b *Bundle,keys [3]ed25519.PrivateKey) {
	t.Helper()
	b.Authority=signed(b.Authority.Statement,keys[0])
	b.Witness=signed(b.Witness.Statement,keys[1])
	b.Floor=signed(b.Floor.Statement,keys[2])
	var err error
	p.BundleSHA256,err=BundleDigest(*b)
	if err!=nil{t.Fatal(err)}
}
func TestPinnedDistinctThreeDomainClaims(t *testing.T){
	pin,bundle,_:=fixture(t)
	v,err:=New(pin);if err!=nil{t.Fatal(err)}
	got,err:=v.Verify(bundle)
	if err!=nil||got.BundleSHA256!=pin.BundleSHA256||got.ProvisioningEpoch!=2{
		t.Fatalf("valid three-domain descriptor rejected: %+v %v",got,err)
	}
	raw,err:=json.Marshal(bundle);if err!=nil{t.Fatal(err)}
	if _,err=v.VerifyJSON(raw);err!=nil{t.Fatalf("canonical JSON rejected %v",err)}
	pin.AuthorityAttestor[0]^=1 // verifier must have cloned externally pinned keys.
	if _,err=v.Verify(bundle);err!=nil{t.Fatalf("mutable caller key changed verification: %v",err)}
}
func TestRejectsIndependentCorrectlySignedButCollocatedClaims(t *testing.T){
	for _,tc:=range []struct{name string;change func(*Bundle)}{
		{"host",func(b *Bundle){b.Floor.Statement.HostIdentitySHA256=b.Authority.Statement.HostIdentitySHA256}},
		{"storage",func(b *Bundle){b.Witness.Statement.StorageIdentitySHA256=b.Authority.Statement.StorageIdentitySHA256}},
		{"failure_domain",func(b *Bundle){b.Floor.Statement.FailureDomainID=b.Witness.Statement.FailureDomainID}},
		{"service_identity",func(b *Bundle){b.Witness.Statement.ServiceSPKISHA256=b.Floor.Statement.ServiceSPKISHA256}},
	} {
		t.Run(tc.name,func(t *testing.T){
			pin,bundle,keys:=fixture(t);tc.change(&bundle);resign(t,&pin,&bundle,keys)
			v,err:=New(pin);if err!=nil{t.Fatal(err)}
			if _,err=v.Verify(bundle);!errors.Is(err,ErrUntrusted){
				t.Fatal("collocated descriptors accepted",err)
			}
		})
	}
}
func TestRejectsForgerySubstitutionAndDrift(t *testing.T) {
	for _,tc:=range []struct{name string;change func(*Pin,*Bundle,[3]ed25519.PrivateKey)}{
		{"forged_signature",func(p *Pin,b *Bundle,k [3]ed25519.PrivateKey){b.Witness.SignatureHex=strings.Repeat("0",128);p.BundleSHA256,_=BundleDigest(*b)}},
		{"wrong_role",func(p *Pin,b *Bundle,k [3]ed25519.PrivateKey){b.Floor.Statement.Role=RoleAuthority;resign(t,p,b,k)}},
		{"wrong_epoch",func(p *Pin,b *Bundle,k [3]ed25519.PrivateKey){b.Witness.Statement.AuthorityEpoch++;resign(t,p,b,k)}},
		{"foreign_archive",func(p *Pin,b *Bundle,k [3]ed25519.PrivateKey){b.Witness.Statement.ArchiveID=strings.Repeat("d",64);resign(t,p,b,k)}},
		{"unqualified_evidence",func(p *Pin,b *Bundle,k [3]ed25519.PrivateKey){b.Floor.Statement.ExternalEvidenceSHA256="";resign(t,p,b,k)}},
		{"wrong_signer",func(p *Pin,b *Bundle,k [3]ed25519.PrivateKey){b.Witness=signed(b.Witness.Statement,k[0]);p.BundleSHA256,_=BundleDigest(*b)}},
		{"digest_mismatch",func(p *Pin,b *Bundle,k [3]ed25519.PrivateKey){p.BundleSHA256=strings.Repeat("0",64)}},
	}{
		t.Run(tc.name,func(t *testing.T){
			p,b,k:=fixture(t);tc.change(&p,&b,k);v,err:=New(p)
			if err!=nil{t.Fatal(err)}
			if _,err=v.Verify(b);!errors.Is(err,ErrUntrusted){t.Fatalf("invalid provision accepted %v",err)}
		})
	}
}
func TestNoUnpinnedOrSharedAttestorKeys(t *testing.T) {
	p,b,_:=fixture(t)
	p.FloorAttestor=p.AuthorityAttestor
	if _,err:=New(p);!errors.Is(err,ErrUntrusted){t.Fatalf("shared attestor accepted %v",err)}
	p,b,_=fixture(t)
	p.BundleSHA256=""
	if _,err:=New(p);!errors.Is(err,ErrUntrusted){t.Fatalf("missing pin accepted %v",err)}
	p,b,_=fixture(t)
	p.AuthorityAttestor=nil
	if _,err:=New(p);!errors.Is(err,ErrUntrusted){t.Fatalf("missing signer accepted %v",err)}
	_ = b
}
func TestCanonicalJSONOnly(t *testing.T){
	p,b,_:=fixture(t);v,err:=New(p);if err!=nil{t.Fatal(err)}
	raw,_:=json.Marshal(b)
	for _,bad:=range [][]byte{
		append(bytes.Clone(raw),' '),
		append(bytes.Clone(raw),[]byte("{}")...),
		bytes.Replace(raw,[]byte(`"schema":`),[]byte(`"ignored":5,"schema":`),1),
		[]byte(`{"schema":"forge.fsa.provision.v1","schema":"forge.fsa.provision.v1"}`),
	} {
		if _,err=v.VerifyJSON(bad);!errors.Is(err,ErrUntrusted){t.Fatal("noncanonical JSON accepted",err)}
	}
	if _,err=v.VerifyJSON(nil);!errors.Is(err,ErrUntrusted){t.Fatal("empty input accepted")}
	if _,err=v.VerifyJSON(bytes.Repeat([]byte("x"),MaxBundleBytes+1));!errors.Is(err,ErrUntrusted){t.Fatal("oversized input accepted")}
}

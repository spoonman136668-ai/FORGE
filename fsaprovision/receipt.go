// Package fsaprovision validates externally pinned, independently signed
// provisioning descriptors. It does not provision, deploy or certify hosts.
package fsaprovision

import (
	"bytes"
	"crypto/ed25519"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"io"
	"strings"
)

const (
	Schema = "forge.fsa.provision.v1"
	RoleAuthority = "authority"
	RoleWitness = "witness"
	RoleFloor = "floor"
	statementDomain = "FORGE-FSA-PROVISION-STATEMENT-V1\n"
	bundleDomain = "FORGE-FSA-PROVISION-BUNDLE-V1\n"
	MaxBundleBytes = 16384
)

var ErrUntrusted = errors.New("FORGE_FSA_PROVISIONING_UNTRUSTED_OR_UNVERIFIED")

// Statement is a signed claim by a separately pinned attestor.
// Its physical truth MUST be independently established before deployment.
type Statement struct {
	Schema string `json:"schema"`
	Role string `json:"role"`
	ArchiveID string `json:"archive_id"`
	BindingSHA256 string `json:"binding_sha256"`
	AuthorityEpoch uint64 `json:"authority_epoch"`
	ProvisioningEpoch uint64 `json:"provisioning_epoch"`
	HostIdentitySHA256 string `json:"host_identity_sha256"`
	StorageIdentitySHA256 string `json:"storage_identity_sha256"`
	FailureDomainID string `json:"failure_domain_id"`
	ServiceSPKISHA256 string `json:"service_spki_sha256"`
	ExternalEvidenceSHA256 string `json:"external_evidence_sha256"`
}

type SignedStatement struct {
	Statement Statement `json:"statement"`
	SignatureHex string `json:"signature_hex"`
}

type Bundle struct {
	Schema string `json:"schema"`
	Authority SignedStatement `json:"authority"`
	Witness SignedStatement `json:"witness"`
	Floor SignedStatement `json:"floor"`
}

// Pin MUST originate outside the supplied bundle and from an authenticated,
// immutable operator decision. Recomputing it from untrusted input defeats
// the binding. The keys are independent attestor keys, not service credentials.
type Pin struct {
	ArchiveID string
	BindingSHA256 string
	AuthorityEpoch uint64
	ProvisioningEpoch uint64
	BundleSHA256 string
	AuthorityAttestor ed25519.PublicKey
	WitnessAttestor ed25519.PublicKey
	FloorAttestor ed25519.PublicKey
}

type Verifier struct{ pin Pin }

// ValidatedDescriptor is structural, cryptographic verification only.
// It is NOT physical independence, hardware durability or science authority.
type ValidatedDescriptor struct {
	BundleSHA256 string
	ArchiveID string
	BindingSHA256 string
	ProvisioningEpoch uint64
}

func hex64(s string) bool {
	if len(s)!=64 { return false }
	for _, c := range s {
		if !((c>='0'&&c<='9')||(c>='a'&&c<='f')) { return false }
	}
	return true
}
func domainID(s string) bool {
	if len(s)<3 || len(s)>96 {return false}
	for _,c:=range s {
		if !((c>='a'&&c<='z')||(c>='0'&&c<='9')||c=='-') {return false}
	}
	return true
}
func distinct(a,b,c []byte)bool {
	return !bytes.Equal(a,b) && !bytes.Equal(a,c) && !bytes.Equal(b,c)
}
func New(pin Pin) (*Verifier,error) {
	if !hex64(pin.ArchiveID)||!hex64(pin.BindingSHA256)||!hex64(pin.BundleSHA256)||
		pin.AuthorityEpoch==0||pin.ProvisioningEpoch==0||
		len(pin.AuthorityAttestor)!=ed25519.PublicKeySize||
		len(pin.WitnessAttestor)!=ed25519.PublicKeySize||
		len(pin.FloorAttestor)!=ed25519.PublicKeySize||
		!distinct(pin.AuthorityAttestor,pin.WitnessAttestor,pin.FloorAttestor) {
		return nil,ErrUntrusted
	}
	pin.AuthorityAttestor=bytes.Clone(pin.AuthorityAttestor)
	pin.WitnessAttestor=bytes.Clone(pin.WitnessAttestor)
	pin.FloorAttestor=bytes.Clone(pin.FloorAttestor)
	return &Verifier{pin:pin},nil
}
func stampedDigest(domain string, raw []byte)string {
	d:=sha256.New()
	_,_=d.Write([]byte(domain))
	_,_=d.Write(raw)
	return hex.EncodeToString(d.Sum(nil))
}

// BundleDigest is a serialization helper, NOT a trust bootstrap.
// Use only a separately acquired expected digest as Pin.BundleSHA256.
func BundleDigest(b Bundle) (string,error) {
	raw,err:=json.Marshal(b)
	if err!=nil{return "",err}
	return stampedDigest(bundleDomain,raw),nil
}
func (v *Verifier) verifyStatement(s SignedStatement,role string,key ed25519.PublicKey) error {
	x:=s.Statement
	if x.Schema!=Schema||x.Role!=role||
		x.ArchiveID!=v.pin.ArchiveID||x.BindingSHA256!=v.pin.BindingSHA256||
		x.AuthorityEpoch!=v.pin.AuthorityEpoch||
		x.ProvisioningEpoch!=v.pin.ProvisioningEpoch||
		!hex64(x.HostIdentitySHA256)||!hex64(x.StorageIdentitySHA256)||
		!hex64(x.ServiceSPKISHA256)||!hex64(x.ExternalEvidenceSHA256)||
		!domainID(x.FailureDomainID)||
		len(s.SignatureHex)!=ed25519.SignatureSize*2 ||
		s.SignatureHex!=strings.ToLower(s.SignatureHex) {
		return ErrUntrusted
	}
	sig,err:=hex.DecodeString(s.SignatureHex)
	if err!=nil||len(sig)!=ed25519.SignatureSize{return ErrUntrusted}
	raw,err:=json.Marshal(x)
	if err!=nil{return ErrUntrusted}
	message:=append([]byte(statementDomain),raw...)
	if !ed25519.Verify(key,message,sig){return ErrUntrusted}
	return nil
}

// Verify accepts exactly one descriptor for each of three roles. All three
// must claim disjoint host, storage, failure-domain and service-key identity.
// Even correct independent signatures cannot prove actual physical separation.
func (v *Verifier) Verify(b Bundle) (ValidatedDescriptor,error) {
	if v==nil || b.Schema!=Schema {return ValidatedDescriptor{},ErrUntrusted}
	digest,err:=BundleDigest(b)
	if err!=nil||digest!=v.pin.BundleSHA256{return ValidatedDescriptor{},ErrUntrusted}
	items:=[]SignedStatement{b.Authority,b.Witness,b.Floor}
	roles:=[]string{RoleAuthority,RoleWitness,RoleFloor}
	keys:=[]ed25519.PublicKey{v.pin.AuthorityAttestor,v.pin.WitnessAttestor,v.pin.FloorAttestor}
	for i,s:=range items {
		if err:=v.verifyStatement(s,roles[i],keys[i]);err!=nil{return ValidatedDescriptor{},ErrUntrusted}
		for j:=0;j<i;j++ {
			x,y:=s.Statement,items[j].Statement
			if x.HostIdentitySHA256==y.HostIdentitySHA256||
				x.StorageIdentitySHA256==y.StorageIdentitySHA256||
				x.FailureDomainID==y.FailureDomainID||
				x.ServiceSPKISHA256==y.ServiceSPKISHA256 {
				return ValidatedDescriptor{},ErrUntrusted
			}
		}
	}
	return ValidatedDescriptor{
		BundleSHA256:digest,ArchiveID:v.pin.ArchiveID,
		BindingSHA256:v.pin.BindingSHA256,ProvisioningEpoch:v.pin.ProvisioningEpoch,
	},nil
}

// VerifyJSON requires the exact canonical JSON bytes of the signed bundle.
// This avoids duplicate JSON fields, unknown fields, trailing input and
// alternate encodings at the wire boundary.
func (v *Verifier) VerifyJSON(raw []byte) (ValidatedDescriptor,error) {
	if len(raw)==0||len(raw)>MaxBundleBytes{return ValidatedDescriptor{},ErrUntrusted}
	var b Bundle
	d:=json.NewDecoder(bytes.NewReader(raw))
	d.DisallowUnknownFields()
	if d.Decode(&b)!=nil{return ValidatedDescriptor{},ErrUntrusted}
	var trailing any
	if d.Decode(&trailing)!=io.EOF{return ValidatedDescriptor{},ErrUntrusted}
	canonical,err:=json.Marshal(b)
	if err!=nil||!bytes.Equal(canonical,raw){return ValidatedDescriptor{},ErrUntrusted}
	return v.Verify(b)
}

package main

import (
	"bytes"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"testing"

	u01 "github.com/spoonman136668-ai/forge/research/acc61_u01"
)

func fixture(t *testing.T, n int, seed uint64) (request, request, request) {
	t.Helper()
	weights, err := u01.StructuredWeights(n,seed)
	if err != nil { t.Fatal(err) }
	compressed, err := u01.EncodeRLE(weights)
	if err != nil { t.Fatal(err) }
	raw := make([]byte,len(weights))
	for i,v := range weights {raw[i]=byte(v)}
	dir:=t.TempDir()
	densePath:=filepath.Join(dir,"dense.bin")
	rlePath:=filepath.Join(dir,"encoded.rle")
	if err:=os.WriteFile(densePath,raw,0600);err!=nil{t.Fatal(err)}
	if err:=os.WriteFile(rlePath,compressed,0600);err!=nil{t.Fatal(err)}
	rawSHA:=sha256.Sum256(raw)
	encodedSHA:=sha256.Sum256(compressed)
	base:=request{Size:n,Seed:seed,Variant:"structured",WeightSHA:hex.EncodeToString(rawSHA[:]),Queries:8}
	dense:=base
	dense.Arm="DENSE";dense.ArtifactPath=densePath;dense.ArtifactSHA=hex.EncodeToString(rawSHA[:])
	decoded:=base
	decoded.Arm="RLE_PREDECODE";decoded.ArtifactPath=rlePath;decoded.ArtifactSHA=hex.EncodeToString(encodedSHA[:])
	stream:=decoded
	stream.Arm="RLE_STREAM"
	return dense,decoded,stream
}

func TestACC125OSWorkerExactSourceAndPredictions(t *testing.T) {
	a,b,c:=fixture(t,64,161101)
	var results [3]result
	for i,req:=range []request{a,b,c} {
		var output bytes.Buffer
		if err:=run(req,&output);err!=nil{t.Fatalf("ACC125_WORKER:%s:%v",req.Arm,err)}
		if err:=json.Unmarshal(output.Bytes(),&results[i]);err!=nil{t.Fatal(err)}
		if results[i].Queries!=8 || results[i].SourceWeightSHA256!=a.WeightSHA || !results[i].CPUandRSSQualified || results[i].PeakPhysicalRSSBytes==0 {
			t.Fatalf("ACC125_CUSTODY_OR_COUNTER:%s:%+v",req.Arm,results[i])
		}
		if results[i].ScientificAcceptance!="NOT_GRANTED" {t.Fatal("ACC125_SCIENCE_LEAK")}
	}
	for i:=1;i<len(results);i++ {
		if results[0].InputSHA256!=results[i].InputSHA256 || results[0].OutputSHA256!=results[i].OutputSHA256 {
			t.Fatalf("ACC125_HASH_PARITY_FAIL:%s",results[i].Arm)
		}
	}
	if results[2].LiveRepresentationBytes>=results[0].LiveRepresentationBytes {
		t.Fatal("ACC125_STREAMING_REPRESENTATION_NOT_SMALLER")
	}
	if results[1].LiveRepresentationBytes!=results[0].LiveRepresentationBytes {
		t.Fatal("ACC125_PREDECODE_MUST_RETAIN_DENSE_STORAGE")
	}
	if results[0].SourceEncodedBytes!=0 || results[2].SourceEncodedBytes==0 {t.Fatal("ACC125_SOURCE_FORMAT")}
	if results[1].PeakLoadingBytes<=results[0].PeakLoadingBytes {t.Fatal("ACC125_PREDECODE_LOAD_PEAK_UNDERCHARGED")}
}

func TestACC125TamperFailsClosed(t *testing.T) {
	a,b,_:=fixture(t,64,161101)
	mutators:=[]func(*request){
		func(x *request){x.Queries=4097},
		func(x *request){x.Seed=999},
		func(x *request){x.Size=42},
		func(x *request){x.WeightSHA=strings.Repeat("0",64)},
		func(x *request){x.ArtifactSHA=strings.Repeat("f",64)},
		func(x *request){x.Arm="ORACLE"},
		func(x *request){x.Variant="reserved_test"},
		func(x *request){x.ArtifactPath=""},
	}
	for i,m:=range mutators {
		copy:=a
		m(&copy)
		var output bytes.Buffer
		if err:=run(copy,&output);err==nil || output.Len()!=0 {t.Fatalf("ACC125_FAILOPEN:%d",i)}
	}
	raw,err:=os.ReadFile(b.ArtifactPath)
	if err!=nil{t.Fatal(err)}
	raw[1]=0 // zero-length encoded run
	damaged:=filepath.Join(t.TempDir(),"damaged.rle")
	if err:=os.WriteFile(damaged,raw,0600);err!=nil{t.Fatal(err)}
	b.ArtifactPath=damaged
	digest:=sha256.Sum256(raw)
	b.ArtifactSHA=hex.EncodeToString(digest[:])
	if err:=run(b,&bytes.Buffer{});err==nil {t.Fatal("ACC125_CORRUPT_RLE_ACCEPTED")}
}

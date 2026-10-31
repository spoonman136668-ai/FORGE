package main

import (
	"crypto/sha256"
	"encoding/binary"
	"encoding/hex"
	"reflect"
	"os"
	"path/filepath"
	"strings"
	"testing"

	u01 "github.com/spoonman136668-ai/forge/research/acc61_u01"
)

func TestACC125IndependentOracleMatchesDenseKernel(t *testing.T) {
	for _,size:=range []int{64,128} {
		for _,seed:=range u01.FrozenSeeds {
			weights,err:=u01.StructuredWeights(size,seed)
			if err!=nil{t.Fatal(err)}
			inputSHA,outputSHA,err:=independentHashes(weights,size,seed,5)
			if err!=nil{t.Fatal(err)}
			inputs:=sha256.New()
			outputs:=sha256.New()
			var one [1]byte
			var word [8]byte
			for index:=uint32(0);index<5;index++{
				v,err:=u01.InputVector(size,seed,index)
				if err!=nil{t.Fatal(err)}
				for _,x:=range v{one[0]=byte(x);_,_=inputs.Write(one[:])}
				answers,err:=u01.DenseMatVec(weights,size,v)
				if err!=nil{t.Fatal(err)}
				for _,x:=range answers{
					binary.LittleEndian.PutUint64(word[:],uint64(x))
					_,_=outputs.Write(word[:])
				}
			}
			if inputSHA!=hex.EncodeToString(inputs.Sum(nil))||
				outputSHA!=hex.EncodeToString(outputs.Sum(nil))||
				!reflect.DeepEqual(inputSHA,hex.EncodeToString(inputs.Sum(nil))) {
				t.Fatalf("ACC125_ORACLE_INCONSISTENT:size=%d:seed=%d",size,seed)
			}
		}
	}
}

func TestACC125InvalidCohortFailsBeforeBinaryRead(t *testing.T) {
	for _,queries:=range []int{0,-1,4097}{
		if _,err:=runAll("/missing/worker",queries,1);err==nil{
			t.Fatalf("ACC125_INVALID_QUERY_ACCEPTED:%d",queries)
		}
	}
}

func TestACC126ReceiptAtomicExclusiveNoOverwrite(t *testing.T) {
	destination := filepath.Join(t.TempDir(), "u01-receipt.json")
	first := &receipt{
		Schema: "forge.acc125.u01.cold-process-matrix.v1",
		ScientificAcceptance: "NOT_GRANTED",
		Decision: "RESOURCE_AND_SCIENCE_WITNESS_UNVERIFIED",
	}
	if err := writeReceiptExclusive(destination, first); err != nil {
		t.Fatalf("ACC126_FIRST_RECEIPT_WRITE:%v", err)
	}
	before, err := os.ReadFile(destination)
	if err != nil { t.Fatal(err) }
	if !strings.Contains(string(before), "NOT_GRANTED") {
		t.Fatal("ACC126_RECEIPT_SCIENCE_STATUS_MISSING")
	}
	second := &receipt{Schema:"TAMPER",ScientificAcceptance:"PROMOTED"}
	if err := writeReceiptExclusive(destination, second); err == nil {
		t.Fatal("ACC126_RECEIPT_OVERWRITE_MUST_FAIL")
	}
	after, err := os.ReadFile(destination)
	if err != nil { t.Fatal(err) }
	if string(before) != string(after) {
		t.Fatal("ACC126_RECEIPT_CHANGED_AFTER_REJECTED_OVERWRITE")
	}
	if err := writeReceiptExclusive("", first); err == nil {
		t.Fatal("ACC126_EMPTY_RECEIPT_DESTINATION_ACCEPTED")
	}
	if err := writeReceiptExclusive(filepath.Join(t.TempDir(),"x.json"), nil); err == nil {
		t.Fatal("ACC126_NIL_RECEIPT_ACCEPTED")
	}
}

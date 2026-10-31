package main

import (
	"crypto/sha256"
	"encoding/binary"
	"encoding/hex"
	"reflect"
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

// ACC-125 source-free, opt-in controller for the 60 frozen U01 child runs.
// It spawns only the U01 child binary passed by an authorized caller.
// It is not a scheduler, FORGE owner controller, model trainer, or promotion path.
// Each cold child loads ONLY its arm-specific, SHA-verified source representation.
package main

import (
	"bytes"
	"context"
	"crypto/sha256"
	"encoding/binary"
	"encoding/hex"
	"encoding/json"
	"errors"
	"flag"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"strconv"
	"time"

	u01 "github.com/spoonman136668-ai/forge/research/acc61_u01"
)

type childRecord struct {
	Schema string `json:"schema"`
	Arm string `json:"arm"`
	Size int `json:"size"`
	Seed uint64 `json:"seed"`
	Variant string `json:"variant"`
	Queries int `json:"queries"`
	ArtifactSHA256 string `json:"artifact_sha256"`
	SourceWeightSHA256 string `json:"source_weight_sha256"`
	InputSHA256 string `json:"input_sha256"`
	OutputSHA256 string `json:"output_sha256"`
	SourceEncodedBytes int `json:"source_encoded_bytes"`
	SourceDenseBytes int `json:"source_dense_bytes"`
	LiveRepresentationBytes int `json:"live_representation_bytes"`
	LiveScratchBytes int `json:"live_scratch_bytes"`
	PeakLoadingBytes int `json:"peak_loading_bytes"`
	WallNanos int64 `json:"wall_nanos"`
	UserCPUNanos int64 `json:"user_cpu_nanos"`
	SystemCPUNanos int64 `json:"system_cpu_nanos"`
	PeakPhysicalRSSBytes uint64 `json:"peak_physical_rss_bytes"`
	CPUandRSSQualified bool `json:"cpu_and_rss_qualified"`
	ScientificAcceptance string `json:"scientific_acceptance"`
}

type measuredChild struct {
	Record childRecord `json:"record"`
	ExternalWallNanos int64 `json:"external_wall_nanos"`
	ExternalUserCPUNanos int64 `json:"external_user_cpu_nanos"`
	ExternalSystemCPUNanos int64 `json:"external_system_cpu_nanos"`
}

type caseRecord struct {
	Size int `json:"size"`
	Seed uint64 `json:"seed"`
	SourceWeightSHA256 string `json:"source_weight_sha256"`
	EncodedArtifactSHA256 string `json:"encoded_artifact_sha256"`
	IndependentInputSHA256 string `json:"independent_input_sha256"`
	IndependentOutputSHA256 string `json:"independent_output_sha256"`
	Children []measuredChild `json:"children"`
}

type receipt struct {
	Schema string `json:"schema"`
	WorkerBinarySHA256 string `json:"worker_binary_sha256"`
	HostOS string `json:"host_os"`
	HostArch string `json:"host_arch"`
	QueriesPerChild int `json:"queries_per_child"`
	ColdChildCount int `json:"cold_child_count"`
	FullFrozen60 bool `json:"full_frozen_60"`
	Cases []caseRecord `json:"cases"`
	AllExactOutputHashesMatched bool `json:"all_exact_output_hashes_matched"`
	SourceRestrictedToStructured bool `json:"source_restricted_to_structured"`
	ParentGenerationCPUPeakRSSQualified bool `json:"parent_generation_cpu_peak_rss_qualified"`
	PredecodeFitCostQualified bool `json:"predecode_fit_cost_qualified"`
	IndependentScienceWitness bool `json:"independent_science_witness"`
	ScientificAcceptance string `json:"scientific_acceptance"`
	Decision string `json:"decision"`
}

func digest(data []byte) string {
	sum:=sha256.Sum256(data)
	return hex.EncodeToString(sum[:])
}

// This independently computes exact signed int64 scalar results from the
// original tensor; it does not call any of the three worker implementations.
func independentHashes(weights []int8, n int, seed uint64, queries int) (string,string,error) {
	ih,oh:=sha256.New(),sha256.New()
	var word [8]byte
	var one [1]byte
	for index:=0;index<queries;index++{
		vector,err:=u01.InputVector(n,seed,uint32(index))
		if err!=nil{return "","",err}
		for _,v:=range vector {one[0]=byte(v);_,_=ih.Write(one[:])}
		for row:=0;row<n;row++ {
			var s int64
			for col:=0;col<n;col++ {
				s+=int64(weights[row*n+col])*int64(vector[col])
			}
			binary.LittleEndian.PutUint64(word[:],uint64(s))
			_,_=oh.Write(word[:])
		}
	}
	return hex.EncodeToString(ih.Sum(nil)),hex.EncodeToString(oh.Sum(nil)),nil
}

func runChild(binaryPath string, arm string, n int, seed uint64, queries int, path, artifactSHA, weightSHA string, timeout time.Duration) (measuredChild,error) {
	ctx,cancel:=context.WithTimeout(context.Background(),timeout)
	defer cancel()
	args:=[]string{
		"-arm",arm,"-size",strconv.Itoa(n),"-seed",strconv.FormatUint(seed,10),
		"-variant","structured","-artifact",path,
		"-artifact-sha256",artifactSHA,"-weight-sha256",weightSHA,
		"-queries",strconv.Itoa(queries),
	}
	cmd:=exec.CommandContext(ctx,binaryPath,args...)
	cmd.Env=os.Environ()
	var stdout,stderr bytes.Buffer
	cmd.Stdout=&stdout; cmd.Stderr=&stderr
	start:=time.Now()
	err:=cmd.Run()
	wall:=time.Since(start).Nanoseconds()
	if err!=nil {
		if ctx.Err()!=nil{return measuredChild{},fmt.Errorf("ACC125_CHILD_TIMEOUT:%s:%d:%d:%w",arm,n,seed,ctx.Err())}
		return measuredChild{},fmt.Errorf("ACC125_CHILD_FAILED:%s:%d:%d:%w:%s",arm,n,seed,err,stderr.String())
	}
	var child childRecord
	if err:=json.Unmarshal(bytes.TrimSpace(stdout.Bytes()),&child);err!=nil{
		return measuredChild{},fmt.Errorf("ACC125_CHILD_NONJSON:%s:%w",arm,err)
	}
	if child.Schema!="forge.acc125.u01.isolated-child.v1"||
		child.Arm!=arm||child.Size!=n||child.Seed!=seed||child.Variant!="structured"||
		child.Queries!=queries||child.ArtifactSHA256!=artifactSHA||
		child.SourceWeightSHA256!=weightSHA||child.ScientificAcceptance!="NOT_GRANTED"||
		!child.CPUandRSSQualified||child.PeakPhysicalRSSBytes==0||
		child.UserCPUNanos<0||child.SystemCPUNanos<0{
		return measuredChild{},errors.New("ACC125_CHILD_RECEIPT_CONTRACT_VIOLATION")
	}
	if cmd.ProcessState==nil {return measuredChild{},errors.New("ACC125_MISSING_NATIVE_PROCESS_STATE")}
	return measuredChild{
		Record:child,ExternalWallNanos:wall,
		ExternalUserCPUNanos:cmd.ProcessState.UserTime().Nanoseconds(),
		ExternalSystemCPUNanos:cmd.ProcessState.SystemTime().Nanoseconds(),
	},nil
}

func runAll(workerPath string, queries int, childTimeout time.Duration) (*receipt,error) {
	if queries<1||queries>4096 {return nil,errors.New("ACC125_INVALID_QUERY_LIMIT")}
	binaryContents,err:=os.ReadFile(workerPath)
	if err!=nil {return nil,fmt.Errorf("ACC125_BINARY_READ:%w",err)}
	out:=&receipt{
		Schema:"forge.acc125.u01.cold-process-matrix.v1",
		WorkerBinarySHA256:digest(binaryContents),
		HostOS:runtime.GOOS,HostArch:runtime.GOARCH,QueriesPerChild:queries,
		FullFrozen60:queries==4096,
		SourceRestrictedToStructured:true,
		ParentGenerationCPUPeakRSSQualified:false,
		PredecodeFitCostQualified:false,
		IndependentScienceWitness:false,
		ScientificAcceptance:"NOT_GRANTED",Decision:"RESOURCE_AND_SCIENCE_WITNESS_UNVERIFIED",
		AllExactOutputHashesMatched:true,
	}
	for _,n:=range u01.FrozenSizes {
		for _,seed:=range u01.FrozenSeeds {
			weights,err:=u01.StructuredWeights(n,seed)
			if err!=nil{return nil,err}
			encoded,err:=u01.EncodeRLE(weights)
			if err!=nil{return nil,err}
			dense:=make([]byte,len(weights))
			for i,v:=range weights{dense[i]=byte(v)}
			weightSHA:=digest(dense)
			encodedSHA:=digest(encoded)
			inputSHA,outputSHA,err:=independentHashes(weights,n,seed,queries)
			if err!=nil{return nil,err}
			dir,err:=os.MkdirTemp("","forge-acc125-*")
			if err!=nil{return nil,err}
			// Remove the staged artifacts after all three isolated children finish.
			densePath:=filepath.Join(dir,"dense.bin")
			encodedPath:=filepath.Join(dir,"rle.bin")
			err=os.WriteFile(densePath,dense,0600)
			if err==nil {err=os.WriteFile(encodedPath,encoded,0600)}
			if err!=nil {os.RemoveAll(dir);return nil,err}
			entry:=caseRecord{
				Size:n,Seed:seed,SourceWeightSHA256:weightSHA,
				EncodedArtifactSHA256:encodedSHA,
				IndependentInputSHA256:inputSHA,IndependentOutputSHA256:outputSHA,
			}
			arms:=[]struct{arm,path,sha string}{
				{"DENSE",densePath,weightSHA},
				{"RLE_PREDECODE",encodedPath,encodedSHA},
				{"RLE_STREAM",encodedPath,encodedSHA},
			}
			for _,a:=range arms {
				child,runErr:=runChild(workerPath,a.arm,n,seed,queries,a.path,a.sha,weightSHA,childTimeout)
				if runErr!=nil {os.RemoveAll(dir);return nil,runErr}
				if child.Record.InputSHA256!=inputSHA||
					child.Record.OutputSHA256!=outputSHA||
					child.Record.SourceWeightSHA256!=weightSHA {
					os.RemoveAll(dir)
					return nil,fmt.Errorf("ACC125_INDEPENDENT_EXACT_OUTPUT_FAIL:%d:%d:%s",n,seed,a.arm)
				}
				entry.Children=append(entry.Children,child)
				out.ColdChildCount++
			}
			if err:=os.RemoveAll(dir);err!=nil{return nil,err}
			out.Cases=append(out.Cases,entry)
		}
	}
	if len(out.Cases)!=20||out.ColdChildCount!=60 {
		return nil,errors.New("ACC125_FROZEN_COHORT_DRIFT")
	}
	if queries!=4096 {out.Decision="SMOKE_ONLY_NOT_FROZEN_EXECUTION"}
	return out,nil
}

// writeReceiptExclusive commits a complete JSON receipt once. It never
// replaces a prior result, even under concurrent invocations, and stages the
// temporary file in the destination directory for same-filesystem atomicity.
func writeReceiptExclusive(destination string, record *receipt) error {
	if destination == "" || record == nil {
		return errors.New("ACC126_INVALID_RECEIPT_DESTINATION_OR_RECORD")
	}
	staged, err := os.CreateTemp(filepath.Dir(destination), ".acc126-receipt-*.tmp")
	if err != nil { return fmt.Errorf("ACC126_TEMP_CREATE:%w", err) }
	name := staged.Name()
	defer os.Remove(name)
	if err := staged.Chmod(0600); err != nil {
		_ = staged.Close()
		return fmt.Errorf("ACC126_TEMP_MODE:%w", err)
	}
	if err := json.NewEncoder(staged).Encode(record); err != nil {
		_ = staged.Close()
		return fmt.Errorf("ACC126_TEMP_ENCODE:%w", err)
	}
	if err := staged.Sync(); err != nil {
		_ = staged.Close()
		return fmt.Errorf("ACC126_TEMP_SYNC:%w", err)
	}
	if err := staged.Close(); err != nil {
		return fmt.Errorf("ACC126_TEMP_CLOSE:%w", err)
	}
	if err := os.Link(name, destination); err != nil {
		return fmt.Errorf("ACC126_RECEIPT_EXISTS_OR_HARDLINK_UNSUPPORTED:%w", err)
	}
	return nil
}

func main(){
	var bin,out string
	var queries,timeoutSec int
	flag.StringVar(&bin,"worker-bin","","qualified worker executable (compiled separately)")
	flag.StringVar(&out,"out","","required JSON receipt file path")
	flag.IntVar(&queries,"queries",4096,"must equal 4096 for original frozen study")
	flag.IntVar(&timeoutSec,"child-timeout-sec",1200,"finite timeout per cold child")
	flag.Parse()
	if bin==""||out==""||timeoutSec<1||timeoutSec>7200{
		fmt.Fprintln(os.Stderr,"ACC125_RUNNER_MISSING_OR_INVALID_ARGS")
		os.Exit(2)
	}
	receipt,err:=runAll(bin,queries,time.Duration(timeoutSec)*time.Second)
	if err!=nil{fmt.Fprintln(os.Stderr,err);os.Exit(2)}
	// External child wall/CPU readings are recorded, but parent source-generation
	// CPU/RSS is not charged, so whole-study resource acceptance stays blocked.
	if err:=writeReceiptExclusive(out,receipt);err!=nil{
		fmt.Fprintln(os.Stderr,err)
		os.Exit(2)
	}
	fmt.Printf("ACC125_COLD_CHILDREN=%d FROZEN=%t DECISION=%s\n",
		receipt.ColdChildCount,receipt.FullFrozen60,receipt.Decision)
}

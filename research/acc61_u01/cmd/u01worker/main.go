// ACC-125 runs one isolated U01 weight-representation experiment per process.
// It never generates a dense source tensor in the measured RLE_STREAM worker.
// A separate, independent controller must materialize and hash the inputs
// before dispatch. No benchmark or science admission occurs on compilation.
package main

import (
	"crypto/sha256"
	"encoding/binary"
	"encoding/hex"
	"encoding/json"
	"errors"
	"flag"
	"fmt"
	"io"
	"os"
	"runtime"
	"strconv"
	"strings"
	"time"

	u01 "github.com/spoonman136668-ai/forge/research/acc61_u01"
)

const schema = "forge.acc125.u01.isolated-child.v1"

type request struct {
	Arm string
	Size int
	Seed uint64
	Variant string
	ArtifactPath string
	ArtifactSHA string
	WeightSHA string
	Queries int
}

type result struct {
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

func isHex256(value string) bool {
	if len(value) != 64 || strings.ToLower(value) != value {
		return false
	}
	for _, c := range value {
		if c < '0' || c > '9' && c < 'a' || c > 'f' {
			return false
		}
	}
	return true
}

func decodeSourceHashRLE(src []byte, n int) (string, error) {
	if err := u01.ValidateRLE(src, n*n); err != nil {
		return "", err
	}
	h := sha256.New()
	var chunk [4096]byte
	for offset := 0; offset < len(src); offset += 5 {
		remaining := int(binary.LittleEndian.Uint32(src[offset+1:]))
		for i := range chunk {
			chunk[i] = src[offset]
		}
		for remaining > 0 {
			size := remaining
			if size > len(chunk) { size = len(chunk) }
			_, _ = h.Write(chunk[:size])
			remaining -= size
		}
	}
	return hex.EncodeToString(h.Sum(nil)), nil
}

func denseBytesMatVec(raw []byte, n int, vector []int8) ([]int64, error) {
	if err := u01.ValidateMatrix(n, len(raw), vector); err != nil { return nil, err }
	result := make([]int64, n)
	for row := 0; row < n; row++ {
		var sum int64
		for col := 0; col < n; col++ {
			sum += int64(int8(raw[row*n+col])) * int64(vector[col])
		}
		result[row] = sum
	}
	return result, nil
}

// run never opens or synthesizes a second representation inside the child.
// It hashes every one of the 4,096 frozen input vectors and every output row.
func run(req request, out io.Writer) error {
	if req.Arm != "DENSE" && req.Arm != "RLE_PREDECODE" && req.Arm != "RLE_STREAM" {
		return errors.New("ACC125_UNKNOWN_ARM")
	}
	if !u01.ValidFrozenSize(req.Size) { return errors.New("ACC125_NONFROZEN_SIZE") }
	validSeed := false
	for _, s := range u01.FrozenSeeds { validSeed = validSeed || s == req.Seed }
	if !validSeed { return errors.New("ACC125_NONFROZEN_SEED") }
	if req.Variant != "structured" && req.Variant != "random_control" {
		return errors.New("ACC125_UNKNOWN_SOURCE_VARIANT")
	}
	if req.Queries < 1 || req.Queries > 4096 { return errors.New("ACC125_BAD_QUERY_COUNT") }
	if !isHex256(req.ArtifactSHA) || !isHex256(req.WeightSHA) {
		return errors.New("ACC125_MISSING_IMMUTABLE_SOURCE_DIGEST")
	}
	if strings.TrimSpace(req.ArtifactPath) == "" { return errors.New("ACC125_MISSING_SOURCE_PATH") }
	start := time.Now()
	src, err := os.ReadFile(req.ArtifactPath)
	if err != nil { return fmt.Errorf("ACC125_SOURCE_READ:%w", err) }
	sum := sha256.Sum256(src)
	actualArtifact := hex.EncodeToString(sum[:])
	if actualArtifact != req.ArtifactSHA { return errors.New("ACC125_ARTIFACT_DIGEST_MISMATCH") }
	encodedBytes, denseBytes := 0, req.Size*req.Size
	var dense []int8
	var rawDense []byte
	var encoded []byte
	peakLoadingBytes := len(src)
	switch req.Arm {
	case "DENSE":
		if len(src) != denseBytes { return errors.New("ACC125_DENSE_LENGTH_MISMATCH") }
		if actualArtifact != req.WeightSHA { return errors.New("ACC125_DENSE_SOURCE_ID_MISMATCH") }
		rawDense = src
	case "RLE_PREDECODE", "RLE_STREAM":
		encoded = src
		encodedBytes = len(encoded)
		actualSource, err := decodeSourceHashRLE(encoded, req.Size)
		if err != nil { return fmt.Errorf("ACC125_SOURCE_DECODE_DIGEST:%w", err) }
		if actualSource != req.WeightSHA { return errors.New("ACC125_RLE_SOURCE_ID_MISMATCH") }
		if req.Arm == "RLE_PREDECODE" {
			dense, err = u01.DecodeRLE(encoded, req.Size*req.Size)
			if err != nil { return fmt.Errorf("ACC125_PREDECODE:%w", err) }
			peakLoadingBytes += len(dense)
			encoded = nil
			src = nil
			runtime.GC() // still charge peak RSS through the OS high-water counter.
		}
	}
	inputHash := sha256.New()
	outputHash := sha256.New()
	var outputByte [8]byte
	var inputByte [1]byte
	for i := 0; i < req.Queries; i++ {
		vector, err := u01.InputVector(req.Size, req.Seed, uint32(i))
		if err != nil { return err }
		for _, v := range vector {
			inputByte[0] = byte(v)
			_, _ = inputHash.Write(inputByte[:])
		}
		var output []int64
		switch req.Arm {
		case "DENSE":
			output, err = denseBytesMatVec(rawDense, req.Size, vector)
		case "RLE_PREDECODE":
			output, err = u01.DenseMatVec(dense, req.Size, vector)
		case "RLE_STREAM":
			output, err = u01.StreamMatVec(encoded, req.Size, vector)
		}
		if err != nil { return fmt.Errorf("ACC125_MATVEC:%w", err) }
		if len(output) != req.Size { return errors.New("ACC125_OUTPUT_SHAPE_DRIFT") }
		for _, value := range output {
			binary.LittleEndian.PutUint64(outputByte[:], uint64(value))
			_, _ = outputHash.Write(outputByte[:])
		}
	}
	representation := len(rawDense) + len(encoded) + len(dense)
	scratch := req.Size + req.Size*8 // vector and output
	if req.Arm == "RLE_STREAM" { scratch += (req.Size+1)*8 } // prefix
	user, system, rss, err := platformProcessUsage()
	if err != nil || rss == 0 || user < 0 || system < 0 {
		return fmt.Errorf("ACC125_OS_RESOURCE_UNVERIFIED:%v", err)
	}
	// Prevent compiler from eliding either owned weight representation.
	runtime.KeepAlive(rawDense)
	runtime.KeepAlive(encoded)
	runtime.KeepAlive(dense)
	receipt := result{
		Schema:schema, Arm:req.Arm, Size:req.Size, Seed:req.Seed,
		Variant:req.Variant, Queries:req.Queries,
		ArtifactSHA256:actualArtifact, SourceWeightSHA256:req.WeightSHA,
		InputSHA256:hex.EncodeToString(inputHash.Sum(nil)),
		OutputSHA256:hex.EncodeToString(outputHash.Sum(nil)),
		SourceEncodedBytes:encodedBytes, SourceDenseBytes:denseBytes,
		LiveRepresentationBytes:representation, LiveScratchBytes:scratch,
		PeakLoadingBytes:peakLoadingBytes,
		WallNanos:time.Since(start).Nanoseconds(),
		UserCPUNanos:user, SystemCPUNanos:system, PeakPhysicalRSSBytes:rss,
		CPUandRSSQualified:true, ScientificAcceptance:"NOT_GRANTED",
	}
	return json.NewEncoder(out).Encode(receipt)
}

func main() {
	var req request
	var seed string
	flag.StringVar(&req.Arm,"arm","","DENSE|RLE_PREDECODE|RLE_STREAM")
	flag.IntVar(&req.Size,"size",0,"frozen square dimension")
	flag.StringVar(&seed,"seed","","public frozen seed")
	flag.StringVar(&req.Variant,"variant","structured","structured|random_control")
	flag.StringVar(&req.ArtifactPath,"artifact","","pre-materialized arm-specific data path")
	flag.StringVar(&req.ArtifactSHA,"artifact-sha256","","sha256 of arm-specific input bytes")
	flag.StringVar(&req.WeightSHA,"weight-sha256","","sha256 of canonical source dense bytes")
	flag.IntVar(&req.Queries,"queries",4096,"queries (exactly 4096 for frozen experiment)")
	flag.Parse()
	seedNumber, err := strconv.ParseUint(seed,10,64)
	if err != nil { fmt.Fprintln(os.Stderr,"ACC125_SEED_PARSE:",err); os.Exit(2) }
	req.Seed=seedNumber
	if err := run(req,os.Stdout); err != nil {
		fmt.Fprintln(os.Stderr,err)
		os.Exit(2)
	}
}

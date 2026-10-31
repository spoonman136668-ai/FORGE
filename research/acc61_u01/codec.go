// Package acc61u01 implements the exact, source-free U01 lossless tensor
// representations. It is a research-only correctness kernel, NOT a JIT compiler,
// qualified benchmark, learned model, or resource/performance claim.
package acc61u01

import (
	"crypto/sha256"
	"encoding/binary"
	"errors"
	"fmt"
)

var Palette = [16]int8{-117, -87, -66, -44, -25, -9, 0, 7, 15, 28, 39, 53, 70, 86, 104, 119}
var FrozenSizes = [4]int{64, 128, 256, 512}
var FrozenSeeds = [5]uint64{161101, 161103, 161107, 161109, 161111}

func ValidFrozenSize(n int) bool {
	for _, candidate := range FrozenSizes {
		if n == candidate {
			return true
		}
	}
	return false
}

// StructuredWeights builds the frozen public, lossy-free source tensor.
// Consecutive 16-column blocks share a palette value; every arm must consume
// one authenticated identical tensor, never a model- or arm-specific variant.
func StructuredWeights(n int, seed uint64) ([]int8, error) {
	if !ValidFrozenSize(n) {
		return nil, fmt.Errorf("ACC61_NONFROZEN_SIZE:%d", n)
	}
	weights := make([]int8, n*n)
	for row := 0; row < n; row++ {
		for block := 0; block < n/16; block++ {
			idx := (uint64(row/8)*1315423911 + uint64(block)*2654435761 + seed*11400714819323198485) & 15
			value := Palette[idx]
			for col := block * 16; col < (block+1)*16; col++ {
				weights[row*n+col] = value
			}
		}
	}
	return weights, nil
}

// RandomWeights is a negative compressibility control, never a training set.
// xorshift64* is explicitly specified here, avoiding unstable runtime RNG APIs.
func RandomWeights(n int, seed uint64) ([]int8, error) {
	if !ValidFrozenSize(n) {
		return nil, fmt.Errorf("ACC61_NONFROZEN_SIZE:%d", n)
	}
	w := make([]int8, n*n)
	state := seed | 1
	for i := range w {
		state ^= state >> 12
		state ^= state << 25
		state ^= state >> 27
		w[i] = int8(byte((state * 2685821657736338717) >> 56))
	}
	return w, nil
}

// InputVector deterministically specifies independent public inference inputs.
func InputVector(n int, seed uint64, number uint32) ([]int8, error) {
	if !ValidFrozenSize(n) {
		return nil, fmt.Errorf("ACC61_NONFROZEN_SIZE:%d", n)
	}
	vector := make([]int8, n)
	state := (seed ^ (uint64(number)+1)*0x9e3779b97f4a7c15) | 1
	for i := range vector {
		state ^= state >> 12
		state ^= state << 25
		state ^= state >> 27
		vector[i] = int8(byte((state * 2685821657736338717) >> 56))
	}
	return vector, nil
}

// EncodeRLE uses canonical (signed-value byte, uint32 LE repeat count) records.
// Encode and decode require a flat dense source, and the wire format is 5 bytes
// per run. A future benchmark must charge any temporary dense source material.
func EncodeRLE(weights []int8) ([]byte, error) {
	if len(weights) == 0 || len(weights) > 512*512 {
		return nil, errors.New("ACC61_INVALID_WEIGHT_LENGTH")
	}
	out := make([]byte, 0, len(weights)/2)
	for i := 0; i < len(weights); {
		j := i + 1
		for j < len(weights) && weights[j] == weights[i] && j-i < int(^uint32(0)) {
			j++
		}
		var record [5]byte
		record[0] = byte(weights[i])
		binary.LittleEndian.PutUint32(record[1:], uint32(j-i))
		out = append(out, record[:]...)
		i = j
	}
	return out, nil
}

func ValidateRLE(encoded []byte, expected int) error {
	if expected <= 0 || expected > 512*512 || len(encoded) == 0 || len(encoded)%5 != 0 {
		return errors.New("ACC61_RLE_INVALID_SIZE")
	}
	count := 0
	for i := 0; i < len(encoded); i += 5 {
		run := binary.LittleEndian.Uint32(encoded[i+1:])
		if run == 0 || uint64(run) > uint64(expected-count) {
			return errors.New("ACC61_RLE_ZERO_OR_OVERRUN")
		}
		if i != 0 && encoded[i] == encoded[i-5] {
			return errors.New("ACC61_RLE_NONCANONICAL_ADJACENT")
		}
		count += int(run)
	}
	if count != expected {
		return errors.New("ACC61_RLE_UNDERRUN")
	}
	return nil
}

func DecodeRLE(encoded []byte, expected int) ([]int8, error) {
	if err := ValidateRLE(encoded, expected); err != nil {
		return nil, err
	}
	out := make([]int8, expected)
	at := 0
	for i := 0; i < len(encoded); i += 5 {
		count := int(binary.LittleEndian.Uint32(encoded[i+1:]))
		for j := 0; j < count; j++ {
			out[at+j] = int8(encoded[i])
		}
		at += count
	}
	return out, nil
}

func ValidateMatrix(n, length int, vector []int8) error {
	if n <= 0 || n > 512 || length != n*n || len(vector) != n {
		return fmt.Errorf("ACC61_INFERENCE_SHAPE:%d:%d:%d", n, length, len(vector))
	}
	return nil
}

// DenseMatVec is the unfused scalar reference with signed int64 accumulation.
func DenseMatVec(weights []int8, n int, vector []int8) ([]int64, error) {
	if err := ValidateMatrix(n, len(weights), vector); err != nil {
		return nil, err
	}
	result := make([]int64, n)
	for row := 0; row < n; row++ {
		var sum int64
		for col := 0; col < n; col++ {
			sum += int64(weights[row*n+col]) * int64(vector[col])
		}
		result[row] = sum
	}
	return result, nil
}

// StreamMatVec does not materialize a dense weight tensor. Runs may straddle
// row boundaries. Prefix sums implement exact int64 sum-of-products for each run.
func StreamMatVec(encoded []byte, n int, vector []int8) ([]int64, error) {
	if n <= 0 || n > 512 || len(vector) != n {
		return nil, errors.New("ACC61_STREAM_SHAPE")
	}
	if err := ValidateRLE(encoded, n*n); err != nil {
		return nil, err
	}
	prefix := make([]int64, n+1)
	for i, value := range vector {
		prefix[i+1] = prefix[i] + int64(value)
	}
	result := make([]int64, n)
	position := 0
	for i := 0; i < len(encoded); i += 5 {
		remaining := int(binary.LittleEndian.Uint32(encoded[i+1:]))
		value := int64(int8(encoded[i]))
		for remaining != 0 {
			row, col := position/n, position%n
			take := n-col
			if remaining < take {
				take = remaining
			}
			result[row] += value * (prefix[col+take] - prefix[col])
			position += take
			remaining -= take
		}
	}
	return result, nil
}

func WeightSHA256(weights []int8) [32]byte {
	data := make([]byte, len(weights))
	for i, value := range weights {
		data[i] = byte(value)
	}
	return sha256.Sum256(data)
}

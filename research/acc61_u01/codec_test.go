package acc61u01

import (
	"bytes"
	"encoding/binary"
	"reflect"
	"testing"
)

func TestACC124FrozenSizesAndSeeds(t *testing.T) {
	if FrozenSizes != [4]int{64, 128, 256, 512} ||
		FrozenSeeds != [5]uint64{161101, 161103, 161107, 161109, 161111} {
		t.Fatal("ACC124_FROZEN_MATRIX_DRIFT")
	}
	for _, n := range []int{-1, 0, 1, 63, 65, 513} {
		if _, err := StructuredWeights(n, 161101); err == nil {
			t.Fatalf("ACC124_ACCEPTED_NONFROZEN_SIZE:%d", n)
		}
		if _, err := RandomWeights(n, 161101); err == nil {
			t.Fatalf("ACC124_RANDOM_ACCEPTED_NONFROZEN_SIZE:%d", n)
		}
		if _, err := InputVector(n, 161101, 0); err == nil {
			t.Fatalf("ACC124_INPUT_ACCEPTED_NONFROZEN_SIZE:%d", n)
		}
	}
}

func TestACC124SixtyPairedFrozenArmSmokes(t *testing.T) {
	// 4 frozen sizes x 5 seeds x 3 independent inputs = 60 lightweight
	// correctness cases. This is NOT the frozen 60 cold child process study.
	var checked int
	for _, n := range FrozenSizes {
		for _, seed := range FrozenSeeds {
			original, err := StructuredWeights(n, seed)
			if err != nil {
				t.Fatal(err)
			}
			second, err := StructuredWeights(n, seed)
			if err != nil || !reflect.DeepEqual(original, second) {
				t.Fatal("ACC124_NONDETERMINISTIC_WEIGHT")
			}
			encoded, err := EncodeRLE(original)
			if err != nil {
				t.Fatal(err)
			}
			if len(encoded) >= len(original) {
				t.Fatalf("ACC124_STRUCTURED_REPRESENTATION_NOT_COMPACT:%d:%d", n, seed)
			}
			restored, err := DecodeRLE(encoded, n*n)
			if err != nil || !reflect.DeepEqual(original, restored) {
				t.Fatalf("ACC124_RLE_NOT_LOSSLESS:%d:%d:%v", n, seed, err)
			}
			if WeightSHA256(original) != WeightSHA256(restored) {
				t.Fatal("ACC124_WEIGHT_SHA_MISMATCH")
			}
			for index := uint32(0); index < 3; index++ {
				input, err := InputVector(n, seed, index)
				if err != nil {
					t.Fatal(err)
				}
				dense, err := DenseMatVec(original, n, input)
				if err != nil {
					t.Fatal(err)
				}
				predecoded, err := DenseMatVec(restored, n, input)
				if err != nil {
					t.Fatal(err)
				}
				streamed, err := StreamMatVec(encoded, n, input)
				if err != nil {
					t.Fatal(err)
				}
				if !reflect.DeepEqual(dense, predecoded) || !reflect.DeepEqual(dense, streamed) {
					t.Fatalf("ACC124_OUTPUT_MISMATCH:size=%d:seed=%d:input=%d", n, seed, index)
				}
				checked++
			}
		}
	}
	if checked != 60 {
		t.Fatalf("ACC124_COUNT=%d", checked)
	}
}

func TestACC124RunsCrossRowBoundaries(t *testing.T) {
	weights := make([]int8, 16)
	for i := range weights {
		weights[i] = -3
	}
	encoded, err := EncodeRLE(weights)
	if err != nil || len(encoded) != 5 {
		t.Fatalf("ACC124_CROSS_ROW_RLE:%v", err)
	}
	vector := []int8{-128, 127, -22, 31}
	want, _ := DenseMatVec(weights, 4, vector)
	got, err := StreamMatVec(encoded, 4, vector)
	if err != nil || !reflect.DeepEqual(want, got) {
		t.Fatalf("ACC124_CROSS_ROW_MISMATCH:%v", err)
	}
}

func TestACC124CorruptedRLEFailsClosed(t *testing.T) {
	record := func(value byte, count uint32) []byte {
		b := make([]byte, 5)
		b[0] = value
		binary.LittleEndian.PutUint32(b[1:], count)
		return b
	}
	cases := [][]byte{
		nil, {1, 2, 3}, record(5, 0), record(5, 17),
		record(5, 15),
		append(record(5, 8), record(5, 8)...),
	}
	for i, encoded := range cases {
		if err := ValidateRLE(encoded, 16); err == nil {
			t.Fatalf("ACC124_BAD_RECORD_ACCEPTED:%d", i)
		}
		if _, err := DecodeRLE(encoded, 16); err == nil {
			t.Fatalf("ACC124_BAD_DECODE_ACCEPTED:%d", i)
		}
		if _, err := StreamMatVec(encoded, 4, []int8{1, 2, 3, 4}); err == nil {
			t.Fatalf("ACC124_BAD_STREAM_ACCEPTED:%d", i)
		}
	}
	if _, err := StreamMatVec(record(5, 16), 4, []int8{1, 2}); err == nil {
		t.Fatal("ACC124_BAD_INPUT_VECTOR_ACCEPTED")
	}
	if _, err := DenseMatVec([]int8{1}, 4, []int8{1, 2, 3, 4}); err == nil {
		t.Fatal("ACC124_BAD_DENSE_SHAPE_ACCEPTED")
	}
}

func TestACC124RandomNegativeCompressibilityControl(t *testing.T) {
	weights, err := RandomWeights(128, 161101)
	if err != nil {
		t.Fatal(err)
	}
	other, err := RandomWeights(128, 161101)
	if err != nil || !reflect.DeepEqual(weights, other) {
		t.Fatal("ACC124_RANDOM_NOT_DETERMINISTIC")
	}
	encoded, err := EncodeRLE(weights)
	if err != nil {
		t.Fatal(err)
	}
	if len(encoded) <= len(weights) {
		t.Fatal("ACC124_RANDOM_NEGATIVE_CONTROL_WAS_COMPRESSIBLE")
	}
	decoded, err := DecodeRLE(encoded, 128*128)
	if err != nil || !reflect.DeepEqual(decoded, weights) {
		t.Fatalf("ACC124_RANDOM_LOSSLESS_ROUNDTRIP:%v", err)
	}
	vector, err := InputVector(128, 161101, 11)
	if err != nil {
		t.Fatal(err)
	}
	dense, err := DenseMatVec(weights, 128, vector)
	if err != nil {
		t.Fatal(err)
	}
	streamed, err := StreamMatVec(encoded, 128, vector)
	if err != nil || !reflect.DeepEqual(dense, streamed) {
		t.Fatalf("ACC124_RANDOM_VECTOR_MISMATCH:%v", err)
	}
	if bytes.Equal([]byte{byte(weights[0])}, []byte{byte(weights[1])}) {
		// Adjacent random values may collide; no specific values are assumed.
		t.Log("Random control includes an allowed adjacent-value collision")
	}
}

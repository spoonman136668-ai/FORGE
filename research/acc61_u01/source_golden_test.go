package acc61u01

import (
	"crypto/sha256"
	"encoding/hex"
	"testing"
)

// ACC-127: These fingerprints were independently derived from the existing
// frozen public generator specification, without running this Go package.
// This test catches inadvertent source identity drift across platforms.
// These are FIT/DEV synthetic public inputs, not withheld real-model data.
func TestACC127StructuredSourceIdentityIndependentGoldens(t *testing.T) {
	golden := map[int]map[uint64]string{
		64: {
			161101: "00620892615ab7ce617a6b7c69134af17436f789d3c49d7cc09f0d26b7376af0",
			161103: "290ad793ce63834dbb5cecc494a4827b073245af71c2b1c8a75785449cc70630",
			161107: "86aff3666f4b259b6ea4762d371f6cf63b627073948c366b000b4a0b2d218705",
			161109: "2d8fabfd3f1c20a89507b4a7a25d8bf92ebcf4d533b7fe38c09db92ea9930187",
			161111: "a6a5942abce6df030ea0da28ae09c2097d06c44eee2b33dffb77d3c8ece5e675",
		},
		128: {
			161101: "7e27cc7389e6ca0ce59fb5c85a0e394b7880ad70a87183601232ad42f73f94fe",
			161103: "08a305308a03828f7cba5a2014554f41b92054933e47a33d3230d42c1aacc872",
			161107: "33cca4f62636b15a073ee60ceea23cb4341382660659ac93e7a807bfe9d4a211",
			161109: "3f82f3cc60b07a5fa6d3ad84463c66912fc2d6aca3a12b4eccd510c0f2152fbc",
			161111: "00215d3dcedd90860a9e637294d19c67b89e85995af71ad176c500b471cf32b6",
		},
		256: {
			161101: "c7c41394ef4ca81d5034316996ebd1403994a83fc3aa7fa905157ba65721424d",
			161103: "8867af3ce4248a080832f42541168c7f8c7bcf225fb460eb1af08bc07a0e58b7",
			161107: "710a87c7d891a5d5a025416ae33ac170233dda47375c52000a080b8ca6fe3e4f",
			161109: "57e3330d19df9335136010a829adad6ad7b09769e3ea4db3d5144679542bd99d",
			161111: "7a4b04260f4edf6177ed2db06263496dd8123fbeff24ddd20c6d995d0360c399",
		},
		512: {
			161101: "5a2110d8d1d9275304fe8e2339b8d31de435894f62e2d08b2a546203215551d1",
			161103: "1590e521ba3fb410f81a44d0a06580da69c77119ea02441f17336f38214c7fbb",
			161107: "94fbac5c9920286e289d7777d84854f750d4000993feb36df540405b873083df",
			161109: "ad50f4cbc496fc4636e48ed1d9ec2c92de2279d4349b20cb52d408bdbc06d403",
			161111: "eb906c1c14d4e5091c23882128b950769a8fabd747f062b8929db20f802a772e",
		},
	}
	if len(golden) != len(FrozenSizes) {
		t.Fatal("ACC127_SOURCE_DIMENSION_COVERAGE_DRIFT")
	}
	for _, n := range FrozenSizes {
		cases, ok := golden[n]
		if !ok || len(cases) != len(FrozenSeeds) {
			t.Fatalf("ACC127_SOURCE_SIZE_MISSING:%d", n)
		}
		for _, seed := range FrozenSeeds {
			weight, err := StructuredWeights(n, seed)
			if err != nil {
				t.Fatal(err)
			}
			actual := WeightSHA256(weight)
			if hex.EncodeToString(actual[:]) != cases[seed] {
				t.Fatalf("ACC127_SOURCE_DRIFT:size=%d:seed=%d", n, seed)
			}
		}
	}
}

func TestACC127Full4096InputIdentityIndependentGoldens(t *testing.T) {
	// The full 4096-query input byte stream is SHA-bound independently
	// of any compression arm and without admitting model performance.
	golden := map[int]string{
		64:  "ef11ce65bd9d4dad2f3a4a62e06a0787dc368ed6301dc9639fd2d3c7a1fa3fbc",
		128: "f40a746b3aeb56854b0be6a9a8c61044f218dd06d5d695722924e8556531dd50",
		256: "393757c6ba967854f6202672a75a0f9f4e2688ae3701b805a82f1cf010ece4f6",
		512: "4133d56f6e181fa62b27ecec403118b76731c2b64d46128a618c883526f14518",
	}
	const seed uint64 = 161101
	for _, n := range FrozenSizes {
		h := sha256.New()
		var one [1]byte
		for query := uint32(0); query < 4096; query++ {
			vector, err := InputVector(n, seed, query)
			if err != nil {
				t.Fatal(err)
			}
			for _, value := range vector {
				one[0] = byte(value)
				if _, err := h.Write(one[:]); err != nil {
					t.Fatal(err)
				}
			}
		}
		if got := hex.EncodeToString(h.Sum(nil)); got != golden[n] {
			t.Fatalf("ACC127_INPUT_STREAM_DRIFT:size=%d:seed=%d:got=%s", n, seed, got)
		}
	}
}

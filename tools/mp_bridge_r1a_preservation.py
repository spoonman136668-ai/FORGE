from pathlib import Path
import sys

root = Path(sys.argv[1])
pine = root / "internal/plane/pine_successor.go"
bridge = root / "internal/plane/roadmap_catalog_v2_bridge.go"

ps = pine.read_text(encoding="utf-8")
old = """	w.Preserve = postBTVAppendUniqueStrings(append([]string{}, parent.Preserve...), w.Preserve...)
	w.Preservation, err = mergePreservationContractsV2(parent.Preservation, e.Preservation)
	if err != nil {
		return WorkOrder{}, "", err
	}
	w.UI, err = postBTVMergeUI(parent.UI, w.UI)
"""
new = """	w.Preserve = postBTVAppendUniqueStrings(append([]string{}, parent.Preserve...), w.Preserve...)
	parentPreservation, err := preservationContractToV2(parent.Preservation)
	if err != nil {
		return WorkOrder{}, "", err
	}
	mergedPreservation, err := mergePreservationContractsV2(parentPreservation, e.Preservation)
	if err != nil {
		return WorkOrder{}, "", err
	}
	w.Preservation, err = preservationContractFromV2(mergedPreservation)
	if err != nil {
		return WorkOrder{}, "", err
	}
	if w.Preservation != nil {
		w.PreservationSchema = "ckb-plane.preservation.v1"
	}
	w.UI, err = postBTVMergeUI(parent.UI, w.UI)
"""
if ps.count(old) != 1:
    raise SystemExit("MP_R1A_BRIDGE_PINE_ANCHOR")
pine.write_text(ps.replace(old, new, 1), encoding="utf-8", newline="\n")

bs = bridge.read_text(encoding="utf-8")
anchor = """func clonePreservationContractsV2(in PreservationContractsV2) PreservationContractsV2 {
"""
if bs.count(anchor) != 1:
    raise SystemExit("MP_R1A_BRIDGE_CLONE_ANCHOR")
insert = r'''func preservationContractToV2(in *PreservationContract) (PreservationContractsV2, error) {
	if in == nil {
		return PreservationContractsV2{}, nil
	}
	raw, err := json.Marshal(in)
	if err != nil {
		return PreservationContractsV2{}, errors.New("ROADMAP_V2_PARENT_PRESERVATION_ENCODE_FAILED")
	}
	var out PreservationContractsV2
	if err = json.Unmarshal(raw, &out); err != nil {
		return PreservationContractsV2{}, errors.New("ROADMAP_V2_PARENT_PRESERVATION_INCOMPATIBLE")
	}
	if err = out.Validate(); err != nil {
		return PreservationContractsV2{}, err
	}
	return out, nil
}

func preservationContractsV2Empty(in PreservationContractsV2) bool {
	return len(in.UIMarkers) == 0 &&
		len(in.BehaviorContracts) == 0 &&
		len(in.SourceContracts) == 0 &&
		len(in.InterfaceContracts) == 0 &&
		len(in.EvidenceContracts) == 0 &&
		len(in.AcceptedInterfaces) == 0
}

func preservationContractFromV2(in PreservationContractsV2) (*PreservationContract, error) {
	if preservationContractsV2Empty(in) {
		return nil, nil
	}
	if err := in.Validate(); err != nil {
		return nil, err
	}
	raw, err := json.Marshal(in)
	if err != nil {
		return nil, errors.New("ROADMAP_V2_PRESERVATION_ENCODE_FAILED")
	}
	var out PreservationContract
	if err = json.Unmarshal(raw, &out); err != nil {
		return nil, errors.New("ROADMAP_V2_PRESERVATION_CONVERSION_FAILED")
	}
	if err = out.Validate(); err != nil {
		return nil, err
	}
	return &out, nil
}

'''
bridge.write_text(bs.replace(anchor, insert + anchor, 1), encoding="utf-8", newline="\n")

print("MP_R1A_PR614_PRESERVATION_BRIDGE=PASS")

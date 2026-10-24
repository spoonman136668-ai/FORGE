from pathlib import Path
import sys

p = Path(sys.argv[1])
s = p.read_text(encoding="utf-8")

field = '\tPreserve      []string `yaml:"preserve"`\n'
if s.count(field) != 1:
    raise SystemExit("MP_RECON_MODEL_PRESERVE_ANCHOR")
if "PreservationSchema string" in s or "type PreservationContract struct" in s:
    raise SystemExit("MP_RECON_MODEL_ALREADY_VERSIONED")
s = s.replace(
    field,
    field
    + '\tPreservationSchema string `yaml:"preservation_schema,omitempty" json:"preservation_schema,omitempty"`\n'
    + '\tPreservation *PreservationContract `yaml:"preservation,omitempty" json:"preservation,omitempty"`\n',
    1,
)

anchor = "func decodeYAML(b []byte, v any) error {"
if s.count(anchor) != 1:
    raise SystemExit("MP_RECON_DECODE_ANCHOR")
pres = r'''type PreservationContract struct {
	AcceptedInterfaces any `yaml:"acceptedinterfaces,omitempty" json:"acceptedinterfaces,omitempty"`
	BehaviorContracts any `yaml:"behaviorcontracts,omitempty" json:"behaviorcontracts,omitempty"`
	EvidenceContracts any `yaml:"evidencecontracts,omitempty" json:"evidencecontracts,omitempty"`
	InterfaceContracts any `yaml:"interfacecontracts,omitempty" json:"interfacecontracts,omitempty"`
	SourceContracts any `yaml:"sourcecontracts,omitempty" json:"sourcecontracts,omitempty"`
	UIMarkers any `yaml:"uimarkers,omitempty" json:"uimarkers,omitempty"`
}

func validPreservationValue(v any, depth int) bool {
	if depth>12 {return false}
	switch x:=v.(type) {
	case nil, bool, int, int64, uint64, float64:
		return true
	case string:
		return len(x)<=8192
	case []any:
		if len(x)>256 {return false}
		for _, item:=range x {if !validPreservationValue(item,depth+1) {return false}}
		return true
	case map[string]any:
		if len(x)>256 {return false}
		for key,item:=range x {if len(key)==0||len(key)>128||!validPreservationValue(item,depth+1) {return false}}
		return true
	default:
		return false
	}
}
func (p *PreservationContract) Validate() error {
	if p==nil {return nil}
	values:=[]any{p.AcceptedInterfaces,p.BehaviorContracts,p.EvidenceContracts,p.InterfaceContracts,p.SourceContracts,p.UIMarkers}
	present:=false
	for _,v:=range values {
		if v!=nil {
			present=true
			if !validPreservationValue(v,0) {return errors.New("PRESERVATION_CONTRACT_INVALID: type or bounds")}
		}
	}
	if !present {return errors.New("PRESERVATION_CONTRACT_INVALID: empty mapping")}
	return nil
}

'''
s = s.replace(anchor, pres + anchor, 1)

old = '''func ParseOrder(b []byte) (WorkOrder, error) {
	var w WorkOrder
	err := decodeYAML(b, &w)
	if err == nil {
		err = w.Validate()
	}
	return w, err
}
'''
new = '''func ParseOrder(b []byte) (WorkOrder, error) {
	var w WorkOrder
	err := decodeYAML(b, &w)
	if err != nil {
		// Retain the original strict error while identifying the bounded
		// preservation field for historical-observation diagnostics.
		if regexp.MustCompile("(?m)^preservation:").Match(b) {
			return w, fmt.Errorf("preservation: %w", err)
		}
		return w, err
	}
	return w, w.Validate()
}
'''
if s.count(old) != 1:
    raise SystemExit("MP_RECON_PARSEORDER_ANCHOR")
s = s.replace(old, new, 1)

tail = '\treturn nil\n}\n\nvar hardForbidden'
if s.count(tail) != 1:
    raise SystemExit("MP_RECON_VALIDATE_TAIL")
validation = '''	if w.Preservation == nil {
		if w.PreservationSchema != "" {
			return errors.New("preservation: preservation_schema provided without preservation contract")
		}
	} else {
		if w.PreservationSchema != "ckb-plane.preservation.v1" {
			return errors.New("preservation: explicit preservation_schema ckb-plane.preservation.v1 required")
		}
		if err := w.Preservation.Validate(); err != nil {
			return err
		}
	}
	return nil
}

var hardForbidden'''
s = s.replace(tail, validation, 1)

for needle in (
    "PreservationSchema string",
    "type PreservationContract struct",
    "ckb-plane.preservation.v1",
    'fmt.Errorf("preservation: %w", err)',
):
    if needle not in s:
        raise SystemExit("MP_RECON_MODEL_POSTCHECK")

p.write_text(s, encoding="utf-8", newline="\n")
print("MP_RECON_PRESERVATION_REAPPLIED=PASS")

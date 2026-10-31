"""G86B exact-row redundancy audit; research-only. Requires authentic pinned safetensors file."""
import argparse, hashlib, json
from pathlib import Path

def file_sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(8*1024*1024), b''):
            h.update(chunk)
    return h.hexdigest()

def duplicate_rows(matrix):
    """Count bitwise-exact duplicate rows; works on numpy arrays of any dtype."""
    import numpy as np
    a = np.ascontiguousarray(matrix)
    if a.ndim != 2:
        raise ValueError('MATRIX_MUST_BE_2D')
    seen = set()
    duplicates = 0
    for row in a:
        key = row.tobytes()
        if key in seen:
            duplicates += 1
        else:
            seen.add(key)
    return {'rows':int(a.shape[0]), 'columns':int(a.shape[1]), 'duplicate_rows':duplicates,
            'duplicate_fraction':duplicates/int(a.shape[0]) if a.shape[0] else 0.0}

def audit(path, expected_sha):
    from safetensors import safe_open
    if not (len(expected_sha)==64 and all(c in '0123456789abcdef' for c in expected_sha)):
        raise ValueError('EXPECTED_SHA256_REQUIRED')
    actual = file_sha256(path)
    if actual != expected_sha:
        raise RuntimeError('MODEL_WEIGHT_IDENTITY_DRIFT')
    rows = []
    with safe_open(str(path), framework='pt', device='cpu') as f:
        for name in sorted(f.keys()):
            if name.endswith('.weight') and any(s in name for s in ('q_proj','k_proj','v_proj','o_proj','gate_proj','up_proj','down_proj','lm_head')):
                tensor = f.get_tensor(name)
                if tensor.ndim != 2:
                    continue
                row = duplicate_rows(tensor.numpy())
                row['tensor'] = name
                rows.append(row)
    if not rows:
        raise RuntimeError('NO_PROJECTION_MATRICES_FOUND')
    return {'schema':'forge.acc.g86b.exact-rows.v1','model_sha256':actual,'status':'STRUCTURAL_AUDIT_ONLY',
            'scientific_acceptance':'NOT_GRANTED','layers':rows}

if __name__ == '__main__':
    p=argparse.ArgumentParser()
    p.add_argument('weights',type=Path)
    p.add_argument('--expected-sha256',required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    result=audit(a.weights,a.expected_sha256)
    a.output.write_text(json.dumps(result,indent=2)+'\n')

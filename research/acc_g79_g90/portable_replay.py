"""Portable G89/G90 replay without altering the immutable original experiment files.

Usage: python research/acc_g79_g90/portable_replay.py g89 --output out/g89.json
       python research/acc_g79_g90/portable_replay.py g90 --output out/g90.json

The original source has a frozen Git blob identity; only its one output path
literal is rewritten in an in-memory AST. This is *not* authentic GPU evidence.
"""
import argparse
import ast
import hashlib
from pathlib import Path

SOURCES = {
    "g89": ("research/acc_g89/g89.py", "/mnt/data/g89/results.json", "650656aea1fec7aa745e975614917638d7e9a320"),
    "g90": ("research/acc_g90/g90.py", "/mnt/data/g90/results.json", "d1cf18d025f41c37bce0c8e1e82b88e1313556c6"),
}

def git_blob(data):
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\\0" + data).hexdigest()

def patched_tree(source, old_output, new_output):
    tree = ast.parse(source)
    matches = 0
    class Replace(ast.NodeTransformer):
        def visit_Constant(self, node):
            nonlocal matches
            if isinstance(node.value, str) and node.value == old_output:
                matches += 1
                return ast.copy_location(ast.Constant(new_output), node)
            return node
    tree = Replace().visit(tree)
    if matches != 1:
        raise RuntimeError(f"OUTPUT_LITERAL_MATCH_COUNT_{matches}")
    return ast.fix_missing_locations(tree)

def prepare(repo_root, experiment, output):
    if experiment not in SOURCES:
        raise ValueError("UNSUPPORTED_EXPERIMENT")
    path, old, expected_blob = SOURCES[experiment]
    source_path = Path(repo_root) / path
    data = source_path.read_bytes()
    if git_blob(data) != expected_blob:
        raise RuntimeError("FROZEN_SOURCE_BLOB_DRIFT")
    destination = Path(output).resolve()
    if destination.suffix.lower() != ".json":
        raise ValueError("JSON_OUTPUT_REQUIRED")
    tree = patched_tree(data.decode("utf-8"), old, str(destination))
    return source_path, destination, compile(tree, str(source_path), "exec")

def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("experiment", choices=sorted(SOURCES))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[2])
    args = parser.parse_args(argv)
    source, destination, code = prepare(args.repo_root, args.experiment, args.output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    exec(code, {"__name__": "__main__", "__file__": str(source)})

if __name__ == "__main__":
    main()

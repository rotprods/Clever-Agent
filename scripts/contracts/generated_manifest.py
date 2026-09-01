from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUTPUTS = [
    Path("contracts/sdk/python/clever"),
    Path("contracts/sdk/typescript/src/gen"),
    Path("contracts/sdk/swift/Sources/CleverContracts/Gen"),
    Path("contracts/sdk/rust/src/gen"),
    Path("contracts/fixtures/wire"),
]
MANIFEST = Path("contracts/generated_manifest.json")


def digest_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build() -> dict[str, object]:
    files: list[dict[str, object]] = []
    for root in OUTPUTS:
        absolute = ROOT / root
        if not absolute.exists():
            raise RuntimeError(f"missing generated output root: {root}")
        for path in sorted(item for item in absolute.rglob("*") if item.is_file()):
            files.append({"path":path.relative_to(ROOT).as_posix(),"sha256":digest_file(path),"bytes":path.stat().st_size})
    proto_files = sorted((ROOT / "contracts/proto").rglob("*.proto"))
    proto_digest = hashlib.sha256()
    for path in proto_files:
        proto_digest.update(path.relative_to(ROOT).as_posix().encode())
        proto_digest.update(b"\0")
        proto_digest.update(path.read_bytes())
        proto_digest.update(b"\0")
    return {
        "schema_version":1,
        "authority":"contracts/proto + contracts/contract_manifest.json + contracts/toolchain.lock.json",
        "proto_tree_sha256":proto_digest.hexdigest(),
        "toolchain_lock_sha256":digest_file(ROOT / "contracts/toolchain.lock.json"),
        "generated_file_count":len(files),
        "files":files,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    payload = build()
    expected = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    path = ROOT / MANIFEST
    if args.check:
        if not path.is_file() or path.read_text(encoding="utf-8") != expected:
            raise SystemExit("generated binding manifest drift")
        print(f"OK: {payload['generated_file_count']} generated files match manifest")
        return 0
    path.write_text(expected, encoding="utf-8")
    print(f"Wrote {MANIFEST} for {payload['generated_file_count']} generated files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""W02-09 real-model materialization lane.

This module deliberately stops before inference. It pins one OpenJarvis catalog
model, acquires one immutable real-weight artifact only under an explicit
network grant, and verifies the artifact offline by size, SHA-256 and GGUF
magic. Missing, mock or corrupt weights are BLOCKED, never PASS.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MANIFEST = ROOT / "inventory/cp03/W02_REAL_MODEL_LANE.json"
SHA40 = re.compile(r"^[0-9a-f]{40}$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
BLOCKED_EXIT = 3


class LaneError(RuntimeError):
    """Invalid lane configuration (not an environmental block)."""


def _read_manifest(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_manifest(manifest: dict[str, Any]) -> None:
    if manifest.get("task") != "W02-09" or manifest.get("lane") != "L2_REAL_MODEL_PINNED_WEIGHTS":
        raise LaneError("manifest is not the canonical W02-09 L2 lane")
    upstream = manifest.get("upstream", {})
    model = manifest.get("model", {})
    engine = manifest.get("engine", {})
    artifact = manifest.get("artifact", {})
    acquire = manifest.get("acquisition", {})
    counters = manifest.get("counters", {})

    for label, value in (
        ("OpenJarvis commit", upstream.get("commit")),
        ("base model revision", model.get("base_revision")),
        ("runtime commit", engine.get("runtime_commit")),
        ("artifact revision", artifact.get("revision")),
    ):
        if not isinstance(value, str) or not SHA40.fullmatch(value):
            raise LaneError(f"{label} must be an immutable 40-char lowercase commit")
    if artifact.get("kind") != "REAL_MODEL_WEIGHTS":
        raise LaneError("mock/synthetic artifacts cannot satisfy W02-09")
    if artifact.get("format") != "GGUF" or artifact.get("magic_hex") != "47475546":
        raise LaneError("W02-09 lane must pin GGUF magic")
    if artifact.get("repository") != "bartowski/Qwen_Qwen3-0.6B-GGUF":
        raise LaneError("unexpected real-weight repository")
    if artifact.get("filename") != "Qwen_Qwen3-0.6B-Q4_K_M.gguf":
        raise LaneError("unexpected real-weight filename")
    if type(artifact.get("size_bytes")) is not int or artifact["size_bytes"] < 100_000_000:
        raise LaneError("real weight size is implausible")
    if not isinstance(artifact.get("sha256"), str) or not SHA256.fullmatch(artifact["sha256"]):
        raise LaneError("artifact sha256 must be pinned")
    url = artifact.get("download_url", "")
    if not isinstance(url, str) or not url.startswith("https://huggingface.co/"):
        raise LaneError("artifact download URL must use HTTPS Hugging Face")
    if artifact["revision"] not in url or artifact["filename"] not in url:
        raise LaneError("artifact URL must embed the immutable revision and filename")
    if engine.get("openjarvis_key") != "llamacpp":
        raise LaneError("lane must use the OpenJarvis llamacpp engine key")
    if engine.get("runtime_execution_in_w02_09") is not False:
        raise LaneError("W02-09 must not execute the inference runtime")
    if model.get("catalog_model_id") != "qwen3:0.6b" or model.get("license") != "Apache-2.0":
        raise LaneError("model identity/license pin drift")
    if acquire.get("explicit_grant_env") != "CLEVER_ALLOW_MODEL_ACQUISITION":
        raise LaneError("acquisition grant name drift")
    if acquire.get("offline_verify_required") is not True:
        raise LaneError("offline verification is mandatory")
    expected = {
        "global_denominator": 7565,
        "openjarvis_obligations": 646,
        "w02_proof_units": 47,
        "verified_capabilities": 0,
        "parity_promotions": 0,
        "model_executions": 0,
        "provider_egress_executions": 0,
    }
    if counters != expected:
        raise LaneError("forbidden counter/denominator drift in W02-09 manifest")


def _hash_and_magic(path: Path) -> tuple[int, str, str]:
    digest = hashlib.sha256()
    total = 0
    magic = b""
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            if total == 0:
                magic = chunk[:4]
            total += len(chunk)
            digest.update(chunk)
    return total, digest.hexdigest(), magic.hex()


def verify_artifact(path: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    artifact = manifest["artifact"]
    if not path.is_file():
        return _receipt("BLOCKED", "ARTIFACT_MISSING", path, manifest)
    size, digest, magic = _hash_and_magic(path)
    mismatches: list[str] = []
    if size != artifact["size_bytes"]:
        mismatches.append(f"size:{size}!={artifact['size_bytes']}")
    if digest != artifact["sha256"]:
        mismatches.append("sha256")
    if magic != artifact["magic_hex"]:
        mismatches.append(f"magic:{magic}")
    if mismatches:
        return _receipt("BLOCKED", "ARTIFACT_CORRUPT:" + ",".join(mismatches), path, manifest, size, digest, magic)
    return _receipt("PASS", "PINNED_REAL_WEIGHTS_VERIFIED", path, manifest, size, digest, magic)


def _receipt(
    status: str,
    reason: str,
    path: Path,
    manifest: dict[str, Any],
    size: int | None = None,
    digest: str | None = None,
    magic: str | None = None,
) -> dict[str, Any]:
    artifact = manifest["artifact"]
    return {
        "schema_version": 1,
        "task": "W02-09",
        "lane": "L2_REAL_MODEL_PINNED_WEIGHTS",
        "status": status,
        "reason": reason,
        "artifact_path": str(path),
        "artifact_repository": artifact["repository"],
        "artifact_revision": artifact["revision"],
        "artifact_filename": artifact["filename"],
        "expected_size_bytes": artifact["size_bytes"],
        "observed_size_bytes": size,
        "expected_sha256": artifact["sha256"],
        "observed_sha256": digest,
        "observed_magic_hex": magic,
        "model_executions": 0,
        "provider_egress_executions": 0,
        "parity_promotions": 0,
        "verified_capabilities": 0,
        "global_denominator": 7565,
        "openjarvis_obligations": 646,
    }


def acquire_artifact(destination: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    grant_name = manifest["acquisition"]["explicit_grant_env"]
    grant_value = manifest["acquisition"]["explicit_grant_value"]
    if os.environ.get(grant_name) != grant_value:
        return _receipt("BLOCKED", "ACQUISITION_GRANT_MISSING", destination, manifest)

    if destination.exists():
        existing = verify_artifact(destination, manifest)
        if existing["status"] == "PASS":
            existing["reason"] = "ALREADY_PRESENT_AND_VERIFIED"
            return existing

    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.with_name(destination.name + manifest["acquisition"]["atomic_partial_suffix"])
    partial.unlink(missing_ok=True)
    request = urllib.request.Request(
        manifest["artifact"]["download_url"],
        headers={"User-Agent": "Clever-Agent-W02-09/1.0"},
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response, partial.open("wb") as output:
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                output.write(chunk)
    except Exception as exc:  # network availability is an environmental BLOCKED condition
        partial.unlink(missing_ok=True)
        return _receipt("BLOCKED", f"ACQUISITION_FAILED:{type(exc).__name__}", destination, manifest)

    verified = verify_artifact(partial, manifest)
    if verified["status"] != "PASS":
        partial.unlink(missing_ok=True)
        verified["artifact_path"] = str(destination)
        return verified
    partial.replace(destination)
    final = verify_artifact(destination, manifest)
    final["reason"] = "ACQUIRED_AND_VERIFIED"
    return final


def _emit(receipt: dict[str, Any], receipt_path: Path | None) -> int:
    text = json.dumps(receipt, indent=2, sort_keys=True) + "\n"
    if receipt_path:
        receipt_path.parent.mkdir(parents=True, exist_ok=True)
        receipt_path.write_text(text, encoding="utf-8")
    sys.stdout.write(text)
    return 0 if receipt["status"] == "PASS" else BLOCKED_EXIT


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("validate-manifest", "verify", "acquire"))
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--artifact", type=Path)
    parser.add_argument("--receipt", type=Path)
    args = parser.parse_args(argv)
    manifest = _read_manifest(args.manifest)
    try:
        validate_manifest(manifest)
    except (LaneError, KeyError, TypeError, ValueError) as exc:
        sys.stderr.write(f"INVALID W02-09 MANIFEST: {exc}\n")
        return 2

    if args.command == "validate-manifest":
        receipt = {
            "schema_version": 1,
            "task": "W02-09",
            "status": "PASS",
            "reason": "MANIFEST_PINNED",
            "model_executions": 0,
            "provider_egress_executions": 0,
            "parity_promotions": 0,
        }
        return _emit(receipt, args.receipt)
    if args.artifact is None:
        parser.error("--artifact is required for verify/acquire")
    if args.command == "verify":
        return _emit(verify_artifact(args.artifact, manifest), args.receipt)
    return _emit(acquire_artifact(args.artifact, manifest), args.receipt)


if __name__ == "__main__":
    raise SystemExit(main())

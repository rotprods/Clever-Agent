from __future__ import annotations

import argparse
import contextlib
import importlib
import inspect
import json
from pathlib import Path
import struct
import sys
import time
from typing import BinaryIO, Iterable

ROOT = Path(__file__).resolve().parents[2]
GENERATED = ROOT / "contracts/sdk/python/gen"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(GENERATED) not in sys.path:
    sys.path.insert(0, str(GENERATED))

from adapters.openjarvis import ADAPTER_ID, RUNTIME_ID, UPSTREAM_COMMIT, UPSTREAM_REPOSITORY
from clever.v1 import adapter_pb2, common_pb2, runtime_pb2

MAX_FRAME_BYTES = 4 * 1024 * 1024
WIRE_MAJOR = 1
WIRE_MINOR = 1
_RESERVED_METADATA_TOKENS = ("permission", "scope", "risk", "policy", "authorization", "authz")

# Domain import hints, not implementation/provider allowlists.
_REGISTRATION_IMPORT_HINTS = {
    "AgentRegistry": ("openjarvis.agents",),
    "BenchmarkRegistry": ("openjarvis.bench",),
    "ChannelRegistry": ("openjarvis.channels",),
    "CompressionRegistry": ("openjarvis.sessions.compression",),
    "ConnectorRegistry": ("openjarvis.connectors",),
    "EngineRegistry": ("openjarvis.engine",),
    "FactStoreRegistry": ("openjarvis.memory",),
    "LearningRegistry": ("openjarvis.learning.intelligence",),
    "MemoryRegistry": ("openjarvis.memory", "openjarvis.tools.storage"),
    "MinerRegistry": ("openjarvis.mining",),
    "ModelRegistry": ("openjarvis.intelligence",),
    "RouterPolicyRegistry": ("openjarvis.learning.routing.heuristic_policy", "openjarvis.learning.routing.learned_router"),
    "SkillRegistry": ("openjarvis.skills",),
    "SpeechRegistry": ("openjarvis.speech",),
    "TTSRegistry": ("openjarvis.tools.text_to_speech",),
    "ToolRegistry": ("openjarvis.tools",),
}
_REGISTRY_PRIMITIVES = {
    "ModelRegistry": adapter_pb2.REGISTRY_PRIMITIVE_MODEL,
    "EngineRegistry": adapter_pb2.REGISTRY_PRIMITIVE_ENGINE,
    "MemoryRegistry": adapter_pb2.REGISTRY_PRIMITIVE_MEMORY,
    "FactStoreRegistry": adapter_pb2.REGISTRY_PRIMITIVE_FACT_STORE,
    "AgentRegistry": adapter_pb2.REGISTRY_PRIMITIVE_AGENT,
    "ToolRegistry": adapter_pb2.REGISTRY_PRIMITIVE_TOOL,
    "RouterPolicyRegistry": adapter_pb2.REGISTRY_PRIMITIVE_ROUTER_POLICY,
    "BenchmarkRegistry": adapter_pb2.REGISTRY_PRIMITIVE_BENCHMARK,
    "ChannelRegistry": adapter_pb2.REGISTRY_PRIMITIVE_CHANNEL,
    "LearningRegistry": adapter_pb2.REGISTRY_PRIMITIVE_LEARNING,
    "SkillRegistry": adapter_pb2.REGISTRY_PRIMITIVE_SKILL,
    "SpeechRegistry": adapter_pb2.REGISTRY_PRIMITIVE_SPEECH,
    "CompressionRegistry": adapter_pb2.REGISTRY_PRIMITIVE_COMPRESSION,
    "TTSRegistry": adapter_pb2.REGISTRY_PRIMITIVE_TTS,
    "ConnectorRegistry": adapter_pb2.REGISTRY_PRIMITIVE_CONNECTOR,
    "MinerRegistry": adapter_pb2.REGISTRY_PRIMITIVE_MINER,
}


def contract_version() -> common_pb2.ContractVersion:
    return common_pb2.ContractVersion(major=WIRE_MAJOR, minor=WIRE_MINOR)


def is_reserved_metadata_key(key: str) -> bool:
    return any(token in key.casefold() for token in _RESERVED_METADATA_TOKENS)


def sanitize_metadata(metadata: dict[str, str]) -> dict[str, str]:
    return {str(k): str(v) for k, v in sorted(metadata.items()) if not is_reserved_metadata_key(str(k))}


def _import_registry_domains(registry_names: Iterable[str]) -> list[str]:
    failures: list[str] = []
    seen: set[str] = set()
    for registry_name in sorted(registry_names):
        for module_name in _REGISTRATION_IMPORT_HINTS.get(registry_name, ()):
            if module_name in seen:
                continue
            seen.add(module_name)
            try:
                with contextlib.redirect_stdout(sys.stderr):
                    module = importlib.import_module(module_name)
                    if module_name == "openjarvis.intelligence":
                        register_builtin = getattr(module, "register_builtin_models", None)
                        if callable(register_builtin):
                            register_builtin()
            except Exception as exc:
                failures.append(f"{module_name}:{type(exc).__name__}")
    return sorted(failures)


def _registry_classes() -> list[tuple[str, type]]:
    module = importlib.import_module("openjarvis.core.registry")
    base = getattr(module, "RegistryBase")
    return sorted([
        (name, candidate) for name, candidate in vars(module).items()
        if name.endswith("Registry") and inspect.isclass(candidate)
        and candidate is not base and issubclass(candidate, base)
    ], key=lambda item: item[0])


def _entry_identity(entry: object) -> tuple[str, str]:
    if inspect.isclass(entry) or inspect.isfunction(entry):
        module = getattr(entry, "__module__", type(entry).__module__)
        qualname = getattr(entry, "__qualname__", getattr(entry, "__name__", type(entry).__name__))
        return f"{module}.{qualname}", type(entry).__name__
    return f"{type(entry).__module__}.{type(entry).__qualname__}", type(entry).__name__


def discover_registry_snapshot() -> tuple[adapter_pb2.RegistrySnapshot, dict[str, object]]:
    classes = _registry_classes()
    import_failures = _import_registry_domains(name for name, _ in classes)
    classes = _registry_classes()
    entries: list[adapter_pb2.NativeRegistryEntry] = []
    unsupported_registries: list[str] = []
    registry_counts: dict[str, int] = {}
    for registry_name, registry_cls in classes:
        primitive = _REGISTRY_PRIMITIVES.get(registry_name)
        if primitive is None:
            unsupported_registries.append(registry_name)
            continue
        items = sorted(registry_cls.items(), key=lambda item: str(item[0]))
        registry_counts[registry_name] = len(items)
        for key, entry in items:
            implementation, native_type = _entry_identity(entry)
            metadata = sanitize_metadata({
                "registry_class": registry_name,
                "entry_module": getattr(entry, "__module__", type(entry).__module__),
                "entry_qualname": getattr(entry, "__qualname__", getattr(entry, "__name__", type(entry).__qualname__)),
            })
            entries.append(adapter_pb2.NativeRegistryEntry(
                primitive=primitive, key=str(key), implementation=implementation,
                native_type=native_type, metadata=metadata,
            ))
    entries.sort(key=lambda row: (row.primitive, row.key, row.implementation))
    snapshot = adapter_pb2.RegistrySnapshot(runtime_id=RUNTIME_ID, entries=entries)
    diagnostics: dict[str, object] = {
        "schema_version": 1, "source_repo": "openjarvis",
        "upstream_repository": UPSTREAM_REPOSITORY, "upstream_commit": UPSTREAM_COMMIT,
        "registry_class_count": len(classes), "registry_counts": dict(sorted(registry_counts.items())),
        "entry_count": len(entries), "import_failures": import_failures,
        "unsupported_registries": sorted(unsupported_registries),
        "entries": [{
            "primitive": adapter_pb2.RegistryPrimitive.Name(row.primitive), "key": row.key,
            "implementation": row.implementation, "native_type": row.native_type,
            "metadata": dict(sorted(row.metadata.items())),
        } for row in entries],
    }
    return snapshot, diagnostics


def _read_exact(stream: BinaryIO, size: int) -> bytes:
    chunks: list[bytes] = []
    remaining = size
    while remaining:
        chunk = stream.read(remaining)
        if not chunk:
            raise EOFError(f"truncated adapter frame: expected {size} bytes")
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


def read_frame(stream: BinaryIO, *, max_frame_bytes: int = MAX_FRAME_BYTES) -> adapter_pb2.AdapterFrame | None:
    prefix = stream.read(4)
    if prefix == b"":
        return None
    if len(prefix) < 4:
        prefix += _read_exact(stream, 4 - len(prefix))
    length, = struct.unpack(">I", prefix)
    if length == 0 or length > max_frame_bytes:
        raise ValueError("adapter frame length outside allowed range")
    frame = adapter_pb2.AdapterFrame()
    frame.ParseFromString(_read_exact(stream, length))
    if frame.contract_version.major != WIRE_MAJOR:
        raise ValueError("unsupported Clever adapter major")
    if not frame.frame_id.strip() or frame.WhichOneof("body") is None:
        raise ValueError("adapter frame identity/body missing")
    return frame


def write_frame(stream: BinaryIO, frame: adapter_pb2.AdapterFrame, *, max_frame_bytes: int = MAX_FRAME_BYTES) -> None:
    if not 0 < frame.ByteSize() <= max_frame_bytes:
        raise ValueError("adapter frame length outside allowed range")
    payload = frame.SerializeToString(deterministic=True)
    stream.write(struct.pack(">I", len(payload)))
    stream.write(payload)
    stream.flush()


def _now_timestamp() -> tuple[int, int]:
    return divmod(time.time_ns(), 1_000_000_000)


def _stamp(message: object) -> None:
    target = getattr(message, "sent_at", None)
    if target is not None:
        target.seconds, target.nanos = _now_timestamp()


def _frame(frame_id: str, body_name: str, body: object) -> adapter_pb2.AdapterFrame:
    result = adapter_pb2.AdapterFrame(contract_version=contract_version(), frame_id=frame_id)
    _stamp(result)
    getattr(result, body_name).CopyFrom(body)
    return result


def hello_frame() -> adapter_pb2.AdapterFrame:
    return _frame("openjarvis-hello", "hello", adapter_pb2.AdapterHello(
        contract_version=contract_version(), adapter_id=ADAPTER_ID,
        runtime=runtime_pb2.RuntimeDescriptor(
            contract_version=contract_version(), runtime_id=RUNTIME_ID,
            runtime_kind="python-sidecar", implementation_version=UPSTREAM_COMMIT[:12],
            process_id=str(__import__("os").getpid()),
        ),
        upstream_repository=UPSTREAM_REPOSITORY, upstream_commit=UPSTREAM_COMMIT,
        max_frame_bytes=MAX_FRAME_BYTES,
        supported_features=["be32-length-prefix", "registry-snapshot", "runtime-health", "cancel", "shutdown"],
    ))


def health_frame(*, degraded: bool = False, reasons: Iterable[str] = ()) -> adapter_pb2.AdapterFrame:
    reason_list = sorted(set(str(reason) for reason in reasons if str(reason)))
    status = runtime_pb2.RUNTIME_HEALTH_STATUS_DEGRADED if degraded or reason_list else runtime_pb2.RUNTIME_HEALTH_STATUS_READY
    health = runtime_pb2.RuntimeHealth(contract_version=contract_version(), runtime_id=RUNTIME_ID, status=status, degradation_reasons=reason_list)
    health.observed_at.seconds, health.observed_at.nanos = _now_timestamp()
    return _frame("openjarvis-health", "health", health)


def run_protocol(stdin: BinaryIO, stdout: BinaryIO) -> int:
    from adapters.openjarvis.control import serve
    return serve(stdin, stdout, sys.modules[__name__])


def main() -> int:
    parser = argparse.ArgumentParser(description="Clever OpenJarvis supervised sidecar")
    parser.add_argument("--dump-registry", action="store_true")
    args = parser.parse_args()
    if args.dump_registry:
        _, diagnostics = discover_registry_snapshot()
        print(json.dumps(diagnostics, sort_keys=True, separators=(",", ":")))
        return 0
    return run_protocol(sys.stdin.buffer, sys.stdout.buffer)


if __name__ == "__main__":
    raise SystemExit(main())

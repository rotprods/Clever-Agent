from __future__ import annotations

import argparse
import contextlib
from dataclasses import dataclass
from enum import Enum
import importlib
import inspect
import json
import sys
from typing import Any, Iterable, Mapping, Protocol, Sequence

from adapters.openjarvis import UPSTREAM_COMMIT, UPSTREAM_REPOSITORY


class BridgeState(str, Enum):
    UNAVAILABLE = "UNAVAILABLE"
    REGISTERED = "REGISTERED"
    SERVING = "SERVING"
    CLOSED = "CLOSED"


class ModelBridgeError(RuntimeError):
    pass


class ModelUnavailable(ModelBridgeError):
    pass


class NativeContractError(ModelBridgeError):
    pass


class NativeLifecycleError(ModelBridgeError):
    def __init__(self, operation: str, error: BaseException) -> None:
        super().__init__(f"native engine {operation} failed: {type(error).__name__}: {error}")
        self.operation = operation
        self.native_error_type = type(error).__name__


class ExternalAdmissionRequired(ModelBridgeError):
    pass


class _NativeEngine(Protocol):
    def prepare(self, model: str) -> None: ...
    def can_serve(self, model: str) -> bool: ...
    def list_models(self) -> Sequence[str]: ...
    def health(self) -> bool: ...
    def close(self) -> None: ...


@dataclass(frozen=True)
class NativeCatalogEntry:
    key: str
    implementation: str
    native_type: str
    state: BridgeState = BridgeState.REGISTERED

    def as_dict(self) -> dict[str, str]:
        return {
            "key": self.key,
            "implementation": self.implementation,
            "native_type": self.native_type,
            "state": self.state.value,
        }


@dataclass(frozen=True)
class NativeCatalog:
    engines: tuple[NativeCatalogEntry, ...]
    models: tuple[NativeCatalogEntry, ...]
    import_failures: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, object]:
        return {
            "schema_version": 1,
            "source_repo": "openjarvis",
            "upstream_repository": UPSTREAM_REPOSITORY,
            "upstream_commit": UPSTREAM_COMMIT,
            "engine_count": len(self.engines),
            "model_count": len(self.models),
            "engines": [entry.as_dict() for entry in self.engines],
            "models": [entry.as_dict() for entry in self.models],
            "import_failures": list(self.import_failures),
            "upstream_execution": False,
            "model_executions": 0,
            "provider_egress_executions": 0,
            "parity_promotions": 0,
        }


def _entry_identity(entry: object) -> tuple[str, str]:
    if inspect.isclass(entry) or inspect.isfunction(entry):
        module = getattr(entry, "__module__", type(entry).__module__)
        qualname = getattr(entry, "__qualname__", getattr(entry, "__name__", type(entry).__name__))
        return f"{module}.{qualname}", type(entry).__name__
    entry_type = type(entry)
    return f"{entry_type.__module__}.{entry_type.__qualname__}", entry_type.__name__


def _catalog_entries(registry: type) -> tuple[NativeCatalogEntry, ...]:
    rows: list[NativeCatalogEntry] = []
    for key, entry in sorted(registry.items(), key=lambda item: str(item[0])):
        implementation, native_type = _entry_identity(entry)
        rows.append(
            NativeCatalogEntry(
                key=str(key),
                implementation=implementation,
                native_type=native_type,
            )
        )
    return tuple(rows)


def _native_registry_classes() -> tuple[type, type, tuple[str, ...]]:
    failures: list[str] = []
    with contextlib.redirect_stdout(sys.stderr):
        for module_name in ("openjarvis.engine", "openjarvis.intelligence"):
            try:
                module = importlib.import_module(module_name)
                if module_name == "openjarvis.intelligence":
                    register_builtin = getattr(module, "register_builtin_models", None)
                    if callable(register_builtin):
                        register_builtin()
            except Exception as exc:  # optional extras/platform bindings can fail at import
                failures.append(f"{module_name}:{type(exc).__name__}")
        registry_module = importlib.import_module("openjarvis.core.registry")
    return (
        getattr(registry_module, "EngineRegistry"),
        getattr(registry_module, "ModelRegistry"),
        tuple(sorted(failures)),
    )


def discover_native_catalog(
    *,
    engine_registry: type | None = None,
    model_registry: type | None = None,
    import_failures: Iterable[str] = (),
) -> NativeCatalog:
    failures = tuple(sorted(str(item) for item in import_failures))
    if engine_registry is None or model_registry is None:
        if engine_registry is not None or model_registry is not None:
            raise ValueError("engine_registry and model_registry must be supplied together")
        engine_registry, model_registry, native_failures = _native_registry_classes()
        failures = tuple(sorted((*failures, *native_failures)))
    return NativeCatalog(
        engines=_catalog_entries(engine_registry),
        models=_catalog_entries(model_registry),
        import_failures=failures,
    )


class EngineModelBridge:
    """Lifecycle-only bridge for one native OpenJarvis engine.

    W02-08 deliberately does not expose generate/stream. External lifecycle calls are
    fail-closed because the Rust T0 W02-07 egress grant is not serializable authority.
    A later execution lane must be admitted through that kernel boundary rather than
    teaching this Python adapter to self-authorize provider access.
    """

    def __init__(
        self,
        *,
        engine_id: str,
        engine: _NativeEngine,
        registered_models: Iterable[str],
        external: bool = False,
    ) -> None:
        if not engine_id.strip():
            raise ValueError("engine_id must be non-empty")
        required = ("prepare", "can_serve", "list_models", "health", "close")
        missing = [name for name in required if not callable(getattr(engine, name, None))]
        if missing:
            raise NativeContractError(f"native engine missing lifecycle methods: {','.join(missing)}")
        self._engine_id = engine_id
        self._engine = engine
        self._registered_models = frozenset(
            value.strip() for value in map(str, registered_models) if value.strip()
        )
        self._external = bool(external)
        self._prepared_models: set[str] = set()
        self._closed = False

    @property
    def engine_id(self) -> str:
        return self._engine_id

    @property
    def external(self) -> bool:
        return self._external

    @property
    def execution_enabled(self) -> bool:
        return False

    def _ensure_open(self) -> None:
        if self._closed:
            raise NativeLifecycleError("lifecycle", RuntimeError("bridge is closed"))

    def _require_lifecycle_admission(self, operation: str) -> None:
        self._ensure_open()
        if self._external:
            raise ExternalAdmissionRequired(
                f"external engine {operation} requires prior Rust T0 W02-07 admission; W02-08 cannot self-authorize egress"
            )

    def list_models(self) -> list[str]:
        self._require_lifecycle_admission("list_models")
        try:
            raw = self._engine.list_models()
        except Exception as exc:
            raise NativeLifecycleError("list_models", exc) from exc
        if isinstance(raw, (str, bytes)) or not isinstance(raw, Sequence):
            raise NativeContractError("native engine list_models must return a sequence of strings")
        models = [str(item) for item in raw]
        if any(not item.strip() for item in models):
            raise NativeContractError("native engine list_models returned an empty model id")
        return models

    def health(self) -> bool:
        self._require_lifecycle_admission("health")
        try:
            result = self._engine.health()
        except Exception as exc:
            raise NativeLifecycleError("health", exc) from exc
        if type(result) is not bool:
            raise NativeContractError("native engine health must return bool")
        return result

    def can_serve(self, model: str) -> bool:
        self._require_lifecycle_admission("can_serve")
        if not model.strip():
            raise ValueError("model must be non-empty")
        try:
            result = self._engine.can_serve(model)
        except Exception as exc:
            raise NativeLifecycleError("can_serve", exc) from exc
        if type(result) is not bool:
            raise NativeContractError("native engine can_serve must return bool")
        return result

    def prepare(self, model: str) -> None:
        self._require_lifecycle_admission("prepare")
        if not model.strip():
            raise ValueError("model must be non-empty")
        discovered = set(self.list_models())
        if model not in self._registered_models and model not in discovered:
            raise ModelUnavailable(f"model {model!r} is not registered or listed by engine {self._engine_id!r}")
        try:
            self._engine.prepare(model)
        except Exception as exc:
            self._prepared_models.discard(model)
            raise NativeLifecycleError("prepare", exc) from exc
        self._prepared_models.add(model)

    def state(self, model: str) -> BridgeState:
        if self._closed:
            return BridgeState.CLOSED
        if not model.strip():
            return BridgeState.UNAVAILABLE
        registered = model in self._registered_models
        if self._external:
            return BridgeState.REGISTERED if registered else BridgeState.UNAVAILABLE
        try:
            listed = model in self.list_models()
        except (NativeLifecycleError, NativeContractError):
            listed = False
        if not registered and not listed:
            return BridgeState.UNAVAILABLE
        if model not in self._prepared_models:
            return BridgeState.REGISTERED
        try:
            healthy = self.health()
            serviceable = self.can_serve(model)
            listed_after_prepare = model in self.list_models()
        except (NativeLifecycleError, NativeContractError):
            return BridgeState.REGISTERED
        if healthy and serviceable and listed_after_prepare:
            return BridgeState.SERVING
        return BridgeState.REGISTERED

    def close(self) -> None:
        if self._closed:
            return
        try:
            self._engine.close()
        except Exception as exc:
            raise NativeLifecycleError("close", exc) from exc
        self._prepared_models.clear()
        self._closed = True


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect OpenJarvis model/engine registrations without executing inference")
    parser.add_argument("--dump-catalog", action="store_true")
    args = parser.parse_args()
    if not args.dump_catalog:
        parser.error("--dump-catalog is required; W02-08 exposes no inference execution CLI")
    catalog = discover_native_catalog()
    print(json.dumps(catalog.as_dict(), sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

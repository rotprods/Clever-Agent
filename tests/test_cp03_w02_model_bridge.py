from __future__ import annotations

import unittest

from adapters.openjarvis.model_bridge import (
    BridgeState,
    EngineModelBridge,
    ExternalAdmissionRequired,
    ModelUnavailable,
    NativeCatalogEntry,
    NativeContractError,
    NativeLifecycleError,
    discover_native_catalog,
)


class _Registry:
    _items: dict[str, object] = {}

    @classmethod
    def items(cls):
        return cls._items.items()


class _EngineRegistry(_Registry):
    _items = {"local": object}


class _ModelRegistry(_Registry):
    _items = {"model-a": object, "model-b": object}


class FakeEngine:
    def __init__(self, *, models=None, healthy=True, serviceable=True, prepare_error=None):
        self.models = list(models or ["model-a"])
        self.healthy = healthy
        self.serviceable = serviceable
        self.prepare_error = prepare_error
        self.calls: list[tuple[str, str | None]] = []

    def prepare(self, model: str) -> None:
        self.calls.append(("prepare", model))
        if self.prepare_error is not None:
            raise self.prepare_error

    def can_serve(self, model: str) -> bool:
        self.calls.append(("can_serve", model))
        return self.serviceable

    def list_models(self):
        self.calls.append(("list_models", None))
        return list(self.models)

    def health(self) -> bool:
        self.calls.append(("health", None))
        return self.healthy

    def close(self) -> None:
        self.calls.append(("close", None))


class BrokenHealthEngine(FakeEngine):
    def health(self):
        self.calls.append(("health", None))
        return "yes"


class OpenJarvisModelBridgeTests(unittest.TestCase):
    def test_catalog_discovery_registers_without_execution(self) -> None:
        catalog = discover_native_catalog(
            engine_registry=_EngineRegistry,
            model_registry=_ModelRegistry,
        )
        payload = catalog.as_dict()
        self.assertEqual(payload["engine_count"], 1)
        self.assertEqual(payload["model_count"], 2)
        self.assertEqual(payload["model_executions"], 0)
        self.assertEqual(payload["provider_egress_executions"], 0)
        self.assertEqual(payload["parity_promotions"], 0)
        self.assertTrue(all(row["state"] == "REGISTERED" for row in payload["engines"] + payload["models"]))
        self.assertIsInstance(catalog.engines[0], NativeCatalogEntry)

    def test_registered_is_not_serving_until_prepare_and_runtime_checks_pass(self) -> None:
        engine = FakeEngine(models=["model-a"], healthy=True, serviceable=True)
        bridge = EngineModelBridge(
            engine_id="local",
            engine=engine,
            registered_models=["model-a"],
        )
        self.assertEqual(bridge.state("model-a"), BridgeState.REGISTERED)
        self.assertFalse(bridge.execution_enabled)
        bridge.prepare("model-a")
        self.assertEqual(bridge.state("model-a"), BridgeState.SERVING)
        self.assertIn(("prepare", "model-a"), engine.calls)
        self.assertIn(("health", None), engine.calls)
        self.assertIn(("can_serve", "model-a"), engine.calls)

    def test_can_serve_default_true_cannot_promote_unprepared_model(self) -> None:
        engine = FakeEngine(models=["model-a"], healthy=True, serviceable=True)
        bridge = EngineModelBridge(engine_id="local", engine=engine, registered_models=["model-a"])
        self.assertTrue(bridge.can_serve("model-a"))
        self.assertEqual(bridge.state("model-a"), BridgeState.REGISTERED)

    def test_missing_model_is_unavailable_and_prepare_fails_before_native_prepare(self) -> None:
        engine = FakeEngine(models=["model-a"])
        bridge = EngineModelBridge(engine_id="local", engine=engine, registered_models=["model-a"])
        self.assertEqual(bridge.state("missing"), BridgeState.UNAVAILABLE)
        with self.assertRaises(ModelUnavailable):
            bridge.prepare("missing")
        self.assertNotIn(("prepare", "missing"), engine.calls)

    def test_prepare_failure_is_not_serving_and_preserves_failure(self) -> None:
        engine = FakeEngine(models=["model-a"], prepare_error=RuntimeError("weights unavailable"))
        bridge = EngineModelBridge(engine_id="local", engine=engine, registered_models=["model-a"])
        with self.assertRaises(NativeLifecycleError) as raised:
            bridge.prepare("model-a")
        self.assertEqual(raised.exception.operation, "prepare")
        self.assertEqual(bridge.state("model-a"), BridgeState.REGISTERED)

    def test_health_and_can_serve_must_be_native_bools(self) -> None:
        engine = BrokenHealthEngine(models=["model-a"])
        bridge = EngineModelBridge(engine_id="local", engine=engine, registered_models=["model-a"])
        with self.assertRaises(NativeContractError):
            bridge.health()

    def test_close_is_idempotent_and_state_is_closed(self) -> None:
        engine = FakeEngine(models=["model-a"])
        bridge = EngineModelBridge(engine_id="local", engine=engine, registered_models=["model-a"])
        bridge.prepare("model-a")
        bridge.close()
        bridge.close()
        self.assertEqual(bridge.state("model-a"), BridgeState.CLOSED)
        self.assertEqual(engine.calls.count(("close", None)), 1)

    def test_external_lifecycle_fails_before_native_call(self) -> None:
        engine = FakeEngine(models=["model-a"])
        bridge = EngineModelBridge(
            engine_id="cloud",
            engine=engine,
            registered_models=["model-a"],
            external=True,
        )
        self.assertEqual(bridge.state("model-a"), BridgeState.REGISTERED)
        for operation in (
            lambda: bridge.list_models(),
            lambda: bridge.health(),
            lambda: bridge.can_serve("model-a"),
            lambda: bridge.prepare("model-a"),
        ):
            with self.assertRaises(ExternalAdmissionRequired):
                operation()
        self.assertEqual(engine.calls, [])
        self.assertFalse(bridge.execution_enabled)
        self.assertFalse(hasattr(bridge, "generate"))
        self.assertFalse(hasattr(bridge, "stream"))

    def test_registry_injection_is_all_or_nothing(self) -> None:
        with self.assertRaises(ValueError):
            discover_native_catalog(engine_registry=_EngineRegistry)


if __name__ == "__main__":
    unittest.main()

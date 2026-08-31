from __future__ import annotations

import json
from pathlib import Path
import subprocess
import tempfile
import unittest

from scripts.cosgraph.engine import build_cos_hypergraph
from scripts.graphify.engine import graphify_repository
from scripts.graphify.model import Node, RepositoryGraph, stable_id
from scripts.upstream.ledger import UpstreamPin, load_upstream_pins
from scripts.upstream.source_projection import materialize_pin
from scripts.upstream.sync_upstreams import acquire, pin_ref
from scripts.upstream.verify_pins import verify


def _git(repository: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=repository,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr)
    return result.stdout.strip()


class LedgerTests(unittest.TestCase):
    def test_exact_sha_and_safe_source_parse(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ledger.yaml"
            path.write_text(
                "version: 1\nsources:\n"
                "  - id: alpha\n"
                "    repository: org/repo\n"
                "    url: https://github.com/org/repo\n"
                "    branch: main\n"
                f"    pinned_commit: {'a' * 40}\n"
                "    license: MIT\n"
                "    role: test\n"
                "    integration: adapter\n",
                encoding="utf-8",
            )
            pins = load_upstream_pins(path)
            self.assertEqual(pins[0].pinned_commit, "a" * 40)


class AcquisitionTests(unittest.TestCase):
    def _source_repo(self, root: Path) -> tuple[Path, str]:
        source = root / "source"
        source.mkdir()
        _git(source, "init", "--quiet")
        _git(source, "config", "user.email", "test@example.invalid")
        _git(source, "config", "user.name", "Graphify Test")
        (source / "hello.py").write_text("def hello():\n    return 'world'\n", encoding="utf-8")
        (source / "package.json").write_text(json.dumps({"dependencies": {"alpha": "1"}}), encoding="utf-8")
        (source / "asset.bin").write_bytes(b"binary-asset-that-must-not-materialize")
        _git(source, "add", ".")
        _git(source, "commit", "--quiet", "-m", "fixture")
        return source, _git(source, "rev-parse", "HEAD")

    def test_object_store_is_exact_retryable_and_sparse_projection_excludes_binary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source, commit = self._source_repo(root)
            pin = UpstreamPin("fixture", "local/fixture", source.as_posix(), "master", commit, "MIT", "test", "adapter")
            cache = root / "cache"
            first = acquire(pin, cache)
            second = acquire(pin, cache)
            repository = cache / pin.id
            self.assertEqual(first["actual_commit"], commit)
            self.assertEqual(second["actual_commit"], commit)
            self.assertEqual(_git(repository, "rev-parse", pin_ref(pin)), commit)
            self.assertFalse((repository / "hello.py").exists())

            projection = materialize_pin(pin, cache)
            self.assertEqual(projection["worktree_head"], commit)
            self.assertTrue((repository / "hello.py").exists())
            self.assertTrue((repository / "package.json").exists())
            self.assertFalse((repository / "asset.bin").exists())

    def test_wrong_sha_and_unreachable_remote_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source, _ = self._source_repo(root)
            wrong = UpstreamPin("wrong", "local/wrong", source.as_posix(), "master", "0" * 40, "MIT", "test", "adapter")
            with self.assertRaises(RuntimeError):
                acquire(wrong, root / "wrong-cache")
            unreachable = UpstreamPin(
                "offline",
                "local/offline",
                (root / "does-not-exist").as_posix(),
                "master",
                "1" * 40,
                "MIT",
                "test",
                "adapter",
            )
            with self.assertRaises(RuntimeError):
                acquire(unreachable, root / "offline-cache")

    def test_verifier_uses_immutable_pin_ref_not_floating_head(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source, commit = self._source_repo(root)
            local_pin = UpstreamPin("fixture", "local/fixture", source.as_posix(), "master", commit, "MIT", "test", "adapter")
            cache = root / "cache"
            acquire(local_pin, cache)
            repository = cache / local_pin.id

            # Preserve the already-acquired object store but make its declared
            # origin match the same HTTPS-only policy enforced in production.
            github_url = "https://github.com/local/fixture"
            _git(repository, "remote", "set-url", "origin", github_url)
            ledger = root / "ledger.yaml"
            ledger.write_text(
                "version: 1\nsources:\n"
                "  - id: fixture\n"
                "    repository: local/fixture\n"
                f"    url: {github_url}\n"
                "    branch: master\n"
                f"    pinned_commit: {commit}\n"
                "    license: MIT\n"
                "    role: test\n"
                "    integration: adapter\n",
                encoding="utf-8",
            )
            payload = verify(ledger, cache)
            self.assertEqual(payload["sources"][0]["status"], "VERIFIED")
            self.assertEqual(payload["sources"][0]["actual_commit"], commit)


class GraphifyTests(unittest.TestCase):
    def test_graph_is_deterministic_and_extracts_python_surfaces(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "app.py").write_text(
                "from fastapi import FastAPI\napp = FastAPI()\n"
                "class ResearchAgent: pass\n"
                "@app.get('/health')\ndef health(): return {'ok': True}\n",
                encoding="utf-8",
            )
            first = graphify_repository(root, "sample", "b" * 40).to_dict()
            second = graphify_repository(root, "sample", "b" * 40).to_dict()
            self.assertEqual(first, second)
            kinds = {node["kind"] for node in first["nodes"]}
            self.assertIn("agent", kinds)
            self.assertIn("route", kinds)

    def test_shared_workspace_dependency_is_one_node_with_multiple_edges(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in ("one", "two"):
                package = root / name
                package.mkdir()
                (package / "package.json").write_text(
                    json.dumps({"dependencies": {"shared-lib": "1.0.0"}}),
                    encoding="utf-8",
                )
            graph = graphify_repository(root, "workspace", "d" * 40).to_dict()
            dependencies = [
                node
                for node in graph["nodes"]
                if node["kind"] == "dependency" and node["name"] == "shared-lib"
            ]
            self.assertEqual(len(dependencies), 1)
            requires = [
                edge
                for edge in graph["edges"]
                if edge["relation"] == "requires" and edge["target"] == dependencies[0]["id"]
            ]
            self.assertEqual(len(requires), 2)

    def test_stable_id_changes_when_semantic_identity_changes(self) -> None:
        self.assertEqual(stable_id("x", "a"), stable_id("x", "a"))
        self.assertNotEqual(stable_id("x", "a"), stable_id("x", "b"))


class COSGraphTests(unittest.TestCase):
    def _graph(self, repo: str, kind: str, name: str, language: str = "python") -> dict:
        graph = RepositoryGraph(repo, "c" * 40)
        node = Node(
            id=stable_id("symbol", repo, kind, name),
            kind=kind,
            name=name,
            source_repo=repo,
            source_commit="c" * 40,
            path=f"src/{name}.py",
            language=language,
        )
        graph.add_node(node)
        return graph.to_dict()

    def test_source_nodes_are_never_dropped(self) -> None:
        g1 = self._graph("a", "agent", "PlannerAgent")
        g2 = self._graph("b", "agent", "RouterAgent")
        result = build_cos_hypergraph([g1, g2])
        expected = len(g1["nodes"]) + len(g2["nodes"])
        self.assertEqual(len(result["source_nodes"]), expected)
        self.assertEqual(result["invariants"]["source_nodes_preserved"], expected)

    def test_persistence_overlap_becomes_merge_state_not_rewrite(self) -> None:
        g1 = self._graph("a", "persistence", "MemoryStore")
        g2 = self._graph("b", "persistence", "SessionStore")
        result = build_cos_hypergraph([g1, g2])
        component = next(
            item
            for item in result["canonical_components"]
            if item["family"] == "persistence"
        )
        self.assertEqual(component["decision"], "MERGE_STATE")
        self.assertEqual(component["source_repositories"], ["a", "b"])
        self.assertFalse(component["rewrite_allowed"])


if __name__ == "__main__":
    unittest.main()

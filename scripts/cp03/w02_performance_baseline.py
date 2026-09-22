from __future__ import annotations

import argparse
import asyncio
import json
import os
from pathlib import Path
import statistics
import subprocess
import sys
import threading
import time
from typing import Any, Callable

import httpx

ROOT = Path(__file__).resolve().parents[2]
GENERATED = ROOT / "contracts" / "sdk" / "python" / "gen"
for path in (ROOT, GENERATED):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from adapters.openjarvis.sidecar import MAX_FRAME_BYTES, read_frame, write_frame
from adapters.openjarvis.unary_inference import (
    PINNED_ARTIFACT_SHA256,
    PINNED_ENGINE_ID,
    PINNED_MODEL_ID,
    _artifact_path,
    _messages,
    _native_engine_factory,
    attest_pinned_artifact,
)
from clever.v1 import adapter_pb2, common_pb2, identity_pb2, inference_pb2

TASK = "W02-16"
SUITE = "P01_SAME_HOST_PERFORMANCE_BASELINE"
SUITE_VERSION = 1
BUDGET: dict[str, Any] = {
    "warmups_per_path": 1,
    "samples_per_path": 3,
    "max_output_tokens": 32,
    "temperature": 0.0,
    "prompt": "Reply with exactly four words: clever jarvis performance baseline",
    "order": ["direct", "adapted", "adapted", "direct", "direct", "adapted"],
    "ctx_size": 2048,
    "llama_threads": 2,
    "llama_parallel": 1,
}


def _request(label: str) -> inference_pb2.InferenceRequest:
    deadline = time.time_ns() + 120_000_000_000
    seconds, nanos = divmod(deadline, 1_000_000_000)
    req = inference_pb2.InferenceRequest(
        contract_version=common_pb2.ContractVersion(major=1, minor=2),
        request_id=f"perf-{label}",
        attempt_id=f"perf-{label}-attempt-1",
        principal=identity_pb2.PrincipalRef(user_id="clever-perf-local"),
        session_id="clever-perf-same-host",
        engine_id=PINNED_ENGINE_ID,
        model_id=PINNED_MODEL_ID,
        inputs=[
            inference_pb2.InferenceInput(
                role=inference_pb2.INFERENCE_ROLE_USER,
                content=BUDGET["prompt"],
            )
        ],
        config=inference_pb2.InferenceConfig(
            max_output_tokens=BUDGET["max_output_tokens"],
            temperature=BUDGET["temperature"],
            stream=True,
        ),
        idempotency_key=f"perf-{label}-idem",
    )
    req.deadline_at.seconds = seconds
    req.deadline_at.nanos = nanos
    return req


def _rss_kib(pid: int) -> int:
    try:
        for line in Path(f"/proc/{pid}/status").read_text().splitlines():
            if line.startswith("VmRSS:"):
                return int(line.split()[1])
    except (FileNotFoundError, ProcessLookupError, PermissionError, ValueError):
        return 0
    return 0


class _RssSampler:
    def __init__(self, pids: dict[str, int]) -> None:
        self.pids = pids
        self.peak = {name: 0 for name in pids}
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def _run(self) -> None:
        while not self._stop.is_set():
            for name, pid in self.pids.items():
                self.peak[name] = max(self.peak[name], _rss_kib(pid))
            self._stop.wait(0.01)

    def __enter__(self) -> "_RssSampler":
        self._thread.start()
        return self

    def __exit__(self, *_: object) -> None:
        self._stop.set()
        self._thread.join(timeout=1.0)
        for name, pid in self.pids.items():
            self.peak[name] = max(self.peak[name], _rss_kib(pid))


def _tokenize_output(host: str, text: str) -> int:
    """Count generated text with the exact same-host llama.cpp tokenizer.

    The pinned OpenJarvis ``stream_full`` endpoint does not request OpenAI
    ``include_usage`` stream metadata, so a successful model stream may have no
    completion-token count. P01 must not fabricate throughput from bytes,
    characters or chunks. Tokenization happens after the timed interval against
    the already-running loopback llama-server and therefore provides a common,
    model-native denominator for direct and adapted paths without provider
    egress or a second model execution.
    """
    if not text:
        raise RuntimeError("cannot tokenize empty streamed output")
    response = httpx.post(
        f"{host.rstrip('/')}/tokenize",
        json={"content": text, "add_special": False, "parse_special": False},
        timeout=10.0,
    )
    response.raise_for_status()
    payload = response.json()
    tokens = payload.get("tokens") if isinstance(payload, dict) else None
    if not isinstance(tokens, list) or not tokens:
        raise RuntimeError("llama-server /tokenize returned no output tokens")
    return len(tokens)


def _resolve_output_tokens(
    reported_tokens: int | None,
    text: str,
    host: str,
    *,
    tokenizer: Callable[[str, str], int] = _tokenize_output,
) -> tuple[int, str]:
    if type(reported_tokens) is int and reported_tokens > 0:
        return reported_tokens, "stream_usage"
    count = tokenizer(host, text)
    if type(count) is not int or count <= 0:
        raise RuntimeError("same-host tokenizer produced no measurable output tokens")
    return count, "llama_server_tokenize_output_text"


def _sample_result(
    path: str,
    started_ns: int,
    first_ns: int | None,
    ended_ns: int,
    output_tokens: int,
    peak: dict[str, int],
    token_count_source: str,
) -> dict[str, Any]:
    if first_ns is None or output_tokens <= 0:
        raise RuntimeError(f"{path} produced no measurable streamed output")
    latency_ms = (ended_ns - started_ns) / 1_000_000
    ttft_ms = (first_ns - started_ns) / 1_000_000
    return {
        "path": path,
        "latency_ms": latency_ms,
        "ttft_ms": ttft_ms,
        "output_tokens": output_tokens,
        "token_count_source": token_count_source,
        "throughput_tokens_per_s": output_tokens / ((ended_ns - started_ns) / 1_000_000_000),
        "peak_rss_kib": peak,
    }


def run_direct(label: str, llama_pid: int) -> dict[str, Any]:
    req = _request(label)
    host = os.environ["LLAMACPP_HOST"].rstrip("/")
    engine = None
    first_ns: int | None = None
    reported_output_tokens: int | None = None
    text_parts: list[str] = []
    started_ns = time.monotonic_ns()
    try:
        engine, message_type, role_type = _native_engine_factory(host)
        messages = _messages(req, message_type, role_type)
        usage: dict[str, Any] | None = None

        async def consume() -> None:
            nonlocal first_ns, usage
            async for native in engine.stream_full(
                messages,
                model=PINNED_MODEL_ID,
                temperature=float(BUDGET["temperature"]),
                max_tokens=int(BUDGET["max_output_tokens"]),
                chat_template_kwargs={"enable_thinking": False},
            ):
                content = getattr(native, "content", None)
                if isinstance(content, str) and content:
                    text_parts.append(content)
                    if first_ns is None:
                        first_ns = time.monotonic_ns()
                native_usage = getattr(native, "usage", None)
                if isinstance(native_usage, dict):
                    usage = native_usage

        with _RssSampler({"client": os.getpid(), "llama_server": llama_pid}) as sampler:
            asyncio.run(consume())
        ended_ns = time.monotonic_ns()
        if usage and type(usage.get("completion_tokens")) is int:
            reported_output_tokens = int(usage["completion_tokens"])
        output_tokens, token_count_source = _resolve_output_tokens(
            reported_output_tokens,
            "".join(text_parts),
            host,
        )
        return _sample_result(
            "direct",
            started_ns,
            first_ns,
            ended_ns,
            output_tokens,
            sampler.peak,
            token_count_source,
        )
    finally:
        if engine is not None and callable(getattr(engine, "close", None)):
            engine.close()


class SidecarClient:
    def __init__(self) -> None:
        env = os.environ.copy()
        env["PYTHONPATH"] = os.pathsep.join(
            x for x in [str(ROOT), str(GENERATED), env.get("CLEVER_OPENJARVIS_SRC", ""), env.get("PYTHONPATH", "")] if x
        )
        self.proc = subprocess.Popen(
            [sys.executable, str(ROOT / "adapters/openjarvis/sidecar.py")],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
        )
        assert self.proc.stdin is not None and self.proc.stdout is not None
        hello = read_frame(self.proc.stdout)
        if hello is None or hello.WhichOneof("body") != "hello":
            raise RuntimeError("sidecar did not emit AdapterHello")
        ack = adapter_pb2.AdapterFrame(
            contract_version=common_pb2.ContractVersion(major=1, minor=1),
            frame_id="perf-hello-ack",
            hello_ack=adapter_pb2.AdapterHelloAck(
                contract_version=common_pb2.ContractVersion(major=1, minor=1),
                adapter_id=hello.hello.adapter_id,
                accepted=True,
                max_frame_bytes=MAX_FRAME_BYTES,
                negotiated_features=["streaming-inference"],
            ),
        )
        write_frame(self.proc.stdin, ack)

    def run(self, label: str, llama_pid: int) -> dict[str, Any]:
        assert self.proc.stdin is not None and self.proc.stdout is not None
        req = _request(label)
        frame_id = f"perf-frame-{label}"
        frame = adapter_pb2.AdapterFrame(
            contract_version=common_pb2.ContractVersion(major=1, minor=1),
            frame_id=frame_id,
            inference_request=req,
        )
        first_ns: int | None = None
        reported_output_tokens: int | None = None
        text_parts: list[str] = []
        started_ns = time.monotonic_ns()
        with _RssSampler({"client": self.proc.pid, "llama_server": llama_pid}) as sampler:
            write_frame(self.proc.stdin, frame)
            while True:
                response = read_frame(self.proc.stdout)
                if response is None:
                    raise RuntimeError("sidecar EOF before inference terminal")
                if response.correlation_id != frame_id:
                    continue
                body = response.WhichOneof("body")
                if body == "inference_chunk":
                    content = response.inference_chunk.text_delta
                    if content:
                        text_parts.append(content)
                        if first_ns is None:
                            first_ns = time.monotonic_ns()
                elif body == "inference_error":
                    raise RuntimeError(f"sidecar inference error: {response.inference_error.message}")
                elif body == "error":
                    raise RuntimeError(f"sidecar adapter error: {response.error.code}: {response.error.message}")
                elif body == "inference_terminal":
                    usage = response.inference_terminal.usage
                    if usage.HasField("output_tokens"):
                        reported_output_tokens = int(usage.output_tokens)
                    break
        ended_ns = time.monotonic_ns()
        host = os.environ["LLAMACPP_HOST"].rstrip("/")
        output_tokens, token_count_source = _resolve_output_tokens(
            reported_output_tokens,
            "".join(text_parts),
            host,
        )
        return _sample_result(
            "adapted",
            started_ns,
            first_ns,
            ended_ns,
            output_tokens,
            sampler.peak,
            token_count_source,
        )

    def close(self) -> None:
        if self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.proc.kill()
                self.proc.wait(timeout=3)
        if self.proc.stderr is not None:
            stderr = self.proc.stderr.read().decode("utf-8", errors="replace")
            if self.proc.returncode not in (0, -15) and stderr:
                raise RuntimeError(f"sidecar exited {self.proc.returncode}: {stderr[-2000:]}")


def _summary(samples: list[dict[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for path in ("direct", "adapted"):
        rows = [x for x in samples if x["path"] == path]
        if len(rows) != BUDGET["samples_per_path"]:
            raise RuntimeError(f"expected fixed {BUDGET['samples_per_path']} {path} samples, got {len(rows)}")
        out[path] = {
            "sample_count": len(rows),
            "latency_ms_median": statistics.median(x["latency_ms"] for x in rows),
            "ttft_ms_median": statistics.median(x["ttft_ms"] for x in rows),
            "throughput_tokens_per_s_median": statistics.median(x["throughput_tokens_per_s"] for x in rows),
            "client_peak_rss_kib_max": max(x["peak_rss_kib"]["client"] for x in rows),
            "llama_server_peak_rss_kib_max": max(x["peak_rss_kib"]["llama_server"] for x in rows),
        }
    out["adapted_over_direct"] = {
        "latency_ratio": out["adapted"]["latency_ms_median"] / out["direct"]["latency_ms_median"],
        "ttft_ratio": out["adapted"]["ttft_ms_median"] / out["direct"]["ttft_ms_median"],
        "throughput_ratio": out["adapted"]["throughput_tokens_per_s_median"] / out["direct"]["throughput_tokens_per_s_median"],
    }
    return out


def validate(report: dict[str, Any]) -> None:
    assert report["schema_version"] == 1
    assert report["task"] == TASK and report["suite"] == SUITE
    assert report["result"] == "PASS"
    assert report["budget"] == BUDGET
    assert report["same_host"] is True
    assert report["paths"] == ["direct_openjarvis_stream_full", "canonical_adapterframe_sidecar_stream"]
    assert report["provider_egress_executions"] == 0
    assert report["tool_executions"] == 0 and report["parity_promotions"] == 0
    assert report["global_denominator"] == 7565 and report["openjarvis_obligations"] == 646
    assert len(report["samples"]) == BUDGET["samples_per_path"] * 2
    expected = {"direct": BUDGET["samples_per_path"], "adapted": BUDGET["samples_per_path"]}
    observed = {name: sum(1 for row in report["samples"] if row["path"] == name) for name in expected}
    assert observed == expected
    for row in report["samples"]:
        assert row["latency_ms"] > 0 and 0 < row["ttft_ms"] <= row["latency_ms"]
        assert row["output_tokens"] > 0 and row["throughput_tokens_per_s"] > 0
        assert row["token_count_source"] in {"stream_usage", "llama_server_tokenize_output_text"}
        assert row["peak_rss_kib"]["client"] > 0 and row["peak_rss_kib"]["llama_server"] > 0
    for path in ("direct", "adapted"):
        assert report["summary"][path]["sample_count"] == BUDGET["samples_per_path"]
    assert report["performance_threshold"] == "MEASUREMENT_ONLY_NO_POST_HOC_THRESHOLD"


def run(out: Path) -> None:
    artifact = _artifact_path()
    attest_pinned_artifact(artifact)
    llama_pid = int(os.environ["CLEVER_W02_LLAMA_PID"])
    if _rss_kib(llama_pid) <= 0:
        raise RuntimeError("local llama-server PID is not measurable on this host")
    sidecar = SidecarClient()
    try:
        # Fixed warmups are deliberately excluded from measured samples.
        run_direct("warmup-direct", llama_pid)
        sidecar.run("warmup-adapted", llama_pid)
        samples: list[dict[str, Any]] = []
        counts = {"direct": 0, "adapted": 0}
        for path in BUDGET["order"]:
            counts[path] += 1
            label = f"{path}-{counts[path]}"
            samples.append(run_direct(label, llama_pid) if path == "direct" else sidecar.run(label, llama_pid))
        report = {
            "schema_version": 1,
            "project_id": "CLEVER-JARVIS-001",
            "checkpoint": "CP03",
            "parent_wave": "CP03-W02",
            "task": TASK,
            "gate": "G5",
            "suite": SUITE,
            "suite_version": SUITE_VERSION,
            "result": "PASS",
            "source_head": os.environ.get("GITHUB_SHA", "UNKNOWN"),
            "github_actions_run_id": int(os.environ.get("GITHUB_RUN_ID", "0")),
            "same_host": True,
            "host_class": os.environ.get("RUNNER_NAME", "local-linux"),
            "engine": PINNED_ENGINE_ID,
            "model_id": PINNED_MODEL_ID,
            "artifact_sha256": PINNED_ARTIFACT_SHA256,
            "runtime_commit": os.environ.get("LLAMACPP_SHA", "UNKNOWN"),
            "openjarvis_commit": os.environ.get("OPENJARVIS_SHA", "UNKNOWN"),
            "paths": ["direct_openjarvis_stream_full", "canonical_adapterframe_sidecar_stream"],
            "budget": BUDGET,
            "samples": samples,
            "summary": _summary(samples),
            "performance_threshold": "MEASUREMENT_ONLY_NO_POST_HOC_THRESHOLD",
            "provider_egress_executions": 0,
            "tool_executions": 0,
            "parity_promotions": 0,
            "verified_capabilities": 0,
            "global_denominator": 7565,
            "openjarvis_obligations": 646,
            "prior_p02_evidence_id": "EVID-W02-RECOVERY-RETEST-20260922",
        }
        validate(report)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    finally:
        sidecar.close()


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    run_p = sub.add_parser("run")
    run_p.add_argument("--out", type=Path, required=True)
    val_p = sub.add_parser("validate")
    val_p.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    if args.cmd == "run":
        run(args.out)
    else:
        validate(json.loads(args.report.read_text()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

from dataclasses import dataclass
import multiprocessing as mp
import os
import queue
import signal
import time
from typing import Callable

from clever.v1 import common_pb2, inference_pb2

from adapters.openjarvis.streaming_inference import execute_stream
from adapters.openjarvis.unary_inference import UnaryInferenceRejected


@dataclass(frozen=True)
class LocalCancellationReceipt:
    requested: bool
    acknowledged: bool
    process_stopped: bool
    forced_kill: bool
    remote_effect: str = "UNKNOWN_NOT_ATTESTED"


@dataclass
class ActiveInferenceWorker:
    request_id: str
    attempt_id: str
    request_frame_id: str
    process: mp.Process
    events: mp.Queue
    last_sequence: int = 0


def _contract_version() -> common_pb2.ContractVersion:
    return common_pb2.ContractVersion(major=1, minor=2)


def _worker_main(request_bytes: bytes, events: mp.Queue) -> None:
    request = inference_pb2.InferenceRequest()
    request.ParseFromString(request_bytes)

    def emit_chunk(chunk: inference_pb2.InferenceChunk) -> None:
        events.put(("chunk", chunk.SerializeToString(deterministic=True)))

    def emit_terminal(terminal: inference_pb2.InferenceTerminal) -> None:
        events.put(("terminal", terminal.SerializeToString(deterministic=True)))

    try:
        execute_stream(request, emit_chunk=emit_chunk, emit_terminal=emit_terminal)
    except UnaryInferenceRejected as exc:
        failure = inference_pb2.InferenceError(
            contract_version=_contract_version(),
            request_id=request.request_id,
            attempt_id=request.attempt_id,
            code=exc.code,
            message=str(exc),
            retryable=exc.retryable,
        )
        events.put(("error", failure.SerializeToString(deterministic=True)))
    except BaseException as exc:  # worker boundary: report, never turn crash into success
        failure = inference_pb2.InferenceError(
            contract_version=_contract_version(),
            request_id=request.request_id,
            attempt_id=request.attempt_id,
            code=inference_pb2.INFERENCE_ERROR_CODE_INTERNAL,
            message=f"stream worker failed: {type(exc).__name__}: {exc}",
            retryable=False,
        )
        events.put(("error", failure.SerializeToString(deterministic=True)))
    finally:
        events.put(("worker_exit", b""))


def start_stream_worker(
    request: inference_pb2.InferenceRequest,
    *,
    request_frame_id: str,
    context: mp.context.BaseContext | None = None,
) -> ActiveInferenceWorker:
    ctx = context or mp.get_context("spawn")
    events: mp.Queue = ctx.Queue()
    process = ctx.Process(
        target=_worker_main,
        args=(request.SerializeToString(deterministic=True), events),
        name=f"clever-inference-{request.request_id[:32]}",
        daemon=False,
    )
    process.start()
    return ActiveInferenceWorker(
        request_id=request.request_id,
        attempt_id=request.attempt_id,
        request_frame_id=request_frame_id,
        process=process,
        events=events,
    )


def terminate_worker_bounded(
    worker: ActiveInferenceWorker,
    *,
    terminate_timeout: float = 0.35,
    kill_timeout: float = 0.35,
) -> LocalCancellationReceipt:
    if terminate_timeout <= 0 or kill_timeout <= 0:
        raise ValueError("cancellation timeouts must be positive")
    process = worker.process
    if not process.is_alive():
        process.join(timeout=0)
        return LocalCancellationReceipt(True, True, True, False)

    process.terminate()
    process.join(timeout=terminate_timeout)
    forced = False
    if process.is_alive():
        forced = True
        process.kill()
        process.join(timeout=kill_timeout)
    stopped = not process.is_alive()
    return LocalCancellationReceipt(True, stopped, stopped, forced)


def cancelled_terminal(worker: ActiveInferenceWorker) -> inference_pb2.InferenceTerminal:
    return inference_pb2.InferenceTerminal(
        contract_version=_contract_version(),
        request_id=worker.request_id,
        attempt_id=worker.attempt_id,
        final_sequence=worker.last_sequence,
        finish_reason=inference_pb2.INFERENCE_FINISH_REASON_CANCELLED,
        usage=inference_pb2.InferenceUsage(
            measurement=inference_pb2.INFERENCE_USAGE_MEASUREMENT_UNKNOWN
        ),
    )


def decode_worker_event(kind: str, payload: bytes):
    if kind == "chunk":
        message = inference_pb2.InferenceChunk()
    elif kind == "terminal":
        message = inference_pb2.InferenceTerminal()
    elif kind == "error":
        message = inference_pb2.InferenceError()
    else:
        return None
    message.ParseFromString(payload)
    return message


def poll_worker_event(worker: ActiveInferenceWorker, timeout: float = 0.0):
    try:
        return worker.events.get(timeout=timeout)
    except queue.Empty:
        return None


def stubborn_process_target() -> None:
    if os.name == "posix":
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
    while True:
        time.sleep(0.05)

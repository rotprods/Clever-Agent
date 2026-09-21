from __future__ import annotations

import multiprocessing as mp
import os
import time

import pytest

from adapters.openjarvis.cancellation import (
    ActiveInferenceWorker,
    cancelled_terminal,
    stubborn_process_target,
    terminate_worker_bounded,
)
from clever.v1 import inference_pb2


def _worker_for(process: mp.Process, *, request_id: str = "req", attempt_id: str = "attempt") -> ActiveInferenceWorker:
    return ActiveInferenceWorker(
        request_id=request_id,
        attempt_id=attempt_id,
        request_frame_id="frame-1",
        process=process,
        events=mp.get_context("spawn").Queue(),
    )


def test_cancelled_terminal_preserves_identity_and_local_sequence() -> None:
    ctx = mp.get_context("spawn")
    process = ctx.Process(target=time.sleep, args=(0.01,))
    process.start()
    process.join(timeout=1)
    worker = _worker_for(process, request_id="request-1", attempt_id="attempt-1")
    worker.last_sequence = 7
    terminal = cancelled_terminal(worker)
    assert terminal.request_id == "request-1"
    assert terminal.attempt_id == "attempt-1"
    assert terminal.final_sequence == 7
    assert terminal.finish_reason == inference_pb2.INFERENCE_FINISH_REASON_CANCELLED
    assert terminal.usage.measurement == inference_pb2.INFERENCE_USAGE_MEASUREMENT_UNKNOWN


def test_bounded_cancel_stops_cooperative_worker() -> None:
    ctx = mp.get_context("spawn")
    process = ctx.Process(target=time.sleep, args=(10,))
    process.start()
    receipt = terminate_worker_bounded(_worker_for(process), terminate_timeout=0.3, kill_timeout=0.3)
    assert receipt.requested
    assert receipt.acknowledged
    assert receipt.process_stopped
    assert not receipt.forced_kill
    assert receipt.remote_effect == "UNKNOWN_NOT_ATTESTED"
    assert not process.is_alive()


@pytest.mark.skipif(os.name != "posix", reason="SIGTERM-ignore adversarial is POSIX-specific")
def test_worker_ignoring_cancel_is_force_killed_without_remote_success_claim() -> None:
    ctx = mp.get_context("spawn")
    process = ctx.Process(target=stubborn_process_target)
    process.start()
    time.sleep(0.15)
    receipt = terminate_worker_bounded(_worker_for(process), terminate_timeout=0.15, kill_timeout=0.35)
    assert receipt.requested
    assert receipt.acknowledged
    assert receipt.process_stopped
    assert receipt.forced_kill
    assert receipt.remote_effect == "UNKNOWN_NOT_ATTESTED"
    assert not process.is_alive()


def test_invalid_cancellation_deadlines_are_rejected() -> None:
    ctx = mp.get_context("spawn")
    process = ctx.Process(target=time.sleep, args=(0.01,))
    process.start()
    process.join(timeout=1)
    worker = _worker_for(process)
    with pytest.raises(ValueError, match="positive"):
        terminate_worker_bounded(worker, terminate_timeout=0, kill_timeout=0.1)

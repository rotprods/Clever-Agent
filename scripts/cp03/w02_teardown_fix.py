from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TARGET = ROOT / "scripts/cp03/w02_teardown_port.py"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if new in text:
        return text
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected one source occurrence, found {count}")
    return text.replace(old, new, 1)


def remove_once(text: str, old: str, label: str) -> str:
    count = text.count(old)
    if count == 0:
        return text
    if count != 1:
        raise RuntimeError(f"{label}: expected zero or one source occurrence, found {count}")
    return text.replace(old, "", 1)


def main() -> int:
    text = TARGET.read_text(encoding="utf-8")
    text = replace_once(
        text,
        r'.args([\"-KILL\", target.as_str()])',
        r'.args([\"-KILL\", \"--\", target.as_str()])',
        "negative process-group operand",
    )
    text = remove_once(
        text,
        "    process::Command,\n",
        "Linux-unused Command import",
    )
    text = replace_once(
        text,
        '    Command::new("/bin/kill")\n',
        '    std::process::Command::new("/bin/kill")\n',
        "non-Linux process probe",
    )
    # The external cleanup hook intentionally runs with env_clear(). The lifecycle
    # fixture therefore must not import Clever/OpenJarvis protobuf dependencies for
    # cleanup-only modes. Import the wire helper lazily only for the supervised peer.
    text = remove_once(
        text,
        "import fake_adapter_sidecar as wire\n\n",
        "eager cleanup-fixture wire import",
    )
    text = replace_once(
        text,
        "def serve(mode: str) -> int:\n    handshake()",
        "def serve(mode: str) -> int:\n    global wire\n    import fake_adapter_sidecar as wire\n    handshake()",
        "lazy supervised-peer wire import",
    )
    text = replace_once(
        text,
        "use std::{env, fs, path::PathBuf, time::{Duration, Instant, SystemTime, UNIX_EPOCH}};",
        "use std::{env, fs, path::{Path, PathBuf}, time::{Duration, Instant, SystemTime, UNIX_EPOCH}};",
        "lifecycle Path import",
    )
    text = replace_once(
        text,
        "fn cleanup(mode: &str, marker: &PathBuf) -> AdapterCleanupCommand {",
        "fn cleanup(mode: &str, marker: &Path) -> AdapterCleanupCommand {",
        "lifecycle cleanup Path argument",
    )
    TARGET.write_text(text, encoding="utf-8")
    check = TARGET.read_text(encoding="utf-8")
    if r'.args([\"-KILL\", \"--\", target.as_str()])' not in check:
        raise RuntimeError("process-group kill fix did not persist")
    if "    process::Command,\n" in check:
        raise RuntimeError("stale unconditional Command import remains")
    if '    std::process::Command::new("/bin/kill")\n' not in check:
        raise RuntimeError("non-Linux process probe fix did not persist")
    if "import fake_adapter_sidecar as wire\n\n" in check:
        raise RuntimeError("cleanup fixture still eagerly imports adapter runtime")
    if "global wire\n    import fake_adapter_sidecar as wire\n    handshake()" not in check:
        raise RuntimeError("lazy supervised-peer import fix did not persist")
    if "fn cleanup(mode: &str, marker: &Path) -> AdapterCleanupCommand" not in check:
        raise RuntimeError("lifecycle cleanup Path fix did not persist")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

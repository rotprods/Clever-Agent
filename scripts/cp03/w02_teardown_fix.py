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


def main() -> int:
    text = TARGET.read_text(encoding="utf-8")
    text = replace_once(
        text,
        r'.args([\"-KILL\", target.as_str()])',
        r'.args([\"-KILL\", \"--\", target.as_str()])',
        "negative process-group operand",
    )
    text = replace_once(
        text,
        "    process::Command,\n",
        "",
        "Linux-unused Command import",
    )
    text = replace_once(
        text,
        r'    Command::new(\"/bin/kill\")\n',
        r'    std::process::Command::new(\"/bin/kill\")\n',
        "non-Linux process probe",
    )
    TARGET.write_text(text, encoding="utf-8")
    check = TARGET.read_text(encoding="utf-8")
    if r'.args([\"-KILL\", \"--\", target.as_str()])' not in check:
        raise RuntimeError("process-group kill fix did not persist")
    if "    process::Command,\n" in check:
        raise RuntimeError("stale unconditional Command import remains")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

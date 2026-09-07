"""Reproduce Git path-collapse bookkeeping and strengthen the existing limit test."""
from pathlib import Path
import subprocess
import tempfile

root = Path(__file__).resolve().parents[2]
p = root / 'kernel/crates/clever-kernel/tests/control_guards.rs'
s = p.read_text()
before = '''    let mut peer = connect("negotiated-limit");
    assert_eq!(peer.negotiated_max_frame_bytes(), 512);
    assert!(peer.request_health().is_err());'''
after = '''    for mode in ["negotiated-limit", "wire-padding"] {
        let mut peer = connect(mode);
        assert_eq!(peer.negotiated_max_frame_bytes(), 512);
        assert!(peer.request_health().is_err(), "accepted oversized wire mode {mode}");
    }'''
assert s.count(before) == 1
p.write_text(s.replace(before, after, 1))
with tempfile.TemporaryDirectory() as folder:
    folder = Path(folder)
    subprocess.run(['git', 'init', '-q', str(folder)], check=True)
    file = folder / 'evidence/new/result.json'
    file.parent.mkdir(parents=True)
    file.write_text('{}')
    collapsed = subprocess.check_output(['git', '-C', str(folder), 'status', '--porcelain', '-z']).decode()
    expanded = subprocess.check_output(['git', '-C', str(folder), 'status', '--porcelain', '-z', '-uall']).decode()
    assert collapsed == '?? evidence/\0'
    assert expanded == '?? evidence/new/result.json\0'
    print('PASS: scope regression reproduced; -uall exposes the exact file without widening allowlist')

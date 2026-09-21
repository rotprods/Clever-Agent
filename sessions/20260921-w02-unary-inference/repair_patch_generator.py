from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
path = ROOT / "scripts/cp03/w02_unary_patch.py"
text = path.read_text(encoding="utf-8")
old = "    LifecycleMode, NativeRegistryEntry, PlatformConstraint, PrincipalRef, ProvenanceRef,\\n"
new = "    LifecycleMode, NativeRegistryEntry, PlatformConstraint, ProvenanceRef,\\n"
if new not in text:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"expected one PrincipalRef generator anchor, found {count}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")
else:
    assert old not in text
print("W02-10 patch generator repair: PASS")

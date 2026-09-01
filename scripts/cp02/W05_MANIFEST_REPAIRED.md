# CP02 W05 manifest repair checkpoint

`contracts/generated_manifest.json` was regenerated on top of `8c31b28f441f8423c79102127fef035edbb6042b` after hardening `scripts/contracts/generated_manifest.py` to exclude transient runtime caches (`__pycache__`, `.pyc`, `.pyo`, cache directories and `.DS_Store`).

This marker intentionally triggers the authoritative W05 security/recovery gauntlet from a non-bot commit. It changes no contract, kernel or security semantics.

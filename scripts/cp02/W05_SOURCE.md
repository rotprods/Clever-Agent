# CP02 W05 authoritative source

The adversarial source introduced at `e89988013906b9defd0eaf1bafc1dbb318f9b4e2` was mechanically formatted by the pinned Rust toolchain into `1c2c3232e2354a96be1a0da98fa82fbab3c95400`.

This marker exists to trigger the authoritative W05 workflow from a non-`GITHUB_TOKEN` commit because GitHub intentionally does not recursively trigger workflows from bot-token pushes. No adversarial invariant is relaxed by this file.

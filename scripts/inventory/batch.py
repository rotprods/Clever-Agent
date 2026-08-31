from __future__ import annotations

import argparse
import json
from pathlib import Path

from scripts.inventory.scan_repository import scan_repository
from scripts.upstream.ledger import load_upstream_pins


def main() -> int:
    parser = argparse.ArgumentParser(description="Compile W02 structural inventories for all exact upstream pins")
    parser.add_argument("--ledger", default="UPSTREAM_LEDGER.yaml")
    parser.add_argument("--cache", default=".cache/upstreams")
    parser.add_argument("--output-dir", default="inventory/upstreams")
    parser.add_argument("--summary", default="reports/cp01/structural_inventory_summary.json")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, object]] = []
    for pin in load_upstream_pins(args.ledger):
        inventory = scan_repository(Path(args.cache) / pin.id, pin)
        output = output_dir / f"{pin.id}.json"
        output.write_text(json.dumps(inventory, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        rows.append(
            {
                "id": pin.id,
                "source_commit": pin.pinned_commit,
                "tree_entry_count": inventory["tree_entry_count"],
                "manifest_count": len(inventory["manifests"]),
                "package_workspace_root_count": len(inventory["package_workspace_roots"]),
                "runtime_boundary_count": len(inventory["runtime_service_app_boundaries"]),
                "test_file_count": len(inventory["test_files"]),
                "ci_release_file_count": len(inventory["ci_release_files"]),
                "doc_file_count": len(inventory["doc_files"]),
                "license_notice_file_count": len(inventory["license_notice_files"]),
                "languages": inventory["summary"]["languages"],
                "tree_sha256": inventory["tree_sha256"],
            }
        )
        print(f"inventory: {pin.id}: {inventory['tree_entry_count']} entries")

    summary = {
        "schema_version": 1,
        "inventory_type": "cp01_structural_inventory_summary",
        "sources": sorted(rows, key=lambda row: str(row["id"])),
    }
    summary_path = Path(args.summary)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

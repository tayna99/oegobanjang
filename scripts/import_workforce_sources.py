#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT_DIR / "backend"
DEFAULT_MANIFEST = ROOT_DIR / "data-pipeline" / "source_manifests" / "workforce_official_sources.json"
DEFAULT_OUTPUT_DIR = ROOT_DIR / "data-pipeline" / "raw" / "workforce_official"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.agent_runtime.rag.workforce_source_importer import import_workforce_sources


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch official workforce source URLs into raw JSONL records.")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument(
        "--enable-fetch",
        action="store_true",
        help="Fetch official URLs. This is the default for the CLI and is kept for explicit runbooks.",
    )
    parser.add_argument(
        "--no-fetch",
        action="store_true",
        help="Do not use network; only report that configured sources would be skipped.",
    )
    parser.add_argument("--timeout-seconds", type=int, default=20)
    parser.add_argument("--max-bytes", type=int, default=5_000_000)
    args = parser.parse_args()

    report = import_workforce_sources(
        manifest_path=args.manifest,
        output_dir=args.output_dir,
        fetch_enabled=not args.no_fetch,
        timeout_seconds=args.timeout_seconds,
        max_bytes=args.max_bytes,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

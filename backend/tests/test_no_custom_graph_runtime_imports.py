from __future__ import annotations

from pathlib import Path


PRODUCTION_PATHS = [
    "backend/app/api",
    "backend/app/agent_runtime/agents",
    "backend/app/agent_runtime/langchain_v1",
    "backend/app/agent_runtime/runner.py",
]


def test_production_runtime_does_not_import_custom_graph() -> None:
    root = Path(__file__).resolve().parents[2]
    offenders: list[str] = []

    for relative in PRODUCTION_PATHS:
        path = root / relative
        files = [path] if path.is_file() else list(path.rglob("*.py"))
        for file_path in files:
            source = file_path.read_text(encoding="utf-8")
            if "app.agent_runtime.graph" in source or "agent_runtime.graph" in source:
                offenders.append(str(file_path.relative_to(root)))

    assert offenders == []

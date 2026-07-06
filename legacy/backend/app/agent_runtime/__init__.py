from __future__ import annotations

__all__ = ["run_workflow"]


def __getattr__(name: str):
    if name == "run_workflow":
        from .runner import run_workflow

        return run_workflow
    raise AttributeError(name)

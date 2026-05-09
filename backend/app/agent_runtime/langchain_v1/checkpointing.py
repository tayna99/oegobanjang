from __future__ import annotations

import sqlite3
import aiosqlite
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.config import get_settings

from .tools import RuntimePreflightError


def runtime_checkpoint_config(*, thread_id: str) -> dict[str, dict[str, str]]:
    settings = get_settings()
    return {
        "configurable": {
            "thread_id": thread_id,
            "checkpoint_ns": settings.langchain_checkpoint_namespace,
        }
    }


@lru_cache(maxsize=1)
def get_langchain_checkpointer() -> Any | None:
    settings = get_settings()
    if not settings.langchain_checkpoint_enabled:
        return None

    try:
        from langgraph.checkpoint.sqlite import SqliteSaver
    except ImportError as exc:  # pragma: no cover - covered via preflight tests.
        raise RuntimePreflightError(
            "langgraph-checkpoint-sqlite is required for durable checkpointing"
        ) from exc

    checkpoint_path = Path(settings.normalized_langchain_checkpoint_path)
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(checkpoint_path, check_same_thread=False)
    saver = SqliteSaver(conn)
    setup = getattr(saver, "setup", None)
    if callable(setup):
        setup()
    return saver


def clear_checkpointer_cache() -> None:
    get_langchain_checkpointer.cache_clear()
    global _ASYNC_CHECKPOINTER
    _ASYNC_CHECKPOINTER = None


_ASYNC_CHECKPOINTER: Any | None = None


async def get_async_langchain_checkpointer() -> Any | None:
    global _ASYNC_CHECKPOINTER
    settings = get_settings()
    if not settings.langchain_checkpoint_enabled:
        return None
    if _ASYNC_CHECKPOINTER is not None:
        return _ASYNC_CHECKPOINTER

    try:
        from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
    except ImportError as exc:  # pragma: no cover - dependency preflight.
        raise RuntimePreflightError(
            "langgraph-checkpoint-sqlite is required for durable checkpointing"
        ) from exc

    checkpoint_path = Path(settings.normalized_langchain_checkpoint_path)
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    conn = await aiosqlite.connect(checkpoint_path)
    saver = AsyncSqliteSaver(conn)
    await saver.setup()
    _ASYNC_CHECKPOINTER = saver
    return saver

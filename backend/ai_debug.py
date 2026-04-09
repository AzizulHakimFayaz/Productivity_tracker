from __future__ import annotations

import datetime
import threading
from collections import deque


_LOCK = threading.Lock()
_LOGS = deque(maxlen=1200)
_MODEL_STATUS = "initializing"


def set_model_status(status: str) -> None:
    global _MODEL_STATUS
    with _LOCK:
        _MODEL_STATUS = str(status or "unknown")


def get_model_status() -> str:
    with _LOCK:
        return _MODEL_STATUS


def ai_debug_log(source: str, message: str) -> None:
    ts = datetime.datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] [{source}] {message}"
    with _LOCK:
        _LOGS.append(line)


def get_ai_debug_logs(limit: int = 300) -> list[str]:
    lim = max(1, int(limit))
    with _LOCK:
        return list(_LOGS)[-lim:]


def clear_ai_debug_logs() -> None:
    with _LOCK:
        _LOGS.clear()

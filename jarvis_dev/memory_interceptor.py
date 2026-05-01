"""
Jarvis Memory Interceptor
Saves and loads conversation history to/from memory/memory.json
Works alongside the existing jarvis_memory.py infrastructure.
"""

import json
import os
from datetime import datetime

MEMORY_DIR  = os.path.join(os.path.dirname(os.path.abspath(__file__)), "memory")
MEMORY_FILE = os.path.join(MEMORY_DIR, "memory.json")
DEBUG_LOG   = os.path.join(MEMORY_DIR, "memory_debug.log")
MAX_HISTORY = 50


def _ensure_dir():
    os.makedirs(MEMORY_DIR, exist_ok=True)


def _log(msg: str):
    _ensure_dir()
    with open(DEBUG_LOG, "a", encoding="utf-8") as f:
        f.write(f"[{datetime.now().isoformat()}] {msg}\n")


def load_memory() -> list[dict]:
    if not os.path.exists(MEMORY_FILE):
        return []
    try:
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except Exception as e:
        _log(f"load_memory error: {e}")
        return []


def save_memory(history: list[dict]):
    _ensure_dir()
    try:
        with open(MEMORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history[-MAX_HISTORY:], f, indent=2, ensure_ascii=False)
    except OSError as e:
        _log(f"save_memory error: {e}")


def record_exchange(user: str, assistant: str):
    history = load_memory()
    history.append({
        "timestamp": datetime.now().isoformat(),
        "user":      user,
        "assistant": assistant,
    })
    save_memory(history)


def get_recent(n: int = 5) -> list[dict]:
    return load_memory()[-n:]


def clear_memory():
    save_memory([])
    _log("clear_memory: history wiped")


if __name__ == "__main__":
    print("=== Memory Interceptor Self-Test ===")
    clear_memory()
    record_exchange("What is a linked list?", "A linked list is a linear data structure...")
    record_exchange("Show me C reversal.", "```c\nNode* reverse(Node* head){...}\n```")
    history = get_recent(2)
    print(f"✅  {len(history)} exchanges stored in {MEMORY_FILE}")
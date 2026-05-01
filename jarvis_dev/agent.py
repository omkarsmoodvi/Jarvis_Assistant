import re

try:
    from brain.local_llm import LocalLLM
except ModuleNotFoundError:
    from local_llm import LocalLLM

# 🔥 IMPROVED BASE PROMPT
_BASE = """You are Jarvis, a highly accurate AI assistant.

RULES:
- Think step by step internally before answering
- Prioritize correctness over brevity
- If unsure, say "I am not fully confident"
- Do NOT hallucinate
- Give complete and correct answers"""

_CHAT = """Give a natural and helpful reply."""

_GENERAL = """Give a correct and complete answer. Be concise but accurate."""

_EXPLAIN = """Explain clearly in bullet points. Ensure correctness."""

_DEBUG = """Return fully corrected working code inside a single code block."""

_CODEGEN = """Generate correct, complete, working code inside a code block."""

_DSA = """Give correct algorithm code + 3 bullet points for time/space complexity."""

_MODES: dict[str, dict] = {
    "chat":    {"prompt": _CHAT,    "max_tokens": 4096, "temp": 0.5},
    "general": {"prompt": _GENERAL, "max_tokens": 4096, "temp": 0.3},
    "explain": {"prompt": _EXPLAIN, "max_tokens": 4096, "temp": 0.2},
    "debug":   {"prompt": _DEBUG,   "max_tokens": 8192, "temp": 0.1},
    "codegen": {"prompt": _CODEGEN, "max_tokens": 8192, "temp": 0.2},
    "dsa":     {"prompt": _DSA,     "max_tokens": 8192, "temp": 0.2},
}

_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"^\s*(hi|hello|hey)\b", re.I), "chat"),
    (re.compile(r"(fix|debug|error|bug|issue)", re.I), "debug"),
    (re.compile(r"(write|create|build|code)", re.I), "codegen"),
    (re.compile(r"(explain|what is|how)", re.I), "explain"),
]

_DEFAULT = "general"

_CODE_SIGNAL = re.compile(
    r"(#include\s*<|import\s+\w|def\s+\w+\s*\(|class\s+\w+)", re.M
)

def detect_intent(text: str) -> str:
    if "```" in text or _CODE_SIGNAL.search(text):
        return "debug"
    for pattern, mode in _PATTERNS:
        if pattern.search(text):
            return mode
    return _DEFAULT

def build_prompt(user_input: str, mode: str):
    cfg = _MODES[mode]
    system_text = f"{_BASE}\n\n{cfg['prompt']}\n\nThink carefully before answering."
    return system_text, user_input

def is_bad_response(text: str) -> bool:
    if not text:
        return True
    if len(text.strip()) < 5:
        return True
    if "I don't know" in text:
        return False
    return False

class Agent:
    def __init__(self):
        self.brain = LocalLLM()
        self._history = []

    def run(self, user_input: str, callback=None, **kwargs) -> str:
        user_input = user_input.strip()
        mode = detect_intent(user_input)
        cfg = _MODES[mode]

        # 🔥 Better routing logic
        is_heavy = mode in ["explain", "dsa"] or len(user_input.split()) > 25

        if is_heavy:
            self.brain.switch_model("heavy")
        else:
            self.brain.switch_model("fast")

        system_prompt, user_message = build_prompt(user_input, mode)

        response = self.brain.generate(
            system_prompt=system_prompt,
            user_message=user_message,
            callback=callback,
            max_tokens=cfg["max_tokens"],
            temp=cfg["temp"],
        )

        # 🔥 RETRY IF BAD
        if is_bad_response(response):
            response = self.brain.generate(
                system_prompt + "\nDouble check your answer and correct it.",
                user_message,
                max_tokens=cfg["max_tokens"],
                temp=0.2,
            )

        self._history.append({"user": user_input, "assistant": response})
        return response

    def clear_history(self):
        self._history.clear()
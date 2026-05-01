"""
jarvis_gui.py
J.A.R.V.I.S — AI Chatbot GUI  (PySide6)
Launched by nova_full_jarvis.py  →  "💬 AI Chatbot" button
Also runnable standalone:  python jarvis_gui.py

Everything is in this single file — no jarvis_chatbot_gui.py needed.
Voice: en-US-AriaNeural  (edge-tts + pygame)
Model: Meta-Llama-3-8B-Instruct.Q4_K_M.gguf  (100% offline, GPT4All)
"""

import sys
import os
import re
import math
import threading
import asyncio
import tempfile
from datetime import datetime

# ---------------------------------------------------------------------------
# Path setup — makes agent.py importable when launched from any working dir
# ---------------------------------------------------------------------------
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
if _THIS_DIR not in sys.path:
    sys.path.insert(0, _THIS_DIR)

from PySide6.QtCore import (
    Qt, QTimer, QRectF, QPointF, QThread, QObject, Signal
)
from PySide6.QtGui import (
    QPainter, QColor, QPen, QFont, QRadialGradient,
    QBrush, QFontInfo, QTextCursor
)
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTextEdit, QPushButton, QLabel, QFrame, QSizePolicy, QScrollArea
)

# ---------------------------------------------------------------------------
# Jarvis Agent
# ---------------------------------------------------------------------------
try:
    from agent import Agent
    _AGENT_OK = True
except ImportError as _err:
    _AGENT_OK   = False
    _AGENT_ERR  = str(_err)

# ---------------------------------------------------------------------------
# Memory (optional — degrades gracefully if missing)
# ---------------------------------------------------------------------------
try:
    from memory_interceptor import record_exchange, get_recent, clear_memory as _clear_mem
    _MEM_OK = True
except ImportError:
    _MEM_OK = False
    def record_exchange(u, a): pass
    def get_recent(n=5): return []
    def _clear_mem(): pass

# ---------------------------------------------------------------------------
# Voice — en-US-AriaNeural
# ---------------------------------------------------------------------------
ARIA_VOICE  = "en-US-AriaNeural"
ARIA_RATE   = "+0%"
ARIA_PITCH  = "+0Hz"
ARIA_VOLUME = "+0%"
_voice_ready = False

try:
    import edge_tts
    import pygame
    pygame.mixer.init()
    _voice_ready = True
except Exception:
    pass


def _clean_for_speech(text: str) -> str:
    first = True
    def _replace_block(m):
        nonlocal first
        if first:
            first = False
            return ". The corrected code is shown above on your screen. "
        return ". "
    text = re.sub(r"```[\s\S]*?```", _replace_block, text)
    text = re.sub(r"`[^`\n]+`",     "",              text)
    text = re.sub(r"[*_#]",         "",              text)
    text = re.sub(r"<\|[^|]*?\|>",  "",              text)
    text = re.sub(r"\n+",           ". ",            text)
    return re.sub(r"\s{2,}", " ", text).strip()


async def _synth(text: str, path: str):
    await edge_tts.Communicate(
        text, voice=ARIA_VOICE, rate=ARIA_RATE, pitch=ARIA_PITCH
    ).save(path)


def speak_aria(text: str):
    if not _voice_ready:
        return
    spoken = _clean_for_speech(text)
    if not spoken:
        return

    def _run():
        tmp  = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
        path = tmp.name
        tmp.close()
        try:
            asyncio.run(_synth(spoken, path))
            pygame.mixer.music.load(path)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                pygame.time.Clock().tick(10)
        except Exception:
            pass
        finally:
            try:
                pygame.mixer.music.unload()
                os.remove(path)
            except Exception:
                pass

    threading.Thread(target=_run, daemon=True).start()


# ---------------------------------------------------------------------------
# Palette — matches nova_full_jarvis.py exactly
# ---------------------------------------------------------------------------
C_BG      = QColor(5,  12,  20)
C_CARD    = QColor(10, 14,  20, 220)
C_ACCENT  = QColor(60, 200, 255)
C_BORDER  = QColor(60, 200, 255, 40)
C_TEXT    = QColor(220, 236, 251)
C_MUTED   = QColor(120, 150, 180)
C_USER_BG = QColor(20,  45,  70, 200)
C_BOT_BG  = QColor(10,  22,  36, 200)
C_WARN    = QColor(255, 110, 90)
C_GREEN   = QColor(80,  220, 120)
C_YELLOW  = QColor(250, 204, 21)

_ORBITRON = "Orbitron" if QFontInfo(QFont("Orbitron")).family().lower() == "orbitron" else "Segoe UI"
F_UI   = "Segoe UI"
F_CODE = "Consolas"
F_HEAD = _ORBITRON


# ===========================================================================
# Worker — runs Agent in a QThread, streams tokens via Signal
# ===========================================================================
class AgentWorker(QObject):
    token_received = Signal(str)
    response_done  = Signal(str)
    error_occurred = Signal(str)

    def __init__(self, agent, user_input: str):
        super().__init__()
        self._agent = agent
        self._input = user_input

    def run(self):
        try:
            response = self._agent.run(
                self._input,
                callback=lambda tok: self.token_received.emit(tok)
            )
            self.response_done.emit(response)
        except Exception as e:
            self.error_occurred.emit(str(e))


# ===========================================================================
# Mini animated ring  (smaller version of nova_full_jarvis EnergyCore)
# ===========================================================================
class MiniCore(QWidget):
    def __init__(self):
        super().__init__()
        self.phase  = 0.0
        self.active = False
        self.setFixedSize(72, 72)

    def set_active(self, v: bool):
        self.active = v

    def step(self):
        self.phase = (self.phase + (0.28 if self.active else 0.08)) % (math.pi * 2)
        self.update()

    def paintEvent(self, event):
        p  = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        cx, cy = self.width() / 2, self.height() / 2
        br = 24.0

        glow = QRadialGradient(QPointF(cx, cy), br * 2)
        a    = 160 if self.active else 60
        glow.setColorAt(0.0, QColor(60, 200, 255, a))
        glow.setColorAt(1.0, QColor(0,  0,   0,   0))
        p.setBrush(QBrush(glow))
        p.setPen(Qt.NoPen)
        p.drawEllipse(QPointF(cx, cy), br * 2, br * 2)

        t = self.phase / (math.pi * 2)
        for i in range(3 if self.active else 2):
            prog  = (t + i / 3) % 1.0
            r     = br + prog * br * 1.4
            alpha = int(220 * (1.0 - prog))
            pen   = QPen(QColor(60, 200, 255, alpha), 2.0 - prog)
            pen.setCapStyle(Qt.RoundCap)
            p.setPen(pen)
            span  = int(150 * 16 + math.sin(self.phase + i) * 20 * 16)
            start = int((t * 360 + i * 45) * 16)
            p.drawArc(QRectF(cx - r, cy - r, r * 2, r * 2), -start, -span)

        dot = C_ACCENT if self.active else C_MUTED
        p.setBrush(QBrush(dot))
        p.setPen(Qt.NoPen)
        p.drawEllipse(QPointF(cx, cy), 4, 4)


# ===========================================================================
# Animated grid background
# ===========================================================================
class ChatBackground(QWidget):
    def __init__(self):
        super().__init__()
        self.offset = 0.0
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        t = QTimer(self)
        t.timeout.connect(self._step)
        t.start(33)

    def _step(self):
        self.offset = (self.offset + 0.5) % 40
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.fillRect(self.rect(), C_BG)
        p.setPen(QPen(QColor(60, 200, 255, 14), 0.5))
        s, ofs = 40, int(self.offset) % 40
        w, h   = self.width(), self.height()
        for x in range(-s, w + s, s): p.drawLine(x + ofs, 0, x + ofs, h)
        for y in range(-s, h + s, s): p.drawLine(0, y + ofs, w, y + ofs)


# ===========================================================================
# Message bubble
# ===========================================================================
class MessageBubble(QFrame):
    def __init__(self, role: str, text: str = "", parent=None):
        super().__init__(parent)
        self.role = role

        outer = QHBoxLayout(self)
        outer.setContentsMargins(8, 4, 8, 4)
        outer.setSpacing(10)

        badge = QLabel("YOU" if role == "user" else "AI")
        badge.setFixedWidth(34)
        badge.setAlignment(Qt.AlignTop | Qt.AlignHCenter)
        badge.setStyleSheet(
            f"color: {'#3CC8FF' if role == 'user' else '#50DC78'};"
            f"font-family: {F_CODE}; font-size: 9px; font-weight: bold;"
            f"padding-top: 6px; letter-spacing: 1px;"
        )
        outer.addWidget(badge)

        bg = C_USER_BG if role == "user" else C_BOT_BG
        self.body = QTextEdit()
        self.body.setReadOnly(True)
        self.body.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.body.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.body.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.body.document().contentsChanged.connect(self._adjust)
        self.body.setStyleSheet(f"""
            QTextEdit {{
                background: rgba({bg.red()},{bg.green()},{bg.blue()},{bg.alpha()});
                border: 1px solid rgba(60,200,255,25);
                border-radius: 8px;
                color: #DCECFB;
                font-family: {F_CODE};
                font-size: 12px;
                padding: 8px;
            }}
            QScrollBar {{ width:0; height:0; }}
        """)
        outer.addWidget(self.body, 1)

        if text:
            self.body.setPlainText(text)

    def append_token(self, token: str):
        c = self.body.textCursor()
        c.movePosition(QTextCursor.End)
        c.insertText(token)
        self.body.setTextCursor(c)
        self.body.ensureCursorVisible()

    def _adjust(self):
        h = int(self.body.document().size().height()) + 20
        self.body.setFixedHeight(max(40, h))


# ===========================================================================
# Scrollable chat area
# ===========================================================================
class ChatArea(QScrollArea):
    def __init__(self):
        super().__init__()
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setStyleSheet("""
            QScrollArea { border: none; background: transparent; }
            QScrollBar:vertical {
                background: rgba(10,20,30,100); width: 6px; border-radius: 3px;
            }
            QScrollBar::handle:vertical {
                background: rgba(60,200,255,80); border-radius: 3px; min-height: 20px;
            }
        """)
        self._container = QWidget()
        self._container.setStyleSheet("background: transparent;")
        self._layout    = QVBoxLayout(self._container)
        self._layout.setContentsMargins(4, 8, 4, 8)
        self._layout.setSpacing(6)
        self._layout.addStretch(1)
        self.setWidget(self._container)

    def add_bubble(self, bubble):
        self._layout.insertWidget(self._layout.count() - 1, bubble)
        QTimer.singleShot(30, self._bottom)

    def add_widget(self, w):
        self._layout.insertWidget(self._layout.count() - 1, w)
        QTimer.singleShot(30, self._bottom)

    def _bottom(self):
        sb = self.verticalScrollBar()
        sb.setValue(sb.maximum())

    def clear_bubbles(self):
        while self._layout.count() > 1:
            item = self._layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()


# ===========================================================================
# Input bar
# ===========================================================================
class InputBar(QFrame):
    submit_text = Signal(str)

    def __init__(self):
        super().__init__()
        self._code_mode = False
        self.setStyleSheet("""
            QFrame {
                background: rgba(8,14,22,230);
                border-top: 1px solid rgba(60,200,255,35);
            }
        """)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 8, 12, 8)
        lay.setSpacing(8)

        # Code mode toggle
        self.code_btn = QPushButton("{ }")
        self.code_btn.setFixedSize(36, 36)
        self.code_btn.setToolTip("Toggle code paste mode")
        self.code_btn.setCheckable(True)
        self.code_btn.clicked.connect(self._toggle_code)
        self.code_btn.setStyleSheet(self._btn_inactive())

        # Text input
        self.input = QTextEdit()
        self.input.setFixedHeight(36)
        self.input.setPlaceholderText(
            "Ask Jarvis anything…  (Shift+Enter = newline,  Enter = send,  { } = code mode)"
        )
        self.input.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.input.setStyleSheet(f"""
            QTextEdit {{
                background: rgba(16,26,38,200);
                border: 1px solid rgba(60,200,255,50);
                border-radius: 8px;
                color: #DCECFB;
                font-family: {F_CODE};
                font-size: 12px;
                padding: 6px 10px;
            }}
            QTextEdit:focus {{ border-color: rgba(60,200,255,150); }}
        """)
        self.input.installEventFilter(self)

        # Send button
        self.send_btn = QPushButton("SEND  ▶")
        self.send_btn.setFixedHeight(36)
        self.send_btn.clicked.connect(self._on_send)
        self.send_btn.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 rgba(20,80,120,220), stop:1 rgba(40,160,200,220));
                border: 1px solid rgba(60,200,255,140);
                border-radius: 8px;
                color: #EAF6FF;
                font-family: {F_UI}; font-size: 11px; font-weight: bold;
                padding: 0 18px;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 rgba(40,120,180,240), stop:1 rgba(60,200,255,240));
            }}
            QPushButton:pressed {{ background: rgba(60,200,255,200); color: #0a0e14; }}
            QPushButton:disabled {{
                background: rgba(20,30,40,100);
                color: rgba(100,130,160,80);
                border-color: rgba(60,80,100,60);
            }}
        """)

        lay.addWidget(self.code_btn)
        lay.addWidget(self.input, 1)
        lay.addWidget(self.send_btn)

    # -- helpers --
    def _btn_inactive(self):
        return (f"QPushButton {{ background: rgba(20,40,60,180); border: 1px solid rgba(60,200,255,60);"
                f"border-radius:6px; color:#6090B0; font-family:{F_CODE}; font-size:11px; font-weight:bold; }}"
                f"QPushButton:hover {{ border-color:rgba(60,200,255,150); color:#DCECFB; }}")

    def _btn_active(self):
        return (f"QPushButton {{ background: rgba(60,200,255,180); border: 1px solid #3CC8FF;"
                f"border-radius:6px; color:#0a0e14; font-family:{F_CODE}; font-size:11px; font-weight:bold; }}")

    def _toggle_code(self, checked: bool):
        self._code_mode = checked
        self.code_btn.setStyleSheet(self._btn_active() if checked else self._btn_inactive())
        if checked:
            self.input.setFixedHeight(120)
            self.input.setPlaceholderText("Paste your code here, then click SEND…")
        else:
            self.input.setFixedHeight(36)
            self.input.setPlaceholderText(
                "Ask Jarvis anything…  (Shift+Enter = newline,  Enter = send,  { } = code mode)"
            )

    def eventFilter(self, obj, event):
        from PySide6.QtCore import QEvent
        if (obj is self.input
                and event.type() == QEvent.KeyPress
                and event.key() in (Qt.Key_Return, Qt.Key_Enter)
                and not (event.modifiers() & Qt.ShiftModifier)
                and not self._code_mode):
            self._on_send()
            return True
        return super().eventFilter(obj, event)

    def _on_send(self):
        text = self.input.toPlainText().strip()
        if not text:
            return
        self.input.clear()
        if self._code_mode:
            self._toggle_code(False)
            self.code_btn.setChecked(False)
        self.submit_text.emit(text)

    def set_enabled(self, v: bool):
        self.input.setEnabled(v)
        self.send_btn.setEnabled(v)
        self.code_btn.setEnabled(v)


# ===========================================================================
# Title bar
# ===========================================================================
class TitleBar(QFrame):
    def __init__(self, on_voice, on_clear, on_close):
        super().__init__()
        self.setFixedHeight(48)
        self.setStyleSheet("""
            QFrame { background: rgba(6,10,16,240);
                     border-bottom: 1px solid rgba(60,200,255,30); }
        """)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(14, 0, 10, 0)

        title = QLabel("J.A.R.V.I.S  —  AI ASSISTANT")
        title.setStyleSheet(
            f"color:#3CC8FF; font-family:{F_HEAD}; font-size:13px;"
            f"font-weight:bold; letter-spacing:1px;"
        )
        lay.addWidget(title)
        lay.addStretch()

        self.status = QLabel("● LOADING")
        self.status.setStyleSheet(f"color:#506070; font-family:{F_CODE}; font-size:10px;")
        lay.addWidget(self.status)
        lay.addSpacing(12)

        for tip, ch, cb in [
            ("Toggle Aria Voice", "🔊", on_voice),
            ("Clear Chat",        "🗑",  on_clear),
            ("Close",             "✕",   on_close),
        ]:
            btn = QPushButton(ch)
            btn.setToolTip(tip)
            btn.setFixedSize(32, 28)
            btn.clicked.connect(cb)
            btn.setStyleSheet("""
                QPushButton { background:rgba(60,120,180,14); border:none;
                    border-radius:5px; color:#A0C0E0; font-size:13px; }
                QPushButton:hover { background:rgba(60,200,255,30); color:#EAF6FF; }
                QPushButton:pressed { background:rgba(60,200,255,80); }
            """)
            lay.addWidget(btn)

    def set_status(self, text: str, color: str):
        self.status.setText(text)
        self.status.setStyleSheet(
            f"color:{color}; font-family:{F_CODE}; font-size:10px;"
        )


# ===========================================================================
# Main Window
# ===========================================================================
class JarvisGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("J.A.R.V.I.S — AI Assistant")
        self.resize(880, 700)
        self.setMinimumSize(620, 480)

        self._agent      = None
        self._voice_on   = _voice_ready
        self._generating = False
        self._bot_bubble = None
        self._worker     = None
        self._thread     = None

        self._build_ui()
        self._anim_timer = QTimer(self)
        self._anim_timer.timeout.connect(self.mini_core.step)
        self._anim_timer.start(16)

        self._load_agent()

    # -----------------------------------------------------------------------
    # UI construction
    # -----------------------------------------------------------------------
    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)

        self.bg = ChatBackground()
        self.bg.setParent(central)
        self.bg.lower()

        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.title_bar = TitleBar(self._toggle_voice, self._clear_chat, self.close)
        root.addWidget(self.title_bar)

        # Body
        body = QFrame()
        body.setStyleSheet("background:transparent;")
        body_lay = QHBoxLayout(body)
        body_lay.setContentsMargins(0, 0, 0, 0)
        body_lay.setSpacing(0)

        # Left strip
        left = QFrame()
        left.setFixedWidth(90)
        left.setStyleSheet(
            "background:rgba(6,10,16,180);"
            "border-right:1px solid rgba(60,200,255,20);"
        )
        ll = QVBoxLayout(left)
        ll.setContentsMargins(8, 16, 8, 16)
        ll.setAlignment(Qt.AlignTop | Qt.AlignHCenter)

        self.mini_core = MiniCore()
        ll.addWidget(self.mini_core, 0, Qt.AlignHCenter)
        ll.addSpacing(10)

        self.model_lbl = QLabel("LLAMA\n3  8B")
        self.model_lbl.setAlignment(Qt.AlignCenter)
        self.model_lbl.setStyleSheet(
            f"color:#3CC8FF; font-family:{F_CODE}; font-size:9px;"
            f"font-weight:bold; letter-spacing:1px;"
        )
        ll.addWidget(self.model_lbl)
        ll.addSpacing(8)

        self.gpu_lbl = QLabel("GPU\nONLINE")
        self.gpu_lbl.setAlignment(Qt.AlignCenter)
        self.gpu_lbl.setStyleSheet(
            f"color:#50DC78; font-family:{F_CODE}; font-size:9px; letter-spacing:1px;"
        )
        ll.addWidget(self.gpu_lbl)
        ll.addStretch()

        self.voice_lbl = QLabel("🔊 ARIA" if self._voice_on else "🔇 MUTE")
        self.voice_lbl.setAlignment(Qt.AlignCenter)
        self.voice_lbl.setStyleSheet(
            f"color:{'#3CC8FF' if self._voice_on else '#506070'};"
            f"font-family:{F_CODE}; font-size:8px; letter-spacing:1px;"
        )
        ll.addWidget(self.voice_lbl)

        body_lay.addWidget(left)

        # Right — chat + input
        right = QFrame()
        right.setStyleSheet("background:transparent;")
        rl = QVBoxLayout(right)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(0)

        self.chat_area = ChatArea()
        rl.addWidget(self.chat_area, 1)

        self.input_bar = InputBar()
        self.input_bar.submit_text.connect(self._on_submit)
        rl.addWidget(self.input_bar)

        body_lay.addWidget(right, 1)
        root.addWidget(body, 1)

        self._sys_msg("Loading model… please wait.")

    # -----------------------------------------------------------------------
    # Agent loading
    # -----------------------------------------------------------------------
    def _load_agent(self):
        if not _AGENT_OK:
            self.title_bar.set_status("● ERROR", "#FF6E5A")
            self._sys_msg(f"Cannot import Agent: {_AGENT_ERR}")
            return

        def _load():
            try:
                a = Agent()
                self._agent = a
                QTimer.singleShot(0, self._on_ready)
            except Exception as e:
                self._load_err = str(e)
                QTimer.singleShot(0, self._on_load_err)

        threading.Thread(target=_load, daemon=True).start()

    def _on_ready(self):
        self.title_bar.set_status("● ONLINE", "#50DC78")
        self._sys_msg("System online. How can I help you today, Omkar?")
        self.input_bar.set_enabled(True)
        recent = get_recent(3)
        if recent:
            self._sys_msg(f"{len(recent)} recent exchanges loaded from memory.")

    def _on_load_err(self):
        err = getattr(self, "_load_err", "unknown")
        self.title_bar.set_status("● ERROR", "#FF6E5A")
        self._sys_msg(f"Model load failed: {err}")
        self.gpu_lbl.setText("LOAD\nFAILED")
        self.gpu_lbl.setStyleSheet(
            f"color:#FF6E5A; font-family:{F_CODE}; font-size:9px; letter-spacing:1px;"
        )

    # -----------------------------------------------------------------------
    # Message flow
    # -----------------------------------------------------------------------
    def _on_submit(self, text: str):
        if self._generating or not self._agent:
            return

        self.chat_area.add_bubble(MessageBubble("user", text))

        self._bot_bubble = MessageBubble("bot", "")
        self.chat_area.add_bubble(self._bot_bubble)

        self._set_generating(True)

        self._thread = QThread()
        self._worker = AgentWorker(self._agent, text)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.token_received.connect(self._on_token)
        self._worker.response_done.connect(self._on_done)
        self._worker.error_occurred.connect(self._on_error)
        self._thread.start()

    def _on_token(self, token: str):
        if self._bot_bubble:
            self._bot_bubble.append_token(token)
            self.chat_area._bottom()

    def _on_done(self, response: str):
        self._set_generating(False)
        self._cleanup_thread()
        record_exchange(
            self._bot_bubble.body.toPlainText() if self._bot_bubble else "",
            response
        )
        if self._voice_on:
            speak_aria(response)

    def _on_error(self, error: str):
        if self._bot_bubble:
            self._bot_bubble.body.setPlainText(f"[ERROR] {error}")
        self._set_generating(False)
        self._cleanup_thread()

    def _cleanup_thread(self):
        if self._thread:
            self._thread.quit()
            self._thread.wait()
            self._thread = None
            self._worker = None

    def _set_generating(self, v: bool):
        self._generating = v
        self.mini_core.set_active(v)
        self.input_bar.set_enabled(not v)
        self.title_bar.set_status(
            "● THINKING…" if v else "● ONLINE",
            "#FACC15"     if v else "#50DC78"
        )

    # -----------------------------------------------------------------------
    # Helpers
    # -----------------------------------------------------------------------
    def _sys_msg(self, text: str):
        lbl = QLabel(f"[{datetime.now().strftime('%H:%M:%S')}]  {text}")
        lbl.setStyleSheet(
            f"color:#506070; font-family:{F_CODE}; font-size:10px; padding:4px 16px;"
        )
        self.chat_area.add_widget(lbl)

    def _toggle_voice(self):
        self._voice_on = not self._voice_on
        self.voice_lbl.setText("🔊 ARIA" if self._voice_on else "🔇 MUTE")
        self.voice_lbl.setStyleSheet(
            f"color:{'#3CC8FF' if self._voice_on else '#506070'};"
            f"font-family:{F_CODE}; font-size:8px; letter-spacing:1px;"
        )

    def _clear_chat(self):
        self.chat_area.clear_bubbles()
        _clear_mem()
        if self._agent:
            self._agent.clear_history()
        self._sys_msg("Chat and memory cleared.")

    def resizeEvent(self, event):
        self.bg.setGeometry(self.centralWidget().rect())
        super().resizeEvent(event)

    def closeEvent(self, event):
        self._cleanup_thread()
        if _voice_ready:
            try:
                pygame.mixer.quit()
            except Exception:
                pass
        super().closeEvent(event)


# ===========================================================================
# Entry point
# ===========================================================================
def main():
    app = QApplication.instance() or QApplication(sys.argv)
    win = JarvisGUI()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
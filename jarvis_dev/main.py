import sys
import os
import re
import asyncio
import tempfile
import threading

os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"

ARIA_VOICE = "en-US-AriaNeural"
_voice_ready = False

try:
    import edge_tts
    import pygame
    pygame.mixer.init()
    _voice_ready = True
except Exception:
    pass 

def _clean_for_speech(text: str) -> str:
    text = re.sub(r"```[\s\S]*?```", " Code is shown on screen. ", text)
    text = re.sub(r"`[^`\n]+`", "", text)
    def remove_code_lines(t):
        clean = []
        for line in t.split("\n"):
            if re.match(r"(#include|import |def |void |int |struct |printf|cout|return |while |for |if \(|\{|\})", line.strip()):
                continue
            clean.append(line)
        return "\n".join(clean)
    text = remove_code_lines(text)
    text = re.sub(r"[*_#]", "", text)
    text = re.sub(r"<\|[^|]*?\|>", "", text)
    text = re.sub(r"\n+", ". ", text)
    text = re.sub(r"\.\s*\.", ".", text)
    text = re.sub(r"\s{2,}", " ", text)
    return text.strip()

async def _synthesize(text: str, path: str):
    await edge_tts.Communicate(text, voice=ARIA_VOICE).save(path)

def speak(text: str):
    if not _voice_ready: return
    spoken = _clean_for_speech(text)
    if not spoken: return

    def _run():
        tmp  = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
        path = tmp.name
        tmp.close()
        try:
            asyncio.run(_synthesize(spoken, path))
            pygame.mixer.music.load(path)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                pygame.time.Clock().tick(10)
        except Exception: pass
        finally:
            try:
                pygame.mixer.music.unload()
                os.remove(path)
            except Exception: pass

    threading.Thread(target=_run, daemon=True).start()

def stream(token: str):
    sys.stdout.write(token)
    sys.stdout.flush()

def read_multiline_code() -> str:
    print("\n📝 [CODE MODE] Paste your code below.")
    print("   Type  SEND  on a new line when finished.\n")
    lines = []
    while True:
        try:
            line = input()
        except EOFError: break
        if line.strip().upper() == "SEND": break
        lines.append(line)
    return "\n".join(lines)

BANNER = """
  Commands:
    code     → paste multi-line code for debugging
    clear    → clear conversation history
    exit     → shut down Jarvis

  Loading model, please wait..."""

QUIT_WORDS = {"exit", "quit", "stop", "bye", "shutdown"}

def main():
    print(BANNER)

    try:
        from agent import Agent
        jarvis = Agent()
    except Exception as e:
        print(f"\n❌ Failed to load model: {e}")
        sys.exit(1)

    backend = jarvis.brain.backend.upper()
    print(f"\n🤖 Jarvis: Online — [Hardware: {backend}]")

    while True:
        try:
            user = input("\n🧑 You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n\n🤖 Jarvis: Goodbye!")
            break

        if not user: continue

        if user.lower() in QUIT_WORDS:
            print("\n🤖 Jarvis: Powering down. Goodbye!")
            break

        if user.lower() == "clear":
            jarvis.clear_history()
            print("🤖 Jarvis: History cleared.\n")
            continue

        if user.lower() == "code":
            user = read_multiline_code()
            if not user.strip():
                print("⚠️  No code received. Try again.\n")
                continue

        print("\n🤖 Jarvis:\n")
        try:
            # Safely passes max_tokens down through the updated agent.py to local_llm.py
            response = jarvis.run(user, callback=stream, max_tokens=8192)
        except Exception as e:
            print(f"\n\n❌ Error: {e}\n")
            continue

        print("\n")
        speak(response)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n🤖 Jarvis: Interrupted. Goodbye!")
        os._exit(0)
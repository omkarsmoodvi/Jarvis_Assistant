import os
import sys

# 🚀 WE ARE USING MLC-LLM NOW TO AVOID THE LLAMA_CPP ERRORS
try:
    from mlc_llm import MLCEngine
except ImportError:
    print("❌ MLC-LLM library not found. Running fix...")
    os.system('pip install --pre mlc-ai-nightly-cu124 -f https://mlc.ai/wheels')
    from mlc_llm import MLCEngine

class LocalLLM:
    def __init__(self):
        # This points to the 1.75GB folder we just downloaded
        self.model_folder = r"E:\MyAssistant\jarvis_dev\models\Qwen2.5-Coder-3B-Instruct-q4f16_1-MLC"
        
        print(f"🧠 Jarvis Brain: Engaging RTX 3050 via MLC-LLM...")
        
        try:
            # ⚡ This connects directly to your CUDA cores
            self.engine = MLCEngine(self.model_folder, device="cuda")
            print("✅ Jarvis Brain: CUDA Engaged (8K Context Ready)")
        except Exception as e:
            print(f"❌ Failed to start MLC Engine: {e}")
            sys.exit(1)

    def generate(self, system_prompt, user_message, callback=None):
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]
        
        output = ""
        # 🏎️ Instant word-by-word streaming
        try:
            for response in self.engine.chat.completions.create(
                messages=messages,
                model=self.model_folder,
                stream=True,
                max_tokens=2048,
                temperature=0.1
            ):
                if response.choices[0].delta.content:
                    token = response.choices[0].delta.content
                    output += token
                    if callback:
                        callback(token)
        except Exception as e:
            print(f"\n❌ Generation Error: {e}")
        
        return output
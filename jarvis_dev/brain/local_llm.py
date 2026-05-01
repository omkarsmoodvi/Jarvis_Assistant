import os
import sys
import gc

try:
    from llama_cpp import Llama
except ImportError:
    print("❌ llama_cpp not installed")
    sys.exit(1)

class LocalLLM:
    def __init__(self):
        self.current_mode = None
        self.model = None

        self.models = {
            "fast": "Qwen2.5-Coder-3B-Instruct-Q4_K_M.gguf",
            "heavy": "DeepSeek-R1-Distill-Qwen-7B-Q4_K_M.gguf"
        }

        self.switch_model("fast")

    def switch_model(self, mode: str):
        if self.current_mode == mode:
            return

        if self.model:
            del self.model
            gc.collect()

        model_path = os.path.join(os.getcwd(), "models", self.models[mode])

        if not os.path.exists(model_path):
            print(f"❌ Model not found: {model_path}")
            sys.exit(1)

        gpu_layers = -1 if mode == "fast" else 24

        self.model = Llama(
            model_path=model_path,
            n_gpu_layers=gpu_layers,
            n_ctx=8192,
            n_batch=512,
            f16_kv=True,
            flash_attn=True,
            verbose=False
        )

        self.current_mode = mode

    def generate(self, system_prompt, user_message, callback=None, **kwargs):
        prompt = f"""<|im_start|>system
{system_prompt}
<|im_end|>
<|im_start|>user
{user_message}
<|im_end|>
<|im_start|>assistant
"""

        max_t = kwargs.get("max_tokens", 4096)
        temp = kwargs.get("temp", 0.3)

        output = ""

        response = self.model(
            prompt,
            max_tokens=max_t,
            stop=["<|im_end|>"],
            stream=True,
            temperature=temp
        )

        for chunk in response:
            token = chunk["choices"][0]["text"]
            output += token

            if callback:
                callback(token)

        return output.strip()

    @property
    def backend(self):
        return "cuda"
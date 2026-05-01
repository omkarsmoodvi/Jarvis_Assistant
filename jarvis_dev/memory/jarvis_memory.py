import json
import os
from datetime import datetime

MEMORY_FILE = os.path.join("memory", "memory.json")

def load_memory_sync():
    if not os.path.exists(MEMORY_FILE):
        return {"conversation": []}
    with open(MEMORY_FILE, 'r', encoding='utf-8') as f:
        try:
            return json.load(f)
        except:
            return {"conversation": []}

def save_memory_sync(data):
    with open(MEMORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def add_memory_entry(speaker, text):
    if not text or text == "None": return
    
    memory = load_memory_sync()
    entry = {"speaker": speaker, "text": text, "ts": datetime.now().isoformat()}
    
    if "conversation" not in memory: memory["conversation"] = []
    memory["conversation"].append(entry)
    
    save_memory_sync(memory)
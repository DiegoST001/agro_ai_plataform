import os
import subprocess
from typing import Tuple

OLLAMA_CMD = os.getenv("OLLAMA_CMD", "ollama")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma3:1b")
OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "120"))

def run_ollama(prompt: str) -> Tuple[str, int, str]:
    try:
        proc = subprocess.run(
            [OLLAMA_CMD, "run", OLLAMA_MODEL, prompt],
            capture_output=True, text=True, timeout=OLLAMA_TIMEOUT
        )
        return (proc.stdout.strip(), proc.returncode, proc.stderr.strip())
    except FileNotFoundError:
        return ("", 127, "ollama no encontrado en PATH")
    except subprocess.TimeoutExpired:
        return ("", 124, "ollama timeout")

def chat(prompt: str, model: str = "llama3"):
    proc = subprocess.run(["ollama", "run", model, prompt], capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr or "ollama error")
    return proc.stdout
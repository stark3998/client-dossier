import os
from functools import lru_cache

_PROMPTS_DIR = os.path.dirname(__file__)


@lru_cache(maxsize=None)
def load_prompt(name: str) -> str:
    path = os.path.join(_PROMPTS_DIR, name)
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

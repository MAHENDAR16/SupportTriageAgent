from __future__ import annotations

# Deterministic MVP heuristic -- a curated hostile/threat word list, not LLM
# judgment. Upgradeable in a later phase without touching graph shape.
ABUSE_KEYWORDS = [
    "idiot",
    "idiots",
    "useless",
    "incompetent",
    "pathetic",
    "stupid",
    "worthless",
    "joke",
    "regret",
    "screw you",
    "hate you",
    "shut up",
]


def detect_abuse(message: str) -> bool:
    lowered = message.lower()
    return any(keyword in lowered for keyword in ABUSE_KEYWORDS)

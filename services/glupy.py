from __future__ import annotations

import random
import re


WORD_PATTERN = re.compile(r"\S+")
URL_PATTERN = re.compile(r"https?://\S+|www\.\S+", re.IGNORECASE)
MENTION_PATTERN = re.compile(r"[@#]\S+")


def _clean_messages(messages: list[str]) -> list[list[str]]:
    cleaned = []
    for message in messages:
        text = URL_PATTERN.sub("", message.strip())
        text = MENTION_PATTERN.sub("", text)
        if not text or text.startswith("/") or not re.search(r"[^\W\d_]", text):
            continue
        words = WORD_PATTERN.findall(text)
        if len(words) >= 2:
            cleaned.append(words)
    return cleaned


def generate_glupy(
    messages: list[str],
    *,
    order: int = 1,
    max_words: int = 18,
    max_length: int = 200,
) -> str | None:
    """Generate a short Markov phrase using the configured n-gram order."""
    order = max(1, min(order, 3))
    words = _clean_messages(messages)
    transitions: dict[str, list[str]] = {}
    for line in words:
        for index in range(len(line) - order):
            key = " ".join(line[index : index + order])
            transitions.setdefault(key, []).append(line[index + order])

    starts = [
        " ".join(line[:order])
        for line in words
        if len(line) > order and " ".join(line[:order]) in transitions
    ]
    if not starts:
        return None

    result = random.choice(starts).split()
    for _ in range(max_words - order):
        choices = transitions.get(" ".join(result[-order:]))
        if not choices:
            break
        result.append(random.choice(choices))
    text = " ".join(result).strip()
    if len(text) > max_length:
        text = text[:max_length].rsplit(" ", 1)[0].strip()
    return text if len(text) >= 2 else None

"""Shared helpers for conversational mock/offline responses."""



from __future__ import annotations

import re

_GREETINGS = frozenset(

    {

        "hi",

        "hello",

        "hey",

        "howdy",

        "greetings",

        "yo",

        "sup",

        "how",

        "are",

        "you",

        "morning",

        "afternoon",

        "evening",

        "good",

        "what's",

        "up",

        "whats",

    }

)



_GREETING_PHRASES = (

    "hi",

    "hello",

    "hey",

    "howdy",

    "good morning",

    "good afternoon",

    "good evening",

    "how are you",

    "what's up",

    "whats up",

)





def is_greeting(text: str) -> bool:

    """Return True when ``text`` looks like a short greeting."""

    normalized = (text or "").strip().lower()

    if not normalized:

        return False

    if normalized in _GREETING_PHRASES:

        return True

    words = re.findall(r"\b\w+\b", normalized)

    if not words or len(words) > 4:

        return False

    return any(word in _GREETINGS for word in words)





def greeting_reply(text: str) -> str:

    """Return a natural assistant greeting."""

    normalized = (text or "").strip().lower()

    if "how are you" in normalized:

        return "I'm doing well, thanks for asking. How can I help with your project today?"

    if any(p in normalized for p in ("good morning", "good afternoon", "good evening")):

        return "Hello! How can I help you today?"

    return "Hi! How can I help you today?"





def offline_build_notice() -> str:

    """Message returned when a build is requested without a configured provider."""

    return (

        "No AI provider is configured. Configure a provider and retry, "

        "or pass `--mock` for offline mode."

    )





__all__ = ["greeting_reply", "is_greeting", "offline_build_notice"]


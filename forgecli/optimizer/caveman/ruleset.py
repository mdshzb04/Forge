"""Self-contained Python implementation of the Caveman ruleset.

The ruleset mirrors the behavior described on https://github.com/JuliusBrussee/caveman.
It does not shell out to anything; it rewrites the system message of a
:class:`ChatRequest` to bias the model toward token-efficient output.

The five intensity levels match the official Caveman project:

* ``off``    - pass-through (handled by the composite, not this class).
* ``lite``   - concise communication; drop filler words and pleasantries.
* ``full``   - full caveman: fragments, [thing][action][reason] pattern.
* ``ultra``  - maximum compression; grunt-level communication.
* ``wenyan`` - Classical Chinese literary style for max semantic density.

The output is deterministic for a given (intensity, prompt) pair, so
tests can pin it.
"""

from __future__ import annotations

from forgecli.optimizer.caveman import (
    CavemanIntensity,
    CavemanPromptOptimizer,
    OptimizedRequest,
    _clone_request,
    _ensure_user_message,
)
from forgecli.providers.base import ChatMessage, ChatRequest, Role

_CAVEMAN_GUIDANCE: dict[CavemanIntensity, str] = {
    CavemanIntensity.OFF: "",
    CavemanIntensity.LITE: (
        "CAVEMAN (lite): communicate concisely. "
        "Drop filler words (just, really, basically, actually). "
        "Drop pleasantries (sure, certainly, happy to, I think). "
        "Use short sentences. Keep technical terms exact."
    ),
    CavemanIntensity.FULL: (
        "CAVEMAN (full): talk like caveman. Brain still big, mouth small.\n\n"
        "Rules:\n"
        "- Drop filler words, pleasantries, transition phrases\n"
        "- Use sentence fragments where meaning is clear\n"
        "- Keep technical terms exact \u2014 never simplify them\n"
        "- Follow [thing] [action] [reason] pattern\n"
        "- No summaries, no disclaimers, no meta-commentary\n"
        "- Code blocks and error messages stay unmodified"
    ),
    CavemanIntensity.ULTRA: (
        "CAVEMAN (ultra): maximum compression.\n\n"
        "- One sentence max per idea\n"
        "- No articles (a, an, the) unless essential\n"
        "- No polite prefixes \u2014 get straight to the point\n"
        "- [action] [thing] directly\n"
        "- Grunt-level communication preferred\n"
        "- Code unchanged. Technical terms unchanged."
    ),
    CavemanIntensity.WENYAN: (
        "CAVEMAN (wenyan): respond in Classical Chinese literary style "
        "(\u6587\u8a00 / wenyanwen).\n\n"
        "- Maximum semantic density per character\n"
        "- Use classical parallel structure where appropriate\n"
        "- Eliminate all modern conversational padding\n"
        "- \u4e00\u8a00\u4ee5\u84cb\u4e4b: express essence in minimum characters\n"
        "- Code blocks, technical terms, and proper nouns stay in original form"
    ),
}


class CavemanRulesetOptimizer(CavemanPromptOptimizer):
    """Rewrite system messages to apply the Caveman ruleset."""

    name = "caveman.ruleset"

    def __init__(self, *, intensity: CavemanIntensity = CavemanIntensity.LITE) -> None:
        self._intensity = CavemanIntensity.parse(intensity)

    @property
    def intensity(self) -> CavemanIntensity:
        return self._intensity

    def set_intensity(self, intensity: CavemanIntensity | str) -> None:
        self._intensity = CavemanIntensity.parse(intensity)

    async def optimize_chat(self, request: ChatRequest) -> OptimizedRequest:
        if self._intensity is CavemanIntensity.OFF:
            return OptimizedRequest(
                request=request,
                notes=("caveman off",),
                intensity=CavemanIntensity.OFF,
                source="caveman-ruleset",
            )

        guidance = _CAVEMAN_GUIDANCE[self._intensity]
        messages = list(request.messages)

        if not _ensure_user_message(messages):
            return OptimizedRequest(
                request=request,
                notes=("no user message; caveman passthrough",),
                intensity=self._intensity,
                source="caveman-ruleset",
            )

        rewritten = _rewrite_messages(messages, guidance)
        notes = _build_notes(self._intensity)
        return OptimizedRequest(
            request=_clone_request(request, rewritten),
            notes=notes,
            intensity=self._intensity,
            source="caveman-ruleset",
        )


def _rewrite_messages(
    messages: list[ChatMessage],
    guidance: str,
) -> list[ChatMessage]:
    """Insert Caveman guidance at the head of the conversation.

    Rules:
    * If the first message is a system message, prepend the guidance
      to it (separated by two newlines).
    * If there is no system message, insert one.
    * If the first system message is *empty*, replace it.
    * Otherwise the user/assistant turns are left untouched.
    """
    if not messages:
        return [ChatMessage(role=Role.SYSTEM, content=guidance)]

    first = messages[0]
    if first.role is Role.SYSTEM:
        existing = first.content.strip()
        if not existing:
            return [ChatMessage(role=Role.SYSTEM, content=guidance), *messages[1:]]
        new_content = f"{guidance}\n\n{first.content}" if guidance else first.content
        return [ChatMessage(role=Role.SYSTEM, content=new_content), *messages[1:]]

    return [ChatMessage(role=Role.SYSTEM, content=guidance), *messages]


def _build_notes(intensity: CavemanIntensity) -> tuple[str, ...]:
    notes: list[str] = [f"caveman intensity={intensity.value}"]
    if intensity is CavemanIntensity.FULL:
        notes.append("caveman full mode \u2014 fragments + [thing][action][reason]")
    elif intensity is CavemanIntensity.ULTRA:
        notes.append("caveman ultra \u2014 maximum compression")
    elif intensity is CavemanIntensity.WENYAN:
        notes.append("caveman wenyan \u2014 classical Chinese literary style")
    elif intensity is CavemanIntensity.LITE:
        notes.append("caveman lite \u2014 concise, no filler")
    return tuple(notes)


__all__ = [
    "CavemanRulesetOptimizer",
]

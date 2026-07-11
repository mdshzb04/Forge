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

        "CAVEMAN (lite): keep responses brief. "

        "Omit filler words such as 'basically', 'actually', or 'really'. "

        "Avoid polite padding like 'sure', 'certainly', or 'happy to help'. "

        "Focus on short statements and preserve technical keywords."

    ),

    CavemanIntensity.FULL: (

        "CAVEMAN (full): adopt a direct, fragment-based speech pattern. "

        "Limit sentence structures to bare essentials.\n\n"

        "Guidelines:\n"

        "- Exclude conversational greetings, filler verbs, and transitions.\n"

        "- Frame responses around sentence fragments where possible.\n"

        "- Maintain precise technical vocabulary and proper names.\n"

        "- Deliver logic using the [subject] [action] [reason] structure.\n"

        "- Strip out summaries, disclaimers, and self-referential notes.\n"

        "- Ensure code blocks are kept exactly as-is."

    ),

    CavemanIntensity.ULTRA: (

        "CAVEMAN (ultra): apply maximum communication compression.\n\n"

        "- Express each core concept in a single sentence or fragment.\n"

        "- Remove non-essential articles (the, a, an).\n"

        "- Eliminate polite prefixes and greeting wrappers.\n"

        "- State [action] [object] directly without padding.\n"

        "- Favor ultra-concise, raw fragments.\n"

        "- Keep all code snippets and key parameters fully intact."

    ),

    CavemanIntensity.WENYAN: (

        "CAVEMAN (wenyan): format the response in Classical Chinese style "

        "(\u6587\u8a00 / wenyanwen).\n\n"

        "- Maximize meaning using the fewest possible characters.\n"

        "- Apply classical parallel structures and concise patterns.\n"

        "- Purge modern chat structures and modern conversational padding.\n"

        "- Convey core findings directly and efficiently.\n"

        "- Retain code segments and proper nouns without translation."

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


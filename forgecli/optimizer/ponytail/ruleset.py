"""Self-contained Python implementation of the Ponytail ruleset.

The ruleset mirrors the behavior described on https://ponytail.dev/ and
the project's GitHub README (DietrichGebert/ponytail). It does not
shell out to anything; it rewrites the system message of a
:class:`ChatRequest` to bias the model toward the lazier correct
solution.

The four intensity levels match the official ``/ponytail`` command:

* ``off``   - pass-through (handled by the composite, not this class).
* ``lite``  - default; appends a single sentence reminding the model to
              name the lazier alternative and lets the user pick.
* ``full``  - prepends the full "ladder" instruction and tells the
              model to ship the shortest diff.
* ``ultra`` - aggressive YAGNI; tells the model to ship the simplest
              implementation that satisfies requirements.

The output is deterministic for a given (intensity, prompt) pair, so
tests can pin it.
"""



from __future__ import annotations

from forgecli.optimizer.ponytail import (
    CompositeOptimizer,
    Intensity,
    OptimizedRequest,
    PromptOptimizer,
    _clone_request,
    _ensure_user_message,
)
from forgecli.providers.base import ChatMessage, ChatRequest, Role

LADDER_INSTRUCTION = (

    "Stop at the first rung that holds. Apply the Ponytail ladder before "

    "writing any code:\n"

    "  1. Does this need to exist? Speculative need = skip it (YAGNI).\n"

    "  2. Already in this codebase? Reuse the helper, util, or pattern "

    "that already lives here.\n"

    "  3. Does the standard library do it? Use it.\n"

    "  4. Native platform feature covers it? (e.g. <input type='date'> "

    "over a picker lib.)\n"

    "  5. Already-installed dependency solves it? Use it. Don't add a "

    "new one.\n"

    "  6. Can it be one line? One line.\n"

    "  7. Only then: the minimum code that works."

)





_INTENSITY_GUIDANCE: dict[Intensity, str] = {

    Intensity.OFF: "",

    Intensity.LITE: (

        "Ponytail (lite): when you reach for code, also name the lazier "

        "correct alternative in a single sentence. The user picks."

    ),

    Intensity.FULL: (

        "Ponytail (full): apply the Ponytail ladder before writing any code. "

        "Ship the shortest diff and the shortest explanation. Never "

        "simplify away validation, error handling, security, or accessibility.\n\n"

        f"{LADDER_INSTRUCTION}"

    ),

    Intensity.ULTRA: (

        "Ponytail (ultra): YAGNI extremist. Ship the one-liner. In the "

        "same breath, name what is being *cut* from the original "

        "requirement and why the cut is safe."

    ),

}





class PonytailRulesetOptimizer(PromptOptimizer):

    """Rewrite system messages to apply the Ponytail ruleset."""



    name = "ponytail.ruleset"



    def __init__(self, *, intensity: Intensity = Intensity.LITE) -> None:

        self._intensity = Intensity.parse(intensity)



    @property

    def intensity(self) -> Intensity:

        return self._intensity



    def set_intensity(self, intensity: Intensity | str) -> None:

        self._intensity = Intensity.parse(intensity)



    async def optimize_chat(self, request: ChatRequest) -> OptimizedRequest:

        if self._intensity is Intensity.OFF:

            return OptimizedRequest(

                request=request,

                notes=("ponytail off",),

                intensity=Intensity.OFF,

                source="ruleset",

            )



        guidance = _INTENSITY_GUIDANCE[self._intensity]

        messages = list(request.messages)



        if not _ensure_user_message(messages):





            return OptimizedRequest(

                request=request,

                notes=("no user message; passthrough",),

                intensity=self._intensity,

                source="ruleset",

            )



        rewritten = _rewrite_messages(messages, guidance)

        notes = _build_notes(self._intensity, len(messages), len(rewritten))

        return OptimizedRequest(

            request=_clone_request(request, rewritten),

            notes=notes,

            intensity=self._intensity,

            source="ruleset",

        )





def _rewrite_messages(

    messages: list[ChatMessage],

    guidance: str,

) -> list[ChatMessage]:

    """Insert Ponytail guidance at the head of the conversation.

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





def _build_notes(

    intensity: Intensity, original_count: int, rewritten_count: int

) -> tuple[str, ...]:

    notes: list[str] = [f"ponytail intensity={intensity.value}"]

    if intensity is Intensity.FULL:

        notes.append("ladder enforced")

    elif intensity is Intensity.ULTRA:

        notes.append("yagni extremist mode")

    elif intensity is Intensity.LITE:

        notes.append("named the lazier alternative")

    if rewritten_count != original_count:

        notes.append(f"inserted system message ({rewritten_count} > {original_count})")

    return tuple(notes)





__all__ = [

    "LADDER_INSTRUCTION",

    "PonytailRulesetOptimizer",

]







_ = CompositeOptimizer


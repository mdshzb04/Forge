"""Memory Compression Engine.

Summarizes old turns in the conversation history, extracts permanent facts, and
compresses message content to prevent linear growth of context windows.
"""



from __future__ import annotations

from typing import TYPE_CHECKING

from forgecli.providers.base import ChatMessage, Role

if TYPE_CHECKING:

    from collections.abc import Iterable





class MemoryCompressionManager:

    """Manages chat turn summaries and historical message pruning to stay within budgets."""



    def __init__(self, keep_recent_turns: int = 4) -> None:

        self.keep_recent = keep_recent_turns



    def compress_history(self, messages: Iterable[ChatMessage]) -> list[ChatMessage]:

        """Compress the list of ChatMessages.

        Keep the system message, and the most recent N user/assistant turns in full.
        Summarize/compress the historical intermediate turns.
        """

        msg_list = list(messages)

        if not msg_list:

            return []



        system_messages = [m for m in msg_list if m.role == Role.SYSTEM]

        other_messages = [m for m in msg_list if m.role != Role.SYSTEM]



        if len(other_messages) <= self.keep_recent:

            return msg_list





        older_messages = other_messages[: -self.keep_recent]

        recent_messages = other_messages[-self.keep_recent :]





        summarized_facts = self._compile_summarized_facts(older_messages)





        summary_msg = ChatMessage(

            role=Role.SYSTEM,

            content=(

                "=== COMPRESSED CONVERSATION HISTORY & FACTS ===\n"

                f"{summarized_facts}\n"

                "================================================"

            ),

        )



        return [*system_messages, summary_msg, *recent_messages]



    def _compile_summarized_facts(self, messages: list[ChatMessage]) -> str:

        """Create a compact bulleted list of facts/events/requests from older messages."""

        facts: list[str] = []

        for m in messages:

            content = m.content.strip()

            if not content:

                continue



            if m.role == Role.USER:



                summary = content.split("\n")[0]

                if len(summary) > 100:

                    summary = summary[:97] + "..."

                facts.append(f"User requested: {summary}")

            elif m.role == Role.ASSISTANT:





                summary = "Answered/Code updated."

                if "error" in content.lower():

                    summary = "Addressed error diagnostics."

                facts.append(f"Assistant: {summary}")





        seen = set()

        dedup_facts = []

        for f in facts:

            if f not in seen:

                seen.add(f)

                dedup_facts.append(f)



        return "\n".join(f"- {fact}" for fact in dedup_facts)


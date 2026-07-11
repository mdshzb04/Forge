"""Prompt Optimizer Engine.

Compacts verbose system prompts and user messages to strip fluff, redundant phrasing,
and polite filler words, saving tokens without changing intent.
"""



from __future__ import annotations

import re
from typing import ClassVar


class PromptOptimizer:

    """Removes verbose phrasing, redundant instructions, and filler words from prompts."""





    FILLER_PATTERNS: ClassVar[list[str]] = [

        r"\b(?:could|would|can)\s+you\s+(?:please|kindly|just)\b",

        r"\bplease\s+(?:write|generate|create|make|help\s+me)\b",

        r"\b(?:thank\s+you|thanks|regards|hi|hello|hey)\b[,.!]?",

        r"\bi\s+am\s+(?:trying\s+to|working\s+on)\b",

        r"\bwould\s+be\s+great\s+if\s+you\s+could\b",

        r"\bi\s+need\s+you\s+to\b",

        r"\bi\s+want\s+to\b",

    ]



    def optimize_user_prompt(self, prompt: str) -> str:

        """Strip filler phrases and collapse redundant spacing from the user prompt."""

        if not prompt:

            return prompt



        lines = []

        for line in prompt.splitlines():

            cleaned = line

            for pat in self.FILLER_PATTERNS:

                cleaned = re.sub(pat, "", cleaned, flags=re.IGNORECASE)





            cleaned = re.sub(r"\s+", " ", cleaned).strip()

            if cleaned:

                lines.append(cleaned)





        return "\n".join(lines)



    def optimize_system_prompt(self, prompt: str) -> str:

        """Deduplicate instructions and constraint clauses in system messages."""

        if not prompt:

            return prompt





        sentences = re.split(r'(?<=[.!?])\s+', prompt)

        seen = set()

        unique_sentences = []



        for s in sentences:

            trimmed = s.strip()

            if not trimmed:

                continue





            norm = re.sub(r"\W+", "", trimmed).lower()

            if norm in seen:

                continue





            is_redundant = False

            for prev in seen:



                prev_words = set(prev.split())

                curr_words = set(norm.split())

                if len(prev_words) > 4 and len(curr_words) > 4:

                    overlap = len(prev_words.intersection(curr_words))

                    if overlap / max(len(prev_words), len(curr_words)) > 0.8:

                        is_redundant = True

                        break



            if not is_redundant:

                seen.add(norm)

                unique_sentences.append(trimmed)



        return " ".join(unique_sentences)


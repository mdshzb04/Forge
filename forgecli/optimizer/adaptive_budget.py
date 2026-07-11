"""Adaptive Context Budget Manager.

Dynamically adapts token size limits and context compression aggressiveness
according to specific LLM models, provider capabilities, and reasoning modes.
"""



from __future__ import annotations

from typing import Any


class AdaptiveContextBudget:

    """Computes context thresholds and determines compression ratios for target models."""



    @staticmethod

    def get_budget_config(model_name: str) -> dict[str, Any]:

        """Return the context limit, target prompt size, and compression aggressiveness for the model."""

        name = model_name.lower()





        max_context = 32_000

        target_context = 8_000

        aggressiveness = "normal"

        is_reasoning_model = False





        if "gemini" in name:



            max_context = 200_000

            target_context = 64_000

            aggressiveness = "lite"

            if "thinking" in name:

                is_reasoning_model = True

                aggressiveness = "normal"

        elif "claude" in name:

            max_context = 100_000

            target_context = 20_000

            aggressiveness = "normal"

            if "thinking" in name or "opus" in name:

                is_reasoning_model = True

        elif "deepseek" in name:

            max_context = 64_000

            target_context = 16_000

            aggressiveness = "normal"

            if "reasoning" in name or "r1" in name:

                is_reasoning_model = True

        elif "gpt-4" in name or "o1" in name or "o3" in name:

            max_context = 64_000

            target_context = 16_000

            aggressiveness = "normal"

            if "o1" in name or "o3" in name:

                is_reasoning_model = True

        elif "ollama" in name or "local" in name:

            max_context = 8_000

            target_context = 3_000

            aggressiveness = "extreme"

        elif "llama" in name or "qwen" in name or "mistral" in name:



            max_context = 16_000

            target_context = 4_000

            aggressiveness = "high"



        return {

            "max_context": max_context,

            "target_context": target_context,

            "aggressiveness": aggressiveness,

            "is_reasoning_model": is_reasoning_model,

        }


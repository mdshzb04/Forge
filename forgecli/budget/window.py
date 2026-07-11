"""Context window management and trimming."""



from __future__ import annotations

import logging
from typing import Any

from forgecli.budget.planner import TokenBudget, TokenPlanner

logger = logging.getLogger("forge.budget.window")





class ContextWindowManager:

    """Manages trimming of messages and files to fit within a token budget."""



    def __init__(self, planner: TokenPlanner | None = None) -> None:

        self.planner = planner or TokenPlanner()



    def trim_messages(self, messages: list[dict[str, Any]], budget: TokenBudget) -> list[dict[str, Any]]:

        """Trim oldest messages (excluding system) until within budget."""



        total_tokens = sum(self.planner.estimate_tokens(m.get("content", "")) for m in messages)



        if total_tokens <= budget.available_context_tokens:

            return list(messages)



        logger.warning("Context budget exceeded (%d > %d). Trimming messages...", total_tokens, budget.available_context_tokens)





        system_msgs = [m for m in messages if m.get("role") == "system"]

        chat_msgs = [m for m in messages if m.get("role") != "system"]





        if not chat_msgs:

            return list(messages)



        last_msg = chat_msgs.pop()



        while chat_msgs:



            current_tokens = sum(self.planner.estimate_tokens(m.get("content", "")) for m in system_msgs + chat_msgs + [last_msg])

            if current_tokens <= budget.available_context_tokens:

                break



            removed = chat_msgs.pop(0)

            logger.debug("Trimmed message of length %d to fit budget", len(removed.get("content", "")))



        return system_msgs + chat_msgs + [last_msg]


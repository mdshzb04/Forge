"""Session model definitions for Dialogue & Session Intelligence."""



from __future__ import annotations

import time
from typing import Any

from pydantic import BaseModel, Field


class Session(BaseModel):

    """Pydantic model representing a conversation session state."""



    session_id: str

    history: list[dict[str, str]] = Field(default_factory=list)

    metadata: dict[str, Any] = Field(default_factory=dict)

    created_at: float = Field(default_factory=time.time)

    updated_at: float = Field(default_factory=time.time)



    def append_message(self, role: str, content: str) -> None:

        """Append a message to the dialogue history.

        Args:
            role: The role (e.g. 'user', 'assistant').
            content: The text content.
        """

        self.history.append({"role": role, "content": content})

        self.updated_at = time.time()



    def clear_history(self) -> None:

        """Clear session dialogue history."""

        self.history.clear()

        self.updated_at = time.time()


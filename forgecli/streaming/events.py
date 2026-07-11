"""Streaming event abstractions."""



from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel


class StreamEvent(BaseModel):

    """Base class for all stream events."""



    event_type: str





class StreamStart(StreamEvent):

    """Event fired when the stream begins."""



    event_type: Literal["start"] = "start"

    response_id: str





class StreamChunk(StreamEvent):

    """A chunk of generated content."""



    event_type: Literal["chunk"] = "chunk"

    text: str





class StreamEnd(StreamEvent):

    """Event fired when the stream completes."""



    event_type: Literal["end"] = "end"

    finish_reason: str

    metrics: dict[str, Any] | None = None


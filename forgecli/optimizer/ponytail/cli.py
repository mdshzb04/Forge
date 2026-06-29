"""Optional adapter for an external ``ponytail`` CLI.

Some Ponytail installations (or future refactors) ship a binary on
``PATH`` that can rewrite a prompt itself. This adapter detects the
binary and forwards the conversation to it. When the binary is not
installed, :meth:`is_available` returns ``False`` and the
:class:`CompositeOptimizer` falls back to the in-process ruleset.
"""

from __future__ import annotations

import asyncio
import contextlib
import os
import shutil
import tempfile
from pathlib import Path

from forgecli.core.errors import ForgeCLIError
from forgecli.optimizer.ponytail import (
    Intensity,
    OptimizedRequest,
    PromptOptimizer,
)
from forgecli.providers.base import ChatMessage, ChatRequest, Role


class PonytailCLIError(ForgeCLIError):
    """Raised when the external ``ponytail`` binary fails."""


class PonytailCLIOptimizer(PromptOptimizer):
    """Forward prompts to an external ``ponytail`` binary via stdin/stdout.

    The CLI is expected to accept a JSON payload on stdin and emit a
    JSON payload on stdout. When such a binary is not present the
    adapter is harmless — :meth:`is_available` returns ``False`` and
    the composite falls back to the in-process ruleset.
    """

    name = "ponytail.cli"

    def __init__(
        self,
        *,
        executable: str | None = None,
        timeout: float = 30.0,
    ) -> None:
        self._executable = executable or os.environ.get(
            "FORGECLI_PONYTAIL_BIN", "ponytail"
        )
        self._timeout = timeout

    @property
    def executable(self) -> str:
        return self._executable

    async def is_available(self) -> bool:
        return shutil.which(self._executable) is not None

    async def optimize_chat(self, request: ChatRequest) -> OptimizedRequest:
        if not await self.is_available():
            raise PonytailCLIError(
                f"Ponytail executable {self._executable!r} not found on PATH"
            )

        binary = shutil.which(self._executable) or self._executable
        payload = _request_to_json(request)
        with tempfile.NamedTemporaryFile(
            "w", suffix=".json", delete=False, encoding="utf-8"
        ) as src:
            src.write(payload)
            src_path = Path(src.name)
        try:
            proc = await asyncio.create_subprocess_exec(
                binary,
                "optimize",
                "--stdin",
                str(src_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            try:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(), timeout=self._timeout
                )
            except TimeoutError as exc:
                proc.kill()
                raise PonytailCLIError(
                    f"ponytail optimize timed out after {self._timeout}s"
                ) from exc
        finally:
            with contextlib.suppress(OSError):
                src_path.unlink()

        if proc.returncode != 0:
            raise PonytailCLIError(
                f"ponytail exited with {proc.returncode}: "
                f"{stderr.decode(errors='replace').strip()}"
            )

        return _json_to_optimized(stdout.decode(errors="replace"))


def _request_to_json(request: ChatRequest) -> str:
    """Serialize a :class:`ChatRequest` for the CLI."""
    import json

    return json.dumps(
        {
            "model": request.model,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
            "messages": [
                {
                    "role": m.role.value,
                    "content": m.content,
                    "name": m.name,
                    "tool_call_id": m.tool_call_id,
                }
                for m in request.messages
            ],
        },
        ensure_ascii=False,
    )


def _json_to_optimized(raw: str) -> OptimizedRequest:
    """Parse the JSON the CLI emitted and rebuild an :class:`OptimizedRequest`."""
    import json

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise PonytailCLIError(f"ponytail returned invalid JSON: {exc}") from exc

    try:
        intensity = Intensity.parse(payload.get("intensity", "lite"))
        messages = [
            ChatMessage(
                role=Role(m["role"]),
                content=m["content"],
                name=m.get("name"),
                tool_call_id=m.get("tool_call_id"),
            )
            for m in payload.get("messages", [])
        ]
    except (KeyError, ValueError) as exc:
        raise PonytailCLIError(
            f"ponytail returned an unexpected payload: {exc}"
        ) from exc

    new_request = ChatRequest(
        model=payload.get("model"),
        messages=messages,
        temperature=payload.get("temperature"),
        max_tokens=payload.get("max_tokens"),
    )
    notes = tuple(payload.get("notes", ()))
    return OptimizedRequest(
        request=new_request,
        notes=notes,
        intensity=intensity,
        source="external",
    )


__all__ = ["PonytailCLIError", "PonytailCLIOptimizer"]

"""Thread-safe context management for the Universal AI Runtime.

Tracks active session states, telemetry markers, and cancellation limits.
"""



from __future__ import annotations

import threading
from pathlib import Path
from typing import Any


class CancellationToken:

    """A thread-safe token used to signal and check cancellation states."""



    def __init__(self) -> None:

        """Initialize the CancellationToken."""

        self._is_cancelled = False

        self._lock = threading.Lock()



    def cancel(self) -> None:

        """Signal cancellation. All subsequent calls to is_cancelled will return True."""

        with self._lock:

            self._is_cancelled = True



    @property

    def is_cancelled(self) -> bool:

        """Check if cancellation has been requested.

        Returns:
            True if cancel() has been called, False otherwise.
        """

        with self._lock:

            return self._is_cancelled





class RuntimeContext:

    """Thread-safe state container passed across the Forge middleware pipeline.

    Encapsulates active session configurations, repository metadata, telemetry
    tracing variables, and shared key-value states.
    """



    def __init__(

        self,

        session_id: str,

        workspace: Path,

        repository_root: Path,

        current_provider: str | None = None,

        current_model: str | None = None,

        metadata: dict[str, Any] | None = None,

        telemetry_context: dict[str, Any] | None = None,

    ) -> None:

        """Initialize the RuntimeContext.

        Args:
            session_id: The unique execution session UUID.
            workspace: Path to the active workspace.
            repository_root: Path to the root git repository directory.
            current_provider: Name of the active provider.
            current_model: Name of the active model.
            metadata: Extensible context dictionary.
            telemetry_context: Observability logging metrics variables.
        """

        self._lock = threading.Lock()

        self._session_id = session_id

        self._workspace = workspace

        self._repository_root = repository_root

        self._current_provider = current_provider

        self._current_model = current_model

        self._metadata = dict(metadata or {})

        self._telemetry_context = dict(telemetry_context or {})

        self._shared_state: dict[str, Any] = {}

        self._cancellation_token = CancellationToken()



    @property

    def session_id(self) -> str:

        """Retrieve the active session identifier."""

        return self._session_id



    @property

    def workspace(self) -> Path:

        """Retrieve the active workspace path."""

        return self._workspace



    @property

    def repository_root(self) -> Path:

        """Retrieve the git repository root path."""

        return self._repository_root



    @property

    def current_provider(self) -> str | None:

        """Retrieve the active provider name thread-safely."""

        with self._lock:

            return self._current_provider



    @current_provider.setter

    def current_provider(self, value: str | None) -> None:

        """Set the active provider name thread-safely."""

        with self._lock:

            self._current_provider = value



    @property

    def current_model(self) -> str | None:

        """Retrieve the active model identifier thread-safely."""

        with self._lock:

            return self._current_model



    @current_model.setter

    def current_model(self, value: str | None) -> None:

        """Set the active model identifier thread-safely."""

        with self._lock:

            self._current_model = value



    @property

    def cancellation_token(self) -> CancellationToken:

        """Retrieve the cancellation token."""

        return self._cancellation_token



    def get_metadata(self, key: str, default: Any = None) -> Any:

        """Retrieve a metadata value thread-safely."""

        with self._lock:

            return self._metadata.get(key, default)



    def set_metadata(self, key: str, value: Any) -> None:

        """Store a metadata key-value pair thread-safely."""

        with self._lock:

            self._metadata[key] = value



    def get_telemetry_context(self, key: str, default: Any = None) -> Any:

        """Retrieve a telemetry value thread-safely."""

        with self._lock:

            return self._telemetry_context.get(key, default)



    def set_telemetry_context(self, key: str, value: Any) -> None:

        """Store a telemetry metric thread-safely."""

        with self._lock:

            self._telemetry_context[key] = value



    def get_state(self, key: str, default: Any = None) -> Any:

        """Retrieve a shared state value thread-safely."""

        with self._lock:

            return self._shared_state.get(key, default)



    def set_state(self, key: str, value: Any) -> None:

        """Set a shared state value thread-safely."""

        with self._lock:

            self._shared_state[key] = value


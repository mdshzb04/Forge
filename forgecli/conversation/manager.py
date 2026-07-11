"""Session Manager for persistent conversation tracking."""



from __future__ import annotations

import json
import logging
import threading
from pathlib import Path
from typing import TYPE_CHECKING

from forgecli.conversation.session import Session

if TYPE_CHECKING:

    pass



logger = logging.getLogger("forge.conversation.manager")





class SessionManager:

    """Manages active dialogue sessions and handles serialization/deserialization."""



    def __init__(self, persistence_dir: Path | None = None) -> None:

        """Initialize the SessionManager.

        Args:
            persistence_dir: Directory where sessions will be saved on disk.
        """

        self._lock = threading.Lock()

        self._sessions: dict[str, Session] = {}

        self._persistence_dir = persistence_dir

        if self._persistence_dir:

            try:

                self._persistence_dir.mkdir(parents=True, exist_ok=True)

            except Exception as e:

                logger.error("Failed to create session persistence directory: %s", e)

                self._persistence_dir = None



    def get_or_create_session(self, session_id: str) -> Session:

        """Get an existing session or create a new one.

        Args:
            session_id: Unique session identifier.
        """

        with self._lock:

            if session_id in self._sessions:

                return self._sessions[session_id]





            if self._persistence_dir:

                session = self._load_session_from_disk(session_id)

                if session:

                    self._sessions[session_id] = session

                    return session





            session = Session(session_id=session_id)

            self._sessions[session_id] = session

            return session



    def save_session(self, session_id: str) -> None:

        """Save a session to disk.

        Args:
            session_id: Unique session identifier.
        """

        with self._lock:

            session = self._sessions.get(session_id)

            if not session:

                return



            if self._persistence_dir:

                self._save_session_to_disk(session)



    def delete_session(self, session_id: str) -> None:

        """Delete a session from memory and disk.

        Args:
            session_id: Unique session identifier.
        """

        with self._lock:

            self._sessions.pop(session_id, None)

            if self._persistence_dir:

                file_path = self._persistence_dir / f"{session_id}.json"

                if file_path.exists():

                    try:

                        file_path.unlink()

                    except Exception as e:

                        logger.error("Failed to delete session file %s: %s", file_path, e)



    def _save_session_to_disk(self, session: Session) -> None:

        if not self._persistence_dir:

            return

        file_path = self._persistence_dir / f"{session.session_id}.json"

        try:

            with open(file_path, "w", encoding="utf-8") as f:

                json.dump(session.model_dump(), f, indent=2)

        except Exception as e:

            logger.error("Failed to save session to disk: %s", e)



    def _load_session_from_disk(self, session_id: str) -> Session | None:

        if not self._persistence_dir:

            return None

        file_path = self._persistence_dir / f"{session_id}.json"

        if not file_path.exists():

            return None

        try:

            with open(file_path, encoding="utf-8") as f:

                data = json.load(f)

                return Session(**data)

        except Exception as e:

            logger.error("Failed to load session from disk: %s", e)

            return None


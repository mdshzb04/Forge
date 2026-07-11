"""Configuration manager for the Universal AI Runtime.

Implements layered settings resolution with thread-safe validation caching.
"""



from __future__ import annotations

import logging
import threading
from pathlib import Path
from typing import Any

from forgecli.config.loader import ConfigLoader
from forgecli.config.settings import ForgeSettings
from forgecli.core.errors import ConfigError
from forgecli.runtime_core.errors import ConfigurationError

logger = logging.getLogger("forge.runtime_core.config_manager")





class ConfigurationManager:

    """Manages layered configuration resolution with support for caching and overrides.

    This manager acts as the entry point for all configuration tasks within the
    Universal AI Runtime, exposing thread-safe methods to load settings. It preserves
    complete backward compatibility by wrapping the existing ConfigLoader and returning
    standard ForgeSettings.

    Precedence order (highest to lowest):
    1. Environment variables (prefixed with FORGECLI_)
    2. User-provided explicit file paths
    3. Local user configurations (forgecli.toml, .forgecli.toml)
    4. Repository settings (Forge.toml)
    5. Project metadata configurations (pyproject.toml)
    """



    DEFAULT_CANDIDATES: tuple[Path, ...] = (

        Path("./pyproject.toml"),

        Path("./Forge.toml"),

        Path("./.forgecli.toml"),

        Path("./forgecli.toml"),

    )



    def __init__(self, *user_paths: Path) -> None:

        """Initialize the ConfigurationManager.

        Args:
            *user_paths: Optional specific paths to configuration files. If provided,
                only these files will be processed instead of the default candidates.
        """

        self._user_paths: tuple[Path, ...] = user_paths

        self._lock = threading.Lock()

        self._cached_settings: ForgeSettings | None = None







        if self._user_paths:

            self._loader = ConfigLoader(*self._user_paths)

            logger.info("ConfigurationManager initialized with user paths: %s", self._user_paths)

        else:

            self._loader = ConfigLoader(*self.DEFAULT_CANDIDATES)

            logger.info("ConfigurationManager initialized with default candidate paths.")



    def get_settings(self, *, force_reload: bool = False) -> ForgeSettings:

        """Load and retrieve the application settings thread-safely.

        Args:
            force_reload: If True, invalidates the cache and forces a filesystem re-read.

        Returns:
            The loaded and validated ForgeSettings instance.

        Raises:
            ConfigurationError: If any loaded TOML file is malformed or invalid.
        """

        with self._lock:

            if force_reload:

                logger.debug("Forcing configuration cache invalidation.")

                self._loader.invalidate()

                self._cached_settings = None



            if self._cached_settings is not None:

                return self._cached_settings



            try:

                logger.debug("Resolving configuration layers...")







                import os















                data: dict[str, Any] = {}

                for path in self._loader._candidate_paths():

                    if not path.exists():

                        continue

                    data = self._loader._merge(data, self._loader._read_toml(path))





                prefix = "FORGECLI_"

                delimiter = "__"

                for env_key in os.environ:

                    if not env_key.upper().startswith(prefix):

                        continue

                    parts = env_key[len(prefix):].lower().split(delimiter)

                    curr = data

                    for part in parts[:-1]:

                        if isinstance(curr, dict) and part in curr:

                            curr = curr[part]

                        else:

                            break

                    else:

                        if isinstance(curr, dict) and parts[-1] in curr:

                            curr.pop(parts[-1])





                settings = ForgeSettings(**data)

                self._cached_settings = settings

                logger.info("Configuration successfully loaded and cached.")

                return settings

            except ConfigError as exc:

                logger.error("Configuration error encountered: %s", exc)

                raise ConfigurationError(

                    message=f"Failed to load runtime configuration: {exc}",

                    context={"original_error": str(exc)},

                ) from exc

            except Exception as exc:

                logger.critical("Unexpected configuration parsing error: %s", exc)

                raise ConfigurationError(

                    message=f"Unexpected error loading configuration: {exc}",

                    context={"error_type": type(exc).__name__},

                ) from exc



    def invalidate_cache(self) -> None:

        """Clear the cached settings instance in a thread-safe manner."""

        with self._lock:

            logger.debug("Invalidating configuration manager cache.")

            self._loader.invalidate()

            self._cached_settings = None


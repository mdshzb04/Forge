"""Model Registry for the Forge Universal AI Runtime.

Tracks known model profiles, context limits, pricing math, capabilities, and resolves aliases.
"""



from __future__ import annotations

import threading

from pydantic import BaseModel, Field

from forgecli.providers.provider_capabilities import Capability


class ModelProfile(BaseModel):

    """Configuration profile containing context windows, pricing, and capabilities for a model."""



    name: str

    context_window: int

    max_output_tokens: int

    input_token_cost: float = 0.0

    output_token_cost: float = 0.0

    capabilities: set[Capability] = Field(default_factory=set)





class ModelRegistry:

    """Thread-safe catalog of model profiles and aliases."""



    def __init__(self) -> None:

        """Initialize the ModelRegistry with default profiles."""

        self._lock = threading.Lock()

        self._profiles: dict[str, ModelProfile] = {}

        self._aliases: dict[str, str] = {}

        self._register_defaults()



    def _register_defaults(self) -> None:

        """Register built-in model profiles."""

        defaults = [

            ModelProfile(

                name="gpt-4o",

                context_window=128000,

                max_output_tokens=4096,

                input_token_cost=5.0,

                output_token_cost=15.0,

                capabilities={

                    Capability.TOOL_CALLING,

                    Capability.VISION,

                    Capability.STREAMING,

                    Capability.JSON_MODE,

                    Capability.STRUCTURED_OUTPUTS,

                    Capability.PROMPT_CACHING,

                },

            ),

            ModelProfile(

                name="claude-3-5-sonnet",

                context_window=200000,

                max_output_tokens=8192,

                input_token_cost=3.0,

                output_token_cost=15.0,

                capabilities={

                    Capability.TOOL_CALLING,

                    Capability.VISION,

                    Capability.STREAMING,

                    Capability.JSON_MODE,

                    Capability.COMPUTER_USE,

                    Capability.PROMPT_CACHING,

                },

            ),

            ModelProfile(

                name="gemini-1.5-pro",

                context_window=2000000,

                max_output_tokens=8192,

                input_token_cost=1.25,

                output_token_cost=5.0,

                capabilities={

                    Capability.TOOL_CALLING,

                    Capability.VISION,

                    Capability.STREAMING,

                    Capability.JSON_MODE,

                    Capability.LONG_CONTEXT,

                    Capability.CONTEXT_CACHING,

                    Capability.AUDIO,

                    Capability.VIDEO,

                },

            ),

            ModelProfile(

                name="llama-3.1-70b-versatile",

                context_window=128000,

                max_output_tokens=4096,

                input_token_cost=0.59,

                output_token_cost=0.79,

                capabilities={

                    Capability.TOOL_CALLING,

                    Capability.STREAMING,

                    Capability.JSON_MODE,

                },

            ),

            ModelProfile(

                name="deepseek-coder",

                context_window=64000,

                max_output_tokens=8192,

                input_token_cost=0.14,

                output_token_cost=0.28,

                capabilities={

                    Capability.TOOL_CALLING,

                    Capability.STREAMING,

                    Capability.JSON_MODE,

                    Capability.PROMPT_CACHING,

                },

            ),

        ]

        for p in defaults:

            self._profiles[p.name] = p





        self._aliases["gpt-4"] = "gpt-4o"

        self._aliases["claude-3-5"] = "claude-3-5-sonnet"

        self._aliases["gemini-pro"] = "gemini-1.5-pro"

        self._aliases["llama3"] = "llama-3.1-70b-versatile"

        self._aliases["deepseek"] = "deepseek-coder"



    def register_profile(self, profile: ModelProfile) -> None:

        """Register a new model profile.

        Args:
            profile: The ModelProfile instance to register.
        """

        with self._lock:

            self._profiles[profile.name] = profile



    def unregister_profile(self, name: str) -> None:

        """Remove a model profile.

        Args:
            name: The model name to unregister.
        """

        with self._lock:

            self._profiles.pop(name, None)



            aliases_to_remove = [k for k, v in self._aliases.items() if v == name]

            for alias in aliases_to_remove:

                self._aliases.pop(alias, None)



    def register_alias(self, alias: str, target: str) -> None:

        """Register a model name alias mapping.

        Args:
            alias: The alias name.
            target: The target model name.
        """

        with self._lock:

            self._aliases[alias] = target



    def resolve_model(self, name: str) -> ModelProfile | None:

        """Resolve a model name or alias to a ModelProfile.

        Args:
            name: Model name or alias.
        """

        with self._lock:



            curr = name

            for _ in range(3):

                if curr in self._aliases:

                    curr = self._aliases[curr]

                else:

                    break

            return self._profiles.get(curr)



    def list_models(self) -> list[str]:

        """List all registered model profile names."""

        with self._lock:

            return list(self._profiles.keys())


"""Capability Negotiation Engine for the Forge Universal AI Runtime."""



from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

from forgecli.providers.provider_capabilities import Capability
from forgecli.runtime_core.errors import ConfigurationError

if TYPE_CHECKING:

    from forgecli.registry.model_registry import ModelRegistry



logger = logging.getLogger("forge.negotiator")





class NegotiationResult(BaseModel):

    """Result of a capability negotiation process."""



    model_name: str

    supported: set[Capability] = Field(default_factory=set)

    unsupported: set[Capability] = Field(default_factory=set)

    is_compatible: bool

    adjusted_features: dict[str, bool] = Field(default_factory=dict)





class CapabilityNegotiator:

    """Evaluates, negotiates, and adapts requested capabilities against model profiles."""



    def __init__(self, model_registry: ModelRegistry) -> None:

        """Initialize the CapabilityNegotiator.

        Args:
            model_registry: The ModelRegistry catalog.
        """

        self._registry = model_registry



    def negotiate(

        self,

        model_name: str,

        required_capabilities: set[Capability],

        optional_capabilities: set[Capability] | None = None,

    ) -> NegotiationResult:

        """Negotiate capability fulfillment for a target model.

        Args:
            model_name: The name or alias of the target model.
            required_capabilities: Capabilities that must be supported.
            optional_capabilities: Capabilities that are preferred but not mandatory.

        Returns:
            A NegotiationResult detailing compatibility and feature adjustments.

        Raises:
            ConfigurationError: If the target model cannot be resolved.
        """

        profile = self._registry.resolve_model(model_name)

        if not profile:

            raise ConfigurationError(f"Cannot negotiate capabilities: Model '{model_name}' not resolved.")



        model_caps = profile.capabilities

        optional = optional_capabilities or set()



        supported_required = required_capabilities.intersection(model_caps)

        unsupported_required = required_capabilities.difference(model_caps)



        supported_optional = optional.intersection(model_caps)



        is_compatible = len(unsupported_required) == 0





        adjusted_features = {}



        if Capability.STREAMING in (required_capabilities | optional):

            adjusted_features["streaming"] = Capability.STREAMING in model_caps



        if Capability.JSON_MODE in (required_capabilities | optional):

            adjusted_features["json_mode"] = Capability.JSON_MODE in model_caps



        return NegotiationResult(

            model_name=profile.name,

            supported=supported_required | supported_optional,

            unsupported=unsupported_required,

            is_compatible=is_compatible,

            adjusted_features=adjusted_features,

        )



    def find_compatible_model(

        self,

        required_capabilities: set[Capability],

        preferred_family: str | None = None,

    ) -> str | None:

        """Find a model name in the registry that satisfies all required capabilities.

        Args:
            required_capabilities: The capabilities required.
            preferred_family: Optional prefix match for model family (e.g. 'gpt' or 'claude').
        """

        for model_name in self._registry.list_models():

            if preferred_family and not model_name.startswith(preferred_family):

                continue

            profile = self._registry.resolve_model(model_name)

            if profile and required_capabilities.issubset(profile.capabilities):

                return model_name

        return None


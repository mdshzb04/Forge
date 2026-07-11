"""Capability Negotiation Middleware for the Forge middleware engine."""



from __future__ import annotations

import contextlib
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING

from forgecli.middleware.base import Middleware
from forgecli.providers.provider_capabilities import Capability
from forgecli.runtime_core.errors import ConfigurationError

if TYPE_CHECKING:

    from forgecli.middleware.context import RequestContext, ResponseContext
    from forgecli.negotiator.negotiator import CapabilityNegotiator





class CapabilityNegotiationMiddleware(Middleware):

    """Pipeline middleware that negotiates capabilities of the target model dynamically."""



    def __init__(self, negotiator: CapabilityNegotiator) -> None:

        """Initialize the CapabilityNegotiationMiddleware.

        Args:
            negotiator: The CapabilityNegotiator engine.
        """

        self._negotiator = negotiator



    @property

    def priority(self) -> int:

        """Priority ordering value (higher runs earlier)."""

        return 750



    async def __call__(

        self,

        request: RequestContext,

        call_next: Callable[[RequestContext], Awaitable[ResponseContext]],

    ) -> ResponseContext:

        """Intercept and negotiate capabilities for the target model.

        Args:
            request: The RequestContext object.
            call_next: Next pipeline runner callback.
        """

        required = set()

        optional = set()



        if request.ai_request.stream:

            optional.add(Capability.STREAMING)





        req_caps = request.metadata.get("required_capabilities", [])

        for cap in req_caps:

            if isinstance(cap, str):

                with contextlib.suppress(ValueError):

                    required.add(Capability(cap))




        opt_caps = request.metadata.get("optional_capabilities", [])

        for cap in opt_caps:

            if isinstance(cap, str):

                with contextlib.suppress(ValueError):

                    optional.add(Capability(cap))






        res = self._negotiator.negotiate(

            model_name=request.ai_request.model_name,

            required_capabilities=required,

            optional_capabilities=optional,

        )



        if not res.is_compatible:



            alt_model = self._negotiator.find_compatible_model(required)

            if alt_model:

                request.ai_request.model_name = alt_model

                res = self._negotiator.negotiate(

                    model_name=alt_model,

                    required_capabilities=required,

                    optional_capabilities=optional,

                )

            else:

                raise ConfigurationError(

                    f"Model '{request.ai_request.model_name}' does not support required capabilities: "

                    f"{[c.value for c in res.unsupported]}"

                )





        if "streaming" in res.adjusted_features:

            request.ai_request.stream = res.adjusted_features["streaming"]



        request.metadata["negotiation_result"] = res



        return await call_next(request)


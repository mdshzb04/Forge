"""Token budget planning and calculations."""



from __future__ import annotations

from dataclasses import dataclass

from forgecli.registry.model_registry import ModelRegistry


@dataclass

class TokenBudget:

    """Represents the token limits for a specific request."""



    model_name: str

    max_context_tokens: int

    requested_completion_tokens: int

    available_context_tokens: int

    reserved_system_tokens: int = 500





class TokenPlanner:

    """Calculates token budgets based on model limits."""



    def __init__(self, registry: ModelRegistry | None = None) -> None:

        self.registry = registry or ModelRegistry()



    def plan_budget(self, model_name: str, requested_max_tokens: int | None = None) -> TokenBudget:

        """Calculate the available context window size for a given model."""

        profile = self.registry.resolve_model(model_name)





        max_context = profile.context_window if profile else 8192

        max_completion = profile.max_output_tokens if profile else 4096





        completion_tokens = requested_max_tokens if requested_max_tokens else (max_completion or 2048)





        reserved_system = 500

        available_context = max_context - completion_tokens - reserved_system



        if available_context < 0:

            available_context = 0



        return TokenBudget(

            model_name=model_name,

            max_context_tokens=max_context,

            requested_completion_tokens=completion_tokens,

            available_context_tokens=available_context,

            reserved_system_tokens=reserved_system,

        )



    def estimate_tokens(self, text: str) -> int:
        """Estimate tokens using the official tokenizers if available, falling back to heuristics."""
        from forgecli.optimizer.token_estimator import TokenEstimator
        return TokenEstimator.estimate_tokens(text)


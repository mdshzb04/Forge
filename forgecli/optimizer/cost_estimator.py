"""Token, Cost, and Latency Estimator.

Estimates prompt and completion tokens, matches them to provider price structures,
and estimates response latency budgets.
"""



from __future__ import annotations

from typing import ClassVar


class TokenCostEstimator:

    """Estimates tokens, costs, and expected latency across major LLM providers."""





    PROVIDER_PRICING: ClassVar[dict[str, tuple[float, float]]] = {

        "gpt-4o": (5.0, 15.0),

        "gpt-4-turbo": (10.0, 30.0),

        "gpt-3.5-turbo": (0.50, 1.50),

        "claude-3-5-sonnet": (3.0, 15.0),

        "claude-3-opus": (15.0, 75.0),

        "claude-3-haiku": (0.25, 1.25),

        "gemini-1.5-pro": (1.25, 5.0),

        "gemini-1.5-flash": (0.075, 0.30),

        "deepseek-coder": (0.14, 0.28),

        "llama-3-70b": (0.60, 0.60),

        "ollama": (0.0, 0.0),

    }



    @staticmethod
    def estimate_tokens(text: str, model_name: str = "claude-3-5-sonnet") -> int:
        """Estimate tokens using the official tokenizers if available, falling back to heuristics."""
        from forgecli.optimizer.token_estimator import TokenEstimator
        return TokenEstimator.estimate_tokens(text, model_name)



    def estimate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:

        """Calculate the cost in USD based on model pricing."""



        matched_model = "gpt-3.5-turbo"

        for key in self.PROVIDER_PRICING:

            if key in model.lower():

                matched_model = key

                break



        input_rate, output_rate = self.PROVIDER_PRICING[matched_model]

        input_cost = (input_tokens / 1_000_000) * input_rate

        output_cost = (output_tokens / 1_000_000) * output_rate

        return input_cost + output_cost



    def estimate_latency(self, model: str, input_tokens: int, expected_output_tokens: int) -> float:

        """Estimate completion latency in seconds.

        Heuristic: base queue overhead + token throughput (dependent on model size).
        """



        base_overhead = 0.5





        speed_tps = 40.0

        if "flash" in model.lower() or "haiku" in model.lower() or "deepseek" in model.lower():

            speed_tps = 90.0

        elif "opus" in model.lower() or "gpt-4" in model.lower():

            speed_tps = 25.0



        throughput_time = expected_output_tokens / speed_tps



        input_overhead = input_tokens / 50000.0



        return base_overhead + throughput_time + input_overhead


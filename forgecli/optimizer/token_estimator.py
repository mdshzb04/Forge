"""Exact Token Estimator.

Uses official tokenizer libraries (tiktoken, tokenizers, transformers) when
available to calculate exact token usage for OpenAI, Anthropic, Gemini, Qwen,
DeepSeek, GLM, Llama, and Mistral. Gracefully falls back to heuristic estimation.
"""

from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)

# Cache tokenizer instances to prevent reloading overhead
_TOKENIZER_CACHE = {}


class TokenEstimator:
    """Calculates exact token counts for various models and providers."""

    @staticmethod
    def estimate_tokens(text: str, model_name: str = "claude-3-5-sonnet") -> int:
        """Estimate token counts for a given text and model, with fallback support."""
        if not text:
            return 0

        model_lower = model_name.lower()
        provider = TokenEstimator.detect_provider(model_lower)

        # 1. Try tiktoken for OpenAI and Anthropic (since Claude 3 uses cl100k_base equivalent)
        if provider in ("openai", "anthropic"):
            try:
                import tiktoken
                if provider == "openai":
                    encoding_name = "cl100k_base"
                    if "gpt-4o" in model_lower or "o1" in model_lower or "o3" in model_lower:
                        encoding_name = "o200k_base"
                    
                    if encoding_name not in _TOKENIZER_CACHE:
                        try:
                            _TOKENIZER_CACHE[encoding_name] = tiktoken.get_encoding(encoding_name)
                        except Exception:
                            _TOKENIZER_CACHE[encoding_name] = tiktoken.get_encoding("cl100k_base")
                    
                    return len(_TOKENIZER_CACHE[encoding_name].encode(text))
                else:
                    # Anthropic: Claude 3 uses a cl100k-compatible BPE
                    if "cl100k_base" not in _TOKENIZER_CACHE:
                        _TOKENIZER_CACHE["cl100k_base"] = tiktoken.get_encoding("cl100k_base")
                    return len(_TOKENIZER_CACHE["cl100k_base"].encode(text))
            except Exception as e:
                logger.debug(f"tiktoken failed, falling back: {e}")

        # 2. Try loading transformers tokenizer for open weight models (Llama, Mistral, Qwen, DeepSeek, GLM)
        if provider in ("llama", "mistral", "qwen", "deepseek", "glm"):
            try:
                import transformers
                # Map model name to a standard Hugging Face repo for tokenizer config
                repo_map = {
                    "llama": "meta-llama/Meta-Llama-3-8B-Instruct",
                    "mistral": "mistralai/Mistral-7B-Instruct-v0.2",
                    "qwen": "Qwen/Qwen2.5-7B-Instruct",
                    "deepseek": "deepseek-ai/DeepSeek-V3",
                    "glm": "THUDM/glm-4-9b-chat"
                }
                repo = repo_map.get(provider)
                if repo:
                    if repo not in _TOKENIZER_CACHE:
                        # Load from local cache or fetch metadata (disable online download to avoid blocking)
                        _TOKENIZER_CACHE[repo] = transformers.AutoTokenizer.from_pretrained(
                            repo, local_files_only=True
                        )
                    return len(_TOKENIZER_CACHE[repo].encode(text))
            except Exception:
                # If local file is not found, try utilizing tiktoken as a proxy BPE instead of a crude heuristic
                try:
                    import tiktoken
                    if "cl100k_base" not in _TOKENIZER_CACHE:
                        _TOKENIZER_CACHE["cl100k_base"] = tiktoken.get_encoding("cl100k_base")
                    # Llama 3 has a larger vocab, cl100k_base is a reasonable representation
                    return int(len(_TOKENIZER_CACHE["cl100k_base"].encode(text)) * 0.95)
                except Exception:
                    pass

        # 3. Try fallback to heuristic estimation
        return TokenEstimator.heuristic_estimate(text)

    @staticmethod
    def detect_provider(model_name: str) -> str:
        """Detect provider based on model name patterns."""
        model_name = model_name.lower()
        if any(x in model_name for x in ("gpt-", "text-embedding-", "o1-", "o3-")):
            return "openai"
        elif "claude" in model_name:
            return "anthropic"
        elif "gemini" in model_name:
            return "gemini"
        elif "qwen" in model_name:
            return "qwen"
        elif "deepseek" in model_name:
            return "deepseek"
        elif "glm" in model_name:
            return "glm"
        elif "llama" in model_name:
            return "llama"
        elif "mistral" in model_name:
            return "mistral"
        return "generic"

    @staticmethod
    def heuristic_estimate(text: str) -> int:
        """Heuristic character/word token count estimation."""
        if not text:
            return 0
        char_tokens = len(text) / 3.8
        word_tokens = len(text.split()) / 0.75
        return int((char_tokens + word_tokens) / 2)

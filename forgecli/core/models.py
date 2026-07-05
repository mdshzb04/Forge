"""Modular registry for all supported AI models in ForgeCLI."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

ModelTier = Literal["latest", "recommended", "normal", "legacy", "deprecated"]


@dataclass(frozen=True)
class ModelDef:
    id: str
    display_name: str
    tier: ModelTier
    provider: str  # Lowercase provider name, e.g., 'openai', 'groq'


# Single source of truth for the model catalog
MODEL_CATALOG: list[ModelDef] = [
    # ---------------------------------------------------------------------------
    # OpenAI
    # ---------------------------------------------------------------------------
    ModelDef(id="gpt-5.5", display_name="GPT-5.5", tier="latest", provider="openai"),
    ModelDef(id="gpt-5", display_name="GPT-5", tier="recommended", provider="openai"),
    ModelDef(id="gpt-5-mini", display_name="GPT-5 Mini", tier="normal", provider="openai"),
    ModelDef(id="gpt-4.1", display_name="GPT-4.1", tier="legacy", provider="openai"),
    ModelDef(id="gpt-4.1-mini", display_name="GPT-4.1 Mini", tier="legacy", provider="openai"),
    ModelDef(id="gpt-4o", display_name="GPT-4o", tier="legacy", provider="openai"),
    ModelDef(id="gpt-4o-mini", display_name="GPT-4o Mini", tier="legacy", provider="openai"),
    ModelDef(id="gpt-4-turbo", display_name="GPT-4 Turbo", tier="legacy", provider="openai"),
    ModelDef(id="o1", display_name="o1", tier="legacy", provider="openai"),
    ModelDef(id="o1-preview", display_name="o1 Preview", tier="legacy", provider="openai"),
    ModelDef(id="o1-mini", display_name="o1 Mini", tier="legacy", provider="openai"),
    # ---------------------------------------------------------------------------
    # Anthropic
    # ---------------------------------------------------------------------------
    ModelDef(
        id="claude-opus-4.8", display_name="Claude Opus 4.8", tier="latest", provider="anthropic"
    ),
    ModelDef(
        id="claude-opus-4.6", display_name="Claude Opus 4.6", tier="latest", provider="anthropic"
    ),
    ModelDef(
        id="claude-sonnet-4.6",
        display_name="Claude Sonnet 4.6",
        tier="recommended",
        provider="anthropic",
    ),
    ModelDef(
        id="claude-sonnet-4.5",
        display_name="Claude Sonnet 4.5",
        tier="legacy",
        provider="anthropic",
    ),
    ModelDef(
        id="claude-haiku-4.5", display_name="Claude Haiku 4.5", tier="legacy", provider="anthropic"
    ),
    ModelDef(
        id="claude-3-5-sonnet-latest",
        display_name="Claude 3.5 Sonnet",
        tier="legacy",
        provider="anthropic",
    ),
    ModelDef(
        id="claude-3-5-haiku-latest",
        display_name="Claude 3.5 Haiku",
        tier="legacy",
        provider="anthropic",
    ),
    ModelDef(
        id="claude-3-opus-latest", display_name="Claude 3 Opus", tier="legacy", provider="anthropic"
    ),
    # ---------------------------------------------------------------------------
    # Google Gemini
    # ---------------------------------------------------------------------------
    ModelDef(
        id="gemini-2.5-pro", display_name="Gemini 2.5 Pro", tier="recommended", provider="google"
    ),
    ModelDef(
        id="gemini-2.5-flash",
        display_name="Gemini 2.5 Flash",
        tier="recommended",
        provider="google",
    ),
    ModelDef(
        id="gemini-2.5-flash-lite",
        display_name="Gemini 2.5 Flash Lite",
        tier="normal",
        provider="google",
    ),
    ModelDef(
        id="gemini-2.0-flash", display_name="Gemini 2.0 Flash", tier="legacy", provider="google"
    ),
    ModelDef(id="gemini-1.5-pro", display_name="Gemini 1.5 Pro", tier="legacy", provider="google"),
    ModelDef(
        id="gemini-1.5-flash", display_name="Gemini 1.5 Flash", tier="legacy", provider="google"
    ),
    ModelDef(
        id="gemini-2.0-flash-exp",
        display_name="Gemini 2.0 Flash Exp",
        tier="legacy",
        provider="google",
    ),
    # ---------------------------------------------------------------------------
    # OpenRouter
    # ---------------------------------------------------------------------------
    ModelDef(id="glm-5.2", display_name="GLM 5.2", tier="normal", provider="openrouter"),
    ModelDef(id="deepseek-v3", display_name="DeepSeek V3", tier="normal", provider="openrouter"),
    ModelDef(id="deepseek-r1", display_name="DeepSeek R1", tier="normal", provider="openrouter"),
    ModelDef(id="qwen3-coder", display_name="Qwen3 Coder", tier="normal", provider="openrouter"),
    ModelDef(id="qwen3-32b", display_name="Qwen3 32B", tier="normal", provider="openrouter"),
    ModelDef(id="kimi-k2", display_name="Kimi K2", tier="normal", provider="openrouter"),
    ModelDef(
        id="llama-4-maverick", display_name="Llama 4 Maverick", tier="normal", provider="openrouter"
    ),
    ModelDef(
        id="llama-4-scout", display_name="Llama 4 Scout", tier="normal", provider="openrouter"
    ),
    ModelDef(
        id="llama-3.3-70b", display_name="Llama 3.3 70B", tier="normal", provider="openrouter"
    ),
    ModelDef(id="gemma-3", display_name="Gemma 3", tier="normal", provider="openrouter"),
    ModelDef(id="devstral", display_name="Devstral", tier="normal", provider="openrouter"),
    ModelDef(id="codestral", display_name="Codestral", tier="normal", provider="openrouter"),
    ModelDef(id="phi-4", display_name="Phi-4", tier="normal", provider="openrouter"),
    ModelDef(
        id="mistral-large", display_name="Mistral Large", tier="normal", provider="openrouter"
    ),
    # ---------------------------------------------------------------------------
    # Groq
    # ---------------------------------------------------------------------------
    ModelDef(id="llama-4-scout", display_name="Llama 4 Scout", tier="normal", provider="groq"),
    ModelDef(id="deepseek-r1", display_name="DeepSeek R1", tier="normal", provider="groq"),
    ModelDef(id="qwen3-32b", display_name="Qwen3 32B", tier="normal", provider="groq"),
    ModelDef(id="gemma-3", display_name="Gemma 3", tier="normal", provider="groq"),
    # ---------------------------------------------------------------------------
    # Mistral
    # ---------------------------------------------------------------------------
    ModelDef(id="mistral-large", display_name="Mistral Large", tier="normal", provider="mistral"),
    ModelDef(id="magistral", display_name="Magistral", tier="normal", provider="mistral"),
    ModelDef(id="mistral-small", display_name="Mistral Small", tier="normal", provider="mistral"),
    ModelDef(id="codestral", display_name="Codestral", tier="normal", provider="mistral"),
    # ---------------------------------------------------------------------------
    # MiniMax
    # ---------------------------------------------------------------------------
    ModelDef(
        id="abab6.5g-chat", display_name="Abab 6.5G Chat", tier="recommended", provider="minimax"
    ),
    ModelDef(id="abab6.5-chat", display_name="Abab 6.5 Chat", tier="legacy", provider="minimax"),
    # ---------------------------------------------------------------------------
    # xAI (Grok)
    # ---------------------------------------------------------------------------
    ModelDef(id="grok-2", display_name="Grok 2", tier="recommended", provider="xai"),
    ModelDef(id="grok-beta", display_name="Grok Beta", tier="latest", provider="xai"),
    # ---------------------------------------------------------------------------
    # Together AI
    # ---------------------------------------------------------------------------
    ModelDef(
        id="llama-3.1-70b", display_name="Llama 3.1 70B", tier="recommended", provider="together"
    ),
    ModelDef(
        id="llama-3.1-405b", display_name="Llama 3.1 405B", tier="latest", provider="together"
    ),
    # ---------------------------------------------------------------------------
    # Fireworks AI
    # ---------------------------------------------------------------------------
    ModelDef(
        id="llama-3.1-70b", display_name="Llama 3.1 70B", tier="recommended", provider="fireworks"
    ),
    ModelDef(
        id="llama-3.1-405b", display_name="Llama 3.1 405B", tier="latest", provider="fireworks"
    ),
    # ---------------------------------------------------------------------------
    # Cohere
    # ---------------------------------------------------------------------------
    ModelDef(id="command-r-plus", display_name="Command R+", tier="recommended", provider="cohere"),
    ModelDef(id="command-r", display_name="Command R", tier="normal", provider="cohere"),
    # ---------------------------------------------------------------------------
    # NVIDIA NIM
    # ---------------------------------------------------------------------------
    ModelDef(
        id="llama-3.1-70b", display_name="Llama 3.1 70B", tier="recommended", provider="nvidia"
    ),
    ModelDef(id="llama-3.1-405b", display_name="Llama 3.1 405B", tier="latest", provider="nvidia"),
    # ---------------------------------------------------------------------------
    # Ollama
    # ---------------------------------------------------------------------------
    ModelDef(id="llama3", display_name="Llama 3", tier="normal", provider="ollama"),
    # ---------------------------------------------------------------------------
    # LM Studio
    # ---------------------------------------------------------------------------
    ModelDef(id="local-model", display_name="Local Model", tier="normal", provider="lmstudio"),
    # ---------------------------------------------------------------------------
    # vLLM
    # ---------------------------------------------------------------------------
    ModelDef(id="local-model", display_name="Local Model", tier="normal", provider="vllm"),
]


def get_model_def(model_id: str, provider: str | None = None) -> ModelDef | None:
    """Retrieve the model definition by model ID, optionally filtering by provider."""
    model_id_lower = model_id.lower().strip()
    provider_lower = provider.lower().strip() if provider else None
    for m in MODEL_CATALOG:
        if m.id == model_id_lower and (provider_lower is None or m.provider == provider_lower):
            return m
    return None


def get_display_name(model_id: str, provider: str | None = None) -> str:
    """Get the friendly display name for a model, defaulting to the ID itself."""
    m = get_model_def(model_id, provider)
    return m.display_name if m else model_id

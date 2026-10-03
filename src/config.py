from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from model_provider import ProviderConfig


@dataclass
class LabConfig:
    """Student TODO: define the shared configuration for the lab.

    Hints:
    - Keep paths for the repo root, dataset directory, and state directory.
    - Add compact-memory settings such as threshold and number of messages to keep.
    - Add provider settings for `openai`, `custom`, `gemini`, `anthropic`, `ollama`, and `openrouter`.
    """

    base_dir: Path
    data_dir: Path
    state_dir: Path
    compact_threshold_tokens: int
    compact_keep_messages: int
    model: ProviderConfig
    judge_model: ProviderConfig


import os
from dotenv import load_dotenv

def load_config(base_dir: Path | None = None) -> LabConfig:
    """Load environment variables and return a LabConfig."""

    root = (base_dir or Path(__file__).resolve().parent.parent).resolve()

    load_dotenv(root / ".env")

    state_dir = root / "state"
    state_dir.mkdir(parents=True, exist_ok=True)

    provider = os.getenv("LLM_PROVIDER", "openai")
    model_name = os.getenv("LLM_MODEL", "gpt-4o-mini")
    
    # Simple logic to get the correct API key / Base URL
    api_key = os.getenv(f"{provider.upper()}_API_KEY")
    if not api_key:
        api_key = os.getenv("OPENAI_API_KEY") if provider in ["openai", "custom", "openrouter"] else None

    base_url = os.getenv(f"{provider.upper()}_BASE_URL")

    model = ProviderConfig(
        provider=provider,
        model_name=model_name,
        temperature=0.0,
        api_key=api_key,
        base_url=base_url
    )

    # For simplicity, use the same model as judge model
    judge_model = ProviderConfig(
        provider=provider,
        model_name=model_name,
        temperature=0.0,
        api_key=api_key,
        base_url=base_url
    )

    return LabConfig(
        base_dir=root,
        data_dir=root / "data",
        state_dir=state_dir,
        compact_threshold_tokens=500,
        compact_keep_messages=4,
        model=model,
        judge_model=judge_model
    )

"""Canonical model catalog for the v0.2 comparison demo."""
from __future__ import annotations

from dataclasses import dataclass, asdict


@dataclass(frozen=True)
class DemoModel:
    model_id: str
    label: str
    mode: str  # naive | agentic
    router_model: str | None = None
    synth_model: str | None = None
    provider: str = "openrouter"

    def to_dict(self) -> dict:
        return asdict(self)


NAIVE_MODELS: list[DemoModel] = [
    # Naive RAG models from SLM_COMPARISON.md
    # Ordered by quality score (best first)
    DemoModel("qwen/qwen3-8b", "Qwen3 8B", "naive"),
    DemoModel("qwen/qwen3-14b", "Qwen3 14B", "naive"),
    DemoModel("nvidia/nemotron-3-nano-30b-a3b", "NVIDIA Nemotron Nano 30B", "naive"),
    DemoModel("ibm-granite/granite-4.1-8b", "IBM Granite 8B", "naive"),
    DemoModel("mistralai/ministral-8b-instruct-2501", "Mistral Ministral 8B", "naive"),
    DemoModel("mistralai/mistral-7b-instruct-2407", "Mistral 7B v3", "naive"),
]


AGENTIC_ROUTERS: list[DemoModel] = [
    # Agentic router models from SLM_COMPARISON.md
    # Best routers ranked by quality score
    DemoModel("qwen/qwen3-14b", "Qwen3 14B (Router)", "agentic"),
    DemoModel("qwen/qwen3-8b", "Qwen3 8B (Router)", "agentic"),
    DemoModel("google/gemma-4-31b-it", "Gemma 4 31B (Router)", "agentic"),
    DemoModel("google/gemma-4-26b-it", "Gemma 4 26B (Router)", "agentic"),
]


AGENTIC_SYNTHS: list[DemoModel] = [
    # Agentic synthesizer models from SLM_COMPARISON.md
    # Best performers ranked first
    DemoModel("qwen/qwen3-8b", "Qwen3 8B (Synth)", "agentic"),
    DemoModel("qwen/qwen3-14b", "Qwen3 14B (Synth)", "agentic"),
    DemoModel("mistralai/ministral-8b-instruct-2501", "Mistral Ministral 8B (Synth)", "agentic"),
    DemoModel("mistralai/mistral-7b-instruct-2407", "Mistral 7B v3 (Synth)", "agentic"),
    DemoModel("nvidia/nemotron-3-nano-30b-a3b", "NVIDIA Nemotron Nano (Synth)", "agentic"),
    DemoModel("ibm-granite/granite-4.1-8b", "IBM Granite 8B (Synth)", "agentic"),
]


def catalog() -> dict[str, list[dict]]:
    return {
        "naive": [m.to_dict() for m in NAIVE_MODELS],
        "agentic_routers": [m.to_dict() for m in AGENTIC_ROUTERS],
        "agentic_synths": [m.to_dict() for m in AGENTIC_SYNTHS],
    }


def models_for_mode(mode: str) -> list[DemoModel]:
    return NAIVE_MODELS if mode == "naive" else AGENTIC_ROUTERS


def routers_for_agentic() -> list[DemoModel]:
    return AGENTIC_ROUTERS


def synths_for_agentic() -> list[DemoModel]:
    return AGENTIC_SYNTHS


def find_model(mode: str, model_id: str) -> DemoModel | None:
    pool = NAIVE_MODELS if mode == "naive" else (AGENTIC_ROUTERS + AGENTIC_SYNTHS)
    for model in pool:
        if model.model_id == model_id:
            return model
    return None


def default_model_id(mode: str) -> str:
    models = models_for_mode(mode)
    return models[0].model_id if models else ""


def default_agentic_router() -> str:
    return AGENTIC_ROUTERS[0].model_id if AGENTIC_ROUTERS else ""


def default_agentic_synths() -> list[str]:
    return [AGENTIC_SYNTHS[0].model_id] if AGENTIC_SYNTHS else []

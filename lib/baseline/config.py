"""Env-driven config for the naive baseline."""
from __future__ import annotations
import os
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent  # = chatbot_v0.2/lib
BUNDLE = ROOT.parent  # = chatbot_v0.2

def _resolve_data_dir() -> Path:
    """Find the data directory inside the bundled chatbot_v0.2 tree."""
    configured = os.getenv("ACTIVIITY_DATA_DIR")
    if configured:
        p = Path(configured)
        if p.exists():
            return p
    # Try bundle path (sibling to lib/)
    bundle = BUNDLE / "data"
    if bundle.exists():
        return bundle
    return bundle

DATA_DIR = _resolve_data_dir()

def _resolve_persist_dir() -> Path:
    """Find the index persist directory — bundle path first."""
    configured = os.getenv("ACTIVIITY_BASELINE_PERSIST")
    if configured:
        p = Path(configured)
        p.mkdir(parents=True, exist_ok=True)
        return p
    # Bundle path (sibling to lib/)
    bundle = BUNDLE / "baseline" / ".index"
    bundle.mkdir(parents=True, exist_ok=True)
    return bundle

PERSIST_DIR = _resolve_persist_dir()


@dataclass(frozen=True)
class Cfg:
    llm_provider: str = os.getenv("LLM_PROVIDER", "openrouter")
    openrouter_api_key: str = os.getenv("OPENROUTER_API_KEY", "")
    openrouter_model: str = os.getenv("LLM_MODEL", "ibm-granite/granite-4.1-8b")
    ollama_base_url: str = os.getenv("OLLAMA_URL", "http://localhost:11434")
    ollama_llm_model: str = os.getenv("OLLAMA_LLM_MODEL", "qwen2.5:14b-instruct")
    llm_temperature: float = float(os.getenv("LLM_TEMPERATURE", "0.2"))
    embed_provider: str = os.getenv("EMBED_PROVIDER", "ollama")
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_embed_model: str = os.getenv("OPENAI_EMBED_MODEL", "text-embedding-3-small")
    ollama_embed_model: str = os.getenv("OLLAMA_EMBED_MODEL", "bge-m3")
    chunk_size: int = int(os.getenv("CHUNK_SIZE", "512"))
    chunk_overlap: int = int(os.getenv("CHUNK_OVERLAP", "64"))
    top_k: int = int(os.getenv("TOP_K", "5"))
    slm_mode: bool = os.getenv("SLM_MODE", "0") == "1"
    qa_prompt_fr: str = (
        "Contexte ci-dessous :\n---------------------\n{context_str}\n"
        "---------------------\nAvant toute recherche, si la requête est uniquement une salutation ou un message bref sans demande (ex. 'bonjour', 'salut', 'merci'), réponds : « Bonjour. Posez une question de management ou sélectionnez une Fiche UA pour que je puisse aider. »\n"
        "En te fondant UNIQUEMENT sur ce contexte (et non sur tes connaissances générales), réponds à la question en français, de façon structurée et concise. Si l'information n'est pas présente dans le contexte, dis explicitement : « Je ne trouve pas cette information dans la base Activiity. »\n"
        "Question : {query_str}\nRéponse :"
    )
    slm_qa_prompt_fr: str = (
        "Tu es un assistant RAG. Tu réponds UNIQUEMENT à partir du contexte ci-dessous.\n"
        "---------------------\n"
        "{context_str}\n"
        "---------------------\n"
        "RÈGLES:\n"
        "- Si la requête est une salutation → réponds « Bonjour. Posez une question de management. »\n"
        "- Sinon, réponds UNIQUEMENT à partir des faits du contexte (pas de connaissances générales)\n"
        "- Si le contexte ne contient PAS la réponse → « Je ne trouve pas cette information dans la base Activiity. »\n"
        "- Si le contexte mentionne un nombre (ex: « 3 principes », « 4 sources »), reproduis-le EXACTEMENT avec chaque item listé\n"
        "- Pas de phrase d'introduction (« D'après le contexte… »), pas de commentaire, pas de conseil ajouté\n"
        "- MAX: 3 phrases. Concis et factuel.\n\n"
        "Question: {query_str}\nRéponse:"
    )


CFG = Cfg()
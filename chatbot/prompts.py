"""French prompts for the Conversational Agentic RAG.

Self-contained — no dependency on activiity.prompts.
Based on the original SLM prompts, adapted for multi-turn chat.
"""
from __future__ import annotations


# ---------------------------------------------------------------------------
# Base SLM prompts (from activiity defaults, bundled for independence)
# ---------------------------------------------------------------------------

SLM_SYSTEM_FR = (
    "Tu es Activiity, assistant management/coaching.\n"
    "RÈGLES:\n"
    "1) Choisis le bon outil selon la question.\n"
    "2) Réponds ONLY avec le contexte récupéré.\n"
    "3) Si pas de réponse → 'Je ne trouve pas cette information.'\n"
    "4) Cite l'UA source.\n"
    "MAX: 3 phrases, 100 mots."
)

SLM_QA_FR = """Contexte: {context_str}

Question: {query_str}
Réponds en français avec SEULEMENT les faits du contexte.
Si pas de réponse → 'Je ne trouve pas cette information.'
MAX: 3 phrases."""

SLM_REFINE_FR = (
    "Q: {query_str}\n"
    "Réponse: {existing_answer}\n"
    "Nouveau contexte: {context_msg}\n"
    "Intègre les faits nouveaux ONLY. Sinon garde réponse existante."
    "MAX: 3 phrases."
)

REFUSAL_FR = (
    "Je ne trouve pas cette information dans la base Activiity. "
    "Pouvez-vous reformuler ou préciser l'UA concernée ?"
)

TOOL_DESC_GLOBAL = (
    "Recherche dans l'ensemble du corpus Activiity (toutes UAs confondues). "
    "À utiliser quand la question est transverse, qu'aucune UA n'est "
    "spécifiquement identifiable, ou pour compléter un résultat partiel."
)

UA_TITLES = {
    "UA-1": "Délégation",
    "UA-2": "Délégation via Sourcing",
    "UA-3": "Nourrir le plaisir de travailler",
    "UA-4": "Motiver",
    "UA-5": "Mauvaise ambiance",
    "UA-6": "Écouter et Dialoguer",
    "UA-7": "Changer les comportements",
    "UA-8": "Agir sur les habitudes",
    "UA-9": "Manager",
    "UA-10": "Compétences commerciales",
}


def tool_desc_ua(ua_id: str) -> str:
    title = UA_TITLES.get(ua_id, "")
    return (
        f"Recherche ciblée dans l'UA {ua_id} ({title}). À utiliser quand "
        f"la question porte spécifiquement sur le thème « {title} »."
    )


# ---------------------------------------------------------------------------
# Chat-specific prompts
# ---------------------------------------------------------------------------

def make_chat_system_prompt(history_text: str = "", max_tokens: int = 200) -> str:
    """Build the system prompt for a conversational turn.

    Includes chat history so the LLM maintains context across turns.
    """
    base = SLM_SYSTEM_FR.rstrip()

    if history_text:
        hist_block = (
            "Historique de conversation récent :\n"
            f"{history_text}\n"
            "Continuer la conversation de façon cohérente.\n\n"
        )
    else:
        hist_block = ""

    return f"{base}\n\n{hist_block}MAX: {max_tokens} mots."


CHAT_QA_FR = """Contexte :
{context_str}

Historique :
{history_text}

Question de l'utilisateur : {query_str}

Réponds en français, de façon conversationnelle mais précise, en t'appuyant
UNIQUEMENT sur le contexte récupéré. Si tu n'as pas la réponse →
"Je ne trouve pas cette information dans la base Activiity."
MAX: 3 phrases."""


CHAT_REFINE_FR = (
    "Q: {query_str}\n"
    "Réponse actuelle: {existing_answer}\n"
    "Nouveau contexte: {context_msg}\n"
    "Complète ou corrige la réponse avec les faits nouveaux UNIQUEMENT. "
    "Sinon garde la réponse existante. MAX: 3 phrases."
)

CHAT_REFUSAL_FR = (
    "Je n'ai pas trouvé d'information pertinente dans la base Activiity. "
    "Tu peux préciser ta question ou me demander autre chose ?"
)


# ---------------------------------------------------------------------------
# Prompt registry (for debugging / inspection)
# ---------------------------------------------------------------------------

PROMPT_REGISTRY = {
    "slm_system": SLM_SYSTEM_FR,
    "slm_qa": SLM_QA_FR,
    "slm_refine": SLM_REFINE_FR,
    "refusal": REFUSAL_FR,
    "chat_system": make_chat_system_prompt,   # function, not string
    "chat_qa": CHAT_QA_FR,
    "chat_refine": CHAT_REFINE_FR,
    "chat_refusal": CHAT_REFUSAL_FR,
}
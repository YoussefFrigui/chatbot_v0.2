"""NaiveRagService — calls OpenRouter directly (avoids llama-index LLM bugs)."""
from __future__ import annotations
import json
import os
import time
import traceback
from collections import Counter
from dataclasses import dataclass

import httpx

from llama_index.core.callbacks import CallbackManager, TokenCountingHandler
from llama_index.core import Settings as LISettings

from lib.baseline.config import CFG
from lib.baseline.index import build_or_load


OR_API = "https://openrouter.ai/api/v1/chat/completions"


@dataclass
class NaiveResult:
    answer: str
    tools_called: list[str]
    retrieved_nodes: list
    tokens_in: int
    tokens_out: int
    iterations: int
    model_name: str
    embed_model: str
    ttft_s: float | None


def _build_prompt(question: str, context: str) -> str:
    """Build a French QA prompt. Matches the agentic prompts from defaults_fr.py."""
    from llama_index.core.prompts import PromptTemplate
    if CFG.slm_mode:
        from lib.activiity.prompts.defaults_fr import SLM_QA_FR, SLM_SYSTEM_FR
        tmpl = PromptTemplate(SLM_QA_FR)
        return SLM_SYSTEM_FR, tmpl.format(context_str=context, query_str=question)
    from lib.activiity.prompts.defaults_fr import QA_FR, SYSTEM_FR
    tmpl = PromptTemplate(QA_FR)
    return SYSTEM_FR, tmpl.format(context_str=context, query_str=question)


class NaiveRagService:
    def __init__(self, data_dir=None, persist_dir=None):
        self.index = build_or_load(
            data_dir=data_dir if data_dir else None or __import__("lib.baseline.config", fromlist=["DATA_DIR"]).DATA_DIR,
            persist_dir=persist_dir if persist_dir else None or __import__("lib.baseline.config", fromlist=["PERSIST_DIR"]).PERSIST_DIR,
        )

        self.token_counter = TokenCountingHandler()
        LISettings.callback_manager = CallbackManager([self.token_counter])

        self.retriever = self.index.as_retriever(similarity_top_k=CFG.top_k)
        self._llm_name  = CFG.openrouter_model
        self._embed_name = getattr(
            LISettings.embed_model,
            "model_name",
            getattr(LISettings.embed_model, "model", "unknown"),
        )

    @staticmethod
    def _dominant_ua(nodes) -> str:
        if not nodes:
            return "GLOBAL"
        c: Counter = Counter()
        for n in nodes:
            ua = n.metadata.get("ua_id") if hasattr(n, "metadata") else n.node.metadata.get("ua_id")
            if ua:
                score = getattr(n, "score", None) or 1.0
                c[ua] += score
        return c.most_common(1)[0][0] if c else "GLOBAL"

    @staticmethod
    def _tool_name_for(ua: str) -> str:
        if ua == "GLOBAL" or not ua:
            return "query_global"
        return f"query_{ua.lower().replace('-', '_')}"

    async def achat_with_trace(self, question: str, history_text: str | None = None, model_override: str | None = None) -> NaiveResult:
        self.token_counter.reset_counts()
        t0 = time.perf_counter()

        if history_text:
            question = f"Historique:\n{history_text}\n\nQuestion actuelle: {question}"

        nodes = self.retriever.retrieve(question)
        t_retrieved = time.perf_counter()

        dominant = self._dominant_ua(nodes)
        tool_name = self._tool_name_for(dominant)

        # Build context from retrieved nodes
        context_parts = []
        for n in nodes:
            text = getattr(n, "text", None) or getattr(getattr(n, "node", None), "text", "")
            if text:
                context_parts.append(text)
        context = "\n\n".join(context_parts[:3])  # top 3 chunks

        system_prompt, prompt = _build_prompt(question, context)

        # Call OpenRouter directly — avoids llama-index LLM stack bugs
        api_key = os.environ.get("OPENROUTER_API_KEY", "")
        if not api_key:
            return NaiveResult(
                answer="[error] OPENROUTER_API_KEY not set. Enter your API key in Settings.",
                tools_called=[tool_name],
                retrieved_nodes=nodes,
                tokens_in=0,
                tokens_out=0,
                iterations=1,
                model_name=self._llm_name,
                embed_model=self._embed_name,
                ttft_s=(t_retrieved - t0),
            )

        try:
            async with httpx.AsyncClient(timeout=120) as client:
                resp = await client.post(
                    OR_API,
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": model_override or CFG.openrouter_model,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": prompt},
                        ],
                        "max_tokens": 1024,
                        "temperature": CFG.llm_temperature,
                    },
                )
                if resp.status_code != 200:
                    err = resp.text[:200]
                    return NaiveResult(
                        answer=f"[error] OpenRouter HTTP {resp.status_code}: {err}",
                        tools_called=[tool_name],
                        retrieved_nodes=nodes,
                        tokens_in=0,
                        tokens_out=0,
                        iterations=1,
                        model_name=self._llm_name,
                        embed_model=self._embed_name,
                        ttft_s=(t_retrieved - t0),
                    )
                data = resp.json()
                answer = data["choices"][0]["message"]["content"]
                tokens_in = data.get("usage", {}).get("prompt_tokens", 0)
                tokens_out = data.get("usage", {}).get("completion_tokens", 0)

        except Exception as e:
            return NaiveResult(
                answer=f"[error] {type(e).__name__}: {e}",
                tools_called=[tool_name],
                retrieved_nodes=nodes,
                tokens_in=0,
                tokens_out=0,
                iterations=1,
                model_name=self._llm_name,
                embed_model=self._embed_name,
                ttft_s=(t_retrieved - t0),
            )

        return NaiveResult(
            answer=answer,
            tools_called=[tool_name],
            retrieved_nodes=nodes,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            iterations=1,
            model_name=self._llm_name,
            embed_model=self._embed_name,
            ttft_s=(t_retrieved - t0),
        )

    def ask(self, question: str) -> NaiveResult:
        import asyncio
        return asyncio.run(self.achat_with_trace(question))

    def ask(self, question: str) -> NaiveResult:
        import asyncio
        return asyncio.run(self.achat_with_trace(question))
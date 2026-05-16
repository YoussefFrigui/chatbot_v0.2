"""AgenticRagService — ReAct agent with 11 tools (10 per-UA + global).
   
Architecture:
  Agent routes question to correct UA tool → tool retrieves from Qdrant
  → NodeCapturingPostprocessor stores retrieved nodes on the service
  → After agent finishes, nodes are synthesized via direct OpenRouter call
  → No llama-index LLM stack involved for synthesis.

Extensible: new tools for JSON, email, web, etc. just plug into the
same NodeCapturingPostprocessor + RawTextSynth pattern.
"""
from __future__ import annotations
import json
import os
import time
from dataclasses import dataclass

import httpx

from llama_index.core import VectorStoreIndex, Settings as LISettings
from llama_index.core.callbacks import CallbackManager, TokenCountingHandler
from llama_index.core.prompts import PromptTemplate
from llama_index.core.response_synthesizers import get_response_synthesizer
from llama_index.core.tools import QueryEngineTool, ToolMetadata
from llama_index.core.agent import ReActAgent
from llama_index.core.schema import NodeWithScore, QueryBundle
from llama_index.core.postprocessor.types import BaseNodePostprocessor
from llama_index.vector_stores.qdrant import QdrantVectorStore
from qdrant_client import QdrantClient, AsyncQdrantClient, models as qm

from lib.activiity.config import CFG, UA_IDS, collection_name
from lib.activiity.providers.factory import build_llm, build_synth_llm, build_embed
from lib.activiity.prompts.defaults_fr import (
    SYSTEM_FR, QA_FR, REFINE_FR, tool_desc_ua, TOOL_DESC_GLOBAL,
    SLM_SYSTEM_FR, SLM_QA_FR, SLM_REFINE_FR,
)

OR_API = "https://openrouter.ai/api/v1/chat/completions"


@dataclass
class AgenticResult:
    answer: str
    tools_called: list[str]
    retrieved_nodes: list
    tokens_in: int
    tokens_out: int
    iterations: int
    model_name: str
    embed_model: str
    ttft_s: float | None


class NodeCapturingPostprocessor(BaseNodePostprocessor):
    """Captures every NodeWithScore that passes through a query engine.
    
    Plugs into node_postprocessors in any QueryEngineTool.
    Works in both sync and async paths because postprocessors receive
    NodeWithScore objects directly from the retriever, before the
    synthesizer is called.
    
    Extensible: add one to every tool — JSON tool, email tool, etc.
    """
    def __init__(self, target_list: list):
        super().__init__()
        self._target = target_list

    def _postprocess_nodes(self, nodes: list[NodeWithScore], query_bundle: QueryBundle | None = None) -> list[NodeWithScore]:
        self._target.extend(nodes)
        return nodes

    def postprocess_nodes(self, nodes: list[NodeWithScore], query_bundle: QueryBundle | None = None) -> list[NodeWithScore]:
        return self._postprocess_nodes(nodes, query_bundle)


class AgenticRagService:
    def __init__(self):
        self.llm = build_llm()
        self.synth_llm = build_synth_llm()
        self.embed = build_embed()
        LISettings.llm = self.llm
        LISettings.embed_model = self.embed

        self.reranker = None
        if CFG.use_reranker:
            try:
                from llama_index.postprocessor.flag_embedding_reranker import FlagEmbeddingReranker
                self.reranker = FlagEmbeddingReranker(
                    model=CFG.reranker_model, top_n=CFG.rerank_keep,
                )
                print(f"[agentic] reranker enabled: {CFG.reranker_model}")
            except Exception as e:
                print(f"[agentic] reranker unavailable ({e}); continuing without")

        self.token_counter = TokenCountingHandler()
        LISettings.callback_manager = CallbackManager([self.token_counter])

        coll = collection_name(
            CFG.openai_embed_model if CFG.embed_provider == "openai"
            else CFG.ollama_embed_model
        )
        client = QdrantClient(url=CFG.qdrant_url, timeout=60, check_compatibility=False)
        aclient = AsyncQdrantClient(url=CFG.qdrant_url, timeout=60, check_compatibility=False)
        if not client.collection_exists(coll):
            raise RuntimeError(
                f"Qdrant collection {coll!r} not found — "
                f"run ingestion first."
            )
        self.client = client
        self.aclient = aclient
        self.collection = coll
        self.vstore = QdrantVectorStore(
            client=client, aclient=aclient, collection_name=coll,
        )
        self.index = VectorStoreIndex.from_vector_store(self.vstore)

        if CFG.slm_mode:
            self._qa_tmpl = PromptTemplate(SLM_QA_FR)
            self._refine_tmpl = PromptTemplate(SLM_REFINE_FR)
            self._system_prompt = SLM_SYSTEM_FR
        else:
            self._qa_tmpl = PromptTemplate(QA_FR)
            self._refine_tmpl = PromptTemplate(REFINE_FR)
            self._system_prompt = SYSTEM_FR

        # Shared list: all tools append their retrieved nodes here.
        self._synth_nodes: list = []
        self.agent = self._build_agent()

        self._llm_name = getattr(self.llm, "model", "unknown")
        self._embed_name = getattr(
            self.embed, "model_name",
            getattr(self.embed, "model", "unknown"),
        )

    def _make_synth(self):
        """Returns raw node text. No LLM call — synthesis happens after agent finishes."""
        return get_response_synthesizer(response_mode="no_text")

    def _make_capture_postprocessor(self) -> NodeCapturingPostprocessor:
        return NodeCapturingPostprocessor(self._synth_nodes)

    def _ua_tool(self, ua_id: str) -> QueryEngineTool:
        from llama_index.core.vector_stores.types import (
            MetadataFilters, MetadataFilter, FilterOperator,
        )
        filters = MetadataFilters(filters=[
            MetadataFilter(key="ua_id", value=ua_id, operator=FilterOperator.EQ),
        ])
        top_k = CFG.rerank_top_k if self.reranker else CFG.top_k_per_ua
        postprocessors = [self.reranker] if self.reranker else []
        postprocessors.append(self._make_capture_postprocessor())
        qe = self.index.as_query_engine(
            similarity_top_k=top_k,
            filters=filters,
            response_synthesizer=self._make_synth(),
            node_postprocessors=postprocessors,
        )
        return QueryEngineTool(
            query_engine=qe,
            metadata=ToolMetadata(
                name=f"query_ua_{ua_id.split('-')[1]}",
                description=tool_desc_ua(ua_id),
            ),
        )

    def _global_tool(self) -> QueryEngineTool:
        top_k = CFG.rerank_top_k if self.reranker else CFG.top_k_global
        postprocessors = [self.reranker] if self.reranker else []
        postprocessors.append(self._make_capture_postprocessor())
        qe = self.index.as_query_engine(
            similarity_top_k=top_k,
            response_synthesizer=self._make_synth(),
            node_postprocessors=postprocessors,
        )
        return QueryEngineTool(
            query_engine=qe,
            metadata=ToolMetadata(
                name="query_global",
                description=TOOL_DESC_GLOBAL,
            ),
        )

    def _build_agent(self) -> ReActAgent:
        tools = [self._ua_tool(u) for u in UA_IDS] + [self._global_tool()]
        return ReActAgent(
            name="Activiity",
            description="Agent RAG management/coaching FR (Fiches Protocole UA-1..UA-10).",
            tools=tools,
            llm=self.llm,
            system_prompt=self._system_prompt,
            max_iterations=CFG.max_iterations,
            timeout=180,
            verbose=False,
        )

    async def achat_with_trace(self, question: str, history_text: str | None = None) -> AgenticResult:
        self.token_counter.reset_counts()
        # Reset node capture list (clear in-place — postprocessors reference this list)
        self._synth_nodes.clear()

        if history_text:
            question = f"Historique:\n{history_text}\n\nQuestion actuelle: {question}"

        from llama_index.core.agent.workflow import ToolCall, ToolCallResult
        tools_called: list[str] = []

        t0 = time.perf_counter()
        answer = ""
        try:
            handler = self.agent.run(user_msg=question)
            async for ev in handler.stream_events():
                if isinstance(ev, ToolCall):
                    tools_called.append(ev.tool_name)
                # Note: ToolCallResult events are NOT needed for node capture.
                # NodeCapturingPostprocessor stores nodes during tool execution.
            await handler  # Ensure agent completes

        except Exception as e:
            answer = f"[agent_error] {type(e).__name__}: {e}"

        # --- Synthesize answer from captured nodes via direct OpenRouter ---
        if not answer:
            try:
                nodes = self._synth_nodes or []
                context_parts = []
                for n in nodes:
                    t = getattr(n, "text", None) or getattr(getattr(n, "node", None), "text", "") or ""
                    if t:
                        context_parts.append(t)
                context = "\n\n".join(context_parts[:5])[:5000] if context_parts else ""

                if context:
                    prompt = self._qa_tmpl.format(context_str=context, query_str=question)
                    api_key = os.environ.get("OPENROUTER_API_KEY", "")
                    if api_key:
                        async with httpx.AsyncClient(timeout=120) as c:
                            r = await c.post(
                                OR_API,
                                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                                json={
                                    "model": CFG.synth_model,
                                    "messages": [{"role": "user", "content": prompt}],
                                    "max_tokens": 512,
                                    "temperature": 0.1,
                                },
                            )
                            if r.status_code == 200:
                                answer = r.json()["choices"][0]["message"]["content"]
                            else:
                                answer = context[:500]
                    else:
                        answer = context[:500]
                else:
                    answer = "[no relevant context retrieved]"
            except Exception as synth_err:
                answer = f"[synthesis_error: {synth_err}]"

        # Deduplicate nodes for the result
        seen = set()
        unique_nodes = []
        for n in self._synth_nodes:
            node = getattr(n, "node", n)
            meta = getattr(node, "metadata", {}) or {}
            src = meta.get("source_path", "")
            txt = getattr(node, "text", "") or getattr(n, "text", "") or ""
            key = (src, txt[:80])
            if key in seen:
                continue
            seen.add(key)
            unique_nodes.append(n)

        iterations = max(1, len(tools_called))

        return AgenticResult(
            answer=answer,
            tools_called=tools_called or ["query_global"],
            retrieved_nodes=unique_nodes,
            tokens_in=self.token_counter.prompt_llm_token_count,
            tokens_out=self.token_counter.completion_llm_token_count,
            iterations=iterations,
            model_name=str(self._llm_name),
            embed_model=str(self._embed_name),
            ttft_s=(time.perf_counter() - t0) if answer and not answer.startswith("[") else None,
        )

    def ask(self, question: str) -> AgenticResult:
        import asyncio
        return asyncio.run(self.achat_with_trace(question))

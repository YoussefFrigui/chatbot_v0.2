"""AgenticRagService — ReAct agent with 11 tools (10 per-UA + global)."""
from __future__ import annotations
import time
from dataclasses import dataclass

from llama_index.core import VectorStoreIndex, Settings as LISettings
from llama_index.core.callbacks import CallbackManager, TokenCountingHandler
from llama_index.core.prompts import PromptTemplate
from llama_index.core.response_synthesizers import get_response_synthesizer
from llama_index.core.tools import QueryEngineTool, ToolMetadata
from llama_index.core.agent import ReActAgent
from llama_index.vector_stores.qdrant import QdrantVectorStore
from qdrant_client import QdrantClient, AsyncQdrantClient, models as qm

from lib.activiity.config import CFG, UA_IDS, collection_name
from lib.activiity.providers.factory import build_llm, build_synth_llm, build_embed
from lib.activiity.prompts.defaults_fr import (
    SYSTEM_FR, QA_FR, REFINE_FR, tool_desc_ua, TOOL_DESC_GLOBAL,
    SLM_SYSTEM_FR, SLM_QA_FR, SLM_REFINE_FR,
)


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
            except Exception as e:  # noqa: BLE001
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

        self._last_nodes: list = []
        self.agent = self._build_agent()

        self._llm_name = getattr(self.llm, "model", "unknown")
        self._embed_name = getattr(
            self.embed, "model_name",
            getattr(self.embed, "model", "unknown"),
        )

    def _make_synth(self):
        return get_response_synthesizer(
            response_mode="compact",
            text_qa_template=self._qa_tmpl,
            refine_template=self._refine_tmpl,
            llm=self.synth_llm,
        )

    def _capture(self, nodes):
        self._last_nodes = list(nodes)
        return nodes

    def _ua_tool(self, ua_id: str) -> QueryEngineTool:
        from llama_index.core.vector_stores.types import (
            MetadataFilters, MetadataFilter, FilterOperator,
        )
        filters = MetadataFilters(filters=[
            MetadataFilter(key="ua_id", value=ua_id, operator=FilterOperator.EQ),
        ])
        top_k = CFG.rerank_top_k if self.reranker else CFG.top_k_per_ua
        postprocessors = [self.reranker] if self.reranker else []
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
        self._last_nodes = []

        if history_text:
            question = f"Historique:\n{history_text}\n\nQuestion actuelle: {question}"

        from llama_index.core.agent.workflow import ToolCall, ToolCallResult
        tools_called: list[str] = []
        captured_nodes: list = []

        t0 = time.perf_counter()
        answer = ""
        try:
            handler = self.agent.run(user_msg=question)
            async for ev in handler.stream_events():
                if isinstance(ev, ToolCall):
                    tools_called.append(ev.tool_name)
                elif isinstance(ev, ToolCallResult):
                    tool_output = ev.tool_output
                    raw = getattr(tool_output, "raw_output", None)
                    if raw is not None:
                        response = getattr(raw, "response", None)
                        if response is not None and hasattr(response, "source_nodes"):
                            captured_nodes.extend(response.source_nodes)
                        elif hasattr(raw, "source_nodes"):
                            captured_nodes.extend(raw.source_nodes)
                    if not captured_nodes:
                        response = getattr(tool_output, "response", None)
                        if response is not None and hasattr(response, "source_nodes"):
                            captured_nodes.extend(response.source_nodes)

            result = await handler
            if hasattr(result, "response") and getattr(result.response, "content", None):
                answer = result.response.content
            else:
                answer = str(result)
        except Exception as e:  # noqa: BLE001
            answer = f"[agent_error] {type(e).__name__}: {e}"

        seen = set()
        unique_nodes = []
        for n in captured_nodes:
            key = (
                n.node.metadata.get("source_path", "") if hasattr(n, "node")
                else n.metadata.get("source_path", ""),
                n.node.text[:80] if hasattr(n, "node") else (n.text[:80] if hasattr(n, "text") else ""),
            )
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
            ttft_s=None,
        )

    def ask(self, question: str) -> AgenticResult:
        import asyncio
        return asyncio.run(self.achat_with_trace(question))
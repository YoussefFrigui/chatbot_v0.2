"""Bridge to Ragas for generative quality metrics."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from eval.config import JUDGE
from eval.parser import Pair


@dataclass
class RagasReport:
    faithfulness: float
    answer_relevancy: float
    context_precision: float
    context_recall: float
    answer_correctness: float
    n_samples: int


def _zero_scores() -> dict:
    return {
        "faithfulness": 0.0,
        "answer_relevancy": 0.0,
        "context_precision": 0.0,
        "context_recall": 0.0,
        "answer_correctness": 0.0,
    }


def _build_judge():
    from ragas.llms import LangchainLLMWrapper
    import os

    if JUDGE.provider == "openrouter":
        from langchain_openai import ChatOpenAI
        llm = ChatOpenAI(
            model=JUDGE.model,
            temperature=JUDGE.temperature,
            base_url="https://openrouter.ai/api/v1",
            api_key=os.getenv("OPENROUTER_API_KEY"),
            timeout=60,
            max_retries=JUDGE.max_retries,
            max_tokens=2048,
        )
        return LangchainLLMWrapper(llm)

    if JUDGE.provider == "ollama":
        from langchain_community.chat_models import ChatOllama
        llm = ChatOllama(
            model=JUDGE.model,
            temperature=JUDGE.temperature,
            base_url=os.getenv("OLLAMA_URL", "http://localhost:11434"),
        )
        return LangchainLLMWrapper(llm)

    if JUDGE.provider == "google":
        from langchain_google_genai import ChatGoogleGenerativeAI
        llm = ChatGoogleGenerativeAI(
            model=JUDGE.model,
            temperature=JUDGE.temperature,
            google_api_key=os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"),
            timeout=120,
            max_retries=3,
        )
        return LangchainLLMWrapper(llm)

    raise ValueError(f"Unknown judge provider: {JUDGE.provider}")


def _build_judge_embeddings():
    from ragas.embeddings import LangchainEmbeddingsWrapper
    import os
    from langchain_community.embeddings import OllamaEmbeddings

    emb = OllamaEmbeddings(
        model="bge-m3",
        base_url=os.getenv("OLLAMA_URL", "http://localhost:11434"),
    )
    return LangchainEmbeddingsWrapper(emb)


async def ragas_for_single(
    question: str,
    answer: str,
    ground_truth: str,
    contexts: list[str] | None,
) -> dict:
    """Run a single-row RAGAS evaluation.

    Only includes metrics that can be computed with the available data.
    Context metrics require ground truth — if missing, runs faith+relevancy only.
    """
    from ragas import evaluate
    from ragas.dataset_schema import EvaluationDataset, SingleTurnSample
    from ragas.metrics import (
        faithfulness,
        answer_relevancy,
        answer_correctness,
    )
    import asyncio

    has_gt = bool(ground_truth and ground_truth.strip())
    has_ctx = bool(contexts and any(c.strip() for c in contexts if c))

    metrics = [faithfulness, answer_relevancy]
    if has_gt:
        metrics.append(answer_correctness)
    if has_gt and has_ctx:
        from ragas.metrics import context_precision, context_recall
        metrics += [context_precision, context_recall]

    sample = SingleTurnSample(
        user_input=question,
        retrieved_contexts=contexts or [""],
        response=answer,
        reference=ground_truth if has_gt else None,
    )
    ds = EvaluationDataset(samples=[sample])

    def _sync_eval():
        judge = _build_judge()
        emb = _build_judge_embeddings()
        for m in metrics:
            m.llm = judge
            if hasattr(m, 'embeddings'):
                m.embeddings = emb
        return evaluate(ds, metrics=metrics, llm=judge, embeddings=emb)

    results = await asyncio.to_thread(_sync_eval)
    row = results.to_pandas().iloc[0].to_dict()
    scores = {"faithfulness": 0.0, "answer_relevancy": 0.0, "context_precision": 0.0, "context_recall": 0.0, "answer_correctness": 0.0}
    for key in scores:
        value = row.get(key)
        scores[key] = float(value) if value is not None and value == value else 0.0
    return scores


async def ragas_report(pairs: Iterable[Pair], traces: Iterable) -> tuple[RagasReport, list[dict]]:
    pairs = list(pairs)
    traces_by_id = {t.pair_id: t for t in traces}
    rows = []
    for pair in pairs:
        trace = traces_by_id.get(pair.id)
        if trace is None or getattr(trace, "error", None) or not pair.ground_truth or not getattr(trace, "answer", ""):
            continue
        rows.append({
            "question": pair.question,
            "answer": trace.answer,
            "contexts": trace.retrieved_chunks or [""],
            "ground_truth": pair.ground_truth,
        })
    if not rows:
        return RagasReport(0.0, 0.0, 0.0, 0.0, 0.0, 0), []

    from ragas import evaluate
    from ragas.dataset_schema import EvaluationDataset, SingleTurnSample
    from ragas.metrics import (
        faithfulness,
        answer_relevancy,
        context_precision,
        context_recall,
        answer_correctness,
    )

    import asyncio

    samples = [SingleTurnSample(
        user_input=row["question"],
        retrieved_contexts=row["contexts"],
        response=row["answer"],
        reference=row["ground_truth"],
    ) for row in rows]
    ds = EvaluationDataset(samples=samples)

    def _sync_eval():
        return evaluate(
            ds,
            metrics=[faithfulness, answer_relevancy, context_precision, context_recall, answer_correctness],
            llm=_build_judge(),
            embeddings=_build_judge_embeddings(),
        )

    results = await asyncio.to_thread(_sync_eval)
    df = results.to_pandas()
    scores_list = []
    for i, pair in enumerate(pairs[: len(df)]):
        scores_list.append({
            "pair_id": pair.id,
            "ragas_faithfulness": df.iloc[i].get("faithfulness", None),
            "ragas_answer_relevancy": df.iloc[i].get("answer_relevancy", None),
            "ragas_context_precision": df.iloc[i].get("context_precision", None),
            "ragas_context_recall": df.iloc[i].get("context_recall", None),
            "ragas_answer_correctness": df.iloc[i].get("answer_correctness", None),
        })

    def _avg(col: str) -> float:
        series = df[col].dropna()
        return float(series.mean()) if len(series) else 0.0

    return RagasReport(
        faithfulness=_avg("faithfulness"),
        answer_relevancy=_avg("answer_relevancy"),
        context_precision=_avg("context_precision"),
        context_recall=_avg("context_recall"),
        answer_correctness=_avg("answer_correctness"),
        n_samples=len(ds),
    ), scores_list

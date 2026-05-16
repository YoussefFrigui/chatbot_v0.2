"""CLI for the Activiity Chatbot v0.2.

Usage:
    # Interactive REPL
    python -m chatbot.cli

    # One-shot question
    python -m chatbot.cli --question "Qu'est-ce que la délégation ?"

    # New session each call
    python -m chatbot.cli --question "..." --session my_session

    # No persistence (ephemeral)
    python -m chatbot.cli --no-persist

    # Stream output
    python -m chatbot.cli --stream -q "Quels sont les 5 principes de la délégation ?"

Environment variables (override defaults):
    LLM_PROVIDER=openrouter
    OPENROUTER_API_KEY=YOUR-KEY-HERE
    LLM_MODEL=qwen/qwen3-14b
    SYNTH_MODEL=qwen/qwen3-8b
    SLM_MODE=1
    CHAT_MAX_HISTORY=10
    QDRANT_URL=http://localhost:6333
    EMBED_PROVIDER=ollama
    OLLAMA_URL=http://localhost:11434
    OLLAMA_LLM_MODEL=qwen2.5:14b-instruct
"""
from __future__ import annotations
import argparse
import asyncio
import sys

from chatbot.service import ChatService, get_chat_service


def _format_output(result) -> str:
    lines = [
        "",
        "+" + "-" * 55 + "+",
        "| " + f"🤖 {result.model_name}".ljust(53) + " |",
        "| " + f"📐 {len(result.tools_called)} tool call(s)  |  {result.iterations} iter(s)".ljust(53) + " |",
        "| " + f"⏱  {result.latency_s:.1f}s".ljust(53) + " |",
        "+" + "-" * 55 + "+",
    ]
    for line in result.answer.split("\n"):
        # Wrap long lines
        while len(line) > 53:
            lines.append("| " + line[:53].ljust(53) + " |")
            line = line[53:]
        lines.append("| " + line.ljust(53) + " |")
    if result.retrieved_sources:
        lines.append("+" + "-" * 55 + "+")
        lines.append("| " + "📎 Sources :".ljust(53) + " |")
        for src in result.retrieved_sources[:5]:
            lines.append("| " + f"  • {src}".ljust(53) + " |")
    if result.error:
        lines.append("+" + "-" * 55 + "+")
        lines.append("| " + f"⚠️  {result.error}".ljust(53) + " |")
    lines.append("+" + "-" * 55 + "+")
    return "\n".join(lines)


async def _run_one(
    svc: ChatService,
    question: str,
    session_id: str,
    mode: str | None,
):
    """Ask a single question and print the result."""
    print(f"\n👤 Vous : {question}")
    result = await svc.chat(question, session_id=session_id, mode=mode)
    print(_format_output(result))
    print(f"   [session: {result.session_id}  turn #{result.history_count}]")


async def _repl(svc: ChatService, session_id: str, mode: str | None):
    """Interactive read-eval-print loop."""
    print("=" * 57)
    print(f"  Activiity Chatbot v0.2  —  session: {session_id}")
    print(f"  Commands: quit/exit/q  |  clear  |  stats")
    print("=" * 57)

    while True:
        try:
            question = input("\n👤 Vous : ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n👋 Au revoir !")
            break

        if not question:
            continue
        if question.lower() in ("quit", "exit", "q"):
            print("👋 Au revoir !")
            break
        if question.lower() == "clear":
            svc.clear_session(session_id)
            print(f"   [session {session_id} effacée]")
            continue
        if question.lower() == "stats":
            stats = svc.session_stats(session_id)
            print(f"   {stats}")
            continue

        await _run_one(svc, question, session_id, mode)


def main():
    ap = argparse.ArgumentParser(
        prog="chatbot",
        description="Activiity conversational RAG chatbot v0.2",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python -m chatbot.cli\n"
            "  python -m chatbot.cli -q 'Qu'est-ce que la délégation ?'\n"
            "  python -m chatbot.cli --stream -q 'Quels sont les 5 principes ?'\n"
            "  python -m chatbot.cli --session coaching --no-persist\n"
        ),
    )
    ap.add_argument(
        "--question", "-q",
        help="Pose une question directe (mode non-interactif)",
    )
    ap.add_argument(
        "--session", "-s",
        default=None,
        help="Identifiant de session (défaut: auto-généré)",
    )
    ap.add_argument(
        "--no-persist",
        action="store_true",
        help="Ne pas persister l'historique sur disque",
    )
    ap.add_argument(
        "--stream",
        action="store_true",
        help="Afficher la réponse mot par mot (streaming simulé)",
    )
    ap.add_argument(
        "--mode",
        choices=["agentic", "naive"],
        default=None,
        help="RAG mode (agentic or naive)",
    )
    args = ap.parse_args()

    svc = get_chat_service(persist=not args.no_persist)
    session_id = args.session or "default"

    if args.question:
        # One-shot mode
        if args.stream:
            async def _stream_qa():
                async for chunk in svc.chat_stream(args.question, session_id, mode=args.mode):
                    print(chunk.delta, end="", flush=True)
                print()
            asyncio.run(_stream_qa())
        else:
            result = asyncio.run(svc.chat(args.question, session_id, mode=args.mode))
            print(_format_output(result))
    else:
        # REPL mode
        asyncio.run(_repl(svc, session_id, args.mode))


if __name__ == "__main__":
    main()
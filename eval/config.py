"""Standalone evaluation configuration for chatbot_v0.2."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os

# NOTE: chatbot_v0.2 can be used two ways:
#  1. Standalone: test/ is a SIBLING of chatbot_v0.2/ (parent repo layout)
#     ROOT = Activiitykdb/  -> LOCAL_TEST = ROOT/test/  (EXISTS)
#  2. Inside parent repo: test/ is a SIBLING of chatbot_v0.2/  (same as above)
#  3. Moved folder: test/ is INSIDE chatbot_v0.2/ (standalone bundle)
#     ROOT = chatbot_v0.2/ -> LOCAL_TEST = ROOT/test/  (may not exist)
ROOT = Path(__file__).resolve().parent.parent
LOCAL_TEST = ROOT / "test"           # test/ inside chatbot_v0.2/ (bundled)
PARENT_TEST = ROOT.parent / "test"   # test/ sibling of chatbot_v0.2/ (parent repo)
SIBLING_TEST = ROOT.with_name("test")  # test/ at same level as ROOT (sibling layout)
TEST_DIR = next((p for p in [LOCAL_TEST, SIBLING_TEST, PARENT_TEST] if p.exists()), LOCAL_TEST)
TIERS = ("reference", "medium", "advanced")
UA_IDS = [f"UA-{i}" for i in range(1, 11)]
OOS_LABEL = "NONE"
ALL_LABELS = UA_IDS + [OOS_LABEL]


@dataclass(frozen=True)
class JudgeConfig:
    provider: str = "openrouter"
    model: str = "openai/gpt-4o-mini"
    fallback_model: str = "openai/gpt-4o-mini"
    temperature: float = 0.0
    max_retries: int = 2


JUDGE = JudgeConfig(
    provider=os.getenv("ACTIVIITY_JUDGE_PROVIDER", "openrouter"),
    model=os.getenv("ACTIVIITY_JUDGE_MODEL", "openai/gpt-4o-mini"),
    fallback_model=os.getenv("ACTIVIITY_JUDGE_FALLBACK_MODEL", "openai/gpt-4o-mini"),
    temperature=float(os.getenv("ACTIVIITY_JUDGE_TEMPERATURE", "0.0")),
    max_retries=int(os.getenv("ACTIVIITY_JUDGE_MAX_RETRIES", "2")),
)

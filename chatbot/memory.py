"""Conversation memory — sliding window over recent turns.

Uses SQLite for persistence (lightweight, single-file, no server).
Each session gets a UUID; history is a simple message list with role tags.

No external dependencies beyond the Python standard library.
"""
from __future__ import annotations
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

from chatbot.config import CHAT


@dataclass
class Message:
    role: str           # "user" | "assistant" | "system"
    content: str
    timestamp: str = ""  # ISO-8601

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.utcnow().isoformat(timespec="seconds") + "Z"


@dataclass
class Turn:
    """One exchange: user message + optional assistant reply."""
    user_msg: Message
    assistant_msg: Optional[Message] = None


class SessionMemory:
    """In-memory + SQLite-backed conversation memory.

    Keeps a sliding window of the last N complete turns plus the current
    pending user message. History is injectable as plain text for prompts.
    """

    def __init__(self, session_id: str | None = None, persist: bool = True):
        self.session_id = session_id or str(uuid.uuid4())
        self.persist = persist
        self._max_turns = CHAT.max_history_turns
        self._system_msg: Message = Message(
            role="system",
            content=CHAT.bot_description,
        )
        self._history: list[Turn] = []
        self._pending_user: Message | None = None
        self._db: sqlite3.Connection | None = None
        if self.persist:
            self._init_db()

    # ------------------------------------------------------------------
    # SQLite persistence
    # ------------------------------------------------------------------
    def _init_db(self):
        db_path = CHAT.persist_dir / f"{self.session_id}.db"
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(str(db_path))
        self._db.execute(
            "CREATE TABLE IF NOT EXISTS messages ("
            "  id INTEGER PRIMARY KEY AUTOINCREMENT,"
            "  role TEXT NOT NULL,"
            "  content TEXT NOT NULL,"
            "  timestamp TEXT NOT NULL,"
            "  turn_num INTEGER NOT NULL DEFAULT 0"
            ")"
        )
        self._db.execute(
            "CREATE TABLE IF NOT EXISTS session_meta ("
            "  key TEXT PRIMARY KEY,"
            "  value TEXT"
            ")"
        )
        self._load_from_db()

    def _load_from_db(self):
        if not self._db:
            return
        rows = self._db.execute(
            "SELECT role, content, timestamp FROM messages ORDER BY id"
        ).fetchall()
        if not rows:
            return
        # Reconstruct: system, user, assistant, user, assistant, ...
        for r in rows:
            if r[0] == "system":
                self._system_msg = Message(role="system", content=r[1], timestamp=r[2])
                break
        current_user = None
        current_assistant = None
        for role, content, ts in rows:
            if role == "system":
                continue
            msg = Message(role=role, content=content, timestamp=ts)
            if role == "user":
                if current_user is not None and current_assistant is not None:
                    self._history.append(Turn(user_msg=current_user, assistant_msg=current_assistant))
                current_user = msg
                current_assistant = None
            elif role == "assistant":
                current_assistant = msg
                if current_user is not None:
                    self._history.append(Turn(user_msg=current_user, assistant_msg=current_assistant))
                    current_user = None
                    current_assistant = None
        if current_user is not None:
            self._pending_user = current_user
        if len(self._history) > self._max_turns:
            self._history = self._history[-self._max_turns:]

    def _save_message(self, msg: Message, turn_num: int):
        if not self._db:
            return
        self._db.execute(
            "INSERT INTO messages (role, content, timestamp, turn_num) VALUES (?, ?, ?, ?)",
            (msg.role, msg.content, msg.timestamp, turn_num),
        )
        self._db.commit()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def add_user_message(self, text: str) -> Message:
        msg = Message(role="user", content=text)
        turn_num = len(self._history) + 1
        self._pending_user = msg
        if self.persist:
            self._save_message(msg, turn_num)
        return msg

    def add_assistant_message(self, text: str) -> Message:
        msg = Message(role="assistant", content=text)
        turn = Turn(
            user_msg=self._pending_user or Message(role="user", content=""),
            assistant_msg=msg,
        )
        self._history.append(turn)
        self._pending_user = None
        if self.persist:
            turn_num = len(self._history)
            self._save_message(msg, turn_num)
        if len(self._history) > self._max_turns:
            self._history = self._history[-self._max_turns:]
        return msg

    def get_history_messages(self) -> list[Message]:
        msgs: list[Message] = [self._system_msg]
        for turn in self._history:
            msgs.append(turn.user_msg)
            if turn.assistant_msg:
                msgs.append(turn.assistant_msg)
        if self._pending_user:
            msgs.append(self._pending_user)
        return msgs

    def get_history_text(self) -> str:
        lines = []
        for turn in self._history[-self._max_turns:]:
            lines.append(f"User: {turn.user_msg.content}")
            if turn.assistant_msg:
                lines.append(f"Assistant: {turn.assistant_msg.content}")
        if self._pending_user:
            lines.append(f"User (current): {self._pending_user.content}")
        return "\n".join(lines)

    def clear(self):
        self._history.clear()
        self._pending_user = None
        if self.persist and self._db:
            self._db.execute("DELETE FROM messages")
            self._db.execute("DELETE FROM session_meta")
            self._db.commit()

    def get_stats(self) -> dict:
        return {
            "session_id": self.session_id,
            "n_turns": len(self._history),
            "has_pending": self._pending_user is not None,
            "persisted": self.persist,
        }
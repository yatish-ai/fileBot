"""
memory_manager.py
Manages short-term conversational memory for FileBOT.
Maintains last N turns, injects context into prompts, handles token overflow.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Tuple
import re


@dataclass
class Turn:
    role: str        # "user" or "assistant"
    content: str
    sources: List[dict] = field(default_factory=list)


class MemoryManager:
    """
    Stores the last `max_turns` conversation turns (user + assistant pairs).
    Provides a formatted history string for prompt injection.
    """

    def __init__(self, max_turns: int = 6, max_history_chars: int = 3000):
        self.max_turns = max_turns          # max user+assistant pairs to keep
        self.max_history_chars = max_history_chars
        self._turns: List[Turn] = []

    # ── Public API ────────────────────────────────────────────────────────────

    def add_turn(self, role: str, content: str, sources: Optional[List[dict]] = None):
        """Append a new turn and prune old ones."""
        self._turns.append(Turn(role=role, content=content, sources=sources or []))
        self._prune()

    def get_history_for_prompt(self) -> str:
        """
        Return a compact conversation history string suitable for injection
        into the LLM prompt. Truncated to avoid token overflow.
        """
        if not self._turns:
            return ""

        lines = []
        for t in self._turns:
            prefix = "User" if t.role == "user" else "FileBOT"
            # Truncate individual turns that are very long
            content = t.content[:600] + "…" if len(t.content) > 600 else t.content
            lines.append(f"{prefix}: {content}")

        history = "\n".join(lines)

        # Hard truncate total history to stay within budget
        if len(history) > self.max_history_chars:
            history = history[-self.max_history_chars:]
            # Clean up any partial line at the start
            first_newline = history.find("\n")
            if first_newline != -1:
                history = history[first_newline + 1:]
            history = "[Earlier messages truncated]\n" + history

        return history

    def get_last_assistant_answer(self) -> Optional[str]:
        """Return the most recent assistant turn content, if any."""
        for t in reversed(self._turns):
            if t.role == "assistant":
                return t.content
        return None

    def get_last_user_query(self) -> Optional[str]:
        """Return the most recent user turn content, if any."""
        for t in reversed(self._turns):
            if t.role == "user":
                return t.content
        return None

    def get_recent_context_window(self, n_pairs: int = 3) -> List[Tuple[str, str]]:
        """
        Return the last n_pairs of (user_query, assistant_answer) tuples,
        oldest first. Useful for reference resolution.
        """
        pairs = []
        turns = list(self._turns)
        i = len(turns) - 1
        while i >= 1 and len(pairs) < n_pairs:
            if turns[i].role == "assistant" and turns[i - 1].role == "user":
                pairs.append((turns[i - 1].content, turns[i].content))
                i -= 2
            else:
                i -= 1
        return list(reversed(pairs))

    def clear(self):
        self._turns = []

    def turn_count(self) -> int:
        return len(self._turns)

    # ── Private ───────────────────────────────────────────────────────────────

    def _prune(self):
        """Keep at most max_turns * 2 individual messages (user+assistant pairs)."""
        max_msgs = self.max_turns * 2
        if len(self._turns) > max_msgs:
            self._turns = self._turns[-max_msgs:]

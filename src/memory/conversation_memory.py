from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from src.models.ticket import ConversationTurn


@dataclass
class ConversationContext:
    """In-memory context for a single conversation thread."""

    customer_id: str
    ticket_id: str
    turns: list[ConversationTurn] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    last_updated: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def add_turn(self, role: str, content: str) -> None:
        """Add a message to the conversation."""
        self.turns.append(ConversationTurn(role=role, content=content))
        self.last_updated = datetime.now(timezone.utc).isoformat()

    def get_context_string(self) -> str:
        """Format conversation history as a string for LLM context."""
        if not self.turns:
            return "(no conversation history)"
        lines = []
        for turn in self.turns:
            role = turn.role if hasattr(turn, 'role') else turn['role']
            content = turn.content if hasattr(turn, 'content') else turn['content']
            lines.append(f"{role.upper()}: {content}")
        return "\n".join(lines)

    def get_summary(self) -> str:
        """Get a brief summary of the conversation."""
        if not self.turns:
            return "No prior conversation"
        return f"{len(self.turns)} turn(s) in conversation history"


class ConversationMemory:
    """Manages in-memory conversation contexts with LRU eviction.
    Stores active conversation threads to provide context for LLM decisions."""

    def __init__(self, max_conversations: int = 100) -> None:
        self.max_conversations = max_conversations
        self.conversations: dict[str, ConversationContext] = {}
        self.access_order: deque[str] = deque()

    def create_context(self, customer_id: str, ticket_id: str) -> ConversationContext:
        """Create a new conversation context."""
        context = ConversationContext(customer_id=customer_id, ticket_id=ticket_id)
        self._store_context(ticket_id, context)
        return context

    def get_context(self, ticket_id: str) -> Optional[ConversationContext]:
        """Retrieve a conversation context by ticket ID."""
        context = self.conversations.get(ticket_id)
        if context:
            # Update access order for LRU eviction
            if ticket_id in self.access_order:
                self.access_order.remove(ticket_id)
            self.access_order.append(ticket_id)
        return context

    def add_user_message(self, ticket_id: str, content: str) -> None:
        """Add a user message to the conversation."""
        context = self.get_context(ticket_id)
        if context:
            context.add_turn("user", content)

    def add_assistant_message(self, ticket_id: str, content: str) -> None:
        """Add an assistant message to the conversation."""
        context = self.get_context(ticket_id)
        if context:
            context.add_turn("assistant", content)

    def get_conversation_string(self, ticket_id: str) -> str:
        """Get formatted conversation history for LLM context."""
        context = self.get_context(ticket_id)
        return context.get_context_string() if context else "(no conversation history)"

    def update_from_ticket(self, ticket_id: str, customer_id: str, conversation_history: list[ConversationTurn]) -> None:
        """Initialize or update conversation from ticket data."""
        context = self.get_context(ticket_id)
        if not context:
            context = self.create_context(customer_id, ticket_id)
        context.turns = conversation_history
        context.last_updated = datetime.now(timezone.utc).isoformat()

    def clear_context(self, ticket_id: str) -> None:
        """Remove a conversation context from memory."""
        if ticket_id in self.conversations:
            del self.conversations[ticket_id]
            if ticket_id in self.access_order:
                self.access_order.remove(ticket_id)

    def clear_all(self) -> None:
        """Clear all conversation contexts."""
        self.conversations.clear()
        self.access_order.clear()

    def _store_context(self, ticket_id: str, context: ConversationContext) -> None:
        """Store a context and evict oldest if max reached."""
        self.conversations[ticket_id] = context
        self.access_order.append(ticket_id)

        # LRU eviction
        if len(self.conversations) > self.max_conversations:
            oldest_ticket = self.access_order.popleft()
            if oldest_ticket in self.conversations:
                del self.conversations[oldest_ticket]

    def get_stats(self) -> dict:
        """Get statistics about current memory usage."""
        return {
            "total_contexts": len(self.conversations),
            "max_capacity": self.max_conversations,
            "memory_utilization": len(self.conversations) / self.max_conversations,
            "conversations": {
                ticket_id: {
                    "turns": len(context.turns),
                    "summary": context.get_summary(),
                }
                for ticket_id, context in self.conversations.items()
            },
        }

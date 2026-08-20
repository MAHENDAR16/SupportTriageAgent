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

    # Appends a new turn (role + content) to this thread's history and
    # bumps last_updated for LRU tracking.
    def add_turn(self, role: str, content: str) -> None:
        """Add a message to the conversation."""
        self.turns.append(ConversationTurn(role=role, content=content))
        self.last_updated = datetime.now(timezone.utc).isoformat()

    # Renders all turns as "ROLE: content" lines, tolerating both Pydantic
    # model turns and plain dict turns.
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

    # Produces a one-line human-readable summary (turn count) of this thread.
    def get_summary(self) -> str:
        """Get a brief summary of the conversation."""
        if not self.turns:
            return "No prior conversation"
        return f"{len(self.turns)} turn(s) in conversation history"


class ConversationMemory:
    """Manages in-memory conversation contexts with LRU eviction.
    Stores active conversation threads to provide context for LLM decisions."""

    # Initializes the empty conversation store and LRU access-order queue.
    def __init__(self, max_conversations: int = 100) -> None:
        self.max_conversations = max_conversations
        self.conversations: dict[str, ConversationContext] = {}
        self.access_order: deque[str] = deque()

    # Builds a fresh ConversationContext for a ticket and stores it,
    # evicting the LRU entry if capacity is exceeded.
    def create_context(self, customer_id: str, ticket_id: str) -> ConversationContext:
        """Create a new conversation context."""
        context = ConversationContext(customer_id=customer_id, ticket_id=ticket_id)
        self._store_context(ticket_id, context)
        return context

    # Looks up a context by ticket_id and, if found, moves it to the front
    # of the LRU access order (most-recently-used).
    def get_context(self, ticket_id: str) -> Optional[ConversationContext]:
        """Retrieve a conversation context by ticket ID."""
        context = self.conversations.get(ticket_id)
        if context:
            # Update access order for LRU eviction
            if ticket_id in self.access_order:
                self.access_order.remove(ticket_id)
            self.access_order.append(ticket_id)
        return context

    # Appends a "user" turn to the ticket's context, if one exists.
    def add_user_message(self, ticket_id: str, content: str) -> None:
        """Add a user message to the conversation."""
        context = self.get_context(ticket_id)
        if context:
            context.add_turn("user", content)

    # Appends an "assistant" turn to the ticket's context, if one exists.
    def add_assistant_message(self, ticket_id: str, content: str) -> None:
        """Add an assistant message to the conversation."""
        context = self.get_context(ticket_id)
        if context:
            context.add_turn("assistant", content)

    # Returns the formatted conversation string for a ticket, or a
    # placeholder if no context exists yet.
    def get_conversation_string(self, ticket_id: str) -> str:
        """Get formatted conversation history for LLM context."""
        context = self.get_context(ticket_id)
        return context.get_context_string() if context else "(no conversation history)"

    # Creates a context if one doesn't exist yet, then overwrites its turns
    # with the ticket's conversation_history. Called from the ingest node.
    def update_from_ticket(self, ticket_id: str, customer_id: str, conversation_history: list[ConversationTurn]) -> None:
        """Initialize or update conversation from ticket data."""
        context = self.get_context(ticket_id)
        if not context:
            context = self.create_context(customer_id, ticket_id)
        context.turns = conversation_history
        context.last_updated = datetime.now(timezone.utc).isoformat()

    # Removes a single ticket's context from both the dict and access order.
    def clear_context(self, ticket_id: str) -> None:
        """Remove a conversation context from memory."""
        if ticket_id in self.conversations:
            del self.conversations[ticket_id]
            if ticket_id in self.access_order:
                self.access_order.remove(ticket_id)

    # Wipes every stored conversation context and the access order queue.
    def clear_all(self) -> None:
        """Clear all conversation contexts."""
        self.conversations.clear()
        self.access_order.clear()

    # Inserts a context into the store and evicts the least-recently-used
    # entry if max_conversations is exceeded.
    def _store_context(self, ticket_id: str, context: ConversationContext) -> None:
        """Store a context and evict oldest if max reached."""
        self.conversations[ticket_id] = context
        self.access_order.append(ticket_id)

        # LRU eviction
        if len(self.conversations) > self.max_conversations:
            oldest_ticket = self.access_order.popleft()
            if oldest_ticket in self.conversations:
                del self.conversations[oldest_ticket]

    # Reports current/max conversation counts, utilization ratio, and a
    # per-ticket summary -- useful for debugging memory pressure.
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

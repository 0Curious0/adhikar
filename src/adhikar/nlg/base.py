from abc import ABC, abstractmethod


class ConversationProvider(ABC):
    @abstractmethod
    async def reply(self, *, system_prompt: str, user_message: str, language_code: str) -> str:
        """Generate one spoken-style reply in `language_code`.

        `system_prompt` is what this particular reply needs to accomplish (e.g. "tell the user
        they're eligible and explain the benefit amount"); `user_message` is the situation or
        context to respond to. Deciding what belongs in each of those is the caller's job —
        this is a generic "produce the right spoken reply" capability, not scheme-aware.
        """
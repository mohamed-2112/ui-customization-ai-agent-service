from typing import Protocol


class LLMClient(Protocol):
    def generate_text(self, *, system_prompt: str, user_prompt: str) -> str:
        """
        Generate text from the configured LLM provider.

        The workflow should depend on this interface,
        not on Hugging Face, OpenAI, Ollama, or any specific provider.
        """
        ...
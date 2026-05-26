from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.core.config import settings


class HuggingFaceLLMClient:
    def __init__(self) -> None:
        if not settings.hf_token:
            raise ValueError(
                "HF_TOKEN is missing. Add it to your .env file before using Hugging Face."
            )

        self.client = OpenAI(
            base_url=settings.hf_base_url,
            api_key=settings.hf_token,
            timeout=settings.llm_timeout_seconds,
        )

    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        retry=retry_if_exception_type(Exception),
        reraise=True,
    )
    def generate_text(self, *, system_prompt: str, user_prompt: str) -> str:
        completion = self.client.chat.completions.create(
            model=settings.hf_model,
            messages=[
                {
                    "role": "system",
                    "content": system_prompt,
                },
                {
                    "role": "user",
                    "content": user_prompt,
                },
            ],
            temperature=settings.llm_temperature,
            max_tokens=settings.llm_max_tokens,
        )

        content = completion.choices[0].message.content

        if not content:
            raise ValueError("The model returned an empty response.")

        return content
import os
from openai import OpenAI
from utils.logger import get_logger

logger = get_logger(__name__)


class LLMError(Exception):
    pass


class DeepSeekClient:
    def __init__(
        self,
        api_key: str | None = None,
        base_url: str = "https://api.deepseek.com",
        model: str = "deepseek-chat",
        max_tokens: int = 300,
        temperature: float = 0.3,
    ):
        self._api_key = api_key or os.environ.get("DEEPSEEK_API_KEY", "")
        self._base_url = base_url
        self._model = model
        self._max_tokens = max_tokens
        self._temperature = temperature
        self._client = OpenAI(api_key=self._api_key, base_url=self._base_url)

    def chat(self, system: str, user: str) -> str:
        try:
            resp = self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                max_tokens=self._max_tokens,
                temperature=self._temperature,
            )
            return resp.choices[0].message.content or ""
        except Exception as e:
            raise LLMError(str(e)) from e

    def is_available(self) -> bool:
        if not self._api_key:
            return False
        try:
            self._client.chat.completions.create(
                model=self._model,
                messages=[{"role": "user", "content": "hi"}],
                max_tokens=1,
                timeout=5,
            )
            return True
        except Exception:
            return False

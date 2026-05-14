"""
LLM Client — wraps Groq API with retry logic and token tracking.
"""
from __future__ import annotations

import time
import logging
from typing import Optional

try:
    from groq import Groq
    _GROQ_AVAILABLE = True
except ImportError:
    _GROQ_AVAILABLE = False
    Groq = None  # type: ignore

from config.settings import GROQ_API_KEY, GROQ_MODEL, TEMPERATURE, MAX_TOKENS

logger = logging.getLogger(__name__)


class LLMClient:
    """Thin wrapper around the Groq chat-completion API."""

    def __init__(
        self,
        api_key: str = GROQ_API_KEY,
        model: str = GROQ_MODEL,
        temperature: float = TEMPERATURE,
        max_tokens: int = MAX_TOKENS,
    ):
        if not _GROQ_AVAILABLE:
            raise ImportError(
                "groq package not installed. Run: pip install groq"
            )
        if not api_key:
            raise ValueError(
                "GROQ_API_KEY is not set. Copy .env.example → .env and add your key."
            )
        self.client = Groq(api_key=api_key)
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens

        # cumulative token counters (for cost-analysis reporting)
        self.total_input_tokens = 0
        self.total_output_tokens = 0

    # ── public API ────────────────────────────────────────────────────────────

    def chat(
        self,
        system_prompt: str,
        user_message: str,
        history: Optional[list[dict]] = None,
        max_retries: int = 3,
    ) -> str:
        """
        Send a chat request to Groq and return the assistant's text reply.

        Parameters
        ----------
        system_prompt : role-specific system instruction
        user_message  : the current user turn
        history       : prior (role, content) turns for multi-round dialogue
        """
        messages = [{"role": "system", "content": system_prompt}]
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": user_message})

        for attempt in range(1, max_retries + 1):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                )
                usage = response.usage
                self.total_input_tokens  += usage.prompt_tokens
                self.total_output_tokens += usage.completion_tokens

                text = response.choices[0].message.content
                logger.debug(
                    "LLM response [%d in / %d out tokens]",
                    usage.prompt_tokens,
                    usage.completion_tokens,
                )
                return text

            except Exception as exc:
                wait = 2 ** attempt
                logger.warning(
                    "Groq API error (attempt %d/%d): %s. Retrying in %ds…",
                    attempt, max_retries, exc, wait,
                )
                if attempt == max_retries:
                    raise
                time.sleep(wait)

    # ── cost helpers ──────────────────────────────────────────────────────────

    def token_summary(self) -> dict:
        return {
            "input_tokens": self.total_input_tokens,
            "output_tokens": self.total_output_tokens,
            "total_tokens": self.total_input_tokens + self.total_output_tokens,
        }

"""Track token usage and estimate cost across LLM calls in a pipeline run."""

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.outputs import LLMResult

# OpenRouter pricing for anthropic/claude-sonnet-4.6 (USD per token)
PRICE_INPUT_PER_TOKEN = 3.0 / 1_000_000
PRICE_OUTPUT_PER_TOKEN = 15.0 / 1_000_000


class TokenUsageCallback(BaseCallbackHandler):
    """Accumulate token usage across all LLM calls in one pipeline run."""

    def __init__(self):
        self.input_tokens = 0
        self.output_tokens = 0

    def on_llm_end(self, response: LLMResult, **kwargs) -> None:
        usage = response.llm_output.get("token_usage", {}) if response.llm_output else {}
        self.input_tokens += usage.get("prompt_tokens", 0)
        self.output_tokens += usage.get("completion_tokens", 0)

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens

    @property
    def estimated_cost_usd(self) -> float:
        return (
            self.input_tokens * PRICE_INPUT_PER_TOKEN
            + self.output_tokens * PRICE_OUTPUT_PER_TOKEN
        )

    def summary(self) -> dict:
        return {
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
            "estimated_cost_usd": round(self.estimated_cost_usd, 6),
        }

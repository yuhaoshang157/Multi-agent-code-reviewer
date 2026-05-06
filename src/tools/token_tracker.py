"""Track token usage and estimate cost across LLM calls in a pipeline run."""

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.outputs import LLMResult

# OpenRouter pricing for anthropic/claude-sonnet-4.6 (USD per token)
PRICE_INPUT_PER_TOKEN = 3.0 / 1_000_000
PRICE_OUTPUT_PER_TOKEN = 15.0 / 1_000_000


class TokenUsageCallback(BaseCallbackHandler):
    """Accumulate token usage across all LLM calls in one pipeline run.

    Tracks both aggregate totals and per-call breakdown so callers can
    attribute token spend to individual pipeline nodes.
    """

    def __init__(self):
        self.input_tokens = 0
        self.output_tokens = 0
        self.calls: list[dict] = []  # per-call breakdown: [{input, output, cost}, ...]

    def on_llm_end(self, response: LLMResult, **kwargs) -> None:
        usage = response.llm_output.get("token_usage", {}) if response.llm_output else {}
        in_tok = usage.get("prompt_tokens", 0)
        out_tok = usage.get("completion_tokens", 0)
        self.input_tokens += in_tok
        self.output_tokens += out_tok
        self.calls.append({
            "input_tokens": in_tok,
            "output_tokens": out_tok,
            "estimated_cost_usd": round(
                in_tok * PRICE_INPUT_PER_TOKEN + out_tok * PRICE_OUTPUT_PER_TOKEN, 6
            ),
        })

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
            "calls": self.calls,  # [planner_call, reviewer_call, reporter_call]
        }

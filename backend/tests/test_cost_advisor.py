import httpx
import pytest
from unittest.mock import patch, MagicMock

from app.pricing import calculate_cost, fits_context_window, get_model_info, UnknownModelError
from app.tokenizers.anthropic_tokenizer import count_anthropic_tokens, AnthropicTokenizerError
from app.agents.pattern_finder import find_patterns
from app.agents.recommender import generate_recommendation


class TestPricing:
    def test_calculates_correct_cost(self):
        cost = calculate_cost("gpt-4o-mini", input_tokens=1_000_000, output_tokens=1_000_000)
        assert cost == 0.15 + 0.60

    def test_zero_tokens_costs_nothing(self):
        assert calculate_cost("gpt-4o", 0, 0) == 0.0

    def test_unknown_model_raises_clear_error(self):
        with pytest.raises(UnknownModelError):
            calculate_cost("not-a-real-model", 100, 100)

    def test_context_window_check(self):
        assert fits_context_window("claude-haiku-4-5", 100_000) is True
        assert fits_context_window("claude-haiku-4-5", 300_000) is False

    def test_get_model_info_returns_full_record(self):
        info = get_model_info("gpt-4o")
        assert "input" in info and "output" in info and "context_window" in info


class TestAnthropicTokenizer:
    def test_returns_input_token_count(self):
        def handler(request):
            return httpx.Response(200, json={"input_tokens": 42})
        client = httpx.Client(transport=httpx.MockTransport(handler))
        assert count_anthropic_tokens("sk-fake", "claude-haiku-4-5", "hello", client=client) == 42

    def test_sends_correct_auth_header_not_bearer(self):
        captured = {}
        def handler(request):
            captured.update(request.headers)
            return httpx.Response(200, json={"input_tokens": 1})
        client = httpx.Client(transport=httpx.MockTransport(handler))
        count_anthropic_tokens("sk-fake-key", "claude-haiku-4-5", "hi", client=client)
        assert captured.get("x-api-key") == "sk-fake-key"

    def test_error_status_raises_clear_exception(self):
        def handler(request):
            return httpx.Response(401, text="unauthorized")
        client = httpx.Client(transport=httpx.MockTransport(handler))
        with pytest.raises(AnthropicTokenizerError):
            count_anthropic_tokens("bad-key", "claude-haiku-4-5", "hi", client=client)


class TestPatternFinder:
    def test_aggregates_correctly_across_providers(self):
        records = [
            {"provider": "openai", "cost_usd": 5.0, "tokens": 1000},
            {"provider": "openai", "cost_usd": 3.0, "tokens": 800},
            {"provider": "anthropic", "cost_usd": 20.0, "tokens": 2000},
        ]
        result = find_patterns(records)
        assert result["total_calls"] == 3
        assert result["total_cost_usd"] == 28.0
        assert result["highest_spend_provider"] == "anthropic"
        assert result["by_provider"]["openai"]["calls"] == 2

    def test_empty_usage_returns_zeroed_summary_not_crash(self):
        result = find_patterns([])
        assert result["total_calls"] == 0
        assert result["highest_spend_provider"] is None


class TestRecommender:
    def test_no_usage_gives_helpful_message_without_calling_llm(self):
        empty_summary = find_patterns([])
        result = generate_recommendation(empty_summary)
        assert "No usage logged" in result

    def test_calls_llm_with_real_usage_and_returns_its_content(self):
        summary = find_patterns([{"provider": "openai", "cost_usd": 10.0, "tokens": 5000}])

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Consider a cheaper model."))]
        mock_client.chat.completions.create.return_value = mock_response

        result = generate_recommendation(summary, client=mock_client)
        assert result == "Consider a cheaper model."
        mock_client.chat.completions.create.assert_called_once()

    def test_empty_llm_response_falls_back_gracefully(self):
        summary = find_patterns([{"provider": "openai", "cost_usd": 1.0, "tokens": 100}])
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content=None))]
        mock_client.chat.completions.create.return_value = mock_response

        result = generate_recommendation(summary, client=mock_client)
        assert "try again" in result.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
"""Tests for the v2 LLM classifier (llm_sieve.py).

Contract under the resilient design:
  * ``classify_posts_batch`` ALWAYS returns one result per input post.
  * On LLM failure, the post is classified by the rule fallback rather
    than dropped.
  * If ``ANTHROPIC_API_KEY`` is missing, every post is routed through the
    rule fallback (the breaker is force-tripped on entry).
"""

from __future__ import annotations

import json
import os
from unittest.mock import MagicMock, patch

import pytest

os.environ.setdefault("DATABASE_URL", "sqlite:///data/reddit_jobs.db")

from src.nlp.llm_sieve import (
    _quick_reject_category,
    classify_post,
    classify_posts_batch,
    openai_available,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_post(post_id: str, title: str, body: str = "") -> dict:
    return {"post_id": post_id, "title": title, "body": body}


def _mock_anthropic_response(payload: dict):
    text_block = MagicMock()
    text_block.text = json.dumps(payload)
    response = MagicMock()
    response.content = [text_block]
    return response


_HIRING_PAYLOAD = {
    "post_category": "hiring",
    "job_type": "Full-time",
    "domain": "Software Engineering",
    "seniority": "Senior",
    "work_mode": "Remote",
    "industry_vertical": "saas",
    "company_stage": "series-a",
    "compensation_min": 150000,
    "compensation_max": 180000,
    "compensation_currency": "USD",
    "compensation_period": "annual",
    "equity_mentioned": True,
    "tech_stack": ["Python", "Postgres", "AWS"],
    "urgency_score": 0.2,
    "confidence": 0.86,
}

_FOR_HIRE_PAYLOAD = {
    "post_category": "for_hire",
    "job_type": "Freelance",
    "domain": "Design & UX",
    "seniority": None,
    "work_mode": None,
    "industry_vertical": None,
    "company_stage": "bootstrapped/indie",
    "compensation_min": None,
    "compensation_max": None,
    "compensation_currency": None,
    "compensation_period": "project",
    "equity_mentioned": False,
    "tech_stack": ["Figma"],
    "urgency_score": 0.1,
    "confidence": 0.74,
}

_ADVICE_PAYLOAD = {
    "post_category": "advice_request",
    "job_type": None,
    "domain": None,
    "seniority": None,
    "work_mode": None,
    "industry_vertical": None,
    "company_stage": None,
    "compensation_min": None,
    "compensation_max": None,
    "compensation_currency": None,
    "compensation_period": None,
    "equity_mentioned": False,
    "tech_stack": ["Go", "Rust"],
    "urgency_score": 0.0,
    "confidence": 0.9,
}


@pytest.fixture(autouse=True)
def _set_api_key(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")


# ---------------------------------------------------------------------------
# Pre-filter
# ---------------------------------------------------------------------------
class TestQuickRejectCategory:
    def test_short_post_other(self):
        assert _quick_reject_category("Hi", "") == "other"

    def test_question_prefix(self):
        assert (
            _quick_reject_category(
                "What is the best framework to choose?",
                "I need advice on picking one for my project",
            )
            == "advice_request"
        )

    def test_meta_marker(self):
        assert (
            _quick_reject_category(
                "[Meta] Weekly hiring thread",
                "Comment with your roles below please.",
            )
            == "discussion"
        )

    def test_hiring_post_passes(self):
        assert (
            _quick_reject_category(
                "[Hiring] Backend Engineer (Remote)",
                "We are looking for a senior backend dev with Python and AWS experience.",
            )
            is None
        )


# ---------------------------------------------------------------------------
# classify_post (single)
# ---------------------------------------------------------------------------
class TestClassifyPost:
    def test_hiring_post_classified(self):
        post = _make_post(
            "h1", "[Hiring] Senior Dev Remote", "We're looking for a senior Python developer."
        )
        mock_client = MagicMock()
        mock_client.messages.create.return_value = _mock_anthropic_response(_HIRING_PAYLOAD)
        with patch("src.nlp.llm_sieve._get_client", return_value=mock_client):
            result = classify_post(post)

        assert result["post_id"] == "h1"
        assert result["post_category"] == "hiring"
        assert result["is_job"] is True
        assert result["llm_classified"] is True

    def test_advice_request_not_a_job(self):
        post = _make_post("a1", "Some real-sounding job title here", "But really an advice request.")
        mock_client = MagicMock()
        mock_client.messages.create.return_value = _mock_anthropic_response(_ADVICE_PAYLOAD)
        with patch("src.nlp.llm_sieve._get_client", return_value=mock_client):
            result = classify_post(post)
        assert result["is_job"] is False
        assert result["post_category"] == "advice_request"


# ---------------------------------------------------------------------------
# classify_posts_batch
# ---------------------------------------------------------------------------
class TestClassifyPostsBatch:
    def test_pre_filter_skips_question_posts(self):
        posts = [
            _make_post("q1", "What is the best framework to choose?",
                       "I need advice on picking one for my project"),
            _make_post("q2", "How do I get a job in tech industry?",
                       "I have been trying for months now to find work"),
        ]
        mock_client = MagicMock()
        with patch("src.nlp.llm_sieve._get_client", return_value=mock_client):
            results = classify_posts_batch(posts)

        mock_client.messages.create.assert_not_called()
        assert len(results) == 2
        for r in results:
            assert r["is_job"] is False
            assert r["llm_classified"] is False

    def test_batch_classifies_real_posts(self):
        posts = [
            _make_post("b1", "[Hiring] Senior Dev Remote",
                       "We are looking for a senior developer"),
            _make_post("b2", "[For Hire] Designer available",
                       "I am a designer available now"),
        ]
        mock_client = MagicMock()
        mock_client.messages.create.side_effect = [
            _mock_anthropic_response(_HIRING_PAYLOAD),
            _mock_anthropic_response(_FOR_HIRE_PAYLOAD),
        ]
        with patch("src.nlp.llm_sieve._get_client", return_value=mock_client):
            results = classify_posts_batch(posts, max_workers=1)

        assert len(results) == 2
        categories = {r["post_category"] for r in results}
        assert "hiring" in categories
        assert "for_hire" in categories

    def test_failed_post_falls_back_to_rule_classifier(self):
        """Posts that fail the LLM call must be classified by the rule
        fallback rather than dropped — the batch always covers every input."""
        posts = [
            _make_post("ok1", "[Hiring] Backend Engineer needed now",
                       "Real job description here with more text."),
            _make_post("bad1", "[Hiring] Another job posting that should still survive",
                       "We're hiring a Python engineer. Apply today."),
        ]
        mock_client = MagicMock()
        mock_client.messages.create.side_effect = [
            _mock_anthropic_response(_HIRING_PAYLOAD),
            RuntimeError("non-retryable failure"),
        ]
        with patch("src.nlp.llm_sieve._get_client", return_value=mock_client):
            results = classify_posts_batch(posts, max_workers=1)

        assert len(results) == 2
        by_id = {r["post_id"]: r for r in results}
        assert by_id["ok1"]["llm_classified"] is True
        # bad1 should have come through the rule fallback.
        assert by_id["bad1"]["llm_classified"] is False
        assert by_id["bad1"]["is_job"] is True   # title has "[Hiring]"

    def test_empty_list_returns_empty(self):
        assert classify_posts_batch([]) == []

    def test_missing_api_key_routes_all_through_fallback(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        posts = [
            _make_post("x1", "[Hiring] Senior Python engineer",
                       "We're hiring a senior Python engineer with AWS experience."),
        ]
        results = classify_posts_batch(posts)
        assert len(results) == 1
        assert results[0]["llm_classified"] is False
        assert results[0]["is_job"] is True


# ---------------------------------------------------------------------------
# openai_available
# ---------------------------------------------------------------------------
class TestOpenaiAvailable:
    def test_true_when_key_set(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
        assert openai_available() is True

    def test_false_when_key_missing(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        assert openai_available() is False

"""Tests for the v2 LLM classifier (llm_sieve.py)."""

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
    """Build a mock Anthropic message response returning the given payload as JSON."""
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

_SCAM_PAYLOAD = {
    "post_category": "scam",
    "job_type": "Contract",
    "domain": None,
    "seniority": None,
    "work_mode": "Remote",
    "industry_vertical": "other",
    "company_stage": "unknown",
    "compensation_min": 200,
    "compensation_max": 200,
    "compensation_currency": "USD",
    "compensation_period": "hourly",
    "equity_mentioned": False,
    "tech_stack": [],
    "urgency_score": 0.4,
    "confidence": 0.88,
}


# ---------------------------------------------------------------------------
# _quick_reject_category()
# ---------------------------------------------------------------------------

class TestQuickRejectCategory:
    def test_too_short_returns_other(self):
        result = _quick_reject_category("Hi", "")
        assert result == "other"

    def test_question_prefix_returns_advice_request(self):
        for prefix in ("what is", "how do i", "should i", "is it worth", "why does"):
            result = _quick_reject_category(
                f"{prefix} the best framework to use",
                "I need advice on picking a framework for my new project",
            )
            assert result == "advice_request", f"Failed for prefix: {prefix!r}"

    def test_title_starting_with_question_mark(self):
        result = _quick_reject_category(
            "? Anyone know about this topic at all?",
            "I have been wondering about this for a long time now",
        )
        assert result == "advice_request"

    def test_meta_marker_returns_discussion(self):
        for marker in ("[meta]", "[discussion]", "[mod post]"):
            result = _quick_reject_category(
                f"{marker} important announcement for all members",
                "Please read this message carefully before posting anything",
            )
            assert result == "discussion", f"Failed for marker: {marker!r}"

    def test_normal_hiring_post_not_rejected(self):
        result = _quick_reject_category(
            "[Hiring] Senior Python Engineer - Remote",
            "We are looking for a senior backend engineer with 5+ years experience.",
        )
        assert result is None

    def test_for_hire_post_not_rejected(self):
        result = _quick_reject_category(
            "[For Hire] Full-stack dev available",
            "Available for freelance projects. React and Node.js.",
        )
        assert result is None

    def test_case_insensitive_question_prefix(self):
        result = _quick_reject_category(
            "What is the best language for backend development?",
            "I am trying to decide between several options for my career",
        )
        assert result == "advice_request"


# ---------------------------------------------------------------------------
# classify_post() — single post LLM path
# ---------------------------------------------------------------------------

class TestClassifyPost:
    def test_hiring_post_fields(self):
        post = _make_post(
            "h1",
            "[Hiring] Senior Backend Engineer (Python) - Remote - $150k-$180k",
            "Acme Analytics (Series A) is hiring. Stack: Python, Postgres, AWS. Equity available.",
        )
        mock_client = MagicMock()
        mock_client.messages.create.return_value = _mock_anthropic_response(_HIRING_PAYLOAD)

        with patch("src.nlp.llm_sieve._get_client", return_value=mock_client):
            result = classify_post(post)

        assert result["post_id"] == "h1"
        assert result["post_category"] == "hiring"
        assert result["is_job"] is True
        assert result["domain"] == "Software Engineering"
        assert result["seniority"] == "Senior"
        assert result["work_mode"] == "Remote"
        assert result["compensation_min"] == 150000
        assert result["compensation_max"] == 180000
        assert result["compensation_currency"] == "USD"
        assert result["compensation_period"] == "annual"
        assert result["equity_mentioned"] is True
        assert "Python" in result["tech_stack"]
        assert result["industry_vertical"] == "saas"
        assert result["company_stage"] == "series-a"
        assert result["llm_classified"] is True

    def test_for_hire_post(self):
        post = _make_post(
            "fh1",
            "[For Hire] Freelance Product Designer - UI/UX",
            "Solo designer available for freelance gigs. Figma, mobile apps, dashboards.",
        )
        mock_client = MagicMock()
        mock_client.messages.create.return_value = _mock_anthropic_response(_FOR_HIRE_PAYLOAD)

        with patch("src.nlp.llm_sieve._get_client", return_value=mock_client):
            result = classify_post(post)

        assert result["post_category"] == "for_hire"
        assert result["is_job"] is True  # for_hire counts as a job post
        assert result["equity_mentioned"] is False

    def test_advice_request_not_a_job(self):
        post = _make_post(
            "a1",
            "Should I learn Go or Rust for backend roles?",
            "Looking for advice on which language will help me get a job.",
        )
        mock_client = MagicMock()
        mock_client.messages.create.return_value = _mock_anthropic_response(_ADVICE_PAYLOAD)

        with patch("src.nlp.llm_sieve._get_client", return_value=mock_client):
            result = classify_post(post)

        assert result["post_category"] == "advice_request"
        assert result["is_job"] is False

    def test_scam_post(self):
        post = _make_post(
            "s1",
            "Remote Data Entry - $200/hr - Contact via WhatsApp only",
            "No experience needed. Training available after a small fee. Message +234...",
        )
        mock_client = MagicMock()
        mock_client.messages.create.return_value = _mock_anthropic_response(_SCAM_PAYLOAD)

        with patch("src.nlp.llm_sieve._get_client", return_value=mock_client):
            result = classify_post(post)

        assert result["post_category"] == "scam"
        assert result["is_job"] is False

    def test_compensation_values_cast_to_int(self):
        """LLM may return floats; result must be int or None."""
        payload = dict(_HIRING_PAYLOAD, compensation_min="120000", compensation_max="160000.0")
        post = _make_post("h2", "Backend Engineer", "Some job description text here")
        mock_client = MagicMock()
        mock_client.messages.create.return_value = _mock_anthropic_response(payload)

        with patch("src.nlp.llm_sieve._get_client", return_value=mock_client):
            result = classify_post(post)

        assert isinstance(result["compensation_min"], int)
        assert isinstance(result["compensation_max"], int)

    def test_missing_optional_fields_default_to_none(self):
        minimal_payload = {
            "post_category": "hiring",
            "job_type": "Full-time",
            "domain": "Software Engineering",
            "seniority": None,
            "work_mode": None,
            "industry_vertical": None,
            "company_stage": None,
            "compensation_min": None,
            "compensation_max": None,
            "compensation_currency": None,
            "compensation_period": None,
            "equity_mentioned": False,
            "tech_stack": [],
            "urgency_score": 0.0,
            "confidence": 0.7,
        }
        post = _make_post("h3", "Hiring developers", "Join our team")
        mock_client = MagicMock()
        mock_client.messages.create.return_value = _mock_anthropic_response(minimal_payload)

        with patch("src.nlp.llm_sieve._get_client", return_value=mock_client):
            result = classify_post(post)

        assert result["seniority"] is None
        assert result["industry_vertical"] is None
        assert result["company_stage"] is None
        assert result["tech_stack"] == []

    def test_raises_on_api_error(self):
        post = _make_post("err1", "Some post", "Some body")
        mock_client = MagicMock()
        mock_client.messages.create.side_effect = RuntimeError("API error")

        with patch("src.nlp.llm_sieve._get_client", return_value=mock_client):
            with pytest.raises(RuntimeError):
                classify_post(post)


# ---------------------------------------------------------------------------
# classify_posts_batch()
# ---------------------------------------------------------------------------

class TestClassifyPostsBatch:
    def test_pre_filter_skips_question_posts(self):
        posts = [
            _make_post("q1", "What is the best framework to choose?", "I need advice on picking one for my project"),
            _make_post("q2", "How do I get a job in tech industry?", "I have been trying for months now to find work"),
        ]

        # No LLM calls should be made — pre-filter catches both
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
            _make_post("b1", "[Hiring] Senior Dev Remote", "We are looking for a senior developer"),
            _make_post("b2", "[For Hire] Designer available", "I am a designer available now"),
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

    def test_failed_post_skipped_not_crashed(self):
        posts = [
            _make_post("ok1", "[Hiring] Backend Engineer needed now", "Real job description here"),
            _make_post("bad1", "[Hiring] Another job posting", "This one will fail the API call"),
        ]
        mock_client = MagicMock()
        mock_client.messages.create.side_effect = [
            _mock_anthropic_response(_HIRING_PAYLOAD),
            RuntimeError("timeout"),
        ]

        with patch("src.nlp.llm_sieve._get_client", return_value=mock_client):
            results = classify_posts_batch(posts, max_workers=1)

        # Only the successful one should be in results
        assert len(results) == 1
        assert results[0]["post_id"] == "ok1"

    def test_empty_list_returns_empty(self):
        results = classify_posts_batch([])
        assert results == []

    def test_all_post_categories_map_to_is_job_correctly(self):
        """hiring, for_hire, gig_freelance → is_job=True; everything else → False."""
        job_categories = {"hiring", "for_hire", "gig_freelance"}
        non_job_categories = {"discussion", "advice_request", "rant", "meme", "scam", "other", "cofounder_search"}

        for category in job_categories:
            payload = dict(_HIRING_PAYLOAD, post_category=category)
            post = _make_post(f"cat_{category}", "Some hiring post", "Some body text here")
            mock_client = MagicMock()
            mock_client.messages.create.return_value = _mock_anthropic_response(payload)

            with patch("src.nlp.llm_sieve._get_client", return_value=mock_client):
                result = classify_post(post)

            assert result["is_job"] is True, f"Expected is_job=True for category={category}"

        for category in non_job_categories:
            payload = dict(_ADVICE_PAYLOAD, post_category=category)
            post = _make_post(f"cat_{category}", "Some other post here", "Some body text here")
            mock_client = MagicMock()
            mock_client.messages.create.return_value = _mock_anthropic_response(payload)

            with patch("src.nlp.llm_sieve._get_client", return_value=mock_client):
                result = classify_post(post)

            assert result["is_job"] is False, f"Expected is_job=False for category={category}"


# ---------------------------------------------------------------------------
# openai_available() — now checks ANTHROPIC_API_KEY
# ---------------------------------------------------------------------------

class TestOpenaiAvailable:
    def test_true_when_key_set(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
        assert openai_available() is True

    def test_false_when_key_missing(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        assert openai_available() is False

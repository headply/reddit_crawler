"""Tests for the scam detection module."""

from __future__ import annotations

import json
import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest

_test_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_test_db.close()
os.environ.setdefault("DATABASE_URL", f"sqlite:///{_test_db.name}")

from src.db import get_connection, init_db, insert_classification, insert_post
from src.nlp.scam_detector import _classify_scam, flag_scams, openai_available


@pytest.fixture(autouse=True)
def setup_db():
    """Initialize a fresh test database for each test."""
    init_db()
    yield
    conn = get_connection()
    try:
        conn.execute("DELETE FROM tech_stack")
        conn.execute("DELETE FROM job_classifications")
        conn.execute("DELETE FROM posts")
        conn.commit()
    finally:
        conn.close()


def _make_post(post_id: str, title: str, body: str = "") -> dict:
    return {
        "post_id": post_id,
        "title": title,
        "body": body,
        "author": "tester",
        "subreddit": "forhire",
        "score": 1,
        "num_comments": 0,
        "created_utc": "2025-01-01T00:00:00+00:00",
        "post_url": f"https://reddit.com/r/forhire/{post_id}",
        "scraped_at": "2025-01-01T00:00:00+00:00",
        "flair": None,
    }


def _make_classification(post_id: str, is_scam=None) -> dict:
    return {
        "post_id": post_id,
        "is_job": True,
        "job_type": "Full-time",
        "domain": "Software Engineering",
        "seniority": "Mid",
        "work_mode": "Remote",
        "sentiment_score": 0.0,
        "tech_stack": [],
        "llm_classified": False,
        "post_category": "hiring",
        "industry_vertical": None,
        "company_stage": None,
        "compensation_min": None,
        "compensation_max": None,
        "compensation_currency": None,
        "compensation_period": None,
        "equity_mentioned": False,
        "urgency_score": 0.0,
        "confidence": 0.8,
        "is_scam": is_scam,
        "scam_reasons": None,
    }


def _mock_anthropic_response(is_scam: bool, reasons: list[str], confidence: float):
    """Build a mock Anthropic message response object."""
    payload = json.dumps({"is_scam": is_scam, "reasons": reasons, "confidence": confidence})
    text_block = MagicMock()
    text_block.text = payload
    response = MagicMock()
    response.content = [text_block]
    return response


# ---------------------------------------------------------------------------
# Unit tests — _classify_scam()
# ---------------------------------------------------------------------------

class TestClassifyScam:
    def test_detects_obvious_scam(self):
        post = {
            "post_id": "scam1",
            "title": "Remote Data Entry $200/hr - No Experience",
            "body": "Training fee required. Contact via WhatsApp only. No company listed.",
        }
        mock_response = _mock_anthropic_response(
            is_scam=True,
            reasons=["pay-to-apply training fee", "WhatsApp-only contact"],
            confidence=0.92,
        )
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response

        result = _classify_scam(mock_client, post)

        assert result["is_scam"] is True
        assert len(result["reasons"]) == 2
        assert result["confidence"] == pytest.approx(0.92)
        assert result["post_id"] == "scam1"

    def test_detects_mlm_scam(self):
        post = {
            "post_id": "scam2",
            "title": "Work From Home Unlimited Earnings",
            "body": "Earn by recruiting others. No cap on income. Build your downline.",
        }
        mock_response = _mock_anthropic_response(
            is_scam=True,
            reasons=["MLM/pyramid language", "recruitment-of-recruiters"],
            confidence=0.88,
        )
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response

        result = _classify_scam(mock_client, post)

        assert result["is_scam"] is True

    def test_detects_crypto_scam(self):
        post = {
            "post_id": "scam3",
            "title": "Crypto Wallet Support Analyst",
            "body": "We need access to your seed phrase to verify your wallet for onboarding.",
        }
        mock_response = _mock_anthropic_response(
            is_scam=True,
            reasons=["requests seed phrase / wallet access"],
            confidence=0.97,
        )
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response

        result = _classify_scam(mock_client, post)

        assert result["is_scam"] is True

    def test_legitimate_post_not_flagged(self):
        post = {
            "post_id": "legit1",
            "title": "[Hiring] Senior Python Engineer - Acme Corp - Remote $150k",
            "body": "Acme Corp (Series B) is hiring a senior Python engineer. Apply at careers.acmecorp.com",
        }
        mock_response = _mock_anthropic_response(
            is_scam=False,
            reasons=[],
            confidence=0.05,
        )
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response

        result = _classify_scam(mock_client, post)

        assert result["is_scam"] is False
        assert result["post_id"] == "legit1"

    def test_legitimate_freelance_not_flagged(self):
        post = {
            "post_id": "legit2",
            "title": "[For Hire] Full-stack developer, 5 years exp, React + Node",
            "body": "Available for freelance projects. Portfolio: github.com/myname. Hourly rate $80.",
        }
        mock_response = _mock_anthropic_response(
            is_scam=False,
            reasons=[],
            confidence=0.03,
        )
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response

        result = _classify_scam(mock_client, post)

        assert result["is_scam"] is False

    def test_low_confidence_not_flagged(self):
        """Confidence below 0.6 must force is_scam=False even if LLM said true."""
        post = {
            "post_id": "uncertain1",
            "title": "Remote assistant needed",
            "body": "Flexible hours. DM for details.",
        }
        mock_response = _mock_anthropic_response(
            is_scam=True,
            reasons=["vague description"],
            confidence=0.45,  # below threshold
        )
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response

        result = _classify_scam(mock_client, post)

        assert result["is_scam"] is False


# ---------------------------------------------------------------------------
# Integration tests — flag_scams()
# ---------------------------------------------------------------------------

class TestFlagScams:
    def test_skips_when_no_api_key(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        result = flag_scams()
        assert result["scanned"] == 0
        assert result["flagged"] == 0
        assert result.get("tripped") is True

    def test_processes_unscanned_posts(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

        insert_post(_make_post("p1", "Suspicious Job Ad", "Pay $50 to apply"))
        insert_classification(_make_classification("p1", is_scam=None))

        mock_response = _mock_anthropic_response(
            is_scam=True,
            reasons=["pay-to-apply"],
            confidence=0.9,
        )
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response

        with patch("src.nlp.scam_detector._get_client", return_value=mock_client):
            result = flag_scams()

        assert result["scanned"] == 1
        assert result["flagged"] == 1

    def test_skips_already_scanned_posts(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

        insert_post(_make_post("p2", "Legit Hiring Post", "Real company real job"))
        insert_classification(_make_classification("p2", is_scam=False))

        mock_client = MagicMock()
        with patch("src.nlp.scam_detector._get_client", return_value=mock_client):
            result = flag_scams()

        # Already has is_scam=False, should not be re-processed
        assert result["scanned"] == 0
        mock_client.messages.create.assert_not_called()

    def test_scam_reasons_persisted(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

        insert_post(_make_post("p3", "MLM Opportunity", "Build your downline now"))
        insert_classification(_make_classification("p3", is_scam=None))

        mock_response = _mock_anthropic_response(
            is_scam=True,
            reasons=["MLM language", "recruitment-of-recruiters"],
            confidence=0.85,
        )
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response

        with patch("src.nlp.scam_detector._get_client", return_value=mock_client):
            flag_scams()

        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT is_scam, scam_reasons FROM job_classifications WHERE post_id='p3'"
            )
            row = cursor.fetchone()
        finally:
            conn.close()

        assert row[0] is True or row[0] == 1
        reasons = json.loads(row[1])
        assert "MLM language" in reasons


# ---------------------------------------------------------------------------
# openai_available() — kept as-is, now checks ANTHROPIC_API_KEY
# ---------------------------------------------------------------------------

class TestOpenaiAvailable:
    def test_returns_true_when_key_set(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
        assert openai_available() is True

    def test_returns_false_when_key_missing(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        assert openai_available() is False

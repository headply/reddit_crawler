"""Tests for the NLP enrichment module."""

import pytest

from src.nlp.enrichment import (
    classify_domain,
    classify_is_job,
    classify_job_type,
    classify_seniority,
    classify_work_mode,
    compute_sentiment,
    compute_urgency,
    enrich_post,
    extract_tech_stack,
)


class TestJobClassification:
    """Tests for job detection classifier."""

    def test_hiring_post_detected(self):
        assert classify_is_job("[Hiring] Python Developer Needed", "") is True

    def test_for_hire_post_rejected(self):
        assert classify_is_job("[For Hire] Developer looking for work", "") is False

    def test_job_opening_detected(self):
        assert classify_is_job(
            "Job Opening: Data Analyst",
            "We are looking for a data analyst to join our team. Apply now.",
        ) is True

    def test_career_advice_rejected(self):
        assert classify_is_job(
            "Should I learn Python or JavaScript?",
            "I need career advice on which language to learn first.",
        ) is False


class TestJobTypeClassification:
    """Tests for job type classification."""

    def test_full_time(self):
        assert classify_job_type("Full-time Software Engineer", "") == "Full-time"

    def test_contract(self):
        assert classify_job_type("Contract Developer Needed", "") == "Contract"

    def test_freelance(self):
        assert classify_job_type("Freelance Designer Wanted", "") == "Freelance"

    def test_internship(self):
        assert classify_job_type("Summer Internship Program", "") == "Internship"


class TestSeniorityClassification:
    """Tests for seniority level classification."""

    def test_junior(self):
        assert classify_seniority("Junior Developer Position", "") == "Junior"

    def test_senior(self):
        assert classify_seniority("Senior Engineer", "") == "Senior"

    def test_lead(self):
        assert classify_seniority("Lead Architect Role", "") == "Lead"


class TestDomainClassification:
    """Tests for domain classification."""

    def test_data(self):
        assert classify_domain("Data Scientist Position", "") == "Data"

    def test_software(self):
        assert classify_domain("Software Developer", "") == "Software"

    def test_design(self):
        assert classify_domain("UX Designer", "") == "Design"

    def test_marketing(self):
        assert classify_domain("Digital Marketing Manager", "") == "Marketing"


class TestWorkModeClassification:
    """Tests for work mode classification."""

    def test_remote(self):
        assert classify_work_mode("Remote Python Developer", "") == "Remote"

    def test_onsite(self):
        assert classify_work_mode("On-site Java Developer", "") == "On-site"

    def test_hybrid(self):
        assert classify_work_mode("Hybrid work model", "") == "Hybrid"


class TestTechStackExtraction:
    """Tests for technology extraction."""

    def test_extract_python(self):
        techs = extract_tech_stack("Python Developer", "Experience with Python and Django")
        assert "Python" in techs
        assert "Django" in techs

    def test_extract_multiple(self):
        techs = extract_tech_stack(
            "Full Stack Developer",
            "Must know React, Node.js, and AWS",
        )
        assert "React" in techs
        assert "Node.js" in techs
        assert "AWS" in techs

    def test_no_techs(self):
        techs = extract_tech_stack("Looking for a manager", "Leadership role")
        assert len(techs) == 0


class TestSentiment:
    """Tests for sentiment analysis."""

    def test_positive_sentiment(self):
        score = compute_sentiment("Amazing opportunity!", "Great team, excellent benefits")
        assert score > 0

    def test_negative_sentiment(self):
        score = compute_sentiment("Terrible job", "Awful working conditions, bad pay")
        assert score < 0


class TestUrgency:
    """Tests for urgency scoring."""

    def test_urgent_post(self):
        score = compute_urgency("URGENT: Need developer ASAP", "Start immediately, deadline today")
        assert score > 0.3

    def test_non_urgent_post(self):
        score = compute_urgency("Open position", "We are hiring for our team")
        assert score < 0.2


class TestEnrichPost:
    """Tests for the full enrichment pipeline."""

    def test_enrich_job_post(self):
        post = {
            "post_id": "test123",
            "title": "[Hiring] Senior Python Developer - Remote",
            "body": "We are looking for a senior Python developer with AWS experience. Apply now!",
        }
        result = enrich_post(post)

        assert result["post_id"] == "test123"
        assert result["is_job"] is True
        assert result["work_mode"] == "Remote"
        assert "Python" in result["tech_stack"]
        assert "sentiment_score" in result
        assert "urgency_score" in result

    def test_enrich_non_job_post(self):
        post = {
            "post_id": "test456",
            "title": "Should I learn React or Angular?",
            "body": "Career advice needed. Which framework is better for jobs?",
        }
        result = enrich_post(post)

        assert result["post_id"] == "test456"
        assert result["is_job"] is False
        assert result["tech_stack"] == []

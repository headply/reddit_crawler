"""High-precision fallback enrichment tests.

The single most important guarantee: when the LLM is offline and the rule
fallback runs, no question, advice request, rant, or meta-thread is
classified as a real hiring or for-hire opportunity.
"""

import pytest

from src.nlp.enrichment import RULE_CONFIDENCE, classify_post_fallback, enrich_post


# ---------------------------------------------------------------------------
# Posts that MUST NOT be classified as hiring / for_hire / gig_freelance.
# Each entry: (id, title, body, expected_category_or_set)
# ---------------------------------------------------------------------------
NEVER_A_JOB = [
    ("q1", "Should I learn Go or Rust for backend roles?", "Advice please."),
    ("q2", "What is the best path into ML?", "I want to switch careers."),
    ("q3", "How do I prepare for the Google interview?", "Got an onsite next week."),
    ("q4", "Anyone else hate take-home assignments?", "Just venting."),
    ("q5", "Has anyone worked at a Series A startup?", "Considering an offer."),
    ("q6", "Should I take the senior offer at 180k or stay?", "Comparing offers."),
    ("q7", "Am I cooked? 200 applications, 0 callbacks", "Job search update."),
    ("q8", "?Need help choosing between two Python jobs", "Both look good."),
    ("rant1", "Rant: I quit my job after a year of being underpaid", "Just frustrated."),
    ("rant2", "Vent: got laid off this morning", "Anyone hiring?"),
    ("rant3", "Recruiter ghosted me after the final round", "So pissed."),
    ("rant4", "Interview experience at Big Co: brutal coding challenge", "Wow."),
    ("meta1", "[Meta] Weekly hiring thread - October 2026", "Post your jobs."),
    ("meta2", "Weekly thread: Who's hiring?", "Comment with roles."),
    ("meta3", "Megathread: salary transparency 2026", "Share comp."),
    # Body has hiring keyword but title is a question — must stay non-job.
    ("body1",
     "Is it worth switching to data engineering?",
     "We are hiring engineers but I'm asking for advice on if I should pivot."),
    # Body claims to be hiring but title is rant — must stay non-job.
    ("body2",
     "Frustrated with how I got fired",
     "We're hiring at my old company but I would never recommend them."),
    # Looks like a job but is a coding-challenge rant.
    ("ch1",
     "Take-home coding challenge took me 14 hours, am I cooked?",
     "Senior Python role at Acme. Why is this so hard?"),
]

# Posts that MUST be recognised as real opportunities by the fallback.
ARE_JOBS = [
    ("h1",
     "[Hiring] Senior Backend Engineer (Python) - Remote - $150-180k",
     "Acme Analytics is hiring a senior backend engineer. Stack: Python, Postgres, AWS.",
     "hiring"),
    ("h2",
     "We're hiring a Mid-level React Developer in Berlin",
     "Hybrid 3 days in office. Strong TypeScript experience required.",
     "hiring"),
    ("h3",
     "Now hiring: DevOps Engineer (Remote, Contract)",
     "Kubernetes, Terraform, AWS. 6-month contract with extension.",
     "hiring"),
    ("h4",
     "Open position: Junior Data Analyst at FinTech startup",
     "SQL and Tableau required. 1-3 years experience.",
     "hiring"),
    ("h5",
     "Looking to hire freelance UI/UX Designer",
     "Need a Figma designer for a 2-week dashboard project. Remote.",
     "hiring"),
    ("fh1",
     "[For Hire] Senior Python developer, 8 yrs experience",
     "I'm available for freelance gigs. Django, FastAPI, AWS. $80/hr.",
     "for_hire"),
    ("fh2",
     "Available for hire — full-stack engineer",
     "10 years experience. React, Node, Postgres. Open to remote contracts.",
     "for_hire"),
    ("g1",
     "[Gig] Need a logo designer for $200",
     "Quick one-off project. Adobe Illustrator. 3-day turnaround.",
     "gig_freelance"),
]


@pytest.mark.parametrize("post_id,title,body", [
    (pid, title, body) for pid, title, body in NEVER_A_JOB
])
def test_never_classifies_question_or_rant_as_job(post_id, title, body):
    """The single most important guarantee of the fallback."""
    result = classify_post_fallback(title, body)
    assert result["is_job"] is False, (
        f"{post_id!r}: title {title!r} was wrongly classified as a job. "
        f"Got category={result['post_category']!r}."
    )
    assert result["post_category"] not in {"hiring", "for_hire", "gig_freelance"}


@pytest.mark.parametrize("post_id,title,body,expected_category", [
    (pid, title, body, cat) for pid, title, body, cat in ARE_JOBS
])
def test_recognises_real_opportunities(post_id, title, body, expected_category):
    result = classify_post_fallback(title, body)
    assert result["is_job"] is True, (
        f"{post_id!r}: title {title!r} was wrongly marked non-job. "
        f"Got category={result['post_category']!r}."
    )
    assert result["post_category"] == expected_category


def test_rule_confidence_is_stamped():
    """Every fallback row must carry the rule-confidence sentinel so the
    LLM upgrade task picks it up later."""
    result = classify_post_fallback(
        "[Hiring] Backend engineer", "We are hiring. Python, AWS."
    )
    assert result["confidence"] == RULE_CONFIDENCE


def test_for_hire_focused_sub_skips_length_floor():
    """`r/forhire` posts are often terse; they must still pass on title tag."""
    result = classify_post_fallback(
        "[Hiring] Logo for $50",
        "Need a logo. DM.",
        subreddit="forhire",
    )
    assert result["is_job"] is True
    assert result["post_category"] == "hiring"


def test_short_post_without_focused_sub_is_rejected():
    result = classify_post_fallback(
        "[Hiring] Designer",
        "DM me.",
        subreddit="webdev",
    )
    # Title-tag exists but combined length < 80 chars and sub isn't in
    # for_hire_focused → falls through to 'other'.
    assert result["is_job"] is False


def test_enrich_post_preserves_post_id():
    out = enrich_post({
        "post_id": "abc123",
        "title": "[Hiring] Senior Python Developer - Remote",
        "body": "Acme is hiring. Python and AWS. Apply via our site.",
        "subreddit": "PythonJobs",
    })
    assert out["post_id"] == "abc123"
    assert out["is_job"] is True
    assert "Python" in out["tech_stack"]
    assert out["work_mode"] == "Remote"
    assert out["confidence"] == RULE_CONFIDENCE


def test_double_negative_signal_demotes_to_discussion():
    """Even with a hiring tag, posts loaded with rant signals stay non-job."""
    result = classify_post_fallback(
        "[Hiring] but applied to 100 jobs, recruiter ghosted, am i cooked",
        "Honestly just a rant about how my interview experience went.",
    )
    assert result["is_job"] is False

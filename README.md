# Reddit Job Intelligence

A platform that monitors Reddit job communities around the clock, filters out the noise, and surfaces only real job opportunities through a fast, well-designed dashboard.

Reddit is one of the most active places where companies and individuals post job openings, but the signal-to-noise ratio is terrible. Career advice threads, job seekers advertising themselves, rants, and memes all live alongside genuine hiring posts. This platform solves that by automatically scraping, classifying, and presenting only the posts that matter.

---

## What it shows you

- Real job postings pulled from ~95 active subreddits, refreshed twice a day
- Each post classified by domain, seniority, work mode, job type, salary, and tech stack
- Scam-flagged posts hidden by default (toggleable)
- A filterable job board with KPI strip, date pills, and per-facet search
- Analytics on hiring trends, in-demand skills, salary distribution by role, and where activity is concentrated
- Tech demand over time, a tech × domain heatmap, and the most common tech combinations
- A "Sources" page showing which subreddits actually produce signal (jobs found per post scraped)

---

## How it works

A scheduled Airflow DAG runs **twice a day** (05:00 and 17:00 UTC). It scrapes new posts from Reddit, deduplicates them, classifies each one with Claude Haiku, runs scam detection, refreshes materialised views, and purges old raw bodies.

The classification path is **resilient**: each LLM call retries on transient errors, and a per-run circuit breaker routes the remainder of a batch through a high-precision rule fallback once the LLM is clearly down. The pipeline never fails because of an LLM issue. When the LLM comes back, a `reclassify_pending` task upgrades the rule-classified rows on the next run.

The rule fallback is precision-first: it **never classifies a question, advice request, or rant as a job**, even if the post happens to contain the word "hiring". It requires an explicit hiring tag (`[Hiring]`, `we're hiring`, `looking to hire`, etc.) in the title.

---

## Architecture

```
┌──────────────┐                     ┌─────────────────────────────────┐
│  Caddy :443  │ ─redditjobs───────▶ │  dashboard :8501                │
│              │                     │  uvicorn → src.api.main         │
│              │                     │   /api/*  → FastAPI routers     │
│              │                     │   /assets → static SPA files    │
│              │                     │   /*      → SPA fallback        │
│              │ ─airflow.redditjobs▶│  airflow :8080                  │
└──────────────┘                     └─────────────────────────────────┘
                                              │ Postgres
                                              ▼
                                     posts / job_classifications /
                                     tech_stack / subreddit_health
                                     + materialised views
```

Stack:
- **Pipeline:** Python, PRAW, Anthropic SDK (Claude Haiku), Postgres
- **Orchestration:** Airflow (LocalExecutor) running in its own container
- **Dashboard backend:** FastAPI (uvicorn) — single binary, port 8501
- **Dashboard frontend:** React + TypeScript + Vite + Tailwind, served as static files by the same FastAPI process

---

## Dashboard

Four tabs:

**Browse** — Paginated job cards with badges (domain, seniority, work mode, type), salary chip, urgency flag, scam flag, tech pills. Sidebar facets: time range, search, scam toggle, confidence threshold, domain, job type, seniority, work mode, tech, subreddit.

**Analytics** — Volume over time, top subreddits, domain donut, work-mode donut, seniority bars, job-type bars, top 20 in-demand skills, salary distribution by (domain × seniority).

**Tech Trends** — Weekly demand for the top 8 technologies, a tech × domain heatmap, and the most common tech pairs.

**Sources** — Per-subreddit table showing jobs found, posts scraped, scams flagged, job-rate ratio, last scraped time. Helps the operator see which sources actually produce signal.

---

## Subreddits monitored

Grouped in [src/config.py](src/config.py) — covers tech job boards, broader tech communities, non-tech (marketing/sales/design/finance/accounting), engineering (non-software), healthcare, HR/recruiting, customer success, regional (Africa, India, LATAM, Asia), remote-specific, and for-hire-focused boards. Noisy or question-heavy communities pass through a strict include-keyword filter so only posts with an explicit hiring marker reach the database.

---

## Setup

### Local development

```bash
git clone https://github.com/headply/reddit_crawler.git
cd reddit_crawler

# Backend
python -m venv .venv && . .venv/Scripts/activate    # or `.venv/bin/activate` on bash
pip install -r requirements.txt
cp .env.example .env
# Fill REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, DATABASE_URL, ANTHROPIC_API_KEY

# Run the pipeline once
python -m src.pipeline.run

# Serve the API (port 8501)
uvicorn src.api.main:app --reload --port 8501

# In another terminal — frontend dev server with proxy → :8501
cd frontend
npm ci
npm run dev      # http://localhost:5173
```

### Docker (production)

```bash
docker compose build
docker compose up -d
```

- Dashboard at `https://redditjobs.{your-domain}` (Caddy reverse-proxy on port 80/443)
- Airflow UI at `https://airflow.redditjobs.{your-domain}` (basic-auth via `CADDY_BASIC_AUTH_HASH`)

### Wipe and start fresh

```bash
python scripts/clear_data.py
```

---

## Resilience guarantees

- **LLM down? Pipeline still completes.** Per-run circuit breaker + tenacity-style retries. After N consecutive failures, the remainder of the batch is classified by the rule fallback. The DAG run is marked successful.
- **Question / advice posts never become "jobs".** The rule fallback applies a hard-veto layer (question prefixes, meta markers, rant markers) before any positive scoring, and requires an explicit hiring tag in the title for the post to be a job.
- **Failed LLM rows get upgraded later.** The `reclassify_pending` DAG task re-runs the LLM on rows that were initially rule-classified, but only when the LLM is available.
- **Twice-daily schedule** at `0 5,17 * * *` UTC. `max_active_runs=1` prevents overlap.

---

## Testing

```bash
pytest                          # 100 tests
pytest tests/test_nlp.py        # fallback precision (question/rant safety)
pytest tests/test_circuit_breaker.py
```

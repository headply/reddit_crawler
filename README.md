# Reddit Job Intelligence Platform

An automated pipeline that scrapes Reddit job communities daily, classifies posts using GPT-4o-mini, and surfaces clean job listings through an interactive Streamlit dashboard.

---

## What It Does

- Scrapes 24 targeted subreddits every day via GitHub Actions
- Passes each post through GPT-4o-mini to determine if it is a real job opportunity (not career advice, job seeking, or discussion)
- Classifies confirmed job posts by domain, seniority, work mode, job type, and tech stack
- Stores results in a PostgreSQL database (Supabase)
- Serves a filterable job board and analytics dashboard on Streamlit Cloud

---

## Tech Stack

- **Scraping:** PRAW (Reddit API)
- **Classification:** OpenAI GPT-4o-mini
- **Database:** PostgreSQL via Supabase (SQLite for local dev)
- **Dashboard:** Streamlit + Plotly
- **Automation:** GitHub Actions (daily cron at 06:00 UTC)

---

## Project Structure

```
reddit_crawler/
├── src/
│   ├── scrape/
│   │   └── reddit_scraper.py      # PRAW scraping logic
│   ├── nlp/
│   │   ├── llm_sieve.py           # GPT-4o-mini classifier
│   │   └── enrichment.py          # Rule-based fallback
│   ├── pipeline/
│   │   └── run.py                 # Orchestrator (scrape + classify + store)
│   ├── dashboard/
│   │   └── app.py                 # Streamlit dashboard
│   ├── db.py                      # Database connections and queries
│   └── config.py                  # Subreddits, domains, keyword patterns
├── data/
│   ├── schema.sql                 # SQLite schema (local dev)
│   └── schema_postgres.sql        # PostgreSQL schema (Supabase)
├── scripts/
│   └── clear_data.py              # Wipe all data for a fresh start
├── .github/
│   └── workflows/
│       └── daily_scrape.yml       # GitHub Actions workflow
├── .env.example
└── requirements.txt
```

---

## Setup

### 1. Clone and install

```bash
git clone https://github.com/headply/reddit_crawler.git
cd reddit_crawler
pip install -r requirements.txt
```

### 2. Environment variables

Copy `.env.example` to `.env` and fill in your credentials:

```bash
cp .env.example .env
```

Required variables:

| Variable | Description |
|---|---|
| `REDDIT_CLIENT_ID` | From https://www.reddit.com/prefs/apps |
| `REDDIT_CLIENT_SECRET` | From https://www.reddit.com/prefs/apps |
| `REDDIT_USER_AGENT` | Any string, e.g. `reddit-job-intel/1.0` |
| `DATABASE_URL` | PostgreSQL connection string from Supabase |
| `OPENAI_API_KEY` | From https://platform.openai.com/api-keys |

### 3. Set up the database

Run the schema in your Supabase SQL editor:

```sql
-- Copy contents of data/schema_postgres.sql and run it in Supabase
```

### 4. Run the pipeline locally

```bash
python -m src.pipeline.run
```

### 5. Run the dashboard locally

```bash
streamlit run src/dashboard/app.py
```

---

## Deployment

### GitHub Actions (automated daily scraping)

Add these as repository secrets under Settings > Secrets and variables > Actions:

- `REDDIT_CLIENT_ID`
- `REDDIT_CLIENT_SECRET`
- `REDDIT_USER_AGENT`
- `DATABASE_URL`
- `OPENAI_API_KEY`

The workflow runs automatically at 06:00 UTC every day. You can also trigger it manually from the Actions tab.

### Streamlit Cloud (dashboard hosting)

1. Connect your GitHub repo on https://streamlit.io/cloud
2. Set the main file path to `src/dashboard/app.py`
3. Add `DATABASE_URL` to your Streamlit secrets

---

## Dashboard Features

**Browse Jobs tab**
- Paginated job cards with title, domain badge, seniority, work mode, job type, and tech tags
- Filters: date range, keyword search, domain, seniority, work mode, tech stack, subreddit
- Sorted by most recent

**Analytics tab**
- Job volume over time (area chart)
- Top subreddits by job count
- Domain breakdown (donut chart)
- Work mode split (Remote / Hybrid / On-site)
- Seniority distribution
- Job type breakdown
- Top 20 in-demand skills

**Tech Trends tab**
- Weekly demand for the top 8 technologies (line chart)
- Tech skills by domain (heatmap)
- Most common technology combinations

---

## Supported Subreddits

| Category | Subreddits |
|---|---|
| Dedicated job boards | forhire, jobbit, remotejobs, techjobs, datajobs |
| Specialised | PythonJobs, webdevjobs, reactjobs, MLjobs, devopsjobs, cybersecurityjobs, uxjobs, gamedevjobs |
| Tech communities | webdev, dataengineering, devops, MachineLearning, androiddev, iOSProgramming, netsec |
| Remote / Freelance | freelance, workonline, digitalnomad |

---

## Job Domains

Software Engineering, Data & Analytics, AI / Machine Learning, DevOps & Cloud, Mobile, Design & UX, Product Management, Marketing & Growth, Security, Game Development, Blockchain & Web3, QA & Testing, Finance & FinTech

---

## Utilities

### Clear all data

Run this before a fresh scrape to wipe the database:

```bash
python scripts/clear_data.py
```

---

## Notes

- The LLM classifier (GPT-4o-mini) costs roughly $0.001 per 100 posts classified.
- If `OPENAI_API_KEY` is not set, the pipeline falls back to rule-based keyword classification automatically.
- GitHub disables scheduled workflows on repositories with no activity for 60 days. Trigger a manual run from the Actions tab to re-enable the schedule.
- The database schema must be re-run on Supabase if you are setting up fresh or need to add the `confidence` and `llm_classified` columns.

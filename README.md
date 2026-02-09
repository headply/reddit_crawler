# Reddit Job Intelligence Platform

An automated pipeline that scrapes Reddit job communities daily, classifies and enriches posts using NLP, stores results in a relational database, and presents interactive insights through a polished Streamlit dashboard.

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                    GitHub Actions (cron: daily)                  │
│                                                                  │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐       │
│  │   Scraper    │───>│  NLP Engine  │───>│   Database   │       │
│  │  (PRAW API)  │    │ (Enrichment) │    │   (SQLite)   │       │
│  └──────────────┘    └──────────────┘    └──────┬───────┘       │
│                                                  │               │
└──────────────────────────────────────────────────┼───────────────┘
                                                   │
                                          ┌────────▼────────┐
                                          │    Dashboard     │
                                          │   (Streamlit)    │
                                          │                  │
                                          │  - Filters       │
                                          │  - Charts        │
                                          │  - Hot Jobs      │
                                          │  - Data Table    │
                                          └─────────────────┘
```

## Tech Stack

| Layer          | Technology                          |
|----------------|-------------------------------------|
| Scraping       | PRAW (Python Reddit API Wrapper)    |
| NLP            | TextBlob, rule-based classifiers    |
| Database       | SQLite (local) / PostgreSQL (prod)  |
| Dashboard      | Streamlit, Plotly                   |
| Automation     | GitHub Actions                      |
| Language       | Python 3.11+                        |

## How the Pipeline Works

### 1. Scraping Layer (`src/scrape/`)
- Connects to Reddit via PRAW using OAuth2 credentials
- Iterates through **10 configurable subreddits**: r/forhire, r/jobs, r/remotework, r/remotejobs, r/datajobs, r/cscareerquestions, r/techjobs, r/jobbit, r/workonline, r/freelance
- Fetches up to 100 new posts per subreddit per run
- **Deduplicates** by checking `post_id` against existing records
- Stores: `post_id`, `title`, `body`, `author`, `subreddit`, `score`, `num_comments`, `created_utc`, `post_url`

### 2. NLP & Enrichment Layer (`src/nlp/`)
For each scraped post, the enrichment engine:

| Feature           | Method                                          | Output                                 |
|-------------------|-------------------------------------------------|----------------------------------------|
| Job Detection     | Keyword scoring (positive vs negative signals)  | Boolean (is this a real job listing?)   |
| Job Type          | Pattern matching against employment keywords    | Full-time / Contract / Freelance / etc. |
| Seniority         | Pattern matching against level keywords         | Junior / Mid / Senior / Lead            |
| Domain            | Pattern matching against industry keywords      | Data / Software / Design / Marketing    |
| Work Mode         | Pattern matching against location keywords      | Remote / Hybrid / On-site               |
| Tech Stack        | Keyword extraction from 40+ technology patterns | List of technologies mentioned          |
| Sentiment Score   | TextBlob polarity analysis                      | -1.0 to 1.0                            |
| Urgency Score     | Urgency keyword ratio heuristic                 | 0.0 to 1.0                             |

### 3. Database Layer (`data/schema.sql`)
Three normalized tables with proper indexing:
- **`posts`** – Raw scraped data with unique constraint on `post_id`
- **`job_classifications`** – Enrichment results linked by `post_id`
- **`tech_stack`** – Many-to-many technology mentions

### 4. Dashboard (`src/dashboard/`)
Interactive Streamlit dashboard with:
- **Sidebar filters**: Job type, domain, work mode, tech stack
- **Metric cards**: Total jobs, avg sentiment, subreddit count, tech count
- **Charts**: Job volume over time, top skills bar chart, sentiment histogram, domain pie chart
- **Hot Jobs section**: High urgency + positive sentiment posts with clickable links
- **Data table**: Full listing with sortable columns and direct Reddit links
- **Material Design icons** (no emojis) and custom CSS styling

## Project Structure

```
reddit-job-intel/
├── data/
│   └── schema.sql              # Database schema
├── src/
│   ├── config.py               # Patterns, keywords, constants
│   ├── db.py                   # Database connection & operations
│   ├── scrape/
│   │   └── reddit_scraper.py   # PRAW-based Reddit scraper
│   ├── nlp/
│   │   └── enrichment.py       # NLP classification & scoring
│   ├── pipeline/
│   │   └── run.py              # Pipeline orchestrator
│   └── dashboard/
│       └── app.py              # Streamlit dashboard
├── tests/
│   ├── test_db.py              # Database tests
│   └── test_nlp.py             # NLP enrichment tests
├── .github/workflows/
│   └── daily_scrape.yml        # Daily automation
├── .env.example                # Environment variable template
├── .gitignore
├── requirements.txt
└── README.md
```

## Setup & Local Development

### Prerequisites
- Python 3.11+
- Reddit API credentials ([create an app](https://www.reddit.com/prefs/apps))

### 1. Clone & Install

```bash
git clone https://github.com/headply/reddit_crawler.git
cd reddit_crawler
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your Reddit API credentials
```

### 3. Run the Pipeline

```bash
# Full pipeline: scrape + enrich
python -m src.pipeline.run

# Enrich only (skip scraping)
python -m src.pipeline.run --skip-scrape
```

### 4. Launch the Dashboard

```bash
streamlit run src/dashboard/app.py
```

### 5. Run Tests

```bash
python -m pytest tests/ -v
```

## Automation (GitHub Actions)

The workflow (`.github/workflows/daily_scrape.yml`) runs daily at 06:00 UTC:

1. Checks out the repository
2. Sets up Python and installs dependencies
3. Downloads the existing database artifact (if any)
4. Runs the full scrape + enrich pipeline
5. Uploads the updated database as an artifact

### Required Secrets

Add these in **Settings > Secrets and variables > Actions**:

| Secret                  | Description                    |
|-------------------------|--------------------------------|
| `REDDIT_CLIENT_ID`      | Reddit app client ID           |
| `REDDIT_CLIENT_SECRET`  | Reddit app client secret       |
| `REDDIT_USER_AGENT`     | User agent string for Reddit   |

## Deployment

### Dashboard (Streamlit Community Cloud)
1. Push the repo to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your repo, set main file path to `src/dashboard/app.py`
4. Add secrets in the Streamlit dashboard settings

### Database
- **Local**: SQLite file at `data/reddit_jobs.db` (auto-created)
- **Production**: Set `DATABASE_URL` to a PostgreSQL connection string (Render / Railway / Supabase free tier)

## Ethical Note on Reddit Data Usage

This project:
- Only collects **publicly available** post data from Reddit
- Uses the **official Reddit API** (PRAW) with proper authentication
- Respects Reddit's **API rate limits** and terms of service
- Does **not** collect private messages, user profiles, or non-public data
- Stores only the minimum data needed for job market analysis
- Is intended for **educational and portfolio purposes**

Please review [Reddit's API Terms](https://www.reddit.com/wiki/api-terms) before deploying.

## Extending the Platform

- **Add subreddits**: Edit `TARGET_SUBREDDITS` in `src/config.py`
- **Add tech keywords**: Extend `TECH_KEYWORDS` in `src/config.py`
- **Switch to PostgreSQL**: Change `DATABASE_URL` in `.env`
- **Add LLM enrichment**: Replace rule-based classifiers in `src/nlp/enrichment.py` with OpenAI / HuggingFace calls
- **Add email alerts**: Hook into the pipeline to send notifications for high-urgency jobs
- **Add salary extraction**: Extend NLP pipeline with regex-based salary parsing

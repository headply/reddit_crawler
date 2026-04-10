# Reddit Job Intelligence

A platform that monitors Reddit job communities around the clock, filters out the noise, and surfaces only real job opportunities through a clean, searchable dashboard.

Reddit is one of the most active places where companies and individuals post job openings, but the signal-to-noise ratio is terrible. Career advice threads, job seekers advertising themselves, rants, and memes all live alongside genuine hiring posts. This platform solves that by automatically scraping, classifying, and presenting only the posts that matter.

---

## What it shows you

- Real job postings pulled from 24 active subreddits, updated daily
- Each post classified by domain, seniority level, work mode, and job type
- Tech stack extracted from every listing
- A filterable job board so you can zero in on what is relevant to you
- Analytics on hiring trends, in-demand skills, and where the activity is concentrated
- Technology demand over time, broken down by week and domain

---

## How it works

A scheduled job runs every day and scrapes new posts from Reddit job communities. Each post goes through an AI classifier that reads the title and body and decides whether it is a genuine job opportunity or not. Posts that pass get tagged with metadata and stored. The dashboard reads from that store in real time.

The result is a clean feed of verified job listings with none of the surrounding noise.

---

## Dashboard

The dashboard has three sections:

**Browse Jobs** -- A paginated list of job cards. Each card shows the title, domain, seniority, work mode, job type, tech stack, score, and how long ago it was posted. Filter by any combination of domain, job type, seniority, work mode, technology, date range, or keyword.

**Analytics** -- Charts showing job volume over time, top subreddits, domain breakdown, work mode split, seniority distribution, job type breakdown, and the top 20 most in-demand skills.

**Tech Trends** -- Weekly demand for the top technologies, a heatmap of which skills appear in which domains, and the most common technology combinations seen together in listings.

---

## Subreddits monitored

Dedicated job boards: forhire, jobbit, remotejobs, techjobs, datajobs, PythonJobs, webdevjobs, reactjobs, MLjobs, devopsjobs, cybersecurityjobs, uxjobs, gamedevjobs

Active communities with regular hiring posts: webdev, dataengineering, devops, MachineLearning, androiddev, iOSProgramming, netsec, freelance, workonline, digitalnomad

---

## Domains tracked

Software Engineering, Data & Analytics, AI and Machine Learning, DevOps and Cloud, Mobile, Design and UX, Product Management, Marketing and Growth, Security, Game Development, Blockchain and Web3, QA and Testing, Finance and FinTech

---

## Setup

```bash
git clone https://github.com/headply/reddit_crawler.git
cd reddit_crawler
pip install -r requirements.txt
cp .env.example .env
# Fill in REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, DATABASE_URL, OPENAI_API_KEY
python -m src.pipeline.run        # run the pipeline
streamlit run src/dashboard/app.py # run the dashboard
```

For deployment, add the same environment variables as GitHub Actions secrets and as Streamlit secrets. The pipeline runs automatically at 06:00 UTC every day via GitHub Actions.

To wipe the database and start fresh:

```bash
python scripts/clear_data.py
```

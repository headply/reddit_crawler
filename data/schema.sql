-- Reddit Job Intelligence Platform - Database Schema
-- Supports SQLite (local dev) and PostgreSQL (production)

-- Raw scraped posts from Reddit
CREATE TABLE IF NOT EXISTS posts (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    post_id         TEXT UNIQUE NOT NULL,
    title           TEXT NOT NULL,
    body            TEXT,
    author          TEXT,
    subreddit       TEXT NOT NULL,
    score           INTEGER DEFAULT 0,
    num_comments    INTEGER DEFAULT 0,
    created_utc     TIMESTAMP NOT NULL,
    post_url        TEXT NOT NULL,
    scraped_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Enriched job classification results
CREATE TABLE IF NOT EXISTS job_classifications (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    post_id         TEXT UNIQUE NOT NULL,
    is_job          BOOLEAN NOT NULL DEFAULT 0,
    job_type        TEXT,          -- Full-time / Contract / Freelance / Internship
    seniority       TEXT,          -- Junior / Mid / Senior / Lead
    domain          TEXT,          -- Data, Software, Design, Marketing, etc.
    work_mode       TEXT,          -- Remote / Hybrid / On-site
    sentiment_score REAL,          -- -1.0 to 1.0
    urgency_score   REAL,          -- 0.0 to 1.0
    classified_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (post_id) REFERENCES posts(post_id)
);

-- Extracted tech stack mentions
CREATE TABLE IF NOT EXISTS tech_stack (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    post_id         TEXT NOT NULL,
    technology      TEXT NOT NULL,
    FOREIGN KEY (post_id) REFERENCES posts(post_id),
    UNIQUE(post_id, technology)
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_posts_subreddit ON posts(subreddit);
CREATE INDEX IF NOT EXISTS idx_posts_created ON posts(created_utc);
CREATE INDEX IF NOT EXISTS idx_classifications_is_job ON job_classifications(is_job);
CREATE INDEX IF NOT EXISTS idx_classifications_domain ON job_classifications(domain);
CREATE INDEX IF NOT EXISTS idx_classifications_work_mode ON job_classifications(work_mode);
CREATE INDEX IF NOT EXISTS idx_tech_stack_technology ON tech_stack(technology);

-- Reddit Job Intelligence Platform - PostgreSQL Schema (Supabase)
--
-- Run this in your Supabase SQL Editor (https://supabase.com/dashboard)
-- to create the required tables before deploying the dashboard.

-- Raw scraped posts from Reddit
CREATE TABLE IF NOT EXISTS posts (
    id              SERIAL PRIMARY KEY,
    post_id         TEXT UNIQUE NOT NULL,
    title           TEXT NOT NULL,
    body            TEXT,
    author          TEXT,
    subreddit       TEXT NOT NULL,
    score           INTEGER DEFAULT 0,
    num_comments    INTEGER DEFAULT 0,
    created_utc     TIMESTAMP NOT NULL,
    post_url        TEXT NOT NULL,
    scraped_at      TIMESTAMP DEFAULT NOW()
);

-- Enriched job classification results
CREATE TABLE IF NOT EXISTS job_classifications (
    id              SERIAL PRIMARY KEY,
    post_id         TEXT UNIQUE NOT NULL,
    is_job          BOOLEAN NOT NULL DEFAULT FALSE,
    job_type        TEXT,
    seniority       TEXT,
    domain          TEXT,
    work_mode       TEXT,
    sentiment_score REAL,
    urgency_score   REAL,
    classified_at   TIMESTAMP DEFAULT NOW(),
    FOREIGN KEY (post_id) REFERENCES posts(post_id)
);

-- Extracted tech stack mentions
CREATE TABLE IF NOT EXISTS tech_stack (
    id              SERIAL PRIMARY KEY,
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

-- Reddit Job Intelligence Platform - V2 Schema Migration (PostgreSQL)
-- Idempotent: safe to run multiple times in Supabase SQL Editor

-- Enable trigram similarity for fuzzy dedupe
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- -------------------------------------------------------------------------
-- posts: new dedup + retention columns
-- -------------------------------------------------------------------------
ALTER TABLE IF EXISTS posts
    ADD COLUMN IF NOT EXISTS content_hash TEXT,
    ADD COLUMN IF NOT EXISTS title_tokens TEXT,
    ADD COLUMN IF NOT EXISTS dedup_status TEXT DEFAULT 'unique',
    ADD COLUMN IF NOT EXISTS canonical_post_id TEXT,
    ADD COLUMN IF NOT EXISTS raw_body_purged_at TIMESTAMP;

CREATE INDEX IF NOT EXISTS idx_posts_content_hash ON posts(content_hash);
CREATE INDEX IF NOT EXISTS idx_posts_dedup_status ON posts(dedup_status);
CREATE INDEX IF NOT EXISTS idx_posts_title_tokens_trgm ON posts USING GIN (title_tokens gin_trgm_ops);

-- -------------------------------------------------------------------------
-- job_classifications: richer fields
-- -------------------------------------------------------------------------
ALTER TABLE IF EXISTS job_classifications
    ADD COLUMN IF NOT EXISTS industry_vertical TEXT,
    ADD COLUMN IF NOT EXISTS company_stage TEXT,
    ADD COLUMN IF NOT EXISTS compensation_min INTEGER,
    ADD COLUMN IF NOT EXISTS compensation_max INTEGER,
    ADD COLUMN IF NOT EXISTS compensation_currency TEXT,
    ADD COLUMN IF NOT EXISTS compensation_period TEXT,
    ADD COLUMN IF NOT EXISTS equity_mentioned BOOLEAN DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS is_scam BOOLEAN DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS scam_reasons TEXT,
    ADD COLUMN IF NOT EXISTS post_category TEXT;

CREATE INDEX IF NOT EXISTS idx_classifications_post_category ON job_classifications(post_category);
CREATE INDEX IF NOT EXISTS idx_classifications_industry_vertical ON job_classifications(industry_vertical);
CREATE INDEX IF NOT EXISTS idx_classifications_company_stage ON job_classifications(company_stage);
CREATE INDEX IF NOT EXISTS idx_classifications_is_scam ON job_classifications(is_scam);

-- -------------------------------------------------------------------------
-- subreddit_health: daily monitoring per subreddit
-- -------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS subreddit_health (
    subreddit TEXT NOT NULL,
    date DATE NOT NULL,
    posts_scraped INTEGER DEFAULT 0,
    jobs_found INTEGER DEFAULT 0,
    scams_flagged INTEGER DEFAULT 0,
    dedup_rate REAL,
    PRIMARY KEY (subreddit, date)
);

-- -------------------------------------------------------------------------
-- Materialized views for analytics
-- -------------------------------------------------------------------------
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_skill_demand_weekly AS
SELECT
    date_trunc('week', p.created_utc)::date AS week,
    ts.technology AS technology,
    COUNT(*) AS mention_count,
    COUNT(DISTINCT p.post_id) AS posts_count
FROM posts p
JOIN tech_stack ts ON p.post_id = ts.post_id
JOIN job_classifications jc ON p.post_id = jc.post_id
WHERE jc.is_job = TRUE
  AND COALESCE(jc.is_scam, FALSE) = FALSE
  AND COALESCE(p.dedup_status, 'unique') = 'unique'
GROUP BY 1, 2;

CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_skill_demand_weekly ON mv_skill_demand_weekly (week, technology);

CREATE MATERIALIZED VIEW IF NOT EXISTS mv_domain_volume_weekly AS
SELECT
    date_trunc('week', p.created_utc)::date AS week,
    jc.domain AS domain,
    COUNT(*) AS post_count
FROM posts p
JOIN job_classifications jc ON p.post_id = jc.post_id
WHERE jc.is_job = TRUE
  AND COALESCE(jc.is_scam, FALSE) = FALSE
  AND COALESCE(p.dedup_status, 'unique') = 'unique'
GROUP BY 1, 2;

CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_domain_volume_weekly ON mv_domain_volume_weekly (week, domain);

CREATE MATERIALIZED VIEW IF NOT EXISTS mv_compensation_by_role AS
SELECT
    jc.domain AS domain,
    jc.seniority AS seniority,
    jc.work_mode AS work_mode,
    COUNT(*) AS count,
    percentile_cont(0.25) WITHIN GROUP (ORDER BY jc.compensation_max) AS p25,
    percentile_cont(0.50) WITHIN GROUP (ORDER BY jc.compensation_max) AS median,
    percentile_cont(0.75) WITHIN GROUP (ORDER BY jc.compensation_max) AS p75
FROM posts p
JOIN job_classifications jc ON p.post_id = jc.post_id
WHERE jc.is_job = TRUE
  AND COALESCE(jc.is_scam, FALSE) = FALSE
  AND COALESCE(p.dedup_status, 'unique') = 'unique'
  AND jc.compensation_max IS NOT NULL
GROUP BY 1, 2, 3;

CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_compensation_by_role ON mv_compensation_by_role (domain, seniority, work_mode);

CREATE MATERIALIZED VIEW IF NOT EXISTS mv_subreddit_quality AS
SELECT
    p.subreddit AS subreddit,
    COUNT(*) AS total_posts,
    SUM(CASE WHEN jc.is_job THEN 1 ELSE 0 END)::float / NULLIF(COUNT(*), 0) AS job_post_rate,
    SUM(CASE WHEN COALESCE(jc.is_scam, FALSE) THEN 1 ELSE 0 END)::float / NULLIF(COUNT(*), 0) AS scam_rate,
    SUM(CASE WHEN p.created_utc >= NOW() - INTERVAL '7 days' THEN 1 ELSE 0 END) AS last_7_days_volume
FROM posts p
LEFT JOIN job_classifications jc ON p.post_id = jc.post_id
WHERE COALESCE(p.dedup_status, 'unique') = 'unique'
GROUP BY 1;

CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_subreddit_quality ON mv_subreddit_quality (subreddit);

export interface MetaResponse {
  total_jobs: number;
  total_posts: number;
  latest_scraped_at: string | null;
  latest_classified_at: string | null;
  llm_classified_pct: number;
  scams_flagged: number;
}

export interface FiltersResponse {
  domains: string[];
  job_types: string[];
  seniorities: string[];
  work_modes: string[];
  techs: string[];
  subreddits: string[];
}

export interface Kpis {
  total_jobs: number;
  new_24h: number;
  remote_pct: number;
  top_domain: string | null;
  tech_skills: number;
}

export interface Job {
  post_id: string;
  title: string;
  excerpt: string | null;
  subreddit: string;
  score: number;
  num_comments: number;
  created_utc: string;
  post_url: string;
  domain: string | null;
  seniority: string | null;
  work_mode: string | null;
  job_type: string | null;
  post_category: string | null;
  industry_vertical: string | null;
  company_stage: string | null;
  compensation_min: number | null;
  compensation_max: number | null;
  compensation_currency: string | null;
  compensation_period: string | null;
  urgency_score: number | null;
  confidence: number | null;
  llm_classified: boolean | null;
  is_scam: boolean | null;
  tech_stack: string[];
}

export interface JobsResponse {
  items: Job[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
  kpis: Kpis;
}

export interface LabelValue { label: string; value: number; }
export interface DateValue { date: string; value: number; }
export interface SalaryBox {
  domain: string;
  seniority: string;
  median: number;
  p25: number;
  p75: number;
  sample_size: number;
}

export interface AnalyticsResponse {
  volume_over_time: DateValue[];
  top_subreddits: LabelValue[];
  domain_breakdown: LabelValue[];
  work_mode_split: LabelValue[];
  seniority_breakdown: LabelValue[];
  job_type_breakdown: LabelValue[];
  top_skills: LabelValue[];
  salary_by_role: SalaryBox[];
}

export interface WeeklyDemandPoint { week: string; tech: string; count: number; }
export interface Heatmap { domains: string[]; techs: string[]; matrix: number[][]; }
export interface TechPair { a: string; b: string; count: number; }
export interface TechTrendsResponse {
  weekly_demand: WeeklyDemandPoint[];
  heatmap: Heatmap;
  pairs: TechPair[];
}

export interface SubredditHealth {
  subreddit: string;
  posts_scraped: number;
  jobs_found: number;
  scams_flagged: number;
  dedup_rate: number | null;
  last_scraped: string | null;
  job_rate: number | null;
}
export interface SubredditHealthResponse {
  items: SubredditHealth[];
  as_of: string;
}

export type DateRange = "today" | "7d" | "30d" | "90d" | "all";

export type PostCategory = "hiring" | "for_hire" | "gig_freelance";

export interface FilterState {
  search: string;
  domain: string[];
  job_type: string[];
  seniority: string[];
  work_mode: string[];
  tech: string[];
  subreddit: string[];
  categories: PostCategory[];
  date_range: DateRange;
  exclude_scams: boolean;
  min_confidence: number;
}

// Default: hiring + gigs (excludes "for hire" self-pitches). Users can
// add for_hire from the top bar.
export const DEFAULT_CATEGORIES: PostCategory[] = ["hiring", "gig_freelance"];

export const EMPTY_FILTERS: FilterState = {
  search: "",
  domain: [],
  job_type: [],
  seniority: [],
  work_mode: [],
  tech: [],
  subreddit: [],
  categories: DEFAULT_CATEGORIES,
  date_range: "30d",
  exclude_scams: true,
  min_confidence: 0,
};

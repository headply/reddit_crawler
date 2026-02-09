"""Configuration constants for the Reddit Job Intelligence Platform."""

from typing import Final

# Target subreddits for scraping
TARGET_SUBREDDITS: Final[list[str]] = [
    "forhire",
    "jobs",
    "remotework",
    "remotejobs",
    "datajobs",
    "cscareerquestions",
    "techjobs",
    "jobbit",
    "workonline",
    "freelance",
]

# Number of posts to fetch per subreddit per run
POSTS_PER_SUBREDDIT: Final[int] = 100

# Tech stack keywords for extraction (lowercase)
TECH_KEYWORDS: Final[dict[str, list[str]]] = {
    "Python": ["python"],
    "JavaScript": ["javascript", "js"],
    "TypeScript": ["typescript", "ts"],
    "Java": ["java"],
    "C++": ["c++", "cpp"],
    "C#": ["c#", "csharp", ".net"],
    "Go": ["golang"],
    "Rust": ["rust"],
    "Ruby": ["ruby", "rails", "ruby on rails"],
    "PHP": ["php"],
    "Swift": ["swift"],
    "Kotlin": ["kotlin"],
    "Scala": ["scala"],
    "R": ["rstudio", "r programming", "r language"],
    "SQL": ["sql", "mysql", "postgresql", "postgres", "sqlite"],
    "NoSQL": ["nosql", "mongodb", "dynamodb", "cassandra", "couchdb"],
    "React": ["react", "reactjs", "react.js"],
    "Angular": ["angular"],
    "Vue.js": ["vue", "vuejs", "vue.js"],
    "Node.js": ["node", "nodejs", "node.js"],
    "Django": ["django"],
    "Flask": ["flask"],
    "FastAPI": ["fastapi"],
    "Spring": ["spring", "spring boot"],
    "Docker": ["docker"],
    "Kubernetes": ["kubernetes", "k8s"],
    "AWS": ["aws", "amazon web services", "ec2", "s3", "lambda"],
    "Azure": ["azure"],
    "GCP": ["gcp", "google cloud"],
    "Terraform": ["terraform"],
    "Jenkins": ["jenkins"],
    "Git": ["git", "github", "gitlab"],
    "Linux": ["linux", "ubuntu", "centos"],
    "TensorFlow": ["tensorflow"],
    "PyTorch": ["pytorch"],
    "Pandas": ["pandas"],
    "Spark": ["spark", "pyspark"],
    "Airflow": ["airflow"],
    "Kafka": ["kafka"],
    "Redis": ["redis"],
    "Elasticsearch": ["elasticsearch", "elastic"],
    "GraphQL": ["graphql"],
    "REST": ["rest api", "restful"],
    "CI/CD": ["ci/cd", "cicd", "continuous integration"],
    "Tableau": ["tableau"],
    "Power BI": ["power bi", "powerbi"],
    "Figma": ["figma"],
    "Jira": ["jira"],
    "Agile": ["agile", "scrum"],
}

# Job type patterns
JOB_TYPE_PATTERNS: Final[dict[str, list[str]]] = {
    "Full-time": ["full-time", "full time", "ft", "permanent", "salaried"],
    "Contract": ["contract", "contractor", "c2c", "w2", "corp-to-corp"],
    "Freelance": ["freelance", "freelancer", "gig", "project-based", "per project"],
    "Internship": ["intern", "internship", "co-op", "coop", "trainee"],
    "Part-time": ["part-time", "part time", "pt"],
}

# Seniority patterns
SENIORITY_PATTERNS: Final[dict[str, list[str]]] = {
    "Junior": ["junior", "jr", "entry level", "entry-level", "associate", "graduate", "new grad"],
    "Mid": ["mid-level", "mid level", "intermediate", "2-5 years", "3+ years"],
    "Senior": ["senior", "sr", "experienced", "5+ years", "7+ years", "lead developer"],
    "Lead": ["lead", "principal", "staff", "architect", "head of", "director", "vp", "manager"],
}

# Domain patterns
DOMAIN_PATTERNS: Final[dict[str, list[str]]] = {
    "Data": ["data engineer", "data scientist", "data analyst", "machine learning", "ml", "ai",
             "analytics", "bi ", "business intelligence", "etl", "data pipeline"],
    "Software": ["software engineer", "software developer", "backend", "frontend", "full stack",
                  "fullstack", "web developer", "mobile developer", "swe", "sde"],
    "DevOps": ["devops", "sre", "site reliability", "infrastructure", "platform engineer",
               "cloud engineer"],
    "Design": ["designer", "ux", "ui", "product design", "graphic design", "figma"],
    "Marketing": ["marketing", "seo", "content", "growth", "social media", "digital marketing"],
    "Product": ["product manager", "product owner", "pm", "program manager"],
    "Security": ["security", "cybersecurity", "infosec", "penetration", "soc analyst"],
    "QA": ["qa", "quality assurance", "test engineer", "testing", "automation test"],
}

# Work mode patterns
WORK_MODE_PATTERNS: Final[dict[str, list[str]]] = {
    "Remote": ["remote", "work from home", "wfh", "anywhere", "distributed", "telecommute"],
    "Hybrid": ["hybrid", "flex", "partially remote", "2 days", "3 days in office"],
    "On-site": ["on-site", "onsite", "in-office", "in office", "on site", "relocate"],
}

# Job indicator patterns (to classify if a post is a real job)
JOB_POSITIVE_PATTERNS: Final[list[str]] = [
    "hiring", "job opening", "we're looking", "we are looking", "job opportunity",
    "apply", "application", "position", "role", "vacancy", "seeking",
    "wanted", "join our team", "open position", "job posting",
    "[hiring]", "[for hire]", "looking to hire", "need a developer",
    "salary", "compensation", "benefits", "equity",
]

JOB_NEGATIVE_PATTERNS: Final[list[str]] = [
    "looking for work", "need a job", "hire me", "for hire",
    "resume review", "career advice", "interview tips",
    "should i", "is it worth", "what should", "how do i",
    "rant", "vent", "frustrated", "quit my job",
    "meme", "joke", "funny",
]

# Urgency indicator patterns
URGENCY_PATTERNS: Final[list[str]] = [
    "asap", "immediately", "urgent", "start now", "right away",
    "start date", "start tomorrow", "this week", "today",
    "need someone", "quickly", "fast", "rush",
    "deadline", "time-sensitive", "limited time",
]

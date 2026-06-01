"""Configuration constants for the Reddit Job Intelligence Platform."""

from typing import Final

# ---------------------------------------------------------------------------
# Target subreddits — grouped for monitoring + per-group volume overrides
# ---------------------------------------------------------------------------
SUBREDDIT_GROUPS: Final[dict[str, list[str]]] = {
    "tech_job_boards": [
        "forhire",
        "jobbit",
        "remotejobs",
        "techjobs",
        "datajobs",
        "PythonJobs",
        "webdevjobs",
        "reactjobs",
        "MLjobs",
        "devopsjobs",
        "cybersecurityjobs",
        "uxjobs",
        "gamedevjobs",
    ],
    "tech_communities": [
        "webdev",
        "dataengineering",
        "devops",
        "MachineLearning",
        "androiddev",
        "iOSProgramming",
        "netsec",
        "freelance",
        "workonline",
        "digitalnomad",
    ],
    "broader_tech": [
        "rust",
        "golang",
        "javascript",
        "learnprogramming",
        "ExperiencedDevs",
        "csMajors",
        "ITCareerQuestions",
        "sysadmin",
        "aws",
        "kubernetes",
        "datascience",
        "analytics",
        "learnmachinelearning",
        "computervision",
        "deeplearning",
        "LLMDevs",
    ],
    "non_tech": [
        "marketing",
        "sales",
        "SEO",
        "contentmarketing",
        "digital_marketing",
        "GraphicDesign",
        "web_design",
        "copywriting",
        "writing",
        "freelanceWriters",
        "accounting",
        "FinanceCareers",
        "ProductManagement",
        "startups",
        "Entrepreneur",
        "smallbusiness",
        "agency",
    ],
    "geo_africa": [
        "nigeria",
        "lagos",
        "kenya",
        "southafrica",
        "tech_jobs_africa",
        "AfricanTech",
    ],
    "geo_india": [
        "developersIndia",
        "indianstartups",
    ],
    "geo_emerging": [
        "brazil",
        "latam",
        "philippines",
    ],
    "remote_specific": [
        "remotework",
        "WorkOnline",
        "beermoney",
        "juststart",
        "slavelabour",
        "HireaWriter",
        "HireanArtist",
        "HireanEditor",
    ],
    "for_hire_focused": [
        "forhire",
        "slavelabour",
        "HireaWriter",
        "HireanArtist",
        "HireanEditor",
        "freelanceWriters",
    ],
}

_TARGETS: list[str] = [s for group in SUBREDDIT_GROUPS.values() for s in group]
TARGET_SUBREDDITS: Final[list[str]] = list(dict.fromkeys(_TARGETS))

# Number of posts to fetch per subreddit per run
POSTS_PER_SUBREDDIT: Final[int] = 50

POSTS_PER_GROUP: Final[dict[str, int]] = {
    "for_hire_focused": 100,
    "geo_africa": 25,
    "geo_india": 25,
    "geo_emerging": 25,
}

SUBREDDIT_TO_GROUP: Final[dict[str, str]] = {
    subreddit: group
    for group, subs in SUBREDDIT_GROUPS.items()
    for subreddit in subs
}

SUBREDDIT_INCLUDE_KEYWORDS: Final[dict[str, list[str]]] = {
    "beermoney": [
        "hiring", "job", "contract", "freelance", "gig",
        "task", "project", "remote", "part-time",
    ]
}

# ---------------------------------------------------------------------------
# Domain categories — used as LLM fallback and for reference
# ---------------------------------------------------------------------------
DOMAIN_PATTERNS: Final[dict[str, list[str]]] = {
    "Software Engineering": [
        "software engineer", "software developer", "backend", "frontend",
        "full stack", "fullstack", "web developer", "swe", "sde",
        "api developer", "systems engineer",
    ],
    "Data & Analytics": [
        "data engineer", "data analyst", "data scientist", "analytics",
        "business intelligence", "bi ", "etl", "data pipeline", "reporting",
        "tableau", "power bi",
    ],
    "AI / Machine Learning": [
        "machine learning", "ml engineer", "ai engineer", "deep learning",
        "nlp", "computer vision", "llm", "generative ai", "data science",
        "research scientist", "pytorch", "tensorflow",
    ],
    "DevOps & Cloud": [
        "devops", "sre", "site reliability", "infrastructure", "platform engineer",
        "cloud engineer", "kubernetes", "terraform", "ci/cd", "aws engineer",
        "azure engineer", "gcp engineer",
    ],
    "Mobile": [
        "ios developer", "android developer", "mobile developer", "swift",
        "kotlin", "react native", "flutter", "mobile engineer",
    ],
    "Design & UX": [
        "designer", "ux", "ui", "product design", "graphic design",
        "figma", "user experience", "visual designer", "interaction design",
    ],
    "Product Management": [
        "product manager", "product owner", "pm ", "program manager",
        "product lead", "head of product",
    ],
    "Marketing & Growth": [
        "marketing", "seo", "content writer", "growth hacker", "social media",
        "digital marketing", "email marketing", "copywriter", "paid ads",
        "sales", "account executive", "account manager", "business development",
    ],
    "Security": [
        "security engineer", "cybersecurity", "infosec", "penetration tester",
        "soc analyst", "appsec", "devsecops", "threat analyst",
    ],
    "Game Development": [
        "game developer", "unity", "unreal", "game designer", "gameplay engineer",
        "game programmer", "3d artist", "level designer",
    ],
    "Blockchain & Web3": [
        "blockchain", "web3", "solidity", "smart contract", "defi", "nft",
        "crypto", "ethereum", "rust blockchain",
    ],
    "QA & Testing": [
        "qa engineer", "quality assurance", "test engineer", "automation test",
        "selenium", "cypress", "sdet",
    ],
    "Finance & FinTech": [
        "fintech", "quantitative", "quant ", "financial engineer",
        "trading systems", "banking software", "payments engineer",
        "accounting", "bookkeeper", "controller", "cpa",
    ],
}

# ---------------------------------------------------------------------------
# Job type patterns (fallback for non-LLM path)
# ---------------------------------------------------------------------------
JOB_TYPE_PATTERNS: Final[dict[str, list[str]]] = {
    "Full-time": ["full-time", "full time", "permanent", "salaried"],
    "Contract": ["contract", "contractor", "c2c", "w2", "corp-to-corp"],
    "Freelance": ["freelance", "freelancer", "gig", "project-based"],
    "Internship": ["intern", "internship", "co-op", "trainee"],
    "Part-time": ["part-time", "part time"],
}

# ---------------------------------------------------------------------------
# Seniority patterns (fallback)
# ---------------------------------------------------------------------------
SENIORITY_PATTERNS: Final[dict[str, list[str]]] = {
    "Intern": ["intern", "internship", "co-op", "trainee"],
    "Junior": ["junior", "jr", "entry level", "entry-level", "associate", "new grad"],
    "Mid": ["mid-level", "mid level", "intermediate", "2-5 years", "3+ years"],
    "Senior": ["senior", "sr", "experienced", "5+ years", "7+ years"],
    "Staff": ["staff engineer", "staff"],
    "Principal": ["principal"],
    "Lead/Manager": ["lead", "manager", "team lead", "head of"],
    "Director+": ["director", "vp", "vice president", "chief", "cto", "cpo", "ciso", "ceo"],
}

# ---------------------------------------------------------------------------
# Work mode patterns (fallback)
# ---------------------------------------------------------------------------
WORK_MODE_PATTERNS: Final[dict[str, list[str]]] = {
    "Remote": ["remote", "work from home", "wfh", "anywhere", "distributed", "telecommute"],
    "Hybrid": ["hybrid", "flex", "partially remote", "2 days", "3 days in office"],
    "On-site": ["on-site", "onsite", "in-office", "in office", "on site", "relocate"],
}

# ---------------------------------------------------------------------------
# Job indicator patterns (fallback is_job classifier)
# ---------------------------------------------------------------------------
JOB_POSITIVE_PATTERNS: Final[list[str]] = [
    "hiring", "job opening", "we're looking", "we are looking", "job opportunity",
    "apply", "application", "position", "vacancy", "seeking", "join our team",
    "[hiring]", "looking to hire", "salary", "compensation", "benefits",
]

JOB_NEGATIVE_PATTERNS: Final[list[str]] = [
    "looking for work", "need a job", "hire me", "[for hire]",
    "resume review", "career advice", "interview tips",
    "should i", "is it worth", "what should", "how do i",
    "rant", "vent", "frustrated", "quit my job", "meme", "joke",
]

# ---------------------------------------------------------------------------
# Urgency patterns (fallback)
# ---------------------------------------------------------------------------
URGENCY_PATTERNS: Final[list[str]] = [
    "asap", "immediately", "urgent", "start now", "right away",
    "start date", "this week", "today", "need someone", "quickly",
    "deadline", "time-sensitive", "limited time",
]

# ---------------------------------------------------------------------------
# Tech stack keywords (used for display/filtering even when LLM classifies)
# ---------------------------------------------------------------------------
TECH_KEYWORDS: Final[dict[str, list[str]]] = {
    "Python": ["python"],
    "JavaScript": ["javascript", "js"],
    "TypeScript": ["typescript", "ts"],
    "Java": ["java"],
    "C++": ["c++", "cpp"],
    "C#": ["c#", "csharp", ".net"],
    "Go": ["golang"],
    "Rust": ["rust"],
    "Ruby": ["ruby", "rails"],
    "PHP": ["php"],
    "Swift": ["swift"],
    "Kotlin": ["kotlin"],
    "Scala": ["scala"],
    "SQL": ["sql", "mysql", "postgresql", "postgres", "sqlite"],
    "NoSQL": ["nosql", "mongodb", "dynamodb", "cassandra"],
    "React": ["react", "reactjs"],
    "Angular": ["angular"],
    "Vue.js": ["vue", "vuejs"],
    "Node.js": ["node", "nodejs", "node.js"],
    "Django": ["django"],
    "Flask": ["flask"],
    "FastAPI": ["fastapi"],
    "Spring": ["spring boot"],
    "Docker": ["docker"],
    "Kubernetes": ["kubernetes", "k8s"],
    "AWS": ["aws", "amazon web services"],
    "Azure": ["azure"],
    "GCP": ["gcp", "google cloud"],
    "Terraform": ["terraform"],
    "TensorFlow": ["tensorflow"],
    "PyTorch": ["pytorch"],
    "Spark": ["spark", "pyspark"],
    "Kafka": ["kafka"],
    "Redis": ["redis"],
    "Elasticsearch": ["elasticsearch"],
    "GraphQL": ["graphql"],
    "Solidity": ["solidity"],
    "Unity": ["unity"],
    "Unreal": ["unreal engine"],
    "Flutter": ["flutter"],
    "React Native": ["react native"],
    "Next.js": ["next.js", "nextjs"],
    "Figma": ["figma"],
    "Airflow": ["airflow"],
}

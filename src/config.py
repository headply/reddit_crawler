"""Configuration constants for the Reddit Job Intelligence Platform."""

from typing import Final

# ---------------------------------------------------------------------------
# Target subreddits — focused job boards + active tech communities
# ---------------------------------------------------------------------------
TARGET_SUBREDDITS: Final[list[str]] = [
    # Dedicated job boards
    "forhire",
    "jobbit",
    "remotejobs",
    "techjobs",
    "datajobs",
    # Specialised job subreddits
    "PythonJobs",
    "webdevjobs",
    "reactjobs",
    "MLjobs",
    "devopsjobs",
    "cybersecurityjobs",
    "uxjobs",
    "gamedevjobs",
    # Active tech communities with regular [Hiring] threads
    "webdev",
    "dataengineering",
    "devops",
    "MachineLearning",
    "androiddev",
    "iOSProgramming",
    "netsec",
    # Remote / freelance channels
    "freelance",
    "workonline",
    "digitalnomad",
]

# Number of posts to fetch per subreddit per run
POSTS_PER_SUBREDDIT: Final[int] = 100

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
    "Junior": ["junior", "jr", "entry level", "entry-level", "associate", "new grad"],
    "Mid": ["mid-level", "mid level", "intermediate", "2-5 years", "3+ years"],
    "Senior": ["senior", "sr", "experienced", "5+ years", "7+ years"],
    "Lead/Principal": ["lead", "principal", "staff", "architect", "head of", "director", "vp"],
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

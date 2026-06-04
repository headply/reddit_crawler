"""Configuration constants for the Reddit Job Intelligence Platform."""

from typing import Final

# ---------------------------------------------------------------------------
# Target subreddits — grouped for monitoring + per-group volume overrides.
#
# Curated to cover:
#   * Dedicated job boards (tech + non-tech)
#   * Active hiring communities per professional domain
#   * Regional / geo-specific hiring channels (Africa, India, LATAM, Asia, EU)
#   * Question-leaning communities — these are wrapped with strict include
#     keyword filters below so only posts with explicit hiring markers slip
#     into the database (avoids polluting the dataset with advice threads).
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
        "cscareeropportunities",
    ],
    "general_job_boards": [
        "jobs",
        "RemoteJobsHub",
        "RemoteWork",
        "digitalnomadjobs",
        "Internships",
        "EngineeringJobs",
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
        "ExperiencedDevs",
        "sysadmin",
        "aws",
        "kubernetes",
        "datascience",
        "analytics",
        "BusinessIntelligence",
        "learnmachinelearning",
        "computervision",
        "deeplearning",
        "LLMDevs",
    ],
    "careers_questions": [
        # These are noisy advice communities. The strict include filter
        # below ensures only posts whose title carries an explicit hiring
        # / for-hire marker make it past the scraper.
        "learnprogramming",
        "ITCareerQuestions",
        "cscareerquestions",
        "csMajors",
    ],
    "non_tech": [
        "marketing",
        "DigitalMarketing",
        "sales",
        "techsales",
        "salestechniques",
        "SEO",
        "contentmarketing",
        "digital_marketing",
        "GraphicDesign",
        "web_design",
        "Design",
        "ProductDesign",
        "userexperience",
        "copywriting",
        "writing",
        "freelanceWriters",
        "accounting",
        "Bookkeeping",
        "tax",
        "FinanceCareers",
        "ProductManagement",
        "startups",
        "Entrepreneur",
        "smallbusiness",
        "agency",
    ],
    "engineering_non_software": [
        "engineeringjobs",
        "civilengineering",
        "MechanicalEngineering",
        "AerospaceEngineering",
        "ECE",
    ],
    "healthcare": [
        "medicine",
        "nursing",
        "healthcareIT",
        "medlabprofessionals",
    ],
    "ops_people": [
        "CustomerSuccess",
        "humanresources",
        "recruiting",
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
        "gameDevClassifieds",
    ],
}

_TARGETS: list[str] = [s for group in SUBREDDIT_GROUPS.values() for s in group]
TARGET_SUBREDDITS: Final[list[str]] = list(dict.fromkeys(_TARGETS))

# ---------------------------------------------------------------------------
# Volume settings — bumped to fetch as much as PRAW comfortably allows.
# PRAW caps listing endpoints at 1000 posts and 60 req/min. With ~95
# subreddits at limit=200 (~2 reqs each), we use ~190 req per run and
# finish in ~3 minutes wall-clock — well within Reddit's limits.
# ---------------------------------------------------------------------------
POSTS_PER_SUBREDDIT: Final[int] = 200

POSTS_PER_GROUP: Final[dict[str, int]] = {
    "for_hire_focused": 400,
    "tech_job_boards": 250,
    "general_job_boards": 250,
    "remote_specific": 200,
    "non_tech": 150,
    "geo_africa": 75,
    "geo_india": 75,
    "geo_emerging": 75,
    "careers_questions": 100,
    "engineering_non_software": 100,
    "healthcare": 100,
    "ops_people": 100,
}

SUBREDDIT_TO_GROUP: Final[dict[str, str]] = {
    subreddit: group
    for group, subs in SUBREDDIT_GROUPS.items()
    for subreddit in subs
}

# ---------------------------------------------------------------------------
# Per-subreddit include filters — applied BEFORE insert so noise channels
# only contribute posts whose title/body contains an explicit hiring marker.
# This prevents r/learnprogramming question threads from being scraped and
# then having to be filtered downstream.
# ---------------------------------------------------------------------------
_HIRING_INCLUDE_KEYWORDS: Final[list[str]] = [
    "[hiring]", "[for hire]", "[gig]", "[task]",
    "hiring", "for hire", "available for hire", "looking to hire",
    "we're hiring", "we are hiring", "now hiring", "open role",
    "open position", "open positions", "job opening", "freelance",
    "contract", "gig", "looking for clients", "open to work",
]

_NOISY_SUBS = (
    # noisy generalist subs — require explicit hiring marker
    "beermoney", "slavelabour", "juststart",
    # question communities
    "learnprogramming", "ITCareerQuestions", "cscareerquestions", "csMajors",
    # broader tech subs where hiring is rare but legit when it happens
    "rust", "golang", "javascript", "ExperiencedDevs", "sysadmin",
    "aws", "kubernetes", "datascience", "analytics",
    "learnmachinelearning", "computervision", "deeplearning", "LLMDevs",
    "BusinessIntelligence",
    # healthcare / engineering / ops — communities where most posts aren't jobs
    "medicine", "nursing", "healthcareIT", "medlabprofessionals",
    "civilengineering", "MechanicalEngineering", "AerospaceEngineering", "ECE",
    "engineeringjobs",
    "humanresources", "recruiting", "CustomerSuccess",
    "sales", "salestechniques", "marketing", "SEO", "contentmarketing",
    "digital_marketing", "DigitalMarketing",
    "Design", "userexperience", "ProductDesign", "GraphicDesign", "web_design",
    "writing", "copywriting",
    "accounting", "Bookkeeping", "tax", "FinanceCareers",
    "ProductManagement", "startups", "Entrepreneur", "smallbusiness", "agency",
    # geo subs — most posts are local discussion, only keep ones with hiring tags
    "nigeria", "lagos", "kenya", "southafrica", "AfricanTech",
    "brazil", "latam", "philippines",
)

SUBREDDIT_INCLUDE_KEYWORDS: Final[dict[str, list[str]]] = {
    sub.lower(): list(_HIRING_INCLUDE_KEYWORDS) for sub in _NOISY_SUBS
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
    "Healthcare": [
        "nurse", "registered nurse", "rn ", "lpn", "medical assistant",
        "physician", "clinical", "healthcare it", "epic analyst", "ehr",
        "lab technician", "phlebotomist",
    ],
    "Customer Success": [
        "customer success", "customer support", "support engineer", "csm ",
        "account support", "client success",
    ],
    "HR & Recruiting": [
        "recruiter", "talent acquisition", "hr generalist", "people ops",
        "people operations", "talent partner",
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
    # job-seeking / advice
    "looking for work", "need a job", "hire me", "[for hire]",
    "resume review", "career advice", "interview tips",
    "should i", "is it worth", "what should", "how do i",
    # rants
    "rant", "vent", "frustrated", "quit my job", "meme", "joke",
    # interview / offer talk (rarely a job post itself)
    "applied to", "rejected", "ghosted", "recruiter ghosted",
    "take-home", "coding challenge", "whiteboard", "interview experience",
    "am i cooked", "should i accept", "should i take", "which offer",
    "comparing offers", "salary negotiation", "lowball", "counter offer",
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

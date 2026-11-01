"""Career-role recommendations and resume-to-job compatibility. Deterministic, no AI or keys needed."""
import re

# canonical skill -> extra spellings found in resumes and job posts
SKILLS = {
    "python": ["python3"], "java": [], "javascript": ["js", "es6", "ecmascript"], "typescript": [],
    "c++": ["cpp"], "c#": ["csharp"], "c programming": [], "go": ["golang", "go programming"], "rust": [], "kotlin": [], "swift": [],
    "php": [], "ruby": [], "scala": [], "matlab": [], "bash": ["shell scripting"],
    "html": ["html5"], "css": ["css3"], "sass": ["scss"], "tailwind": ["tailwindcss"], "bootstrap": [],
    "react": ["reactjs", "react.js"], "angular": ["angularjs"], "vue": ["vuejs", "vue.js"], "next.js": ["nextjs"],
    "node.js": ["nodejs"], "express": ["expressjs", "express.js"], "django": [], "flask": [],
    "fastapi": [], "spring boot": ["springboot", "spring framework"], ".net": ["dotnet", "asp.net"], "rest api": ["restful", "rest apis", "api development"],
    "graphql": [], "react native": [], "flutter": [], "android": [], "ios": [],
    "sql": [], "mysql": [], "postgresql": ["postgres"], "mongodb": ["mongo"], "redis": [], "firebase": [],
    "nosql": [], "oracle": [], "sqlite": [],
    "machine learning": ["ml"], "deep learning": [], "nlp": ["natural language processing"], "computer vision": [],
    "tensorflow": [], "pytorch": [], "scikit-learn": ["sklearn"], "keras": [], "pandas": [], "numpy": [],
    "data analysis": ["data analytics"], "data visualization": ["data visualisation"],
    "statistics": [], "power bi": ["powerbi"], "tableau": [], "excel": [], "etl": [], "spark": ["pyspark"],
    "hadoop": [], "airflow": [], "llm": ["large language models", "generative ai", "genai"], "opencv": [],
    "aws": ["amazon web services"], "azure": [], "gcp": ["google cloud"], "docker": [], "kubernetes": ["k8s"],
    "terraform": [], "ci/cd": ["cicd", "jenkins", "github actions"], "linux": [], "git": ["github", "gitlab"],
    "devops": [], "microservices": [], "system design": [], "data structures": ["dsa", "algorithms"],
    "oop": ["object oriented", "object-oriented"], "agile": ["scrum"], "testing": ["unit testing", "pytest", "junit", "selenium"],
    "cybersecurity": ["information security"], "networking": [], "penetration testing": ["pentesting"],
    "figma": [], "ui design": ["ui/ux", "ux design", "user interface"], "wireframing": [], "prototyping": [],
    "communication": [], "leadership": [], "problem solving": [], "project management": [], "jira": [],
    "seo": [], "content writing": [], "digital marketing": [], "business analysis": [], "sap": [], "salesforce": [],
    "embedded systems": ["embedded", "microcontroller", "arduino"], "iot": [], "vlsi": [], "autocad": [], "solidworks": [],
}

# role -> (summary, skills that matter most, further skills that help)
ROLES = {
    "Full Stack Developer": ("Builds both the user interface and the server side of web applications.",
                              ["javascript", "react", "node.js", "html", "css", "sql", "rest api", "git"],
                              ["typescript", "mongodb", "express", "docker", "next.js"]),
    "Frontend Developer": ("Turns designs into fast, accessible interfaces in the browser.",
                            ["html", "css", "javascript", "react", "git"],
                            ["typescript", "tailwind", "next.js", "figma", "testing"]),
    "Backend Developer": ("Designs APIs, databases and the services behind an application.",
                           ["python", "java", "sql", "rest api", "git", "node.js"],
                           ["django", "flask", "spring boot", "postgresql", "docker", "redis", "microservices"]),
    "Data Analyst": ("Turns raw data into charts and answers that guide decisions.",
                      ["sql", "excel", "python", "data analysis", "data visualization"],
                      ["power bi", "tableau", "pandas", "statistics"]),
    "Data Scientist": ("Builds statistical and machine-learning models on real data.",
                        ["python", "machine learning", "statistics", "pandas", "numpy", "sql"],
                        ["scikit-learn", "tensorflow", "pytorch", "deep learning", "data visualization"]),
    "Machine Learning Engineer": ("Trains, ships and monitors machine-learning systems.",
                                    ["python", "machine learning", "deep learning", "tensorflow", "pytorch"],
                                    ["docker", "aws", "nlp", "computer vision", "llm", "git"]),
    "AI / LLM Engineer": ("Builds products on top of large language models.",
                           ["python", "llm", "nlp", "machine learning", "rest api"],
                           ["pytorch", "fastapi", "docker", "deep learning"]),
    "Mobile App Developer": ("Builds Android and iOS applications.",
                              ["flutter", "react native", "android", "kotlin", "swift", "git"],
                              ["firebase", "rest api", "java", "ui design"]),
    "DevOps / Cloud Engineer": ("Automates deployment and runs applications reliably in the cloud.",
                                  ["linux", "docker", "aws", "ci/cd", "git", "kubernetes"],
                                  ["azure", "gcp", "terraform", "bash", "python", "devops"]),
    "Cybersecurity Analyst": ("Finds and fixes weaknesses and watches for attacks.",
                                ["cybersecurity", "networking", "linux", "penetration testing"],
                                ["python", "bash", "cloud"]),
    "Software Engineer": ("Designs, writes and tests software across the stack.",
                           ["data structures", "oop", "git", "sql", "problem solving"],
                           ["java", "python", "c++", "system design", "testing", "agile"]),
    "QA / Test Engineer": ("Makes sure software works before users see it.",
                            ["testing", "sql", "agile", "jira"],
                            ["python", "java", "ci/cd", "rest api", "git"]),
    "UI / UX Designer": ("Designs how a product looks and feels to use.",
                          ["figma", "ui design", "wireframing", "prototyping"],
                          ["html", "css", "communication"]),
    "Business Analyst": ("Connects business needs to technical solutions using data.",
                          ["business analysis", "sql", "excel", "communication"],
                          ["power bi", "tableau", "jira", "agile", "project management"]),
    "Embedded / IoT Engineer": ("Writes software for devices and hardware.",
                                  ["embedded systems", "c programming", "iot"],
                                  ["c++", "python", "linux", "vlsi", "matlab"]),
    "Digital Marketing Specialist": ("Grows an audience and customers online.",
                                       ["digital marketing", "seo", "content writing"],
                                       ["excel", "data analysis", "communication"]),
}

# Everyday words that are also skills: matched in free text only by their longer aliases,
# but accepted as-is when they are a whole entry in the candidate's skills list.
AMBIGUOUS = {"go": "go", "express": "express"}
SHORT_FORMS = {"node": "node.js", "spring": "spring boot", "security": "cybersecurity", "rest": "rest api",
               "shell": "bash", "ts": "typescript", "analytics": "data analysis"}

_BOUNDARY = r"(?<![A-Za-z0-9+#.]){}(?![A-Za-z0-9+#])"
_PATTERNS = {name: re.compile("|".join(_BOUNDARY.format(re.escape(t)) for t in
                                       ([] if name in AMBIGUOUS else [name]) + aliases), re.I)
             for name, aliases in SKILLS.items() if aliases or name not in AMBIGUOUS}
_EXACT = {t: name for name, aliases in SKILLS.items() for t in [name, *aliases]} | SHORT_FORMS


def skills_in(text):
    """Canonical skills mentioned in free text."""
    return {name for name, pat in _PATTERNS.items() if pat.search(text)}


def resume_skills(r):
    """Skills the candidate lists, plus ones evidenced in projects, experience and certifications."""
    listed = skills_in(" , ".join(r["skills"])) | {_EXACT[s.lower()] for s in r["skills"] if s.lower() in _EXACT}
    blob = " ".join([r["summary"]] + [f"{p['title']} {p['description']} {p['tech']}" for p in r["projects"]]
                    + [f"{e['role']} {e['details']}" for e in r["experience"]]
                    + [c["name"] for c in r["certifications"]] + [e["branch"] for e in r["education"]])
    return listed, listed | skills_in(blob)


def _display(skill):
    return {"sql": "SQL", "html": "HTML", "css": "CSS", "aws": "AWS", "gcp": "GCP", "nlp": "NLP", "llm": "LLM", "oop": "OOP",
            "etl": "ETL", "iot": "IoT", "seo": "SEO", "ios": "iOS", "ci/cd": "CI/CD", "php": "PHP", "sap": "SAP", "vlsi": "VLSI",
            "rest api": "REST APIs", "node.js": "Node.js", "next.js": "Next.js", "power bi": "Power BI", "devops": "DevOps",
            "mysql": "MySQL", "postgresql": "PostgreSQL", "mongodb": "MongoDB", "nosql": "NoSQL", "fastapi": "FastAPI",
            ".net": ".NET", "javascript": "JavaScript", "typescript": "TypeScript", "tensorflow": "TensorFlow",
            "pytorch": "PyTorch", "scikit-learn": "scikit-learn", "opencv": "OpenCV", "autocad": "AutoCAD",
            "github": "GitHub", "c programming": "C", "ui design": "UI design", "ui/ux": "UI/UX"}.get(skill, skill.title()
                                                                                           if " " in skill else skill.capitalize())


def recommend(r, limit=5):
    """Ranks roles by how much of each role's skill set the resume shows. Returns [] for an empty resume."""
    listed, evidence = resume_skills(r)
    if not evidence:
        return []
    out = []
    for role, (summary, core, extra) in ROLES.items():
        have_core = [s for s in core if s in evidence]
        have_extra = [s for s in extra if s in evidence]
        score = round(100 * (0.75 * len(have_core) / len(core) + 0.25 * len(have_extra) / len(extra)))
        if not have_core:
            continue
        out.append({"role": role, "summary": summary, "score": score,
                    "matched": [_display(s) for s in have_core + have_extra],
                    "missing": [_display(s) for s in core if s not in evidence][:5],
                    "to_learn": [_display(s) for s in extra if s not in evidence][:4]})
    out.sort(key=lambda x: -x["score"])
    return out[:limit]


def _title_words(text):
    return {w for w in re.findall(r"[a-z]{3,}", text.lower()) if w not in {"and", "the", "for", "with", "senior", "junior", "lead"}}


def job_match(r, job):
    """Compatibility 0-100 between the resume and one job (title + description)."""
    title, desc = job.get("title", ""), job.get("description", "")
    _, evidence = resume_skills(r)
    wanted_title, wanted_desc = skills_in(title), skills_in(desc)
    wanted = wanted_title | wanted_desc
    matched = sorted(wanted & evidence)
    missing = sorted(wanted - evidence)
    role_text = " ".join([e["role"] for e in r["experience"]] + [p["title"] for p in r["projects"]] + r["skills"])
    title_overlap = len(_title_words(title) & _title_words(role_text)) / max(1, len(_title_words(title)))
    if wanted:
        weights = {s: (2 if s in wanted_title else 1) for s in wanted}
        skill_part = sum(weights[s] for s in matched) / sum(weights.values())
        score = 100 * (0.85 * skill_part + 0.15 * title_overlap)
        basis = "skills"
    elif evidence and title_overlap:
        score, basis = 100 * min(1, title_overlap) * 0.6, "title"
    else:
        score, basis = 0, "none"
    return {"score": round(score), "matched": [_display(s) for s in matched][:8], "missing": [_display(s) for s in missing][:6],
            "basis": basis}

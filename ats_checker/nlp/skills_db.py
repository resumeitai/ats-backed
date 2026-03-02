"""
Skills database for ATS keyword matching and categorization.

Provides a comprehensive dictionary of skills organized by category,
along with lookup functions for skill identification and categorization.
"""

from typing import Optional


SKILLS_DB: dict[str, list[str]] = {
    "programming_languages": [
        "python", "javascript", "typescript", "java", "c", "c++", "c#",
        "ruby", "go", "golang", "rust", "swift", "kotlin", "scala",
        "php", "perl", "r", "matlab", "lua", "haskell", "elixir",
        "erlang", "clojure", "dart", "objective-c", "assembly",
        "visual basic", "vb.net", "fortran", "cobol", "groovy",
        "shell", "bash", "powershell", "sql", "plsql", "t-sql",
        "html", "css", "sass", "scss", "less",
    ],
    "frameworks": [
        "react", "reactjs", "react.js", "angular", "angularjs", "vue",
        "vuejs", "vue.js", "svelte", "next.js", "nextjs", "nuxt.js",
        "nuxtjs", "gatsby", "ember", "backbone", "jquery",
        "django", "flask", "fastapi", "express", "expressjs",
        "nest.js", "nestjs", "spring", "spring boot", "rails",
        "ruby on rails", "laravel", "symfony", "asp.net", ".net",
        "dotnet", ".net core", "blazor", "gin", "echo", "fiber",
        "actix", "rocket", "phoenix", "sinatra",
        "bootstrap", "tailwind", "tailwindcss", "material ui",
        "chakra ui", "ant design", "styled-components",
        "redux", "mobx", "vuex", "pinia", "zustand", "recoil",
        "node.js", "nodejs", "deno", "bun",
        "electron", "react native", "flutter", "ionic", "xamarin",
        "swiftui", "jetpack compose",
        "pytest", "jest", "mocha", "cypress", "selenium", "playwright",
        "unittest", "rspec", "junit",
    ],
    "databases": [
        "mysql", "postgresql", "postgres", "sqlite", "oracle",
        "sql server", "mssql", "mariadb",
        "mongodb", "mongoose", "dynamodb", "couchdb", "couchbase",
        "cassandra", "neo4j", "arangodb", "firebase", "firestore",
        "redis", "memcached", "elasticsearch", "opensearch",
        "supabase", "prisma", "sequelize", "sqlalchemy", "typeorm",
        "hibernate", "active record",
    ],
    "cloud": [
        "aws", "amazon web services", "ec2", "s3", "lambda", "ecs",
        "eks", "fargate", "cloudfront", "route 53", "rds", "sqs",
        "sns", "cloudwatch", "iam", "api gateway", "cognito",
        "azure", "microsoft azure", "azure devops", "azure functions",
        "gcp", "google cloud", "google cloud platform",
        "cloud functions", "bigquery", "cloud run", "gke",
        "heroku", "vercel", "netlify", "digitalocean",
        "cloudflare", "linode", "vultr",
    ],
    "devops": [
        "docker", "kubernetes", "k8s", "podman", "openshift",
        "terraform", "ansible", "puppet", "chef", "pulumi",
        "jenkins", "github actions", "gitlab ci", "circleci",
        "travis ci", "bitbucket pipelines", "argo cd", "spinnaker",
        "nginx", "apache", "caddy", "haproxy", "traefik",
        "prometheus", "grafana", "datadog", "new relic", "splunk",
        "elk stack", "logstash", "kibana", "jaeger",
        "git", "github", "gitlab", "bitbucket", "svn",
        "ci/cd", "continuous integration", "continuous deployment",
        "linux", "unix", "centos", "ubuntu", "debian", "rhel",
        "infrastructure as code", "iac",
        "helm", "istio", "service mesh", "vault", "consul",
    ],
    "soft_skills": [
        "leadership", "communication", "teamwork", "collaboration",
        "problem solving", "problem-solving", "critical thinking",
        "time management", "project management", "agile", "scrum",
        "kanban", "presentation", "public speaking", "mentoring",
        "coaching", "negotiation", "conflict resolution",
        "decision making", "strategic thinking", "creativity",
        "adaptability", "flexibility", "initiative", "self-motivated",
        "attention to detail", "analytical", "organizational",
        "interpersonal", "cross-functional", "stakeholder management",
        "customer service", "client relations",
    ],
    "data_science": [
        "machine learning", "deep learning", "neural networks",
        "natural language processing", "nlp", "computer vision",
        "tensorflow", "pytorch", "keras", "scikit-learn", "sklearn",
        "pandas", "numpy", "scipy", "matplotlib", "seaborn", "plotly",
        "jupyter", "data analysis", "data engineering", "data pipeline",
        "etl", "data visualization", "tableau", "power bi", "looker",
        "apache spark", "spark", "hadoop", "hive", "kafka",
        "airflow", "dbt", "snowflake", "databricks", "redshift",
        "statistics", "regression", "classification", "clustering",
        "reinforcement learning", "generative ai", "llm",
        "large language models", "transformers", "bert", "gpt",
        "hugging face", "mlops", "feature engineering",
        "a/b testing", "hypothesis testing", "bayesian",
        "opencv", "yolo", "image recognition",
    ],
    "design": [
        "figma", "sketch", "adobe xd", "invision", "zeplin",
        "photoshop", "illustrator", "after effects", "premiere pro",
        "ui design", "ux design", "ui/ux", "user interface",
        "user experience", "interaction design", "visual design",
        "wireframing", "prototyping", "design systems",
        "responsive design", "mobile design", "accessibility",
        "wcag", "usability testing", "user research",
        "information architecture", "typography", "color theory",
    ],
    "project_management": [
        "jira", "confluence", "trello", "asana", "monday.com",
        "notion", "linear", "clickup", "basecamp",
        "pmp", "prince2", "six sigma", "lean",
        "waterfall", "agile methodology", "sprint planning",
        "backlog grooming", "retrospective", "daily standup",
        "product management", "product owner", "scrum master",
        "roadmap", "okr", "kpi", "roi",
        "risk management", "resource planning", "budgeting",
        "gantt chart", "milestone", "deliverable",
        "requirements gathering", "business analysis",
        "stakeholder management",
    ],
}

# Build a reverse-lookup index: lowercase skill -> category
_SKILL_TO_CATEGORY: dict[str, str] = {}
for _category, _skills in SKILLS_DB.items():
    for _skill in _skills:
        _SKILL_TO_CATEGORY[_skill.lower()] = _category


def get_skill_category(skill: str) -> Optional[str]:
    """
    Return the category a skill belongs to, or None if not recognized.

    Args:
        skill: The skill name to look up (case-insensitive).

    Returns:
        Category string (e.g. 'programming_languages') or None.
    """
    return _SKILL_TO_CATEGORY.get(skill.lower().strip())


def is_known_skill(word: str) -> bool:
    """
    Check whether a word or phrase is a recognized skill.

    Args:
        word: The word or phrase to check (case-insensitive).

    Returns:
        True if the word is found in the skills database.
    """
    return word.lower().strip() in _SKILL_TO_CATEGORY

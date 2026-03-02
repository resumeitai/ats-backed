"""
Job Description Parser.

Extracts structured, relevant information from raw job postings
(e.g. pasted from LinkedIn, Indeed, Naukri). Filters out noise like
company descriptions, benefits, legal disclaimers, and diversity statements
so the optimizer only processes actual requirements and responsibilities.
"""

import re
from typing import Dict, List, Optional


# Section header patterns (case-insensitive)
_RELEVANT_HEADERS = re.compile(
    r"(?:^|\n)\s*(?:#{1,3}\s*)?("
    r"what you.?ll do|responsibilities|key responsibilities|your role"
    r"|requirements|qualifications|expertise you.?ll bring|what we.?re looking for"
    r"|must.?have|nice.?to.?have|preferred qualifications|desired skills"
    r"|skills|technical skills|required skills|about the (?:position|role|job)"
    r"|job description|role description|your responsibilities"
    r"|what you.?ll need|what we need|key skills"
    r")\s*:?\s*(?:\n|$)",
    re.IGNORECASE,
)

_NOISE_HEADERS = re.compile(
    r"(?:^|\n)\s*(?:#{1,3}\s*)?("
    r"about (?:us|the company|persistent|[\w\s]+(?:ltd|inc|corp))"
    r"|benefits|perks|compensation|what we offer"
    r"|equal opportunity|inclusive environment|diversity"
    r"|our company|company overview|who we are"
    r"|disclaimer|legal|privacy|how to apply|application process"
    r")\s*:?\s*(?:\n|$)",
    re.IGNORECASE,
)

# Patterns to detect job title from the raw text
_TITLE_PATTERNS = [
    # "About The Position" followed by "looking for a <Title>"
    re.compile(r"looking for (?:a |an )?(?:skilled |experienced |senior |junior )?(.+?)(?:\s+to\s+|\s+who\s+|\s+with\s+|\.\s)", re.IGNORECASE),
    # First line that looks like a title (short, no punctuation heavy)
    re.compile(r"^([A-Z][\w\s/\-&]+(?:Developer|Engineer|Designer|Manager|Analyst|Architect|Lead|Specialist|Consultant|Administrator|Coordinator))", re.MULTILINE),
]


class JobDescriptionParser:
    """Parse raw job postings into structured, clean job description data."""

    def __init__(self, raw_text: str):
        self.raw_text = raw_text.strip()

    def parse(self) -> Dict:
        """
        Parse the raw job posting text.

        Returns::

            {
                "job_title": str or None,
                "company_name": str or None,
                "clean_description": str,   # noise-free JD for optimizer
                "requirements": [str, ...],
                "responsibilities": [str, ...],
                "skills_mentioned": [str, ...],
                "experience_level": str or None,  # "junior", "mid", "senior"
                "location": str or None,
            }
        """
        job_title = self._extract_job_title()
        company_name = self._extract_company_name()
        location = self._extract_location()
        experience_level = self._detect_experience_level()

        sections = self._split_into_sections()
        relevant_text = self._extract_relevant_sections(sections)
        requirements = self._extract_bullet_items(sections, is_requirements=True)
        responsibilities = self._extract_bullet_items(sections, is_requirements=False)
        skills = self._extract_skills_from_text(relevant_text)

        return {
            "job_title": job_title,
            "company_name": company_name,
            "clean_description": relevant_text,
            "requirements": requirements,
            "responsibilities": responsibilities,
            "skills_mentioned": skills,
            "experience_level": experience_level,
            "location": location,
        }

    def _extract_job_title(self) -> Optional[str]:
        """Try to extract job title from the raw text."""
        # Check very first line — often the title on job boards
        first_line = self.raw_text.split("\n")[0].strip()
        if first_line and len(first_line) < 80 and not first_line.endswith("."):
            # Looks like a title line
            # Remove location/company suffixes
            title = re.sub(r"\s*[-·|]\s*.*$", "", first_line).strip()
            if title and len(title.split()) <= 8:
                return title

        for pattern in _TITLE_PATTERNS:
            match = pattern.search(self.raw_text)
            if match:
                return match.group(1).strip().rstrip(".")

        return None

    def _extract_company_name(self) -> Optional[str]:
        """Extract company name from the posting."""
        patterns = [
            re.compile(r"(?:About|Join)\s+([\w\s]+?)(?:\n|\.)", re.IGNORECASE),
            re.compile(r"(?:at|with)\s+([\w\s]+?(?:Ltd|Inc|Corp|Technologies|Systems|Solutions)\.?)", re.IGNORECASE),
            re.compile(r"Promoted by(?: hirer)?\s*·?\s*([\w\s]+?)(?:\n|$)", re.IGNORECASE),
        ]
        for pattern in patterns:
            match = pattern.search(self.raw_text[:500])
            if match:
                name = match.group(1).strip()
                if 3 <= len(name) <= 50:
                    return name
        return None

    def _extract_location(self) -> Optional[str]:
        """Extract job location."""
        pattern = re.compile(
            r"([\w\s]+,\s*[\w\s]+,\s*(?:India|USA|US|UK|Canada|Germany|France|Australia|Remote))",
            re.IGNORECASE,
        )
        match = pattern.search(self.raw_text[:300])
        if match:
            return match.group(1).strip()
        if re.search(r"\bremote\b", self.raw_text[:500], re.IGNORECASE):
            return "Remote"
        return None

    def _detect_experience_level(self) -> Optional[str]:
        """Detect experience level from the text."""
        text_lower = self.raw_text.lower()
        if any(term in text_lower for term in ["senior", "sr.", "lead", "principal", "staff"]):
            return "senior"
        if any(term in text_lower for term in ["junior", "jr.", "entry level", "entry-level", "fresher", "graduate"]):
            return "junior"
        if any(term in text_lower for term in ["mid-level", "mid level", "intermediate"]):
            return "mid"
        # Check years of experience
        years_match = re.search(r"(\d+)\+?\s*(?:years?|yrs?)\s*(?:of\s*)?(?:experience|exp)", text_lower)
        if years_match:
            years = int(years_match.group(1))
            if years <= 2:
                return "junior"
            elif years <= 5:
                return "mid"
            else:
                return "senior"
        return None

    def _split_into_sections(self) -> List[Dict]:
        """Split the raw text into sections based on headers."""
        sections = []
        lines = self.raw_text.split("\n")
        current_header = "intro"
        current_lines = []

        for line in lines:
            stripped = line.strip()
            # Check if this line is a section header
            is_relevant = bool(_RELEVANT_HEADERS.match("\n" + stripped + "\n"))
            is_noise = bool(_NOISE_HEADERS.match("\n" + stripped + "\n"))

            if is_relevant or is_noise:
                # Save previous section
                if current_lines:
                    sections.append({
                        "header": current_header,
                        "content": "\n".join(current_lines).strip(),
                        "is_noise": current_header == "intro" and len("\n".join(current_lines)) > 500,
                    })
                current_header = stripped.strip(":# ").strip()
                current_lines = []
                if is_noise:
                    sections.append({"header": current_header, "content": "", "is_noise": True})
                    current_header = "_skip_"
            elif current_header == "_skip_":
                # Skip lines under noise headers until next header
                continue
            else:
                current_lines.append(line)

        # Save last section
        if current_lines and current_header != "_skip_":
            sections.append({
                "header": current_header,
                "content": "\n".join(current_lines).strip(),
                "is_noise": False,
            })

        return sections

    def _extract_relevant_sections(self, sections: List[Dict]) -> str:
        """Combine relevant sections into a clean description."""
        parts = []
        for section in sections:
            if section.get("is_noise"):
                continue
            content = section["content"].strip()
            if not content:
                continue
            # Skip very long intro sections (usually company descriptions)
            if section["header"] == "intro" and len(content) > 600:
                # Try to find the relevant part after "About The Position" type text
                about_pos = re.search(
                    r"(?:about the (?:position|role)|we are looking for|job description)",
                    content,
                    re.IGNORECASE,
                )
                if about_pos:
                    content = content[about_pos.start():]
                else:
                    continue
            parts.append(content)

        return "\n\n".join(parts)

    def _extract_bullet_items(self, sections: List[Dict], is_requirements: bool) -> List[str]:
        """Extract bullet/list items from requirement or responsibility sections."""
        items = []
        target_headers = (
            ["requirements", "qualifications", "expertise", "must-have", "skills",
             "what we're looking for", "what you'll need", "desired skills",
             "preferred qualifications", "technical skills", "required skills",
             "key skills"]
            if is_requirements
            else ["responsibilities", "what you'll do", "your role",
                  "your responsibilities", "role description", "key responsibilities"]
        )

        for section in sections:
            if section.get("is_noise"):
                continue
            header_lower = section["header"].lower()
            if any(t in header_lower for t in target_headers):
                lines = section["content"].split("\n")
                for line in lines:
                    cleaned = re.sub(r"^[\s·•\-\*\d.)\]]+", "", line).strip()
                    if cleaned and len(cleaned) > 5:
                        items.append(cleaned)

        return items

    def _extract_skills_from_text(self, text: str) -> List[str]:
        """Extract technology/skill names from clean description text."""
        # Common tech skills pattern
        known_skills = [
            "Python", "JavaScript", "TypeScript", "Java", "C++", "C#", "Go", "Rust",
            "Ruby", "PHP", "Swift", "Kotlin", "Scala", "R", "MATLAB",
            "React", "React.js", "Angular", "Vue", "Vue.js", "Next.js", "Nuxt",
            "Node.js", "Express", "Django", "Flask", "FastAPI", "Spring Boot",
            "Rails", "Laravel", "ASP.NET",
            "AWS", "Azure", "GCP", "Docker", "Kubernetes", "Terraform",
            "PostgreSQL", "MySQL", "MongoDB", "Redis", "Elasticsearch",
            "Git", "Jenkins", "CI/CD", "GitHub Actions",
            "REST", "GraphQL", "gRPC", "WebSocket",
            "HTML", "CSS", "SASS", "LESS", "Tailwind",
            "Redux", "Flux", "Webpack", "Vite", "Babel",
            "Jest", "Mocha", "Cypress", "Selenium", "Pytest",
            "Machine Learning", "Deep Learning", "NLP", "Computer Vision",
            "TensorFlow", "PyTorch", "scikit-learn", "Pandas", "NumPy",
            "SQL", "NoSQL", "ETL", "Data Pipeline",
            "Agile", "Scrum", "Kanban", "JIRA",
            "Linux", "Unix", "Shell Scripting", "Bash",
            "Microservices", "Serverless", "Event-Driven",
            "OAuth", "JWT", "SSO", "LDAP",
            "Figma", "Sketch", "Adobe XD",
        ]
        found = []
        text_lower = text.lower()
        for skill in known_skills:
            # Case-insensitive search with word boundary
            pattern = re.compile(r"\b" + re.escape(skill) + r"\b", re.IGNORECASE)
            if pattern.search(text):
                found.append(skill)

        return found

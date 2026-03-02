"""
Cover letter generation service using local NLP analysis.

Generates tailored cover letters by analyzing a user's resume content
and a target job description with spaCy NLP. No external AI APIs are
used -- all processing is performed locally via keyword extraction,
semantic similarity, and template-based paragraph construction.
"""

import logging
import random
import re
from typing import Any, Dict, List, Optional, Tuple

from ats_checker.nlp import SpaCyKeywordExtractor, SynonymExpander, TextAnalyzer
from ats_checker.nlp.keyword_extractor import _load_spacy_model

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Tone-specific language variations
# ---------------------------------------------------------------------------

_TONE_CONFIG = {
    "professional": {
        "greetings": [
            "Dear Hiring Manager,",
            "Dear Hiring Team,",
            "Dear Recruitment Team,",
        ],
        "opening_phrases": [
            "I am writing to express my strong interest in the {job_title} position{at_company}.",
            "I am pleased to submit my application for the {job_title} role{at_company}.",
            "With a solid background in {domain}, I am writing to apply for the {job_title} position{at_company}.",
        ],
        "bridge_phrases": [
            "My professional background aligns well with the requirements of this role.",
            "I believe my qualifications make me a strong candidate for this position.",
            "Having reviewed the role requirements, I am confident in my ability to contribute meaningfully.",
        ],
        "skills_intros": [
            "Throughout my career, I have developed strong expertise in {skills_summary}.",
            "My technical proficiency spans {skills_summary}, all of which are central to this role.",
            "I bring hands-on experience with {skills_summary}, directly relevant to your requirements.",
        ],
        "experience_intros": [
            "In my recent experience, I have demonstrated the ability to deliver results in similar environments.",
            "My professional history reflects a consistent track record of impactful contributions.",
            "The following achievements from my career illustrate my readiness for this opportunity.",
        ],
        "experience_connectors": [
            "In this role, I {achievement}.",
            "During this period, I {achievement}.",
            "A key accomplishment was when I {achievement}.",
        ],
        "closing_lines": [
            "I would welcome the opportunity to discuss how my background and skills can contribute to {company_or_team}. I am available for an interview at your earliest convenience.",
            "Thank you for considering my application. I look forward to the possibility of discussing this opportunity further and demonstrating how I can add value to {company_or_team}.",
            "I am eager to bring my skills and experience to {company_or_team} and would appreciate the chance to discuss my candidacy in more detail.",
        ],
        "sign_off": "Sincerely,",
    },
    "enthusiastic": {
        "greetings": [
            "Dear Hiring Manager,",
            "Hello!",
            "Dear Hiring Team,",
        ],
        "opening_phrases": [
            "I am thrilled to apply for the {job_title} position{at_company}! This role is an incredible match for my background and passion.",
            "I was excited to discover the {job_title} opening{at_company}, and I am eager to bring my energy and expertise to your team.",
            "As a passionate {domain} professional, I could not be more excited about the {job_title} opportunity{at_company}.",
        ],
        "bridge_phrases": [
            "What excites me most is how perfectly my skills align with what you are looking for.",
            "I am genuinely passionate about this field, and I cannot wait to show you what I can bring to the table.",
            "This role speaks directly to my professional passions and strengths.",
        ],
        "skills_intros": [
            "I am passionate about {skills_summary}, and I have been fortunate to develop deep expertise in these areas.",
            "My skill set in {skills_summary} has been the driving force behind my career achievements.",
            "I have enthusiastically built expertise in {skills_summary}, and I am eager to apply them in this role.",
        ],
        "experience_intros": [
            "Here are some of the achievements I am most proud of, which I believe directly relate to this role.",
            "I have had some fantastic opportunities to make a real impact, and I would love to share a few highlights.",
            "My career journey has been filled with exciting challenges and accomplishments that directly prepare me for this role.",
        ],
        "experience_connectors": [
            "I had the exciting opportunity to {achievement}, which was incredibly rewarding.",
            "One achievement I am particularly proud of is when I {achievement}.",
            "I jumped at the chance to {achievement}, and the results were outstanding.",
        ],
        "closing_lines": [
            "I am absolutely thrilled about the possibility of joining {company_or_team} and would love to discuss how I can contribute to your success!",
            "I cannot wait to explore this opportunity further! I am available to chat anytime and would be delighted to share more about what I can bring to {company_or_team}.",
            "Thank you so much for considering my application! I am genuinely excited about {company_or_team} and would love the chance to be part of the team.",
        ],
        "sign_off": "Best regards,",
    },
    "concise": {
        "greetings": [
            "Dear Hiring Manager,",
        ],
        "opening_phrases": [
            "I am applying for the {job_title} position{at_company}.",
            "Please consider my application for the {job_title} role{at_company}.",
            "I am interested in the {job_title} position{at_company}.",
        ],
        "bridge_phrases": [
            "My background is a strong fit for this role.",
            "My qualifications match your requirements.",
        ],
        "skills_intros": [
            "Key skills: {skills_summary}.",
            "Relevant expertise: {skills_summary}.",
        ],
        "experience_intros": [
            "Relevant accomplishments:",
            "Key achievements:",
        ],
        "experience_connectors": [
            "I {achievement}.",
        ],
        "closing_lines": [
            "I am available to discuss this opportunity at your convenience. Thank you for your consideration.",
            "I look forward to discussing how I can contribute to {company_or_team}.",
        ],
        "sign_off": "Regards,",
    },
}


class CoverLetterGenerator:
    """
    Generate a tailored cover letter from resume content and a job description.

    Uses spaCy NLP for keyword extraction and semantic matching, combined
    with template-based paragraph construction. All processing is local --
    no external AI API calls are made.

    Args:
        resume: A ``resumes.models.Resume`` instance.
        job_title: The target job title.
        job_description: Full text of the job posting.
        company_name: Name of the hiring company (optional).
        tone: One of ``'professional'``, ``'enthusiastic'``, or ``'concise'``.
    """

    def __init__(
        self,
        resume,
        job_title: str,
        job_description: str,
        company_name: str = "",
        tone: str = "professional",
    ):
        self.resume = resume
        self.resume_content: dict = resume.content if isinstance(resume.content, dict) else {}
        self.job_title = job_title.strip()
        self.job_description = job_description.strip()
        self.company_name = company_name.strip()
        self.tone = tone if tone in _TONE_CONFIG else "professional"

        # NLP tools
        self.extractor = SpaCyKeywordExtractor(max_keywords=50)
        self.expander = SynonymExpander()
        self.analyzer = TextAnalyzer()
        self.nlp = _load_spacy_model()

        # Tone config
        self._tc = _TONE_CONFIG[self.tone]

    # ==================================================================
    # Public API
    # ==================================================================

    def generate(self) -> str:
        """
        Generate a complete cover letter.

        Algorithm:
        1. Extract keywords from the job description using SpaCyKeywordExtractor.
        2. Extract keywords from the resume text.
        3. Find matched skills and experience.
        4. Identify the user's top relevant achievements from resume content.
        5. Build the cover letter using paragraph templates filled with
           NLP-extracted data.

        Returns:
            The full cover letter as a single string.
        """
        # Step 1 & 2: keyword extraction
        job_keywords = self.extractor.extract_keywords(self.job_description)
        resume_text = self._resume_content_to_text()
        resume_keywords = self.extractor.extract_keywords(resume_text)

        # Step 3: skill matching
        matched_skills = self._match_skills(job_keywords, resume_keywords)

        # Step 4: relevant experience
        relevant_experience = self._extract_relevant_experience(job_keywords)

        # Step 5: user info
        user_info = self._get_user_info()

        # Step 6: determine the professional domain from job keywords
        domain = self._infer_domain(job_keywords)

        # Step 7: build paragraphs
        greeting = random.choice(self._tc["greetings"])
        opening = self._build_opening(user_info, domain)
        skills_paragraph = self._build_skills_paragraph(matched_skills, job_keywords)
        experience_paragraph = self._build_experience_paragraph(relevant_experience, job_keywords)
        closing = self._build_closing()

        # Assemble the user's name for the sign-off
        user_name = user_info.get("name", "")

        # Build final letter
        parts = [
            greeting,
            "",
            opening,
            "",
            skills_paragraph,
            "",
            experience_paragraph,
            "",
            closing,
            "",
            self._tc["sign_off"],
            user_name,
        ]

        return "\n".join(parts)

    # ==================================================================
    # Helper: user info extraction
    # ==================================================================

    def _get_user_info(self) -> Dict[str, str]:
        """
        Extract user name, current role, email, and phone from
        ``resume.content['personal']``.

        Returns:
            Dict with keys: name, email, phone, current_role, summary.
        """
        personal = self.resume_content.get("personal", {})
        info: Dict[str, str] = {
            "name": "",
            "email": "",
            "phone": "",
            "current_role": "",
            "summary": "",
        }

        if isinstance(personal, dict):
            # Try common key names for the name field
            for key in ("name", "full_name", "fullName", "firstName"):
                val = personal.get(key, "")
                if val:
                    # If there is also a lastName, combine them
                    last = personal.get("lastName", personal.get("last_name", ""))
                    info["name"] = f"{val} {last}".strip() if last else str(val).strip()
                    break

            info["email"] = str(personal.get("email", "")).strip()
            info["phone"] = str(personal.get("phone", personal.get("phone_number", ""))).strip()
            info["current_role"] = str(
                personal.get("title", personal.get("current_role", personal.get("designation", "")))
            ).strip()
            info["summary"] = str(
                personal.get("summary", personal.get("objective", personal.get("about", "")))
            ).strip()

        # Fallback to the User model if resume personal section is sparse
        if not info["name"] and hasattr(self.resume, "user"):
            user = self.resume.user
            info["name"] = user.full_name or user.get_full_name() or user.username

        return info

    # ==================================================================
    # Helper: skill matching
    # ==================================================================

    def _match_skills(
        self,
        job_keywords: List[dict],
        resume_keywords: List[dict],
    ) -> List[dict]:
        """
        Find skills from the resume that match job requirements.

        Matching is done by:
        1. Direct keyword overlap (case-insensitive).
        2. Synonym expansion (via SynonymExpander) for near-matches.
        3. Skills section of the resume checked against job keywords.

        Returns:
            List of dicts with keys: skill, category, importance.
        """
        job_kw_set = {kw["keyword"].lower() for kw in job_keywords}
        job_kw_map = {kw["keyword"].lower(): kw for kw in job_keywords}
        resume_kw_set = {kw["keyword"].lower() for kw in resume_keywords}

        matched: List[dict] = []
        seen: set = set()

        # Direct matches
        for kw in resume_kw_set & job_kw_set:
            if kw not in seen:
                seen.add(kw)
                jk = job_kw_map.get(kw, {})
                matched.append({
                    "skill": kw,
                    "category": jk.get("category", "general"),
                    "importance": jk.get("importance", "medium"),
                })

        # Synonym-based matches
        for resume_kw in resume_kw_set - seen:
            for job_kw in job_kw_set - seen:
                if self.expander.are_related(resume_kw, job_kw):
                    seen.add(resume_kw)
                    jk = job_kw_map.get(job_kw, {})
                    matched.append({
                        "skill": resume_kw,
                        "category": jk.get("category", "general"),
                        "importance": jk.get("importance", "medium"),
                    })
                    break

        # Also check the explicit skills section of the resume
        skills_section = self.resume_content.get("skills", [])
        explicit_skills = self._flatten_skills_section(skills_section)
        for skill in explicit_skills:
            skill_lower = skill.lower()
            if skill_lower in job_kw_set and skill_lower not in seen:
                seen.add(skill_lower)
                jk = job_kw_map.get(skill_lower, {})
                matched.append({
                    "skill": skill_lower,
                    "category": jk.get("category", "technical"),
                    "importance": jk.get("importance", "medium"),
                })

        # Sort by importance
        importance_order = {"high": 0, "medium": 1, "low": 2}
        matched.sort(key=lambda m: importance_order.get(m["importance"], 3))
        return matched

    @staticmethod
    def _flatten_skills_section(skills_data) -> List[str]:
        """
        Flatten the resume skills section into a list of skill strings.

        Handles formats:
        - List of strings: ["Python", "Django"]
        - List of dicts: [{"name": "Python", "level": "Expert"}, ...]
        - Dict of lists: {"technical": ["Python"], "soft": ["Leadership"]}
        - Plain string: "Python, Django, React"
        """
        result: List[str] = []

        if isinstance(skills_data, list):
            for item in skills_data:
                if isinstance(item, str):
                    # Could be comma-separated
                    result.extend(s.strip() for s in item.split(",") if s.strip())
                elif isinstance(item, dict):
                    # e.g. {"name": "Python", "level": "Expert"}
                    name = item.get("name", item.get("skill", item.get("title", "")))
                    if name:
                        result.append(str(name).strip())
                    else:
                        # Maybe the dict values are the skills
                        for v in item.values():
                            if isinstance(v, str):
                                result.append(v.strip())
                            elif isinstance(v, list):
                                result.extend(str(s).strip() for s in v if s)
        elif isinstance(skills_data, dict):
            for key, value in skills_data.items():
                if isinstance(value, list):
                    for item in value:
                        if isinstance(item, str):
                            result.append(item.strip())
                        elif isinstance(item, dict):
                            name = item.get("name", item.get("skill", ""))
                            if name:
                                result.append(str(name).strip())
                elif isinstance(value, str):
                    result.extend(s.strip() for s in value.split(",") if s.strip())
        elif isinstance(skills_data, str):
            result.extend(s.strip() for s in skills_data.split(",") if s.strip())

        return [s for s in result if s]

    # ==================================================================
    # Helper: relevant experience extraction
    # ==================================================================

    def _extract_relevant_experience(self, job_keywords: List[dict]) -> List[dict]:
        """
        Find the experience entries from the resume that are most relevant
        to the job description, ranked by keyword overlap.

        Each returned entry contains:
            title, company, description, relevance_score, matched_keywords

        Returns at most 3 entries, sorted by relevance descending.
        """
        experience_section = self.resume_content.get("experience", [])
        if not experience_section:
            return []

        job_kw_set = {kw["keyword"].lower() for kw in job_keywords}

        scored_entries: List[dict] = []

        entries = self._normalize_experience(experience_section)

        for entry in entries:
            title = entry.get("title", entry.get("position", entry.get("role", "")))
            company = entry.get("company", entry.get("organization", entry.get("employer", "")))
            description = entry.get("description", entry.get("details", entry.get("responsibilities", "")))

            # Build full text for this entry
            entry_text = f"{title} {company} {description}"
            if isinstance(description, list):
                entry_text = f"{title} {company} " + " ".join(str(d) for d in description)
                description = " ".join(str(d) for d in description)
            else:
                description = str(description)

            entry_text_lower = entry_text.lower()

            # Score by counting how many job keywords appear in this entry
            matched_kws = []
            for kw in job_kw_set:
                if kw in entry_text_lower:
                    matched_kws.append(kw)

            # Semantic similarity boost if spaCy is available
            similarity_score = 0.0
            if self.nlp and len(self.job_description) > 20 and len(entry_text) > 20:
                try:
                    job_doc = self.nlp(self.job_description[:1000])
                    entry_doc = self.nlp(entry_text[:500])
                    similarity_score = job_doc.similarity(entry_doc)
                except Exception:
                    pass

            relevance = len(matched_kws) + (similarity_score * 5)

            scored_entries.append({
                "title": str(title).strip(),
                "company": str(company).strip(),
                "description": str(description).strip(),
                "relevance_score": relevance,
                "matched_keywords": matched_kws,
            })

        # Sort by relevance descending and return top 3
        scored_entries.sort(key=lambda e: e["relevance_score"], reverse=True)
        return scored_entries[:3]

    @staticmethod
    def _normalize_experience(experience_data) -> List[dict]:
        """
        Normalize the experience section into a list of dicts regardless
        of the input format (list of dicts, list of strings, dict, string).
        """
        if isinstance(experience_data, list):
            entries = []
            for item in experience_data:
                if isinstance(item, dict):
                    entries.append(item)
                elif isinstance(item, str):
                    entries.append({"title": "", "company": "", "description": item})
            return entries
        elif isinstance(experience_data, dict):
            return [experience_data]
        elif isinstance(experience_data, str):
            return [{"title": "", "company": "", "description": experience_data}]
        return []

    # ==================================================================
    # Helper: domain inference
    # ==================================================================

    def _infer_domain(self, job_keywords: List[dict]) -> str:
        """
        Infer the broad professional domain from job keywords to use in
        opening paragraph phrasing.

        Returns a human-readable domain string, e.g. "software engineering",
        "data science", "project management".
        """
        category_counts: Dict[str, int] = {}
        for kw in job_keywords:
            cat = kw.get("category", "general")
            category_counts[cat] = category_counts.get(cat, 0) + 1

        category_to_domain = {
            "programming_languages": "software development",
            "frameworks": "software engineering",
            "databases": "data engineering",
            "cloud": "cloud computing",
            "devops": "DevOps and infrastructure",
            "data_science": "data science and analytics",
            "design": "design and user experience",
            "project_management": "project management",
            "soft_skills": "professional services",
            "technical": "technology",
        }

        if not category_counts:
            return "technology"

        top_category = max(category_counts, key=category_counts.get)
        return category_to_domain.get(top_category, "technology")

    # ==================================================================
    # Paragraph builders
    # ==================================================================

    def _build_opening(self, user_info: Dict[str, str], domain: str) -> str:
        """
        Build the opening paragraph.

        Expresses interest in the position, mentions the company if known,
        and provides a brief introduction linking the candidate to the role.
        """
        at_company = f" at {self.company_name}" if self.company_name else ""
        company_or_team = self.company_name if self.company_name else "your team"

        # Choose and format the opening sentence
        opening_template = random.choice(self._tc["opening_phrases"])
        opening_sentence = opening_template.format(
            job_title=self.job_title,
            at_company=at_company,
            domain=domain,
        )

        # Build a context sentence from the user's current role or summary
        context_sentence = ""
        current_role = user_info.get("current_role", "")
        summary = user_info.get("summary", "")

        if current_role:
            context_sentence = (
                f"As a {current_role}, I have built a career focused on {domain}, "
                f"and I am eager to bring that expertise to {company_or_team}."
            )
        elif summary:
            # Use the first sentence of the summary if available
            first_sentence = summary.split(".")[0].strip()
            if first_sentence and len(first_sentence) > 10:
                context_sentence = f"{first_sentence}."
            else:
                context_sentence = random.choice(self._tc["bridge_phrases"])
        else:
            context_sentence = random.choice(self._tc["bridge_phrases"])

        return f"{opening_sentence} {context_sentence}"

    def _build_skills_paragraph(
        self,
        matched_skills: List[dict],
        job_keywords: List[dict],
    ) -> str:
        """
        Build the skills paragraph.

        Highlights matched skills from the resume that align with the job
        requirements. Groups skills by category for readability.
        """
        if not matched_skills:
            # Fallback: pull skills directly from the resume skills section
            skills_section = self.resume_content.get("skills", [])
            flat_skills = self._flatten_skills_section(skills_section)
            if flat_skills:
                skills_summary = self._format_skill_list(flat_skills[:8])
                intro_template = random.choice(self._tc["skills_intros"])
                intro = intro_template.format(skills_summary=skills_summary)
                return (
                    f"{intro} I am confident that these capabilities will enable me to "
                    f"make meaningful contributions in the {self.job_title} role."
                )
            return random.choice(self._tc["bridge_phrases"])

        # Group matched skills by category
        categorized: Dict[str, List[str]] = {}
        for ms in matched_skills:
            cat = ms["category"]
            categorized.setdefault(cat, []).append(ms["skill"])

        # Build the skills list for the intro sentence (up to 8 skills)
        all_skill_names = [ms["skill"] for ms in matched_skills[:8]]
        skills_summary = self._format_skill_list(all_skill_names)

        intro_template = random.choice(self._tc["skills_intros"])
        intro = intro_template.format(skills_summary=skills_summary)

        # Add category-specific detail if we have enough variety
        detail_parts: List[str] = []
        category_labels = {
            "programming_languages": "programming languages",
            "frameworks": "frameworks and libraries",
            "databases": "database technologies",
            "cloud": "cloud platforms",
            "devops": "DevOps tools",
            "data_science": "data science tools",
            "design": "design tools",
            "project_management": "project management methodologies",
            "soft_skills": "interpersonal skills",
            "technical": "technical skills",
            "general": "key competencies",
        }

        for cat, skills in categorized.items():
            if len(skills) >= 2:
                label = category_labels.get(cat, cat.replace("_", " "))
                formatted = self._format_skill_list(skills[:4])
                detail_parts.append(f"{label} such as {formatted}")

        if detail_parts and self.tone != "concise":
            detail_sentence = (
                "Specifically, I offer proficiency in "
                + "; ".join(detail_parts[:3])
                + "."
            )
            return f"{intro} {detail_sentence}"

        return intro

    def _build_experience_paragraph(
        self,
        relevant_experience: List[dict],
        job_keywords: List[dict],
    ) -> str:
        """
        Build the experience paragraph.

        Pulls the 2-3 most relevant experience entries from the resume
        and connects them to the job requirements.
        """
        if not relevant_experience:
            # Fallback: generic experience statement
            return random.choice(self._tc["bridge_phrases"])

        intro = random.choice(self._tc["experience_intros"])

        achievement_sentences: List[str] = []

        for entry in relevant_experience[:3]:
            title = entry.get("title", "")
            company = entry.get("company", "")
            description = entry.get("description", "")

            # Build a concise achievement statement from the entry
            achievement = self._distill_achievement(title, company, description)

            if achievement:
                connector_template = random.choice(self._tc["experience_connectors"])
                sentence = connector_template.format(achievement=achievement)
                achievement_sentences.append(sentence)

        if not achievement_sentences:
            return random.choice(self._tc["bridge_phrases"])

        # Join sentences into a paragraph
        if self.tone == "concise":
            body = " ".join(achievement_sentences)
        else:
            body = " ".join(achievement_sentences)

        return f"{intro} {body}"

    def _build_closing(self) -> str:
        """
        Build the closing paragraph.

        Expresses enthusiasm and mentions availability.
        """
        company_or_team = self.company_name if self.company_name else "your team"
        closing_template = random.choice(self._tc["closing_lines"])
        return closing_template.format(company_or_team=company_or_team)

    # ==================================================================
    # Text processing utilities
    # ==================================================================

    def _resume_content_to_text(self) -> str:
        """
        Convert the entire resume content JSON into a single text string
        for keyword extraction.
        """
        parts: List[str] = []
        for section_name, section_data in self.resume_content.items():
            parts.append(self._section_to_text(section_data))
        return " ".join(parts)

    @staticmethod
    def _section_to_text(section_data) -> str:
        """
        Convert a resume section (str, list, or dict) into flat text.
        """
        if isinstance(section_data, str):
            return section_data

        if isinstance(section_data, list):
            text_parts = []
            for item in section_data:
                if isinstance(item, dict):
                    text_parts.append(" ".join(str(v) for v in item.values()))
                else:
                    text_parts.append(str(item))
            return " ".join(text_parts)

        if isinstance(section_data, dict):
            return " ".join(str(v) for v in section_data.values())

        return str(section_data)

    def _distill_achievement(self, title: str, company: str, description: str) -> str:
        """
        Distill an experience entry into a concise achievement statement
        suitable for inclusion in a cover letter paragraph.

        Strategy:
        1. If the description contains bullet points, pick the most
           impactful one (containing numbers or action verbs).
        2. Otherwise, extract the first meaningful sentence.
        3. Prepend the role context (title at company) if available.
        """
        # Separate bullet points or sentences
        lines = re.split(r"[\n\r\u2022\-\*]+", description)
        lines = [line.strip() for line in lines if line.strip() and len(line.strip()) > 10]

        if not lines:
            # Fallback: use title and company
            if title and company:
                return f"served as {title} at {company}, contributing to key projects and deliverables"
            elif title:
                return f"served as {title}, contributing to key projects and deliverables"
            return ""

        # Score each line: prefer lines with numbers, action verbs, percentages
        def _score_line(line: str) -> float:
            score = 0.0
            # Numbers and percentages suggest quantified achievements
            if re.search(r"\d+", line):
                score += 3
            if re.search(r"\d+%", line):
                score += 2
            if re.search(r"\$[\d,]+", line):
                score += 2
            # Action verbs at the start
            first_word = line.split()[0].lower().rstrip(".,;:") if line.split() else ""
            from ats_checker.nlp.text_analyzer import ACTION_VERBS
            if first_word in ACTION_VERBS:
                score += 2
            # Longer lines (but not too long) are more informative
            if 20 < len(line) < 200:
                score += 1
            return score

        scored = [(line, _score_line(line)) for line in lines]
        scored.sort(key=lambda x: x[1], reverse=True)
        best_line = scored[0][0]

        # Clean up the line: lowercase the first character if it starts with
        # an action verb (to fit into connector template grammar)
        best_clean = best_line.rstrip(".")
        if best_clean and best_clean[0].isupper():
            # Only lowercase if it looks like a bullet point start, not a proper noun
            first_word = best_clean.split()[0]
            if first_word.lower().rstrip(".,;:") in ACTION_VERBS:
                best_clean = best_clean[0].lower() + best_clean[1:]

        # Add role context if available and tone is not concise
        if self.tone != "concise" and title and company:
            return f"as {title} at {company}, {best_clean}"
        elif title:
            return f"as {title}, {best_clean}"

        return best_clean

    @staticmethod
    def _format_skill_list(skills: List[str]) -> str:
        """
        Format a list of skill strings into a readable English enumeration.

        Examples:
            ["Python"] -> "Python"
            ["Python", "Django"] -> "Python and Django"
            ["Python", "Django", "React"] -> "Python, Django, and React"
        """
        if not skills:
            return ""

        # Capitalize each skill for presentation
        capitalized = []
        for s in skills:
            # Keep abbreviations uppercase, capitalize normal words
            if s.isupper() or len(s) <= 3:
                capitalized.append(s.upper())
            else:
                capitalized.append(s.title())

        if len(capitalized) == 1:
            return capitalized[0]
        elif len(capitalized) == 2:
            return f"{capitalized[0]} and {capitalized[1]}"
        else:
            return ", ".join(capitalized[:-1]) + f", and {capitalized[-1]}"

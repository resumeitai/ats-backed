"""
Resume Optimization Engine.

Automatically optimizes resume content to maximize ATS compatibility for a
given job description.  All optimization is performed locally using spaCy +
NLTK -- no external AI APIs are required.

Usage::

    from ats_checker.optimizer import ResumeOptimizer

    optimizer = ResumeOptimizer(
        resume_content=resume.content,
        job_title="Senior Backend Developer",
        job_description="We are looking for a Python developer ...",
    )
    result = optimizer.optimize()
    # result keys: optimized_content, original_content, changes,
    #              score_before, score_after, improvement
"""

import copy
import logging
import re
from typing import Any, Dict, List, Optional, Set, Tuple

from .nlp import SpaCyKeywordExtractor, SynonymExpander, TextAnalyzer
from .nlp.skills_db import SKILLS_DB, get_skill_category, is_known_skill
from .nlp.text_analyzer import ACTION_VERBS

logger = logging.getLogger(__name__)

# ── Module-level cached NLP instances (mirrors services.py) ──────────────
_keyword_extractor = SpaCyKeywordExtractor()
_synonym_expander = SynonymExpander()
_text_analyzer = TextAnalyzer()

# ── Action-verb replacements for vague phrases ───────────────────────────
_VAGUE_REPLACEMENTS: List[Tuple[str, str, str]] = [
    # (regex_pattern, replacement_template, reason)
    (
        r"\bresponsible for\s+(?:the\s+)?(\w+)",
        r"Led \1",
        "Replaced vague 'responsible for' with strong action verb 'Led'",
    ),
    (
        r"\bworked on\s+(?:the\s+)?(\w+)",
        r"Developed \1",
        "Replaced vague 'worked on' with action verb 'Developed'",
    ),
    (
        r"\bhelped with\s+(?:the\s+)?(\w+)",
        r"Contributed to \1",
        "Replaced vague 'helped with' with 'Contributed to'",
    ),
    (
        r"\bduties included\s+(\w+)",
        r"Executed \1",
        "Replaced vague 'duties included' with action verb 'Executed'",
    ),
    (
        r"\btasked with\s+(\w+)",
        r"Spearheaded \1",
        "Replaced vague 'tasked with' with action verb 'Spearheaded'",
    ),
    (
        r"\bassisted in\s+(\w+)",
        r"Supported \1",
        "Replaced vague 'assisted in' with 'Supported'",
    ),
]

# Quantification patterns: phrases that lack numbers
_QUANTIFIABLE_PATTERNS: List[Tuple[str, str, str]] = [
    (
        r"\b[Mm]anaged\s+(?:a\s+)?team\b(?!\s+of\s+\[?\d)",
        "Managed team of [X] members",
        "Added quantifiable metric placeholder for team size",
    ),
    (
        r"\b[Ii]ncreased\s+(\w+)\b(?!\s+by\s+\[?\d)",
        r"Increased \1 by [X]%",
        "Added quantifiable metric placeholder for improvement percentage",
    ),
    (
        r"\b[Rr]educed\s+(\w+)\b(?!\s+by\s+\[?\d)",
        r"Reduced \1 by [X]%",
        "Added quantifiable metric placeholder for reduction percentage",
    ),
    (
        r"\b[Ii]mproved\s+(\w+)\b(?!\s+by\s+\[?\d)",
        r"Improved \1 by [X]%",
        "Added quantifiable metric placeholder for improvement percentage",
    ),
    (
        r"\b[Ss]aved\s+(?:the\s+company\s+)?(?:over\s+)?\$?(?!\[?\d)",
        "Saved $[X]",
        "Added quantifiable metric placeholder for cost savings",
    ),
]

# Preferred action verbs grouped by context for intelligent selection
_CONTEXT_ACTION_VERBS: Dict[str, List[str]] = {
    "leadership": ["Led", "Directed", "Managed", "Oversaw", "Supervised", "Coordinated"],
    "development": ["Developed", "Built", "Engineered", "Implemented", "Designed", "Architected"],
    "analysis": ["Analyzed", "Evaluated", "Assessed", "Investigated", "Researched"],
    "improvement": ["Optimized", "Improved", "Enhanced", "Streamlined", "Revamped", "Upgraded"],
    "creation": ["Created", "Established", "Launched", "Initiated", "Introduced", "Founded"],
    "collaboration": ["Collaborated", "Partnered", "Facilitated", "Coordinated"],
    "delivery": ["Delivered", "Deployed", "Executed", "Produced", "Generated"],
}


class ResumeOptimizer:
    """
    Automatically optimizes resume content to maximize ATS score for a given
    job description.

    All optimization is done locally using spaCy + NLTK.  No external AI APIs
    are called.
    """

    def __init__(
        self,
        resume_content: dict,
        job_title: str,
        job_description: str,
    ):
        self.original_content: dict = copy.deepcopy(resume_content)
        self.optimized_content: dict = copy.deepcopy(resume_content)
        self.job_title: str = job_title
        self.job_description: str = job_description
        self.changes_made: List[dict] = []

        # Extracted keywords (populated during optimize)
        self.job_keywords: List[dict] = []
        self.resume_keywords: List[dict] = []
        self.missing_keywords: List[dict] = []
        self.job_skill_names: Set[str] = set()

    # ──────────────────────────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────────────────────────

    def optimize(self) -> dict:
        """
        Run the full optimization pipeline.

        Returns a dict with keys:
            optimized_content  - the modified resume content dict
            original_content   - the original (untouched) content dict
            changes            - list of changes made
            score_before       - estimated ATS score before optimization
            score_after        - estimated ATS score after optimization
            improvement        - score_after - score_before
        """
        try:
            # 0. Pre-analysis: extract keywords from the job description and
            #    the *original* resume so we know what is missing.
            self._extract_keywords()

            # 1. Calculate score BEFORE optimization
            score_before = self._calculate_score(self.original_content)

            # 2. Run optimization steps (order matters)
            self._optimize_summary()
            self._optimize_skills()
            self._optimize_experience()
            self._optimize_projects()

            # 3. Calculate score AFTER optimization
            score_after = self._calculate_score(self.optimized_content)

            # 4. Build change report
            changes = self._generate_change_report()

            return {
                "optimized_content": self.optimized_content,
                "original_content": self.original_content,
                "changes": changes,
                "score_before": score_before,
                "score_after": score_after,
                "improvement": score_after - score_before,
            }

        except Exception as exc:
            logger.error("Optimization failed: %s", exc, exc_info=True)
            return {
                "optimized_content": self.original_content,
                "original_content": self.original_content,
                "changes": [],
                "score_before": 0,
                "score_after": 0,
                "improvement": 0,
            }

    # ──────────────────────────────────────────────────────────────────
    # Step 0 -- keyword extraction & gap analysis
    # ──────────────────────────────────────────────────────────────────

    def _extract_keywords(self) -> None:
        """Extract keywords from the job description and the original resume."""
        jd_text = f"{self.job_title} {self.job_description}"
        self.job_keywords = _keyword_extractor.extract_keywords(jd_text)

        resume_text = self._content_to_text(self.original_content)
        self.resume_keywords = _keyword_extractor.extract_keywords(resume_text)

        # Determine which job keywords are missing from the resume
        resume_kw_set = {kw["keyword"].lower() for kw in self.resume_keywords}
        self.missing_keywords = []
        for jk in self.job_keywords:
            kw_lower = jk["keyword"].lower()
            if kw_lower in resume_kw_set:
                continue
            # Check synonym / stem match
            found_via_synonym = False
            for rkw in resume_kw_set:
                if _synonym_expander.are_related(kw_lower, rkw):
                    found_via_synonym = True
                    break
            if not found_via_synonym:
                self.missing_keywords.append(jk)

        # Build a set of skill names from the job description for quick lookup
        self.job_skill_names = set()
        for jk in self.job_keywords:
            kw_lower = jk["keyword"].lower()
            if is_known_skill(kw_lower) or jk.get("category") not in ("general", "organization", None):
                self.job_skill_names.add(kw_lower)

    # ──────────────────────────────────────────────────────────────────
    # Step 1 -- optimize professional summary
    # ──────────────────────────────────────────────────────────────────

    def _optimize_summary(self) -> None:
        """
        Rewrite the professional summary to include the job title and the
        top 3-5 missing high/medium-importance keywords.
        """
        personal = self.optimized_content.get("personal")
        if not isinstance(personal, dict):
            return

        original_summary = personal.get("summary", "")
        if not original_summary or not isinstance(original_summary, str):
            # If no summary exists, generate one from scratch
            new_summary = self._generate_summary()
            if new_summary:
                personal["summary"] = new_summary
                self._record_change(
                    section="personal.summary",
                    original="(empty)",
                    modified=new_summary,
                    reason="Generated professional summary incorporating job title and top keywords",
                )
            return

        summary_lower = original_summary.lower()

        # Collect top keywords to inject (high/medium importance, not already
        # present in summary)
        inject_keywords: List[str] = []
        for kw in self.job_keywords:
            if kw.get("importance") in ("high", "medium"):
                kw_text = kw["keyword"]
                if kw_text.lower() not in summary_lower:
                    inject_keywords.append(kw_text)
            if len(inject_keywords) >= 5:
                break

        # Build the new summary
        new_summary = original_summary.rstrip(". ")

        # Inject job title if not already present
        if self.job_title.lower() not in summary_lower:
            new_summary = self._prepend_job_title(new_summary)

        # Append a keywords clause if we have keywords to inject
        if inject_keywords:
            keywords_phrase = self._build_keywords_clause(inject_keywords)
            # If the summary already ends with a period-terminated sentence,
            # just append.  Otherwise add a period first.
            if not new_summary.rstrip().endswith("."):
                new_summary = new_summary.rstrip() + "."
            new_summary = f"{new_summary} {keywords_phrase}"

        # Ensure it ends cleanly
        new_summary = new_summary.strip()
        if not new_summary.endswith("."):
            new_summary += "."

        if new_summary != original_summary:
            personal["summary"] = new_summary
            self._record_change(
                section="personal.summary",
                original=original_summary,
                modified=new_summary,
                reason="Optimized summary to include job title and top job-description keywords",
            )

    def _generate_summary(self) -> str:
        """Generate a summary from scratch when the resume has none."""
        top_skills: List[str] = []
        for kw in self.job_keywords:
            if kw.get("importance") in ("high", "medium") and is_known_skill(kw["keyword"]):
                top_skills.append(kw["keyword"])
            if len(top_skills) >= 4:
                break

        # Pull experience context if available
        experience = self.optimized_content.get("experience", [])
        years_hint = ""
        if isinstance(experience, list) and experience:
            years_hint = "experienced "

        skills_str = ", ".join(top_skills) if top_skills else "relevant technical skills"
        return (
            f"{years_hint}{self.job_title} professional with expertise in "
            f"{skills_str}. Proven track record of delivering high-quality "
            f"solutions and driving measurable results."
        ).capitalize()

    def _prepend_job_title(self, summary: str) -> str:
        """Insert the job title at the beginning of the summary."""
        # If the summary already starts with a role-like phrase, replace it;
        # otherwise prepend.
        role_prefix = re.match(
            r"^(experienced|senior|junior|mid[- ]level|lead)?\s*\w+\s*(developer|engineer|designer|analyst|manager|specialist|consultant|architect)\b",
            summary,
            re.IGNORECASE,
        )
        if role_prefix:
            # Replace the matched role with the job title
            new_summary = summary[: role_prefix.start()] + self.job_title + summary[role_prefix.end() :]
            return new_summary.strip()
        return f"{self.job_title} with " + summary[0].lower() + summary[1:]

    @staticmethod
    def _build_keywords_clause(keywords: List[str]) -> str:
        """Build a natural-language clause listing keywords."""
        if len(keywords) == 1:
            return f"Skilled in {keywords[0]}."
        elif len(keywords) == 2:
            return f"Skilled in {keywords[0]} and {keywords[1]}."
        else:
            head = ", ".join(keywords[:-1])
            return f"Skilled in {head}, and {keywords[-1]}."

    # ──────────────────────────────────────────────────────────────────
    # Step 2 -- optimize skills section
    # ──────────────────────────────────────────────────────────────────

    def _optimize_skills(self) -> None:
        """
        - Add missing skills from the job description that the user plausibly
          has (present in the skills DB).
        - Reorder skills to put the most relevant ones first.
        """
        skills_data = self.optimized_content.get("skills")
        if skills_data is None:
            # Create a skills section if missing entirely
            skills_to_add = self._get_missing_relevant_skills()
            if skills_to_add:
                self.optimized_content["skills"] = skills_to_add
                self._record_change(
                    section="skills",
                    original="(section missing)",
                    modified=str(skills_to_add),
                    reason="Created skills section with relevant job-description skills",
                )
            return

        if isinstance(skills_data, list):
            self._optimize_skills_list(skills_data)
        elif isinstance(skills_data, dict):
            self._optimize_skills_dict(skills_data)

    def _optimize_skills_list(self, skills_list: list) -> None:
        """Optimize a flat list of skills."""
        original_skills = list(skills_list)
        existing_lower = {s.lower() for s in skills_list if isinstance(s, str)}

        # Add missing relevant skills
        added: List[str] = []
        for skill_name in self._get_missing_relevant_skills():
            if skill_name.lower() not in existing_lower:
                skills_list.append(skill_name)
                existing_lower.add(skill_name.lower())
                added.append(skill_name)

        # Reorder: job-relevant skills first
        skills_list.sort(key=lambda s: self._skill_relevance_key(s))

        self.optimized_content["skills"] = skills_list

        if added:
            self._record_change(
                section="skills",
                original=", ".join(original_skills),
                modified=", ".join(skills_list),
                reason=f"Added missing relevant skills: {', '.join(added)}. Reordered by relevance to job description.",
            )
        elif skills_list != original_skills:
            self._record_change(
                section="skills",
                original=", ".join(original_skills),
                modified=", ".join(skills_list),
                reason="Reordered skills to prioritize job-relevant skills first",
            )

    def _optimize_skills_dict(self, skills_dict: dict) -> None:
        """Optimize a categorized skills dict (e.g. {technical: [...], soft: [...]})."""
        original_repr = str(skills_dict)
        all_existing_lower: Set[str] = set()
        for cat_skills in skills_dict.values():
            if isinstance(cat_skills, list):
                all_existing_lower.update(s.lower() for s in cat_skills if isinstance(s, str))

        added: List[str] = []
        for skill_name in self._get_missing_relevant_skills():
            if skill_name.lower() in all_existing_lower:
                continue

            # Determine the best category for this skill
            skill_cat = get_skill_category(skill_name)
            if skill_cat == "soft_skills":
                target_key = self._find_dict_key(skills_dict, ["soft", "soft_skills", "interpersonal"])
            else:
                target_key = self._find_dict_key(skills_dict, ["technical", "hard", "programming", "tools"])

            if target_key and isinstance(skills_dict[target_key], list):
                skills_dict[target_key].append(skill_name)
            else:
                # Fallback: add to the first list-type value
                for key, val in skills_dict.items():
                    if isinstance(val, list):
                        val.append(skill_name)
                        break
                else:
                    # No list found -- create "other"
                    skills_dict["other"] = [skill_name]

            all_existing_lower.add(skill_name.lower())
            added.append(skill_name)

        # Reorder each list
        for key, val in skills_dict.items():
            if isinstance(val, list):
                val.sort(key=lambda s: self._skill_relevance_key(s))

        self.optimized_content["skills"] = skills_dict

        if added:
            self._record_change(
                section="skills",
                original=original_repr,
                modified=str(skills_dict),
                reason=f"Added missing relevant skills: {', '.join(added)}. Reordered by relevance.",
            )

    def _get_missing_relevant_skills(self) -> List[str]:
        """
        Return a list of skill names from the job description that are
        recognized in the skills DB but missing from the resume.
        """
        resume_text_lower = self._content_to_text(self.original_content).lower()
        current_skills = self._extract_current_skills_set()

        missing_skills: List[str] = []
        seen: Set[str] = set()

        for kw in self.job_keywords:
            kw_text = kw["keyword"]
            kw_lower = kw_text.lower()
            if kw_lower in seen:
                continue
            seen.add(kw_lower)

            if not is_known_skill(kw_lower):
                continue
            if kw_lower in current_skills:
                continue
            # Also check if it appears anywhere in the resume text (synonym match)
            if kw_lower in resume_text_lower:
                continue
            found_synonym = False
            for cs in current_skills:
                if _synonym_expander.are_related(kw_lower, cs):
                    found_synonym = True
                    break
            if found_synonym:
                continue

            # Capitalize nicely
            missing_skills.append(self._title_case_skill(kw_text))

        return missing_skills[:15]  # Cap to avoid bloating

    def _extract_current_skills_set(self) -> Set[str]:
        """Return a lowercase set of all skills currently in the resume."""
        skills_data = self.original_content.get("skills")
        result: Set[str] = set()
        if isinstance(skills_data, list):
            for s in skills_data:
                if isinstance(s, str):
                    result.add(s.lower())
        elif isinstance(skills_data, dict):
            for val in skills_data.values():
                if isinstance(val, list):
                    for s in val:
                        if isinstance(s, str):
                            result.add(s.lower())
        return result

    def _skill_relevance_key(self, skill: str) -> Tuple[int, str]:
        """Sort key: skills appearing in the job description come first."""
        s_lower = skill.lower() if isinstance(skill, str) else ""
        if s_lower in self.job_skill_names:
            return (0, s_lower)
        # Check synonym match
        for js in self.job_skill_names:
            if _synonym_expander.are_related(s_lower, js):
                return (1, s_lower)
        return (2, s_lower)

    @staticmethod
    def _find_dict_key(d: dict, candidates: List[str]) -> Optional[str]:
        """Return the first key from *candidates* that exists in *d*."""
        d_lower = {k.lower(): k for k in d}
        for c in candidates:
            if c.lower() in d_lower:
                return d_lower[c.lower()]
        return None

    @staticmethod
    def _title_case_skill(skill: str) -> str:
        """Title-case a skill name, respecting acronyms."""
        # If the skill is all-caps or has mixed case already, keep it
        if skill.isupper() or any(c.isupper() for c in skill[1:]):
            return skill
        return skill.title()

    # ──────────────────────────────────────────────────────────────────
    # Step 3 -- optimize experience section
    # ──────────────────────────────────────────────────────────────────

    def _optimize_experience(self) -> None:
        """
        For each experience entry:
        - Replace vague phrases with action verbs
        - Inject relevant job keywords into achievement bullet points
        - Add quantifiable metric placeholders where numbers are missing
        """
        experience = self.optimized_content.get("experience")
        if not isinstance(experience, list):
            return

        for idx, entry in enumerate(experience):
            if not isinstance(entry, dict):
                continue

            # Optimize description
            description = entry.get("description", "")
            if isinstance(description, str) and description.strip():
                new_description = self._optimize_text_block(
                    description, section_label=f"experience[{idx}].description"
                )
                if new_description != description:
                    entry["description"] = new_description

            # Optimize achievements
            achievements = entry.get("achievements", [])
            if isinstance(achievements, list):
                new_achievements = []
                for aidx, achievement in enumerate(achievements):
                    if isinstance(achievement, str) and achievement.strip():
                        new_ach = self._optimize_text_block(
                            achievement,
                            section_label=f"experience[{idx}].achievements[{aidx}]",
                        )
                        new_achievements.append(new_ach)
                    else:
                        new_achievements.append(achievement)

                # Inject a missing-keyword bullet if there are high-importance
                # keywords that don't yet appear in any achievement
                keyword_bullet = self._build_keyword_injection_bullet(new_achievements, entry)
                if keyword_bullet:
                    new_achievements.append(keyword_bullet)
                    self._record_change(
                        section=f"experience[{idx}].achievements",
                        original="(new bullet)",
                        modified=keyword_bullet,
                        reason="Injected achievement bullet incorporating missing high-importance keywords",
                    )

                entry["achievements"] = new_achievements

    def _optimize_text_block(self, text: str, section_label: str) -> str:
        """
        Apply vague-phrase replacement and quantification placeholders to a
        text block (description or single achievement bullet).
        """
        new_text = text

        # 1. Replace vague phrases with action verbs
        for pattern, replacement, reason in _VAGUE_REPLACEMENTS:
            match = re.search(pattern, new_text, re.IGNORECASE)
            if match:
                original_fragment = match.group(0)
                replaced = re.sub(pattern, replacement, new_text, count=1, flags=re.IGNORECASE)
                if replaced != new_text:
                    # Find what changed
                    new_match = re.search(
                        re.escape(replacement).replace(r"\1", r"\w+"),
                        replaced,
                        re.IGNORECASE,
                    )
                    modified_fragment = new_match.group(0) if new_match else replacement
                    self._record_change(
                        section=section_label,
                        original=original_fragment,
                        modified=modified_fragment,
                        reason=reason,
                    )
                    new_text = replaced

        # 2. Add quantification placeholders
        for pattern, replacement, reason in _QUANTIFIABLE_PATTERNS:
            match = re.search(pattern, new_text)
            if match:
                original_fragment = match.group(0)
                replaced = re.sub(pattern, replacement, new_text, count=1)
                if replaced != new_text:
                    new_match_text = replacement
                    # Try to extract what was actually inserted
                    try:
                        diff_start = next(
                            i for i, (a, b) in enumerate(zip(new_text, replaced)) if a != b
                        )
                        new_match_text = replaced[diff_start : diff_start + len(replacement) + 10].split(".")[0]
                    except (StopIteration, IndexError):
                        pass
                    self._record_change(
                        section=section_label,
                        original=original_fragment,
                        modified=new_match_text.strip(),
                        reason=reason,
                    )
                    new_text = replaced

        # 3. Ensure the bullet starts with an action verb (if it doesn't already)
        new_text = self._ensure_action_verb_start(new_text, section_label)

        return new_text

    def _ensure_action_verb_start(self, text: str, section_label: str) -> str:
        """If the text doesn't start with an action verb, prepend one."""
        stripped = text.strip()
        if not stripped:
            return text

        first_word = stripped.split()[0].rstrip(".,;:").lower()

        # Already starts with an action verb -- good
        if first_word in ACTION_VERBS:
            return text

        # Skip very short fragments or fragments that start with a number
        # (e.g. "3 years of experience")
        if len(stripped) < 20 or stripped[0].isdigit():
            return text

        # Pick a contextually appropriate action verb
        verb = self._pick_action_verb(stripped)
        if verb:
            new_text = f"{verb} {stripped[0].lower()}{stripped[1:]}"
            self._record_change(
                section=section_label,
                original=stripped[:60],
                modified=new_text[:60],
                reason=f"Prepended strong action verb '{verb}' to strengthen ATS impact",
            )
            return new_text

        return text

    @staticmethod
    def _pick_action_verb(text: str) -> Optional[str]:
        """Choose an action verb that fits the context of *text*."""
        text_lower = text.lower()

        context_hints = {
            "leadership": ["team", "led", "manage", "supervise", "direct", "mentor", "coordinate"],
            "development": ["develop", "build", "code", "software", "application", "system", "feature", "program"],
            "analysis": ["analyz", "evaluat", "research", "assess", "investigat", "data", "report"],
            "improvement": ["optimiz", "improv", "enhanc", "streamlin", "reduc", "increas", "efficien"],
            "creation": ["creat", "establish", "launch", "initiat", "introduc", "found", "start"],
            "collaboration": ["collaborat", "partner", "facilitat", "cross-functional", "stakeholder"],
            "delivery": ["deliver", "deploy", "execut", "produc", "generat", "releas", "ship"],
        }

        for context, hints in context_hints.items():
            for hint in hints:
                if hint in text_lower:
                    verbs = _CONTEXT_ACTION_VERBS.get(context, [])
                    if verbs:
                        return verbs[0]

        # Default to a general-purpose verb
        return "Implemented"

    def _build_keyword_injection_bullet(
        self, existing_achievements: List[str], entry: dict
    ) -> Optional[str]:
        """
        If high-importance job keywords are missing from the experience
        achievements, build a natural bullet point that incorporates them.
        """
        # Collect text of all existing achievements
        all_text = " ".join(
            a for a in existing_achievements if isinstance(a, str)
        ).lower()

        # Find high/medium importance keywords not yet in any achievement
        missing_in_achievements: List[str] = []
        for kw in self.job_keywords:
            if kw.get("importance") not in ("high", "medium"):
                continue
            kw_lower = kw["keyword"].lower()
            if kw_lower in all_text:
                continue
            # Check synonyms
            found = False
            synonyms = _synonym_expander.expand(kw["keyword"])
            for syn in synonyms:
                if syn.lower() in all_text:
                    found = True
                    break
            if not found:
                missing_in_achievements.append(kw["keyword"])

        if not missing_in_achievements:
            return None

        # Pick up to 3 keywords to weave into a bullet
        selected = missing_in_achievements[:3]
        position = entry.get("position", "role")
        company = entry.get("company", "organization")

        if len(selected) == 1:
            bullet = f"Utilized {selected[0]} expertise to deliver key project outcomes and drive operational improvements."
        elif len(selected) == 2:
            bullet = f"Leveraged {selected[0]} and {selected[1]} to build solutions that enhanced team productivity and project delivery."
        else:
            head = ", ".join(selected[:-1])
            bullet = f"Applied {head}, and {selected[-1]} to develop and implement high-impact solutions aligned with business objectives."

        return bullet

    # ──────────────────────────────────────────────────────────────────
    # Step 4 -- optimize projects section
    # ──────────────────────────────────────────────────────────────────

    def _optimize_projects(self) -> None:
        """
        Add missing relevant technology keywords to project technology lists
        and improve project descriptions.
        """
        projects = self.optimized_content.get("projects")
        if not isinstance(projects, list):
            return

        for idx, project in enumerate(projects):
            if not isinstance(project, dict):
                continue

            # Optimize project technologies
            technologies = project.get("technologies", [])
            if isinstance(technologies, list):
                self._optimize_project_technologies(technologies, project, idx)

            # Optimize project description
            description = project.get("description", "")
            if isinstance(description, str) and description.strip():
                new_desc = self._optimize_text_block(
                    description, section_label=f"projects[{idx}].description"
                )
                if new_desc != description:
                    project["description"] = new_desc

    def _optimize_project_technologies(
        self, technologies: list, project: dict, project_idx: int
    ) -> None:
        """Add missing relevant technologies to a project's technology list."""
        original_techs = list(technologies)
        existing_lower = {t.lower() for t in technologies if isinstance(t, str)}

        # Get the project description to determine context
        desc = project.get("description", "")
        desc_lower = desc.lower() if isinstance(desc, str) else ""
        name_lower = project.get("name", "").lower()
        context = f"{name_lower} {desc_lower}"

        added: List[str] = []
        for skill_name in self.job_skill_names:
            if skill_name in existing_lower:
                continue
            # Only add if the skill is contextually related to the project
            # (appears in the project description, or is a synonym of something there)
            cat = get_skill_category(skill_name)
            if cat in ("programming_languages", "frameworks", "databases", "cloud", "devops"):
                # For technical skills, check if they appear in the project context
                if skill_name in context:
                    technologies.append(self._title_case_skill(skill_name))
                    existing_lower.add(skill_name)
                    added.append(skill_name)
                elif any(_synonym_expander.are_related(skill_name, t.lower()) for t in technologies if isinstance(t, str)):
                    # Related to an existing technology -- plausible addition
                    technologies.append(self._title_case_skill(skill_name))
                    existing_lower.add(skill_name)
                    added.append(skill_name)

            if len(added) >= 5:
                break

        if added:
            project["technologies"] = technologies
            self._record_change(
                section=f"projects[{project_idx}].technologies",
                original=", ".join(original_techs),
                modified=", ".join(technologies),
                reason=f"Added relevant technologies: {', '.join(added)}",
            )

    # ──────────────────────────────────────────────────────────────────
    # Score calculation (mirrors ATSScoreAnalyzer logic)
    # ──────────────────────────────────────────────────────────────────

    def _calculate_score(self, content: dict) -> int:
        """
        Estimate the ATS score for the given content using the same weighted
        formula as ``ATSScoreAnalyzer``:
            keyword 50% + skills 20% + structure 15% + formatting 15%
        """
        KEYWORD_WEIGHT = 0.50
        SKILLS_WEIGHT = 0.20
        STRUCTURE_WEIGHT = 0.15
        FORMATTING_WEIGHT = 0.15

        resume_text = self._content_to_text(content)

        # --- Keyword score ---
        resume_keywords = _keyword_extractor.extract_keywords(resume_text)
        resume_text_lower = resume_text.lower()
        resume_kw_set = {kw["keyword"].lower() for kw in resume_keywords}

        total_weight = 0
        matched_weight = 0
        for kw in self.job_keywords:
            keyword = kw["keyword"]
            importance = kw.get("importance", "low")
            weight = 3 if importance == "high" else 2 if importance == "medium" else 1
            total_weight += weight

            found = keyword.lower() in resume_text_lower
            if not found:
                synonyms = _synonym_expander.expand(keyword)
                for syn in synonyms:
                    if syn.lower() in resume_text_lower:
                        found = True
                        break
            if not found:
                for rkw in resume_kw_set:
                    if _synonym_expander.are_related(keyword, rkw):
                        found = True
                        break

            if found:
                matched_weight += weight

        keyword_score = (matched_weight / total_weight * 100) if total_weight > 0 else 0

        # --- Skills gap score ---
        skills_gap = _text_analyzer.identify_skills_gap(resume_keywords, self.job_keywords)
        skills_score = max(0, 100 - len(skills_gap) * 5)

        # --- Structure score ---
        structure_result = _text_analyzer.analyze_structure(content)
        structure_score = structure_result.get("score", 0)

        # --- Formatting score ---
        formatting_result = _text_analyzer.analyze_formatting(content)
        formatting_score = formatting_result.get("score", 0)

        # --- Weighted total ---
        score = int(
            KEYWORD_WEIGHT * keyword_score
            + SKILLS_WEIGHT * skills_score
            + STRUCTURE_WEIGHT * structure_score
            + FORMATTING_WEIGHT * formatting_score
        )
        return min(100, max(0, score))

    # ──────────────────────────────────────────────────────────────────
    # Change tracking
    # ──────────────────────────────────────────────────────────────────

    def _record_change(
        self,
        section: str,
        original: str,
        modified: str,
        reason: str,
    ) -> None:
        """Record a single change for the final report."""
        self.changes_made.append(
            {
                "section": section,
                "original": original,
                "modified": modified,
                "reason": reason,
            }
        )

    def _generate_change_report(self) -> List[dict]:
        """
        Produce a deduplicated, ordered list of every change made during
        optimization.
        """
        # Deduplicate by (section, original, modified) to avoid noise
        seen: Set[Tuple[str, str, str]] = set()
        report: List[dict] = []
        for change in self.changes_made:
            key = (change["section"], change["original"], change["modified"])
            if key in seen:
                continue
            seen.add(key)
            report.append(change)
        return report

    # ──────────────────────────────────────────────────────────────────
    # Utilities
    # ──────────────────────────────────────────────────────────────────

    @staticmethod
    def _content_to_text(content: dict) -> str:
        """
        Convert resume content JSON to plain text (mirrors
        ``ATSScoreAnalyzer._get_resume_text``).
        """
        if isinstance(content, dict):
            parts: List[str] = []
            for section, data in content.items():
                if isinstance(data, str):
                    parts.append(data)
                elif isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict):
                            parts.append(" ".join(str(v) for v in item.values()))
                        else:
                            parts.append(str(item))
                elif isinstance(data, dict):
                    parts.append(" ".join(str(v) for v in data.values()))
            return " ".join(parts)
        elif isinstance(content, str):
            return content
        return str(content)

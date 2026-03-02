"""
LinkedIn profile data parser.
Converts LinkedIn profile JSON (exported or API-sourced) into the
standard ResumeIt resume content format.
"""
import logging
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class LinkedInImporter:
    """
    Parse LinkedIn profile JSON data into a standardized resume content dict.

    LinkedIn data can come from:
    - LinkedIn data export (Settings > Get a copy of your data)
    - LinkedIn API response
    - Manual JSON paste from user

    The parser handles multiple LinkedIn data formats flexibly.
    """

    def __init__(self, linkedin_data: dict):
        if not isinstance(linkedin_data, dict):
            raise ValueError("linkedin_data must be a JSON object (dict).")
        self.data = linkedin_data

    def parse(self) -> dict:
        """
        Parse LinkedIn data into standard resume content format.

        Returns:
            dict with keys: personal, experience, education, skills,
            projects, certifications
        """
        return {
            'personal': self._parse_personal(),
            'experience': self._parse_experience(),
            'education': self._parse_education(),
            'skills': self._parse_skills(),
            'projects': self._parse_projects(),
            'certifications': self._parse_certifications(),
        }

    def _parse_personal(self) -> dict:
        """Extract personal information."""
        personal = {}

        # Try different LinkedIn JSON structures
        # Format 1: Flat fields
        personal['name'] = (
            self.data.get('firstName', '') + ' ' + self.data.get('lastName', '')
        ).strip() or self.data.get('fullName', '') or self.data.get('name', '')

        personal['email'] = (
            self.data.get('emailAddress', '')
            or self.data.get('email', '')
            or self._extract_from_contact('email')
        )

        personal['phone'] = (
            self.data.get('phoneNumber', '')
            or self.data.get('phone', '')
            or self._extract_from_contact('phone')
        )

        personal['location'] = (
            self.data.get('location', '')
            or self._get_nested(self.data, 'location', 'name')
            or self._get_nested(self.data, 'locationName')
            or ''
        )
        if isinstance(personal['location'], dict):
            personal['location'] = personal['location'].get('name', str(personal['location']))

        personal['summary'] = (
            self.data.get('summary', '')
            or self.data.get('headline', '')
            or self.data.get('about', '')
        )

        # LinkedIn headline as a separate field
        headline = self.data.get('headline', '')
        if headline and headline != personal['summary']:
            personal['headline'] = headline

        personal['linkedin_url'] = (
            self.data.get('publicProfileUrl', '')
            or self.data.get('linkedinUrl', '')
            or self.data.get('profileUrl', '')
        )

        return {k: v for k, v in personal.items() if v}

    def _parse_experience(self) -> List[dict]:
        """Extract work experience entries."""
        positions = (
            self.data.get('positions', [])
            or self.data.get('experience', [])
            or self.data.get('workExperience', [])
            or self._get_nested(self.data, 'positions', 'values')
            or []
        )

        if isinstance(positions, dict):
            positions = positions.get('values', [positions])

        experiences = []
        for pos in positions:
            if not isinstance(pos, dict):
                continue

            entry = {
                'position': pos.get('title', '') or pos.get('position', ''),
                'company': (
                    pos.get('companyName', '')
                    or self._get_nested(pos, 'company', 'name')
                    or pos.get('company', '')
                ),
                'start_date': self._format_date(pos.get('startDate') or pos.get('start_date')),
                'end_date': self._format_date(pos.get('endDate') or pos.get('end_date')) or 'Present',
                'location': pos.get('location', '') or self._get_nested(pos, 'locationName') or '',
                'description': pos.get('description', '') or pos.get('summary', ''),
                'achievements': self._extract_achievements(
                    pos.get('description', '') or pos.get('summary', '')
                ),
            }

            if isinstance(entry['company'], dict):
                entry['company'] = entry['company'].get('name', '')

            if entry['position'] or entry['company']:
                experiences.append(entry)

        return experiences

    def _parse_education(self) -> List[dict]:
        """Extract education entries."""
        education_data = (
            self.data.get('education', [])
            or self.data.get('educations', [])
            or self._get_nested(self.data, 'educations', 'values')
            or []
        )

        if isinstance(education_data, dict):
            education_data = education_data.get('values', [education_data])

        entries = []
        for edu in education_data:
            if not isinstance(edu, dict):
                continue

            entry = {
                'degree': edu.get('degree', '') or edu.get('degreeName', ''),
                'field': edu.get('fieldOfStudy', '') or edu.get('field', '') or edu.get('major', ''),
                'institution': (
                    edu.get('schoolName', '')
                    or edu.get('institution', '')
                    or edu.get('school', '')
                ),
                'year': self._format_date(edu.get('endDate') or edu.get('end_date'))
                    or edu.get('year', ''),
                'description': edu.get('description', '') or edu.get('activities', ''),
            }

            if isinstance(entry['institution'], dict):
                entry['institution'] = entry['institution'].get('name', '')

            gpa = edu.get('grade', '') or edu.get('gpa', '')
            if gpa:
                entry['gpa'] = str(gpa)

            if entry['institution'] or entry['degree']:
                entries.append(entry)

        return entries

    def _parse_skills(self) -> List[str]:
        """Extract skills list."""
        skills_data = (
            self.data.get('skills', [])
            or self._get_nested(self.data, 'skills', 'values')
            or []
        )

        if isinstance(skills_data, dict):
            skills_data = skills_data.get('values', [])

        skills = []
        for skill in skills_data:
            if isinstance(skill, str):
                skills.append(skill)
            elif isinstance(skill, dict):
                name = skill.get('name', '') or skill.get('skill', '')
                if name:
                    skills.append(name)

        return skills

    def _parse_projects(self) -> List[dict]:
        """Extract projects."""
        projects_data = (
            self.data.get('projects', [])
            or self._get_nested(self.data, 'projects', 'values')
            or []
        )

        if isinstance(projects_data, dict):
            projects_data = projects_data.get('values', [])

        projects = []
        for proj in projects_data:
            if not isinstance(proj, dict):
                continue

            entry = {
                'name': proj.get('name', '') or proj.get('title', ''),
                'description': proj.get('description', '') or proj.get('summary', ''),
                'url': proj.get('url', '') or proj.get('link', ''),
            }

            if entry['name']:
                projects.append(entry)

        return projects

    def _parse_certifications(self) -> List[dict]:
        """Extract certifications."""
        certs_data = (
            self.data.get('certifications', [])
            or self._get_nested(self.data, 'certifications', 'values')
            or []
        )

        if isinstance(certs_data, dict):
            certs_data = certs_data.get('values', [])

        certs = []
        for cert in certs_data:
            if not isinstance(cert, dict):
                continue

            entry = {
                'name': cert.get('name', '') or cert.get('title', ''),
                'issuer': (
                    cert.get('authority', '')
                    or cert.get('issuer', '')
                    or cert.get('organization', '')
                ),
                'date': self._format_date(cert.get('startDate') or cert.get('date')),
                'url': cert.get('url', '') or cert.get('credentialUrl', ''),
            }

            if isinstance(entry['issuer'], dict):
                entry['issuer'] = entry['issuer'].get('name', '')

            if entry['name']:
                certs.append(entry)

        return certs

    # ---------------------------------------------------------------
    # Helpers
    # ---------------------------------------------------------------

    def _extract_from_contact(self, field_type: str) -> str:
        """Extract from nested contact info structures."""
        contact = self.data.get('contactInfo', {}) or self.data.get('contact', {})
        if isinstance(contact, dict):
            if field_type == 'email':
                return contact.get('email', '') or contact.get('emailAddress', '')
            elif field_type == 'phone':
                return contact.get('phone', '') or contact.get('phoneNumber', '')
        return ''

    @staticmethod
    def _get_nested(data: dict, *keys) -> Any:
        """Safely traverse nested dict keys."""
        current = data
        for key in keys:
            if isinstance(current, dict):
                current = current.get(key)
            else:
                return None
        return current

    @staticmethod
    def _format_date(date_val: Any) -> str:
        """Convert various LinkedIn date formats to string."""
        if not date_val:
            return ''

        if isinstance(date_val, str):
            return date_val

        if isinstance(date_val, dict):
            year = date_val.get('year', '')
            month = date_val.get('month', '')
            if year and month:
                month_names = [
                    '', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                    'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec',
                ]
                try:
                    month_idx = int(month)
                    if 1 <= month_idx <= 12:
                        return f"{month_names[month_idx]} {year}"
                except (ValueError, IndexError):
                    pass
                return f"{month}/{year}"
            elif year:
                return str(year)

        return str(date_val)

    @staticmethod
    def _extract_achievements(description: str) -> List[str]:
        """
        Extract bullet-point achievements from a description string.
        Splits on newlines, bullets, or numbered lists.
        """
        if not description:
            return []

        lines = re.split(r'\n|•|●|◦|▪|–\s|—\s|\d+\.\s', description)
        achievements = []
        for line in lines:
            line = line.strip().lstrip('- *')
            if len(line) > 15:
                achievements.append(line)

        return achievements

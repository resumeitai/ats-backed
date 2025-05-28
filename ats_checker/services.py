"""
Services for ATS Score Checker.
This module contains the core logic for analyzing resumes against job descriptions.
"""
import re
import json
import logging
from collections import Counter
from typing import Dict, List, Tuple, Any

# For actual implementation, you would use NLP libraries
# import spacy
# import nltk
# from nltk.tokenize import word_tokenize
# from nltk.corpus import stopwords

from .models import ATSScore, KeywordMatch, OptimizationSuggestion, JobTitleSynonym

logger = logging.getLogger(__name__)


class ATSScoreAnalyzer:
    """
    Class for analyzing resumes against job descriptions and calculating ATS scores.
    """
    
    def __init__(self, ats_score_obj: ATSScore):
        """
        Initialize with an ATSScore object.
        """
        self.ats_score = ats_score_obj
        self.resume = ats_score_obj.resume
        self.resume_content = self.resume.content
        self.job_title = ats_score_obj.job_title
        self.job_description = ats_score_obj.job_description
        
        # Results
        self.score = 0
        self.analysis = {}
        self.suggestions = []
        self.keywords = []
    
    def analyze(self) -> ATSScore:
        """
        Analyze the resume against the job description and calculate the ATS score.
        """
        try:
            # Extract keywords from job description
            self.extract_keywords()
            
            # Calculate keyword match score
            keyword_score = self.calculate_keyword_match()
            
            # Analyze resume structure
            structure_score = self.analyze_structure()
            
            # Analyze formatting
            formatting_score = self.analyze_formatting()
            
            # Calculate overall score (weighted average)
            self.score = int(0.6 * keyword_score + 0.25 * structure_score + 0.15 * formatting_score)
            
            # Generate suggestions
            self.generate_suggestions()
            
            # Save results to ATSScore object
            self.ats_score.score = self.score
            self.ats_score.analysis = self.analysis
            self.ats_score.suggestions = self.suggestions
            self.ats_score.save()
            
            # Create KeywordMatch objects
            self.save_keyword_matches()
            
            # Create OptimizationSuggestion objects
            self.save_optimization_suggestions()
            
            return self.ats_score
        
        except Exception as e:
            logger.error(f"Error analyzing resume: {str(e)}")
            # Set a default score and error message
            self.ats_score.score = 0
            self.ats_score.analysis = {"error": str(e)}
            self.ats_score.save()
            return self.ats_score
    
    def extract_keywords(self) -> None:
        """
        Extract keywords from job description.
        In a real implementation, this would use NLP libraries like spaCy or NLTK.
        """
        # Simplified implementation for demonstration
        # Remove punctuation and convert to lowercase
        text = re.sub(r'[^\w\s]', '', self.job_description.lower())
        
        # Split into words
        words = text.split()
        
        # Count word frequencies
        word_counts = Counter(words)
        
        # Filter out common words and keep only relevant keywords
        # In a real implementation, you would use a proper stopwords list and more sophisticated NLP
        common_words = {'the', 'and', 'a', 'to', 'of', 'in', 'for', 'with', 'on', 'at', 'from', 'by'}
        keywords = [(word, count) for word, count in word_counts.items() 
                   if word not in common_words and len(word) > 2]
        
        # Sort by frequency
        keywords.sort(key=lambda x: x[1], reverse=True)
        
        # Take top keywords
        top_keywords = keywords[:20]
        
        # Assign importance based on frequency
        self.keywords = []
        for keyword, count in top_keywords:
            importance = 'high' if count > 5 else 'medium' if count > 2 else 'low'
            self.keywords.append({
                'keyword': keyword,
                'count': count,
                'importance': importance
            })
    
    def calculate_keyword_match(self) -> int:
        """
        Calculate the keyword match score.
        """
        if not self.keywords:
            return 0
        
        # Convert resume content to text for analysis
        resume_text = self._get_resume_text()
        
        # Check for each keyword
        total_weight = 0
        matched_weight = 0
        
        for keyword_info in self.keywords:
            keyword = keyword_info['keyword']
            importance = keyword_info['importance']
            
            # Assign weights based on importance
            weight = 3 if importance == 'high' else 2 if importance == 'medium' else 1
            total_weight += weight
            
            # Check if keyword is in resume
            if re.search(r'\b' + re.escape(keyword) + r'\b', resume_text, re.IGNORECASE):
                matched_weight += weight
                keyword_info['found'] = True
                
                # Find context (simplified)
                match = re.search(r'[^.]*\b' + re.escape(keyword) + r'\b[^.]*', resume_text, re.IGNORECASE)
                if match:
                    keyword_info['context'] = match.group(0).strip()
            else:
                keyword_info['found'] = False
                keyword_info['context'] = ''
        
        # Calculate score as percentage
        if total_weight > 0:
            score = (matched_weight / total_weight) * 100
        else:
            score = 0
        
        # Save analysis
        self.analysis['keyword_match'] = {
            'score': score,
            'matched_keywords': sum(1 for k in self.keywords if k.get('found', False)),
            'total_keywords': len(self.keywords),
            'details': self.keywords
        }
        
        return score
    
    def analyze_structure(self) -> int:
        """
        Analyze the structure of the resume.
        """
        # Check for essential sections
        essential_sections = ['education', 'experience', 'skills']
        found_sections = []
        
        # In a real implementation, you would analyze the actual structure
        # Here we're just checking if the keys exist in the resume content
        for section in essential_sections:
            if section in self.resume_content:
                found_sections.append(section)
        
        # Calculate score based on found sections
        score = (len(found_sections) / len(essential_sections)) * 100
        
        # Save analysis
        self.analysis['structure'] = {
            'score': score,
            'found_sections': found_sections,
            'missing_sections': [s for s in essential_sections if s not in found_sections]
        }
        
        return score
    
    def analyze_formatting(self) -> int:
        """
        Analyze the formatting of the resume.
        """
        # In a real implementation, you would analyze the actual formatting
        # Here we're just returning a default score
        score = 80
        
        # Save analysis
        self.analysis['formatting'] = {
            'score': score,
            'issues': []
        }
        
        return score
    
    def generate_suggestions(self) -> None:
        """
        Generate suggestions for improving the resume.
        """
        suggestions = []
        
        # Suggest adding missing keywords
        missing_keywords = [k['keyword'] for k in self.keywords 
                           if k.get('importance') in ['high', 'medium'] and not k.get('found', False)]
        if missing_keywords:
            suggestions.append({
                'type': 'missing_keywords',
                'section': 'general',
                'description': f"Add these important keywords to your resume: {', '.join(missing_keywords)}",
                'keywords': missing_keywords
            })
        
        # Suggest adding missing sections
        if 'structure' in self.analysis and 'missing_sections' in self.analysis['structure']:
            missing_sections = self.analysis['structure']['missing_sections']
            if missing_sections:
                suggestions.append({
                    'type': 'missing_sections',
                    'section': 'structure',
                    'description': f"Add these missing sections to your resume: {', '.join(missing_sections)}",
                    'sections': missing_sections
                })
        
        # Save suggestions
        self.suggestions = suggestions
    
    def save_keyword_matches(self) -> None:
        """
        Save keyword matches to database.
        """
        for keyword_info in self.keywords:
            KeywordMatch.objects.create(
                ats_score=self.ats_score,
                keyword=keyword_info['keyword'],
                found=keyword_info.get('found', False),
                importance=keyword_info['importance'],
                context=keyword_info.get('context', '')
            )
    
    def save_optimization_suggestions(self) -> None:
        """
        Save optimization suggestions to database.
        """
        for suggestion in self.suggestions:
            if suggestion['type'] == 'missing_keywords':
                for keyword in suggestion['keywords']:
                    OptimizationSuggestion.objects.create(
                        ats_score=self.ats_score,
                        section='general',
                        original_text='',
                        suggested_text=f"Consider adding the keyword '{keyword}' to your resume",
                        reason=f"The keyword '{keyword}' is important for this job but was not found in your resume"
                    )
            elif suggestion['type'] == 'missing_sections':
                for section in suggestion['sections']:
                    OptimizationSuggestion.objects.create(
                        ats_score=self.ats_score,
                        section=section,
                        original_text='',
                        suggested_text=f"Add a {section} section to your resume",
                        reason=f"A {section} section is expected in resumes for this type of job"
                    )
    
    def _get_resume_text(self) -> str:
        """
        Convert resume content to text for analysis.
        """
        # In a real implementation, you would extract text from the resume content
        # Here we're just concatenating all values in the resume content
        if isinstance(self.resume_content, dict):
            text = ""
            for section, content in self.resume_content.items():
                if isinstance(content, str):
                    text += content + " "
                elif isinstance(content, list):
                    for item in content:
                        if isinstance(item, dict):
                            text += " ".join(str(v) for v in item.values()) + " "
                        else:
                            text += str(item) + " "
                elif isinstance(content, dict):
                    text += " ".join(str(v) for v in content.values()) + " "
            return text
        elif isinstance(self.resume_content, str):
            return self.resume_content
        else:
            return str(self.resume_content)


def analyze_resume(ats_score_id: int) -> ATSScore:
    """
    Analyze a resume against a job description.
    This function can be called from a Celery task.
    """
    try:
        ats_score = ATSScore.objects.get(id=ats_score_id)
        analyzer = ATSScoreAnalyzer(ats_score)
        return analyzer.analyze()
    except ATSScore.DoesNotExist:
        logger.error(f"ATSScore with ID {ats_score_id} does not exist")
        return None
    except Exception as e:
        logger.error(f"Error analyzing resume: {str(e)}")
        return None


def apply_suggestion(suggestion_id: int) -> bool:
    """
    Apply a suggestion to a resume.
    """
    try:
        suggestion = OptimizationSuggestion.objects.get(id=suggestion_id)
        
        if suggestion.applied:
            return False
        
        # Get the resume
        resume = suggestion.ats_score.resume
        
        # Apply the suggestion
        # In a real implementation, you would modify the resume content based on the suggestion
        # Here we're just marking the suggestion as applied
        suggestion.applied = True
        suggestion.save()
        
        return True
    except OptimizationSuggestion.DoesNotExist:
        logger.error(f"OptimizationSuggestion with ID {suggestion_id} does not exist")
        return False
    except Exception as e:
        logger.error(f"Error applying suggestion: {str(e)}")
        return False
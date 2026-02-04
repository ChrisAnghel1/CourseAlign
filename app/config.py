"""Configuration module for CourseAlign API."""
import json
import os
from typing import Dict, Any
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Application configuration."""
    
    def __init__(self):
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.api_secret = os.getenv("COURSEALIGN_API_SECRET")
        self.courses: Dict[str, Any] = {}
        self._load_courses()
    
    def _load_courses(self):
        """Load courses configuration from courses.json."""
        courses_file = "courses.json"
        if not os.path.exists(courses_file):
            raise FileNotFoundError(f"courses.json not found at {courses_file}")
        
        with open(courses_file, 'r') as f:
            self.courses = json.load(f)
    
    def get_course_config(self, course_code: str) -> Dict[str, Any]:
        """Get configuration for a specific course."""
        if course_code not in self.courses:
            raise ValueError(f"Course {course_code} not found in configuration")
        return self.courses[course_code]
    
    def get_all_course_codes(self) -> list:
        """Get list of all configured course codes."""
        return list(self.courses.keys())


# Global configuration instance
config = Config()

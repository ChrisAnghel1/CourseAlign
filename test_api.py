"""Test script for CourseAlign API."""
import requests
import sys
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")
API_TOKEN = os.getenv("COURSEALIGN_API_SECRET")

if not API_TOKEN:
    print("ERROR: COURSEALIGN_API_SECRET not found in environment variables")
    print("Please set it in your .env file or export it")
    sys.exit(1)

def test_health():
    """Test health endpoint."""
    response = requests.get(f"{API_URL}/health")
    print("Health check:", response.json())
    return response.status_code == 200

def test_courses():
    """Test courses endpoint."""
    response = requests.get(f"{API_URL}/courses")
    print("Courses:", response.json())
    return response.status_code == 200

def index_textbook(course_code, textbook_path):
    """Index a textbook PDF."""
    print(f"\nIndexing textbook for {course_code}...")
    
    with open(textbook_path, 'rb') as f:
        response = requests.post(
            f"{API_URL}/index-textbook",
            headers={"Authorization": f"Bearer {API_TOKEN}"},
            data={"course_code": course_code},
            files={"textbook_pdf": f}
        )
    
    if response.status_code == 200:
        result = response.json()
        print(f"✓ Successfully indexed {result['pages_indexed']} pages, {result['chunks_indexed']} chunks")
        return True
    else:
        print(f"✗ Error: {response.status_code}")
        print(response.text)
        return False

def process_slides(course_code, slides_path, output_path="Study_Context_Guide.docx"):
    """Process lecture slides and generate study guide."""
    print(f"\nProcessing slides for {course_code}...")
    
    with open(slides_path, 'rb') as f:
        response = requests.post(
            f"{API_URL}/process",
            headers={"Authorization": f"Bearer {API_TOKEN}"},
            data={
                "course_code": course_code,
                "output_format": "docx"
            },
            files={"slides_file": f}
        )
    
    if response.status_code == 200:
        with open(output_path, 'wb') as out:
            out.write(response.content)
        print(f"✓ Study guide saved to: {output_path}")
        return True
    else:
        print(f"✗ Error: {response.status_code}")
        print(response.text)
        return False

if __name__ == "__main__":
    print("=== CourseAlign API Test ===\n")
    
    # Test basic endpoints
    test_health()
    test_courses()
    
    # Example usage - modify these paths for your files
    if len(sys.argv) >= 4:
        course_code = sys.argv[1]
        textbook_path = sys.argv[2]
        slides_path = sys.argv[3]
        
        # Index textbook first
        if index_textbook(course_code, textbook_path):
            # Then process slides
            process_slides(course_code, slides_path)
    else:
        print("\n" + "="*50)
        print("To test with your files, run:")
        print('python test_api.py CP312 "path/to/textbook.pdf" "path/to/slides.pptx"')
        print("="*50)

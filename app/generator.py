"""Study guide generator module using OpenAI."""
from typing import List, Dict, Any
from openai import OpenAI
from app.config import config


class StudyGuideGenerator:
    """Generates study context guides using OpenAI chat completion."""
    
    def __init__(self):
        self.client = OpenAI(api_key=config.openai_api_key)
        self.model = "gpt-4o-mini"
    
    def create_system_prompt(self) -> str:
        """Create the system prompt for the CourseAlign specialist."""
        return """You are the CourseAlign Specialist, an expert at connecting lecture content with textbook knowledge.

YOUR ROLE:
- Analyze lecture slides and align them with textbook content
- Provide deep context grounded ONLY in retrieved textbook passages
- Help students understand connections between slides and readings
- Identify assumptions, prerequisites, and open questions

CRITICAL RULES FOR GROUNDING:
1. ONLY use information from the provided textbook chunks
2. ALWAYS cite page numbers from chunk metadata (e.g., "pp. 45-47")
3. NEVER fabricate or guess page numbers
4. If information is not in the chunks, say "not found in provided textbook sections"
5. Never make up textbook claims or citations

OUTPUT STRUCTURE:
Your response must be a well-structured study guide with these sections:

1. CONCEPT MAP
   - List key concepts from the slides
   - Brief definition/context for each

2. MAPPED DEEP DIVES
   For each major concept, provide:
   - **Concept Name**
   - **Textbook Context**: Detailed explanation from textbook chunks with page citations
   - **Confidence Level**: High/Medium/Low based on how well the textbook covers this
   - **Connection to Slides**: How this relates to what was presented

3. SLIDE ASSUMPTIONS & PREREQUISITES
   - Background knowledge assumed by the slides
   - Prerequisites students should know
   - Concepts mentioned but not fully explained

4. OPEN QUESTIONS & GAPS
   - Topics in slides not well-covered by retrieved textbook sections
   - Questions students should research further
   - Areas where additional reading would help

5. SOURCES USED
   - List the textbook page ranges consulted
   - Note any gaps in available material

CONFIDENCE LEVELS:
- **High**: Textbook provides comprehensive coverage with clear explanations
- **Medium**: Textbook mentions the concept but with limited detail
- **Low**: Concept only briefly mentioned or not found in retrieved sections

Remember: Academic integrity requires precise citations. Only reference what you can directly verify from the provided chunks."""

    def create_user_prompt(
        self,
        course_code: str,
        slide_text: str,
        key_concepts: List[str],
        retrieved_chunks: List[Dict[str, Any]]
    ) -> str:
        """
        Create the user prompt with lecture and textbook content.
        
        Args:
            course_code: Course code
            slide_text: Full text from slides
            key_concepts: List of key concepts extracted
            retrieved_chunks: Retrieved textbook chunks with metadata
            
        Returns:
            Formatted user prompt
        """
        # Format retrieved chunks
        chunks_text = self._format_chunks(retrieved_chunks)
        
        # Format key concepts
        concepts_text = "\n".join([f"- {concept}" for concept in key_concepts[:15]])
        
        prompt = f"""
COURSE: {course_code}

LECTURE SLIDES CONTENT:
{slide_text[:4000]}  {f'... [truncated, total length: {len(slide_text)} chars]' if len(slide_text) > 4000 else ''}

KEY CONCEPTS IDENTIFIED:
{concepts_text}

RETRIEVED TEXTBOOK CHUNKS:
{chunks_text}

---

Please create a comprehensive Study Context Guide following your role instructions. Ensure all textbook information includes page citations from the chunk metadata above. Be thorough but grounded exclusively in the provided material.
"""
        return prompt
    
    def _format_chunks(self, chunks: List[Dict[str, Any]]) -> str:
        """Format chunks for the prompt."""
        formatted = []
        
        for i, chunk in enumerate(chunks, 1):
            page_info = f"{chunk['page_start']}-{chunk['page_end']}" if chunk['page_start'] != chunk['page_end'] else str(chunk['page_start'])
            
            formatted.append(f"""
[CHUNK {i}] - Pages {page_info}
{chunk['text']}
""")
        
        return "\n".join(formatted)
    
    def generate_study_guide(
        self,
        course_code: str,
        slide_text: str,
        key_concepts: List[str],
        retrieved_chunks: List[Dict[str, Any]]
    ) -> str:
        """
        Generate study guide using OpenAI chat completion.
        
        Args:
            course_code: Course code
            slide_text: Full text from slides
            key_concepts: List of key concepts
            retrieved_chunks: Retrieved textbook chunks
            
        Returns:
            Generated study guide text
        """
        system_prompt = self.create_system_prompt()
        user_prompt = self.create_user_prompt(
            course_code,
            slide_text,
            key_concepts,
            retrieved_chunks
        )
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3,  # Lower temperature for more consistent, factual output
            max_tokens=4000
        )
        
        return response.choices[0].message.content

"""RAG retrieval module for CourseAlign API."""
import numpy as np
from typing import List, Dict, Any
from openai import OpenAI
from app.pdf_indexer import PDFIndexer
from app.config import config


class RAGRetriever:
    """Handles retrieval of relevant textbook chunks using RAG."""
    
    def __init__(self):
        self.client = OpenAI(api_key=config.openai_api_key)
        self.indexer = PDFIndexer()
        self.embedding_model = "text-embedding-3-small"
    
    def retrieve_relevant_chunks(
        self, 
        course_code: str, 
        query_text: str, 
        top_k: int = 12
    ) -> List[Dict[str, Any]]:
        """
        Retrieve top-k most relevant chunks from course textbook.
        
        Args:
            course_code: Course code
            query_text: Query text (e.g., slide content)
            top_k: Number of chunks to retrieve
            
        Returns:
            List of chunk dicts with relevance scores
        """
        # Load index and chunks
        index, chunks = self.indexer.load_index(course_code)
        
        # Create embedding for query
        response = self.client.embeddings.create(
            model=self.embedding_model,
            input=[query_text]
        )
        query_embedding = np.array([response.data[0].embedding], dtype=np.float32)
        
        # Search FAISS index
        distances, indices = index.search(query_embedding, min(top_k, len(chunks)))
        
        # Prepare results
        results = []
        for i, (distance, idx) in enumerate(zip(distances[0], indices[0])):
            if idx < len(chunks):  # Ensure valid index
                chunk = chunks[idx].copy()
                chunk["relevance_score"] = float(distance)
                chunk["rank"] = i + 1
                results.append(chunk)
        
        return results
    
    def format_chunks_for_prompt(self, chunks: List[Dict[str, Any]]) -> str:
        """
        Format retrieved chunks for inclusion in prompt.
        
        Args:
            chunks: List of chunk dicts
            
        Returns:
            Formatted string for prompt
        """
        formatted_chunks = []
        
        for chunk in chunks:
            page_info = f"Pages {chunk['page_start']}-{chunk['page_end']}" if chunk['page_start'] != chunk['page_end'] else f"Page {chunk['page_start']}"
            
            formatted_chunk = f"""
--- CHUNK {chunk['rank']} ---
{page_info}
Text: {chunk['text'][:800]}{'...' if len(chunk['text']) > 800 else ''}
"""
            formatted_chunks.append(formatted_chunk)
        
        return "\n".join(formatted_chunks)

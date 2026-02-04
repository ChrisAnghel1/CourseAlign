"""PDF indexing module for CourseAlign API."""
import os
import json
import fitz  # PyMuPDF
import numpy as np
import faiss
from typing import List, Dict, Any, Tuple
from openai import OpenAI
from app.config import config


class PDFIndexer:
    """Handles PDF text extraction, chunking, embedding, and FAISS indexing."""
    
    def __init__(self):
        self.client = OpenAI(api_key=config.openai_api_key)
        self.embedding_model = "text-embedding-3-small"
        self.embedding_dimension = 1536
        
    def extract_text_from_pdf(self, pdf_path: str) -> List[Dict[str, Any]]:
        """
        Extract text from PDF page by page.
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            List of dicts with page_number and text
        """
        doc = fitz.open(pdf_path)
        pages = []
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text()
            pages.append({
                "page_number": page_num + 1,  # 1-indexed
                "text": text
            })
        
        doc.close()
        return pages
    
    def chunk_text(
        self, 
        pages: List[Dict[str, Any]], 
        target_words: int = 750, 
        overlap_words: int = 150
    ) -> List[Dict[str, Any]]:
        """
        Chunk text into overlapping segments with metadata.
        
        Args:
            pages: List of page dicts with page_number and text
            target_words: Target chunk size (600-900 range)
            overlap_words: Overlap between chunks (~150)
            
        Returns:
            List of chunk dicts with text, page_start, page_end, chunk_id
        """
        chunks = []
        chunk_id = 0
        
        # Concatenate all text with page markers
        full_text = ""
        page_boundaries = []  # Track where each page starts in the full text
        current_pos = 0
        
        for page in pages:
            page_text = page["text"]
            full_text += page_text + "\n\n"
            page_boundaries.append({
                "page_number": page["page_number"],
                "start_pos": current_pos,
                "end_pos": current_pos + len(page_text)
            })
            current_pos = len(full_text)
        
        # Split into words
        words = full_text.split()
        
        i = 0
        while i < len(words):
            # Extract chunk
            chunk_words = words[i:i + target_words]
            chunk_text = " ".join(chunk_words)
            
            # Determine which pages this chunk spans
            chunk_start_char = len(" ".join(words[:i]))
            chunk_end_char = chunk_start_char + len(chunk_text)
            
            pages_in_chunk = set()
            for pb in page_boundaries:
                # Check if chunk overlaps with this page
                if not (chunk_end_char < pb["start_pos"] or chunk_start_char > pb["end_pos"]):
                    pages_in_chunk.add(pb["page_number"])
            
            if pages_in_chunk:
                page_start = min(pages_in_chunk)
                page_end = max(pages_in_chunk)
            else:
                page_start = 1
                page_end = 1
            
            chunks.append({
                "chunk_id": chunk_id,
                "text": chunk_text,
                "page_start": page_start,
                "page_end": page_end,
                "word_count": len(chunk_words)
            })
            
            chunk_id += 1
            
            # Move forward with overlap
            i += target_words - overlap_words
        
        return chunks
    
    def create_embeddings(self, texts: List[str]) -> np.ndarray:
        """
        Create embeddings for a list of texts using OpenAI.
        
        Args:
            texts: List of text strings
            
        Returns:
            NumPy array of embeddings (n_texts, embedding_dim)
        """
        # OpenAI API has limits, batch if needed
        batch_size = 100
        all_embeddings = []
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            response = self.client.embeddings.create(
                model=self.embedding_model,
                input=batch
            )
            embeddings = [item.embedding for item in response.data]
            all_embeddings.extend(embeddings)
        
        return np.array(all_embeddings, dtype=np.float32)
    
    def build_faiss_index(self, embeddings: np.ndarray) -> faiss.IndexFlatL2:
        """
        Build FAISS index from embeddings.
        
        Args:
            embeddings: NumPy array of embeddings
            
        Returns:
            FAISS index
        """
        dimension = embeddings.shape[1]
        index = faiss.IndexFlatL2(dimension)
        index.add(embeddings)
        return index
    
    def save_index(
        self, 
        course_code: str, 
        index: faiss.IndexFlatL2, 
        chunks: List[Dict[str, Any]]
    ):
        """
        Save FAISS index and chunk metadata to disk.
        
        Args:
            course_code: Course code
            index: FAISS index
            chunks: List of chunk dicts with metadata
        """
        course_config = config.get_course_config(course_code)
        index_dir = course_config["index_path"]
        
        # Create directory if it doesn't exist
        os.makedirs(index_dir, exist_ok=True)
        
        # Save FAISS index
        index_file = os.path.join(index_dir, "index.faiss")
        faiss.write_index(index, index_file)
        
        # Save chunks as JSONL
        chunks_file = os.path.join(index_dir, "chunks.jsonl")
        with open(chunks_file, 'w', encoding='utf-8') as f:
            for chunk in chunks:
                f.write(json.dumps(chunk) + "\n")
    
    def load_index(self, course_code: str) -> Tuple[faiss.IndexFlatL2, List[Dict[str, Any]]]:
        """
        Load FAISS index and chunk metadata from disk.
        
        Args:
            course_code: Course code
            
        Returns:
            Tuple of (FAISS index, list of chunks)
        """
        course_config = config.get_course_config(course_code)
        index_dir = course_config["index_path"]
        
        index_file = os.path.join(index_dir, "index.faiss")
        chunks_file = os.path.join(index_dir, "chunks.jsonl")
        
        if not os.path.exists(index_file):
            raise FileNotFoundError(f"Index not found for course {course_code}")
        
        # Load FAISS index
        index = faiss.read_index(index_file)
        
        # Load chunks
        chunks = []
        with open(chunks_file, 'r', encoding='utf-8') as f:
            for line in f:
                chunks.append(json.loads(line))
        
        return index, chunks
    
    def index_exists(self, course_code: str) -> bool:
        """Check if index exists for a course."""
        try:
            course_config = config.get_course_config(course_code)
            index_dir = course_config["index_path"]
            index_file = os.path.join(index_dir, "index.faiss")
            return os.path.exists(index_file)
        except (ValueError, KeyError):
            return False
    
    def index_textbook(self, course_code: str, pdf_path: str) -> Dict[str, Any]:
        """
        Complete indexing pipeline for a textbook PDF.
        
        Args:
            course_code: Course code
            pdf_path: Path to PDF file
            
        Returns:
            Dict with indexing statistics
        """
        # Extract text from PDF
        pages = self.extract_text_from_pdf(pdf_path)
        
        # Chunk text
        chunks = self.chunk_text(pages)
        
        # Create embeddings
        chunk_texts = [chunk["text"] for chunk in chunks]
        embeddings = self.create_embeddings(chunk_texts)
        
        # Build FAISS index
        index = self.build_faiss_index(embeddings)
        
        # Add course_code to each chunk
        for chunk in chunks:
            chunk["course_code"] = course_code
        
        # Save index and metadata
        self.save_index(course_code, index, chunks)
        
        return {
            "course_code": course_code,
            "pages_indexed": len(pages),
            "chunks_indexed": len(chunks)
        }

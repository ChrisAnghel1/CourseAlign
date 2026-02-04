"""FastAPI main application for CourseAlign API."""
import os
import tempfile
from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Form
from fastapi.responses import Response
from typing import Optional
import logging

from app.auth import verify_token
from app.config import config
from app.pdf_indexer import PDFIndexer
from app.pptx_parser import PPTXParser
from app.rag import RAGRetriever
from app.generator import StudyGuideGenerator
from app.docx_writer import DOCXWriter

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="CourseAlign API",
    description="API for aligning lecture slides with textbook content using RAG",
    version="1.0.0"
)

# Initialize components
pdf_indexer = PDFIndexer()
pptx_parser = PPTXParser()
rag_retriever = RAGRetriever()
study_guide_generator = StudyGuideGenerator()
docx_writer = DOCXWriter()


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}


@app.get("/courses")
async def get_courses():
    """
    Get list of configured course codes.
    
    Returns:
        List of course codes with their index status
    """
    course_codes = config.get_all_course_codes()
    
    courses_info = []
    for course_code in course_codes:
        indexed = pdf_indexer.index_exists(course_code)
        courses_info.append({
            "course_code": course_code,
            "indexed": indexed
        })
    
    return {
        "courses": courses_info,
        "total": len(courses_info)
    }


@app.post("/index-textbook")
async def index_textbook(
    course_code: str = Form(...),
    textbook_pdf: UploadFile = File(...),
    _: str = Depends(verify_token)
):
    """
    Index a textbook PDF for a course.
    
    Args:
        course_code: Course code (must match courses.json)
        textbook_pdf: PDF file to index
        
    Returns:
        Indexing statistics
    """
    # Validate course code
    try:
        config.get_course_config(course_code)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Course code '{course_code}' not found in configuration"
        )
    
    # Validate file type
    if not textbook_pdf.filename.endswith('.pdf'):
        raise HTTPException(
            status_code=400,
            detail="File must be a PDF"
        )
    
    # Save uploaded file to temporary location
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
            content = await textbook_pdf.read()
            temp_file.write(content)
            temp_file_path = temp_file.name
        
        logger.info(f"Indexing textbook for course {course_code}")
        
        # Index the PDF
        result = pdf_indexer.index_textbook(course_code, temp_file_path)
        
        logger.info(f"Successfully indexed {result['pages_indexed']} pages, {result['chunks_indexed']} chunks")
        
        return result
        
    except Exception as e:
        logger.error(f"Error indexing textbook: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error indexing textbook: {str(e)}"
        )
    finally:
        # Clean up temporary file
        if os.path.exists(temp_file_path):
            os.unlink(temp_file_path)


@app.post("/process")
async def process_slides(
    course_code: str = Form(...),
    slides_file: UploadFile = File(...),
    slides_filename: Optional[str] = Form(None),
    output_format: str = Form("docx"),
    _: str = Depends(verify_token)
):
    """
    Process lecture slides and generate Study Context Guide.
    
    Args:
        course_code: Course code
        slides_file: PPTX file
        slides_filename: Optional custom filename for output
        output_format: Output format (must be 'docx')
        
    Returns:
        DOCX file as response
    """
    # Validate output format
    if output_format != "docx":
        raise HTTPException(
            status_code=400,
            detail="Only 'docx' output format is currently supported"
        )
    
    # Validate course code
    try:
        config.get_course_config(course_code)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Course code '{course_code}' not found in configuration"
        )
    
    # Check if course is indexed
    if not pdf_indexer.index_exists(course_code):
        raise HTTPException(
            status_code=404,
            detail=f"Course {course_code} has not been indexed yet. Please index the textbook first."
        )
    
    # Validate file type
    if not (slides_file.filename.endswith('.pptx') or slides_file.filename.endswith('.pdf')):
        raise HTTPException(
            status_code=400,
            detail="Slides file must be a PPTX or PDF file"
        )
    
    # Use provided filename or extract from upload
    output_filename = slides_filename or os.path.splitext(slides_file.filename)[0]
    
    temp_pptx_path = None
    
    try:
        # Save slides file to temporary file
        file_ext = os.path.splitext(slides_file.filename)[1]
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as temp_file:
            content = await slides_file.read()
            temp_file.write(content)
            temp_pptx_path = temp_file.name
        
        logger.info(f"Processing slides for course {course_code}")
        
        # Extract text from slides
        logger.info("Extracting text from slides...")
        pptx_data = pptx_parser.extract_text_from_slides(temp_pptx_path)
        slide_text = pptx_data["full_text"]
        
        # Extract key concepts
        logger.info("Extracting key concepts...")
        key_concepts = pptx_parser.extract_key_concepts(slide_text)
        
        # Retrieve relevant chunks using RAG
        logger.info("Retrieving relevant textbook chunks...")
        retrieved_chunks = rag_retriever.retrieve_relevant_chunks(
            course_code=course_code,
            query_text=slide_text,
            top_k=12
        )
        
        # Generate study guide
        logger.info("Generating study guide...")
        study_guide_content = study_guide_generator.generate_study_guide(
            course_code=course_code,
            slide_text=slide_text,
            key_concepts=key_concepts,
            retrieved_chunks=retrieved_chunks
        )
        
        # Create DOCX
        logger.info("Creating DOCX file...")
        docx_bytes = docx_writer.create_study_guide_docx(
            content=study_guide_content,
            slides_filename=output_filename,
            course_code=course_code
        )
        
        # Return DOCX as response
        response_filename = f"Study Context Guide - {output_filename}.docx"
        
        return Response(
            content=docx_bytes,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={
                "Content-Disposition": f'attachment; filename="{response_filename}"'
            }
        )
        
    except FileNotFoundError as e:
        logger.error(f"File not found: {str(e)}")
        raise HTTPException(
            status_code=404,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error processing slides: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error processing slides: {str(e)}"
        )
    finally:
        # Clean up temporary file
        if temp_pptx_path and os.path.exists(temp_pptx_path):
            os.unlink(temp_pptx_path)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

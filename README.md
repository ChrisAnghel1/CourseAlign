# CourseAlign API

Production-quality Python FastAPI backend that implements an API twin of CourseAlign GPT. This API accepts lecture slide uploads, retrieves relevant context from course textbooks using RAG (Retrieval Augmented Generation), and produces formatted Study Context Guides.

## Features

- **Textbook Indexing**: Extract, chunk, and index textbook PDFs with vector embeddings
- **RAG Retrieval**: Semantic search over textbook content using FAISS
- **Slide Processing**: Extract text from PPTX files including titles, bullets, and speaker notes
- **Study Guide Generation**: AI-powered study guides with grounded textbook citations
- **DOCX Output**: Professional Word documents with structured sections
- **Bearer Token Authentication**: Secure POST endpoints

## Supported Courses

- CP312
- CP372
- CP373
- CP216
- CP468

## Setup

### Prerequisites

- Python 3.9 or higher
- OpenAI API key

### Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd courseAlign-api
   ```

2. **Create a virtual environment**:
   ```bash
   python -m venv venv
   ```

3. **Activate the virtual environment**:
   - Windows:
     ```bash
     venv\Scripts\activate
     ```
   - Linux/Mac:
     ```bash
     source venv/bin/activate
     ```

4. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

5. **Configure environment variables**:
   
   Create a `.env` file in the project root:
   ```bash
   cp .env.example .env
   ```
   
   Edit `.env` and add your credentials:
   ```
   OPENAI_API_KEY=sk-your-openai-api-key-here
   COURSEALIGN_API_SECRET=your-secret-token-here
   ```

## Running the Server

Start the FastAPI server:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

For development with auto-reload:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

The API will be available at `http://localhost:8000`

Interactive API docs: `http://localhost:8000/docs`

## API Endpoints

### 1. Health Check

```bash
GET /health
```

**Response**:
```json
{
  "status": "ok"
}
```

### 2. List Courses

```bash
GET /courses
```

**Response**:
```json
{
  "courses": [
    {
      "course_code": "CP312",
      "indexed": true
    },
    ...
  ],
  "total": 5
}
```

### 3. Index Textbook

Index a textbook PDF for a course. This must be done before processing slides.

```bash
POST /index-textbook
Authorization: Bearer <your-api-secret>
Content-Type: multipart/form-data

Fields:
  - course_code: CP312
  - textbook_pdf: <PDF file>
```

**Example with curl**:
```bash
curl -X POST "http://localhost:8000/index-textbook" \
  -H "Authorization: Bearer your-secret-token-here" \
  -F "course_code=CP312" \
  -F "textbook_pdf=@/path/to/textbook.pdf"
```

**Response**:
```json
{
  "course_code": "CP312",
  "pages_indexed": 450,
  "chunks_indexed": 782
}
```

**What this does**:
- Extracts text page-by-page from the PDF
- Chunks text into ~600-900 word segments with 150 word overlap
- Creates OpenAI embeddings for each chunk
- Builds a FAISS index for similarity search
- Stores index and metadata in `indexes/<course_code>/`

### 4. Process Slides

Process lecture slides and generate a Study Context Guide.

```bash
POST /process
Authorization: Bearer <your-api-secret>
Content-Type: multipart/form-data

Fields:
  - course_code: CP312
  - slides_file: <PPTX file>
  - slides_filename: (optional) Custom name for output
  - output_format: docx
```

**Example with curl**:
```bash
curl -X POST "http://localhost:8000/process" \
  -H "Authorization: Bearer your-secret-token-here" \
  -F "course_code=CP312" \
  -F "slides_file=@/path/to/lecture.pptx" \
  -F "slides_filename=Week 3 Lecture" \
  -F "output_format=docx" \
  -o "Study Context Guide.docx"
```

**Response**:
- Returns a DOCX file as attachment
- Filename: `Study Context Guide - <slides_filename>.docx`

**What this does**:
1. Validates course code and checks if textbook is indexed
2. Extracts text from PPTX (titles, bullets, speaker notes)
3. Identifies key concepts from slides
4. Retrieves top 10-14 most relevant textbook chunks using RAG
5. Generates Study Context Guide with OpenAI
6. Formats output as a professional DOCX with sections:
   - Concept Map
   - Mapped Deep Dives (with textbook page citations)
   - Slide Assumptions & Prerequisites
   - Open Questions & Gaps
   - Sources Used

## Index Storage

Indexes are stored in the `indexes/` directory:

```
indexes/
├── CP312/
│   ├── index.faiss         # FAISS vector index
│   └── chunks.jsonl        # Chunk metadata and text
├── CP372/
│   ├── index.faiss
│   └── chunks.jsonl
...
```

Each chunk in `chunks.jsonl` contains:
- `chunk_id`: Unique identifier
- `text`: Chunk text content
- `page_start`: Starting page number
- `page_end`: Ending page number
- `course_code`: Associated course
- `word_count`: Number of words in chunk

## Project Structure

```
courseAlign-api/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app and routes
│   ├── auth.py              # Bearer token authentication
│   ├── config.py            # Configuration loader
│   ├── pdf_indexer.py       # PDF extraction, chunking, FAISS indexing
│   ├── pptx_parser.py       # PPTX text extraction
│   ├── rag.py               # RAG retrieval system
│   ├── generator.py         # OpenAI study guide generation
│   └── docx_writer.py       # DOCX document creation
├── indexes/                 # Vector indexes (created at runtime)
├── courses.json             # Course configuration
├── requirements.txt         # Python dependencies
├── .env.example             # Environment variables template
├── .env                     # Your environment variables (not in git)
├── .gitignore
└── README.md
```

## Configuration

Course configuration is defined in `courses.json`:

```json
{
  "CP312": {
    "textbook_filename": "Textbook.pdf",
    "index_path": "indexes/CP312"
  },
  ...
}
```

## Error Handling

The API provides clear error messages:

- **400 Bad Request**: Invalid input (wrong course code, wrong file type, etc.)
- **401 Unauthorized**: Invalid or missing Bearer token
- **404 Not Found**: Course not indexed or resource not found
- **500 Internal Server Error**: Server-side processing error

## Security

- All POST endpoints require Bearer token authentication
- Set `COURSEALIGN_API_SECRET` in your `.env` file
- Include in requests: `Authorization: Bearer <your-secret>`
- Never commit `.env` file to version control

## AI Grounding

The study guide generator follows strict grounding rules:

- **Only uses information from retrieved textbook chunks**
- **Always cites page numbers from chunk metadata**
- **Never fabricates textbook claims or page numbers**
- **Includes confidence levels** (High/Medium/Low) per concept
- **Identifies gaps** where slides cover topics not in retrieved chunks
- **Lists assumptions and prerequisites** from slide content

## Development

### Testing with Python

```python
import requests

# Index a textbook
with open('textbook.pdf', 'rb') as f:
    response = requests.post(
        'http://localhost:8000/index-textbook',
        headers={'Authorization': 'Bearer your-secret'},
        data={'course_code': 'CP312'},
        files={'textbook_pdf': f}
    )
    print(response.json())

# Process slides
with open('lecture.pptx', 'rb') as f:
    response = requests.post(
        'http://localhost:8000/process',
        headers={'Authorization': 'Bearer your-secret'},
        data={
            'course_code': 'CP312',
            'output_format': 'docx'
        },
        files={'slides_file': f}
    )
    
    with open('output.docx', 'wb') as out:
        out.write(response.content)
```

### Logging

The application uses Python logging. View logs in the console when running the server.

## Troubleshooting

### "API secret not configured on server"
- Ensure `COURSEALIGN_API_SECRET` is set in your `.env` file

### "OpenAI API error"
- Verify `OPENAI_API_KEY` is valid and has sufficient credits
- Check your OpenAI API usage limits

### "Course has not been indexed yet"
- Run `/index-textbook` endpoint first for that course

### "Invalid authentication credentials"
- Verify Bearer token matches `COURSEALIGN_API_SECRET`

## License

Proprietary - CourseAlign API

## Support

For issues or questions, please contact the development team.

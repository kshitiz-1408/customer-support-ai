import io
import logging
from typing import List, Dict, Any
from pypdf import PdfReader

logger = logging.getLogger("customer_support_backend")


def chunk_text(text: str, chunk_size: int = 800, overlap: int = 150) -> List[str]:
    """
    Slices raw text into chunks of character size 'chunk_size' with 'overlap'.
    Normalizes multiple whitespace occurrences before split.
    """
    # Normalize spaces to ensure deterministic lengths
    clean_text = " ".join(text.split())
    
    if not clean_text:
        return []
        
    if len(clean_text) <= chunk_size:
        return [clean_text]
        
    chunks = []
    start = 0
    while start < len(clean_text):
        end = start + chunk_size
        chunks.append(clean_text[start:end])
        # Increment by step size
        start += (chunk_size - overlap)
        
        # Guard against zero/negative steps
        if chunk_size <= overlap:
            break
            
    return chunks


def extract_chunks_from_pdf(file_bytes: bytes, filename: str) -> List[Dict[str, Any]]:
    """
    Parses a PDF page-by-page, extracts text, chunks it deterministically,
    and returns a list of dictionaries with content and page metadata.
    """
    logger.info(f"Starting PDF parsing execution for file: '{filename}'")
    
    try:
        pdf_reader = PdfReader(io.BytesIO(file_bytes))
        num_pages = len(pdf_reader.pages)
        logger.debug(f"File '{filename}' contains {num_pages} pages.")
    except Exception as e:
        logger.error(f"Failed to read PDF file structure: {str(e)}")
        raise ValueError(f"Unable to read PDF file structure: {str(e)}")
        
    chunks_output = []
    
    for i, page in enumerate(pdf_reader.pages):
        page_num = i + 1
        try:
            page_text = page.extract_text()
        except Exception as e:
            logger.warning(f"Failed to extract text from page {page_num} in '{filename}': {str(e)}")
            continue
            
        if not page_text or not page_text.strip():
            logger.debug(f"Skipping page {page_num} in '{filename}' (empty or non-extractable text)")
            continue
            
        page_chunks = chunk_text(page_text)
        logger.debug(f"Extracted {len(page_chunks)} chunks from page {page_num}")
        
        for chunk in page_chunks:
            chunks_output.append({
                "content": chunk,
                "metadata": {
                    "source": filename,
                    "page": page_num,
                    "type": "pdf"
                }
            })
            
    if not chunks_output:
        logger.error(f"Ingestion rejected: No readable text extracted from '{filename}'")
        raise ValueError("No readable text could be extracted from this PDF document.")
        
    logger.info(f"Successfully processed PDF '{filename}'. Generated {len(chunks_output)} chunks.")
    return chunks_output


def extract_chunks_from_text(text: str, filename: str, doc_type: str) -> List[Dict[str, Any]]:
    """
    Parses MD or TXT files, chunks text, and returns metadata (defaulting page to 1).
    """
    logger.info(f"Starting Text/Markdown parsing for file: '{filename}' (type: {doc_type})")
    
    if not text or not text.strip():
        logger.error(f"Ingestion rejected: Text document is empty or consist only of whitespace in '{filename}'")
        raise ValueError("Text document is empty or unreadable.")
        
    chunks = chunk_text(text)
    
    chunks_output = []
    for chunk in chunks:
        chunks_output.append({
            "content": chunk,
            "metadata": {
                "source": filename,
                "page": 1,
                "type": doc_type
            }
        })
        
    logger.info(f"Successfully processed Text file '{filename}'. Generated {len(chunks_output)} chunks.")
    return chunks_output

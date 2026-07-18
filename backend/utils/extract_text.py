import fitz  # PyMuPDF
from docx import Document
import io
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def extract_text_from_file(file_bytes, file_ext):
    if not file_bytes:
        raise ValueError("File content is empty or None")
        
    if not file_ext:
        raise ValueError("File extension is required")
        
    ext = file_ext.lower()
    
    try:
        if ext == '.pdf':
            return extract_from_pdf(file_bytes)
        elif ext == '.docx':
            return extract_from_docx(file_bytes)
        elif ext == '.txt':
            try:
                return file_bytes.decode('utf-8')
            except UnicodeDecodeError as e:
                raise ValueError(f"Failed to decode text file: {str(e)}")
        else:
            raise ValueError(f"Unsupported file type: {ext}")
    except Exception as e:
        raise Exception(f"Error processing {ext} file: {str(e)}")

def extract_from_pdf(file_bytes):
    text = ""
    try:
        logger.info("Attempting to open PDF from bytes")
        # Open PDF from bytes stream
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        logger.info(f"PDF opened successfully. Page count: {doc.page_count}")
        
        if not doc.page_count:
            logger.error("PDF contains no pages")
            raise ValueError("PDF contains no pages")
            
        for page_num, page in enumerate(doc):
            try:
                logger.debug(f"Processing page {page_num + 1}")
                page_text = page.get_text()
                logger.debug(f"Extracted {len(page_text)} characters from page {page_num + 1}")
                
                if not page_text.strip():
                    logger.warning(f"Page {page_num + 1} contains no text")
                    # Try alternative text extraction method
                    page_text = page.get_text("text")
                    logger.debug(f"Alternative extraction got {len(page_text)} characters")
                    
                text += page_text
                
            except Exception as e:
                logger.error(f"Error extracting text from page {page_num + 1}: {str(e)}", exc_info=True)
                continue
        
        logger.info(f"Finished processing all pages. Total text length: {len(text)}")
                
        if not text.strip():
            logger.error("PDF contains no extractable text (may be a scanned document or image-based PDF)")
            # Try OCR as last resort
            try:
                logger.info("Attempting OCR as fallback...")
                pix = page.get_pixmap()
                # This is a placeholder - you'd need to integrate with an OCR library like Tesseract
                # text = pytesseract.image_to_string(pix)
                logger.warning("OCR is not currently implemented. Please install pytesseract and poppler for OCR support.")
            except Exception as ocr_error:
                logger.error(f"OCR attempt failed: {str(ocr_error)}")
                
            raise ValueError("PDF contains no extractable text (may be a scanned document or image-based PDF)")
            
        return text
    except Exception as e:
        logger.error(f"PDF processing error: {str(e)}", exc_info=True)
        raise Exception(f"PDF processing error: {str(e)}")

def extract_from_docx(file_bytes):
    # Read DOCX from bytes stream
    doc = Document(io.BytesIO(file_bytes))
    text = "\n".join([para.text for para in doc.paragraphs])
    return text

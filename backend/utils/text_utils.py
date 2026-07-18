from langchain.text_splitter import RecursiveCharacterTextSplitter
import uuid
from .translator import translate_document_content, detect_language
from .embeddings import embed_texts

# --- Chunking using LangChain RecursiveCharacterTextSplitter ---
def chunk_text(text, chunk_size=1000, chunk_overlap=200):
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ".", " ", ""]
    )
    chunks = text_splitter.split_text(text)
    return chunks

# Generate embeddings for chunks via the hosted HuggingFace Inference API
def generate_embeddings(chunks):
    return embed_texts(chunks)

# Process Document and Prepare JSON structure with translation support
def process_document(file_name, file_type, raw_text):
    """
    Process document with automatic translation support
    """
    try:
        print(f"📄 Processing document: {file_name}")
        
        # Store original text and detect language
        original_text = raw_text
        original_language = detect_language(raw_text)
        
        # Translate if not in English
        translated_text, detected_lang, was_translated = translate_document_content(raw_text, file_name)
        
        # Use translated text for processing
        processing_text = translated_text
        
        # Create chunks and embeddings from English text
        chunks = chunk_text(processing_text)
        embeddings = generate_embeddings(chunks)

        chunked_data = []
        for chunk, embedding in zip(chunks, embeddings):
            chunked_data.append({
                "text": chunk,
                "embedding": embedding
            })

        document = {
            "document_id": str(uuid.uuid4()),
            "filename": file_name,
            "file_type": file_type,
            "raw_text": processing_text,  # Store the English (processed) text
            "original_text": original_text if was_translated else None,  # Store original if translated
            "original_language": detected_lang,
            "was_translated": was_translated,
            "chunks": chunked_data,
            "summary": {},
            "QnA_log": [],
            "translation_info": {
                "original_language": detected_lang,
                "translated_to": "en" if was_translated else detected_lang,
                "translation_method": "groq_api" if was_translated else "none"
            }
        }

        print(f"✅ Document processed successfully: {file_name}")
        if was_translated:
            print(f"🌍 Document was translated from {detected_lang} to English")
        
        return document
        
    except Exception as e:
        print(f"❌ Document processing error: {str(e)}")
        # Fallback: process without translation
        chunks = chunk_text(raw_text)
        embeddings = generate_embeddings(chunks)

        chunked_data = []
        for chunk, embedding in zip(chunks, embeddings):
            chunked_data.append({
                "text": chunk,
                "embedding": embedding
            })

        return {
            "document_id": str(uuid.uuid4()),
            "filename": file_name,
            "file_type": file_type,
            "raw_text": raw_text,
            "original_text": None,
            "original_language": "unknown",
            "was_translated": False,
            "chunks": chunked_data,
            "summary": {},
            "QnA_log": [],
            "translation_info": {
                "original_language": "unknown",
                "translated_to": "unknown",
                "translation_method": "none"
            }
        }
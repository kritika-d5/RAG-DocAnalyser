from sentence_transformers import SentenceTransformer
from langchain.text_splitter import RecursiveCharacterTextSplitter
import nltk
import uuid
import json

nltk.download('punkt')

# Load embedding model
embedding_model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')

# Raw text from the uploaded PDF (paste your actual content here)
raw_text = """
(PASTE YOUR FULL DOCUMENT TEXT HERE)
"""

# --- Chunking using LangChain RecursiveCharacterTextSplitter ---
def chunk_text(text, chunk_size=1000, chunk_overlap=200):
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ".", " ", ""]
    )
    chunks = text_splitter.split_text(text)
    return chunks

# Generate embeddings for chunks
def generate_embeddings(chunks):
    embeddings = embedding_model.encode(chunks).tolist()
    return embeddings

# Prepare JSON structure
def create_document_json(file_name, file_type, raw_text):
    chunks = chunk_text(raw_text)
    embeddings = generate_embeddings(chunks)

    document = {
        "document_id": str(uuid.uuid4()),
        "filename": file_name,
        "file_type": file_type,
        "raw_text": raw_text,
        "chunks": chunks,
        "embeddings": embeddings,
        "summary": {},  # You can fill this later
        "QnA_log": []
    }

    return document

# Generate JSON for the uploaded document
document_json = create_document_json("EJ1172284.pdf", "PDF", raw_text)

# Save to file
with open("C:/Users/kriti/Downloads/document_upload.json", "w", encoding='utf-8') as f:
    json.dump(document_json, f, ensure_ascii=False, indent=4)

print("Document JSON is ready for upload.")

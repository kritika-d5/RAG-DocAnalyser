from langchain.text_splitter import RecursiveCharacterTextSplitter
import uuid
from .embeddings import embed_texts

# --- Chunking using LangChain RecursiveCharacterTextSplitter ---
def chunk_text(text, chunk_size=1000, chunk_overlap=200):
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ".", " ", ""]
    )
    return text_splitter.split_text(text)

# Generate embeddings for chunks using the local fastembed model
def generate_embeddings(chunks):
    return embed_texts(chunks)

def process_document(file_name, file_type, raw_text):
    """
    Chunk the document, embed each chunk locally, and build the MongoDB record.
    """
    print(f"📄 Processing document: {file_name}")

    chunks = chunk_text(raw_text)
    embeddings = generate_embeddings(chunks)

    chunked_data = [
        {"text": chunk, "embedding": embedding}
        for chunk, embedding in zip(chunks, embeddings)
    ]

    print(f"✅ Document processed successfully: {file_name} ({len(chunked_data)} chunks)")

    return {
        "document_id": str(uuid.uuid4()),
        "filename": file_name,
        "file_type": file_type,
        "raw_text": raw_text,
        "chunks": chunked_data,
        "summary": {},
        "QnA_log": [],
    }

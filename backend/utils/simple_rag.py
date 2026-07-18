from pymongo import MongoClient
from dotenv import load_dotenv
import os
import re
from .embeddings import embed_texts

load_dotenv()

# MongoDB setup using env vars
MONGO_URI = os.getenv("MONGO_URI")
DATABASE_NAME = os.getenv("DATABASE_NAME")
COLLECTION_NAME = os.getenv("COLLECTION_NAME")

client = MongoClient(MONGO_URI)
db = client[DATABASE_NAME]
collection = db[COLLECTION_NAME]

# --- NEW FUNCTION: Replaces the old regex 'simple_search' ---
def vector_search(query, top_k=3):
    """
    Perform a semantic vector search against MongoDB Atlas using the defined index.
    """
    try:
        print(f"Generating embedding for query: '{query}'")
        # 1. Convert user query to vector
        query_embedding = embed_texts(query)

        # 2. Define the MongoDB Aggregation Pipeline
        pipeline = [
            {
                "$vectorSearch": {
                    # --- YOUR INDEX NAME GOES HERE ---
                    "index": "vector_index_final",
                    # ---------------------------------
                    # The path to the vectors inside nested chunks
                    "path": "chunks.embedding",
                    "queryVector": query_embedding,
                    # Look at more candidates for better accuracy before limiting
                    "numCandidates": top_k * 10, 
                    "limit": top_k
                }
            },
            {
                "$project": {
                    "_id": 0,
                    "filename": 1,
                    # We need the text content of the chunks
                    "chunks.text": 1,
                    "score": {"$meta": "vectorSearchScore"}
                }
            }
        ]

        print("Executing vector search against MongoDB...")
        # 3. Run the pipeline
        mongo_results = list(collection.aggregate(pipeline))
        print(f"Found {len(mongo_results)} matching parent documents.")

        # 4. Process results to match the format expected by 'simple_answer'
        # Since Atlas returns the whole document, we extract all text chunks from 
        # the top matching documents.
        processed_chunks = []
        for doc in mongo_results:
            # The vector score belongs to the document match
            doc_score = doc.get('score', 0)
            filename = doc.get('filename', 'Unknown')
            
            if 'chunks' in doc:
                for chunk_obj in doc['chunks']:
                    # Get the text content of the chunk
                    text_content = chunk_obj.get('text', '')
                    if text_content:
                        processed_chunks.append({
                            # Using 'chunk' key to match expected input of simple_answer
                            'chunk': text_content, 
                            'filename': filename,
                            # Using parent doc score for now as approximation
                            'score': doc_score 
                        })
        
        # Return the flattened list of text chunks for answer generation
        return processed_chunks

    except Exception as e:
        print(f"❌ Vector search error: {str(e)}")
        return []

# --- NO CHANGES NEEDED IN THIS FUNCTION ---
def simple_answer(query, chunks):
    """Generate a simple answer from chunks without using LLM"""
    if not chunks:
        return "I couldn't find any relevant information in the uploaded documents to answer your question."
    
    # Combine relevant chunks
    # Note: The previous code used chunk['chunk'], ensuring compatibility here.
    context = "\n\n".join([chunk['chunk'] for chunk in chunks])
    
    # Simple answer generation based on query type
    query_lower = query.lower()
    
    if any(word in query_lower for word in ['what is', 'define', 'explain']):
        # For definition/explanation queries, return the most relevant chunk
        return f"Based on the document, here's what I found:\n\n{chunks[0]['chunk'][:500]}..."
    
    elif any(word in query_lower for word in ['summarize', 'summary', 'overview']):
        # For summary queries, combine key points
        summary_parts = []
        for chunk in chunks[:2]:  # Use top 2 chunks
            summary_parts.append(chunk['chunk'][:200])
        return f"Summary:\n\n" + "\n\n".join(summary_parts)
    
    elif any(word in query_lower for word in ['how', 'process', 'method']):
        # For how-to queries, look for procedural information
        return f"Here's the process or method described in the document:\n\n{chunks[0]['chunk'][:400]}..."
    
    else:
        # Default response
        return f"Here's relevant information from the document:\n\n{chunks[0]['chunk'][:300]}..."

# --- UPDATED MAIN HANDLER ---
def handle_simple_rag_query(user_query, document_ids=None):
    """
    Handle RAG query using Vector Search and simple answer generation.
    NOTE: document_ids filter is ignored in this basic vector search implementation.
    """
    try:
        print(f"🔍 Starting RAG search for: '{user_query}'")
        
        # --- CHANGE: Call vector_search instead of simple_search ---
        # We ignore document_ids for now to allow searching across all data
        chunks = vector_search(user_query, top_k=3)
        
        if not chunks:
            print("❌ No chunks found via vector search.")
            # Fallback message if vector search fails to find anything
            return {
                "answer": f"I couldn't find any relevant information in the uploaded documents to answer: '{user_query}'. Please try rephrasing your question."
            }
        
        print(f"✅ Passing {len(chunks)} text chunks to answer generator.")
        
        # Generate simple answer (this function remains unchanged)
        answer = simple_answer(user_query, chunks)
        
        # Get unique sources
        sources = list(set([chunk['filename'] for chunk in chunks]))
        
        return {
            "answer": answer,
            "sources": sources
        }
        
    except Exception as e:
        print(f"❌ RAG error: {str(e)}")
        return {
            "answer": f"I encountered an error while processing your request: {str(e)}. Please try again."
        }
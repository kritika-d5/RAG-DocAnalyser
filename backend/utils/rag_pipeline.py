from pymongo import MongoClient
from dotenv import load_dotenv
import os
import re
import numpy as np
from .groq_api import groq_generate
from .prompts import rag_prompt
from .embeddings import embed_texts

load_dotenv()

# MongoDB setup using env vars
MONGO_URI = os.getenv("MONGO_URI")
DATABASE_NAME = os.getenv("DATABASE_NAME")
COLLECTION_NAME = os.getenv("COLLECTION_NAME")

client = MongoClient(MONGO_URI)
db = client[DATABASE_NAME]
collection = db[COLLECTION_NAME]

# Words that carry no topic on their own, ignored by the keyword match below
_STOPWORDS = set("""
a an the and or but of in on at to for from by with about as into over than
is are was were be been being am do does did done has have had can could will
would should may might must shall this that these those it its there their they
them he she his her we our you your i me my what which who whom whose when where
why how whether tell give show list explain describe please document documents
doc file text say says said main key important any some all much many more most
""".split())


def _terms(text):
    """Lower-cased content words, with a light plural strip ("risks" -> "risk")."""
    words = re.findall(r"[a-z0-9]+", text.lower())
    out = set()
    for w in words:
        if len(w) < 3 or w in _STOPWORDS:
            continue
        if len(w) > 3 and w.endswith("s") and not w.endswith("ss"):
            w = w[:-1]
        out.add(w)
    return out


def _keyword_match(query_terms, chunk_text):
    """
    (fraction of the query's content words found in the chunk, whether that
    counts as a match). A match needs at least half the words AND at least two
    of them when the query has two or more, so one generic word shared with
    the document ("capital" in "capital of France") isn't enough.
    """
    if not query_terms:
        return 0.0, False
    matched = len(query_terms & _terms(chunk_text))
    overlap = matched / len(query_terms)
    return overlap, overlap >= 0.5 and matched >= min(2, len(query_terms))


def get_similar_chunks(query, document_ids, top_k=4):
    try:
        print(f"🔎 Searching for documents: {document_ids}")
        query_embedding = embed_texts(query)

        # Get all documents matching the given document_ids
        matching_docs = list(collection.find({"document_id": {"$in": document_ids}}))
        print(f"📄 Found {len(matching_docs)} matching documents")

        if not matching_docs:
            return []

        # Shorter queries carry less signal, so use a lower similarity bar
        query_words = len(query.split())
        if query_words < 5:
            similarity_threshold = 0.25
        elif query_words < 10:
            similarity_threshold = 0.22
        else:
            similarity_threshold = 0.20

        print(f"🎯 Using similarity threshold: {similarity_threshold:.2f} (query length: {query_words} words)")

        # Collect all chunks
        all_chunks = []
        for doc in matching_docs:
            if 'chunks' in doc:
                for idx, chunk in enumerate(doc['chunks']):
                    all_chunks.append({
                        'text': chunk.get('text', ''),
                        'embedding': chunk.get('embedding', []),
                        'filename': doc.get('filename', 'Unknown'),
                        'document_id': doc.get('document_id', 'Unknown'),
                        'chunk_index': idx
                    })

        print(f"📦 Total chunks collected: {len(all_chunks)}")

        # Hybrid relevance: semantic similarity from the embeddings, plus a
        # keyword match. The small embedding model misses paraphrases ("grew
        # fastest" vs "fastest-growing") and exact names ("Delta Valley"), so a
        # chunk also qualifies if it contains most of the question's key words.
        query_emb = np.array(query_embedding)
        query_terms = _terms(query)
        scored = []

        for chunk in all_chunks:
            if not chunk['embedding']:
                continue
            try:
                chunk_emb = np.array(chunk['embedding'])
                sim = float(np.dot(chunk_emb, query_emb) / (np.linalg.norm(chunk_emb) * np.linalg.norm(query_emb)))
            except Exception as e:
                print(f"⚠️ Error calculating similarity: {e}")
                continue
            overlap, keyword_hit = _keyword_match(query_terms, chunk['text'])
            scored.append((sim + 0.3 * overlap, sim, keyword_hit, chunk))

        scored.sort(key=lambda x: x[0], reverse=True)

        # Anti-hallucination guard: a chunk must clear the semantic bar OR match
        # the question's key words (see _keyword_match). If nothing qualifies we
        # return no context, so the caller refuses instead of guessing.
        top_chunks = [
            (sim, chunk) for _, sim, keyword_hit, chunk in scored
            if sim > similarity_threshold or keyword_hit
        ][:top_k]

        print(f"✅ Relevant chunks (semantic > {similarity_threshold} or keyword match): {len(top_chunks)}")

        if not top_chunks:
            print("⚠️ No chunks cleared the relevance bar; returning no context.")
            return []

        for i, (sim, chunk) in enumerate(top_chunks):
            print(f"{i+1}. Similarity: {sim:.3f} - Text preview: {chunk['text'][:50]}...")

        results = [{
            'chunk': chunk['text'],
            'filename': chunk['filename'],
            'document_id': chunk['document_id'],
            'chunk_index': chunk['chunk_index'],
            'similarity': float(sim)
        } for sim, chunk in top_chunks]

        return results

    except Exception as e:
        print(f"❌ Error in get_similar_chunks: {str(e)}")
        return get_fallback_chunks(document_ids, top_k)

def get_fallback_chunks(document_ids, top_k=3):
    """Fallback method when vector search fails - returns first few chunks"""
    try:
        matching_docs = list(collection.find({"document_id": {"$in": document_ids}}))
        
        if not matching_docs:
            return []
        
        all_chunks = []
        for doc in matching_docs:
            if 'chunks' in doc:
                for chunk in doc['chunks'][:2]:  # Take first 2 chunks from each doc
                    all_chunks.append({
                        'chunk': chunk.get('text', ''),
                        'filename': doc.get('filename', 'Unknown'),
                        'document_id': doc.get('document_id', 'Unknown'),
                        'similarity': 0.0
                    })
        
        return all_chunks[:top_k]
        
    except Exception as e:
        print(f"Error in fallback chunks: {str(e)}")
        return []

def handle_rag_query(user_query, document_ids, with_trace=False):
    try:
        results = get_similar_chunks(user_query, document_ids)
        
        if not results:
            return {
                "answer": "I couldn't find anything about that in your document. Try rephrasing, or ask about a topic the document covers."
            }
        
        # Group chunks by document for better context
        chunks_by_doc = {}
        doc_names = {}
        
        # Get document names from MongoDB
        for doc_id in document_ids:
            doc = collection.find_one({"document_id": doc_id})
            if doc:
                doc_names[doc_id] = doc.get("filename", f"Document {doc_id}")
        
        for r in results:
            doc_id = r.get("document_id", "unknown")
            if doc_id not in chunks_by_doc:
                chunks_by_doc[doc_id] = []
            chunks_by_doc[doc_id].append(r["chunk"])
        
        # Create structured context with document separation
        context_parts = []
        for doc_id, chunks in chunks_by_doc.items():
            doc_name = doc_names.get(doc_id, f"Document {doc_id}")
            doc_context = f"\n--- Document: {doc_name} ---\n"
            doc_context += "\n".join(chunks)
            context_parts.append(doc_context)
        
        context = "\n\n".join(context_parts)

        prompt = rag_prompt(context, user_query, multi_document=len(chunks_by_doc) > 1)

        # Structured citations (filename + chunk + score) so the UI can show
        # exactly where each answer was grounded.
        sources = [{
            "filename": r["filename"],
            "chunk_index": r.get("chunk_index"),
            "similarity": round(float(r.get("similarity", 0.0)), 3),
            "preview": r["chunk"][:160].strip() + ("…" if len(r["chunk"]) > 160 else ""),
            # Full passage so the UI can expand a citation to the exact text
            "text": r["chunk"].strip()
        } for r in results]

        print("🚀 Starting Groq API RAG generation...")
        answer = groq_generate(prompt, max_tokens=500, temperature=0.3, timeout=90)

        if not answer:
            # LLM unavailable: fall back to the best-matching passage, which is
            # already scoped to this user's documents, and say so honestly.
            print("❌ Groq API generation failed, returning top passage instead")
            answer = (
                "_The AI service is temporarily unavailable, so here is the most "
                f"relevant passage from **{results[0]['filename']}**:_\n\n"
                f"> {results[0]['chunk'].strip()}"
            )

        return {"answer": answer, "sources": sources}

    except Exception as e:
        print(f"RAG query error: {str(e)}")
        return {
            "answer": f"I encountered an error while processing your request: {str(e)}. Please try again."
        }
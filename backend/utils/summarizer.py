from pymongo import MongoClient
from dotenv import load_dotenv
import os
from .groq_api import groq_summarize_generate
from .prompts import sample_document_text, summary_prompt, multi_document_prompt

load_dotenv()

# MongoDB setup using env vars (must match the rest of the app)
MONGO_URI = os.getenv("MONGO_URI")
DATABASE_NAME = os.getenv("DATABASE_NAME")
COLLECTION_NAME = os.getenv("COLLECTION_NAME")

client = MongoClient(MONGO_URI)
db = client[DATABASE_NAME]
collection = db[COLLECTION_NAME]

# Total characters of document text sent per summary request (~3k tokens).
# Kept modest so parallel summaries stay inside Groq's free-tier rate limits.
SUMMARY_CHAR_BUDGET = 12000


def summarize_documents(user_query, document_ids):
    try:
        docs = list(collection.find({"document_id": {"$in": document_ids}}))
        docs = [d for d in docs if (d.get('raw_text') or '').strip()]

        if not docs:
            return {"answer": "No document content found to summarize."}

        if len(docs) == 1:
            doc = docs[0]
            text = sample_document_text(doc, SUMMARY_CHAR_BUDGET)
            prompt = summary_prompt(doc.get('filename', 'document'), text)
        else:
            per_doc_budget = SUMMARY_CHAR_BUDGET // len(docs)
            prompt = multi_document_prompt([
                (d.get('filename', 'document'), sample_document_text(d, per_doc_budget))
                for d in docs
            ])

        print("🚀 Starting Groq API summarization...")
        summary = groq_summarize_generate(prompt, max_tokens=1200, temperature=0.3, timeout=90)

        if summary:
            print("✅ Groq API summarization completed successfully")
            return {"answer": summary.strip()}

        print("❌ Groq API summarization failed, returning document opening instead")
        return {"answer": fallback_summary(docs)}

    except Exception as e:
        print(f"Summarization error: {str(e)}")
        return {"answer": f"Error generating summary: {str(e)}"}


def fallback_summary(docs):
    """
    Shown when the LLM is unavailable. Deliberately makes no claims about the
    content: it says so plainly and shows the opening of each document.
    """
    parts = [
        "_The AI service is busy right now, so a summary couldn't be generated. "
        "Here is how each document opens — try again in a minute for a full summary._"
    ]
    for doc in docs:
        opening = ' '.join((doc.get('raw_text') or '').split())[:600]
        parts.append(f"## {doc.get('filename', 'Document')}\n\n> {opening}…")
    return "\n\n".join(parts)

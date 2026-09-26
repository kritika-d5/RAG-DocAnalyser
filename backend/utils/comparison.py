from pymongo import MongoClient
from dotenv import load_dotenv
import os
from .groq_api import groq_generate
from .prompts import sample_document_text, multi_document_prompt

load_dotenv()

# MongoDB setup using env vars
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DATABASE_NAME = os.getenv("DATABASE_NAME", "document_db")
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "documents")

client = MongoClient(MONGO_URI)
db = client[DATABASE_NAME]
collection = db[COLLECTION_NAME]

# Total characters of document text sent per comparison (~3k tokens),
# split evenly across the documents being compared.
COMPARISON_CHAR_BUDGET = 12000


def compare_documents(user_query, document_ids):
    try:
        if len(document_ids) < 2:
            return {"answer": "Please upload at least 2 documents for comparison."}

        docs = list(collection.find({"document_id": {"$in": document_ids}}))

        if len(docs) < 2:
            return {"answer": "Not enough documents found in DB for comparison."}

        # The UI's automatic comparison uses a generic request; anything else is
        # a specific question the comparison should focus on.
        query_lower = user_query.lower()
        is_generic = "comprehensive summary comparing" in query_lower or "analyze similarities" in query_lower

        per_doc_budget = COMPARISON_CHAR_BUDGET // len(docs)
        prompt = multi_document_prompt(
            [(d['filename'], sample_document_text(d, per_doc_budget)) for d in docs],
            focus=None if is_generic else user_query,
        )

        print("🚀 Starting Groq API comparison...")
        comparison_result = groq_generate(prompt, max_tokens=1500, temperature=0.3, timeout=180)

        if not comparison_result:
            names = "\n".join(f"- {d['filename']}" for d in docs)
            comparison_result = (
                "_The AI service is busy or rate-limited right now, so the comparison "
                "couldn't be generated. Please try again in a minute._\n\n"
                f"Documents to compare:\n\n{names}"
            )

        return {"answer": comparison_result}

    except Exception as e:
        print(f"Comparison error: {str(e)}")
        return {"answer": f"Error performing comparison: {str(e)}"}

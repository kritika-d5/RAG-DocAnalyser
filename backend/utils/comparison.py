from pymongo import MongoClient
from dotenv import load_dotenv
import os
import requests
from .groq_api import groq_generate, test_groq_connection

load_dotenv()

# MongoDB setup using env vars
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DATABASE_NAME = os.getenv("DATABASE_NAME", "document_db")
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "documents")

client = MongoClient(MONGO_URI)
db = client[DATABASE_NAME]
collection = db[COLLECTION_NAME]

def compare_documents(user_query, document_ids):
    try:
        if len(document_ids) < 2:
            return { "answer": "Please upload at least 2 documents for comparison." }

        # Fetch documents from MongoDB
        docs = list(collection.find({ "document_id": { "$in": document_ids } }))

        if len(docs) < 2:
            return { "answer": "Not enough documents found in DB for comparison." }

        filenames = [doc['filename'] for doc in docs]
        
        # Get document contents
        doc_contents = []
        for doc in docs:
            content = doc.get('raw_text', '')[:1500]  # Limit content to avoid timeouts
            doc_contents.append(f"Document: {doc['filename']}\nContent: {content}\n")

        # Use Groq API for comparison
        if "comprehensive summary comparing" in user_query.lower() or "analyze similarities" in user_query.lower():
            # This is a general comparison request
            prompt = f"""You are an expert multi-document analyst. Create a comprehensive summary comparing and analyzing {len(docs)} documents.

# 📚 MULTI-DOCUMENT ANALYSIS

## 📊 OVERALL COMPARISON
[Provide a high-level comparison of all documents, their purposes, and relationships]

## 📝 DOCUMENT-BY-DOCUMENT BREAKDOWN
[For each document, provide:
- **Document Name**: [Document name]
- **Main Purpose**: [What this document is about]
- **Key Points**: [2-3 main points from this document]
- **Unique Contributions**: [What this document adds that others don't]]

## 🔍 CROSS-DOCUMENT FINDINGS
[Analyze patterns, similarities, and differences across documents:
- **Common Themes**: [Topics that appear in multiple documents]
- **Contradictions**: [Any conflicting information between documents]
- **Complementary Information**: [How documents build on each other]]

## 🎯 SYNTHESIZED INSIGHTS
[Overall insights gained from analyzing all documents together]

## 💡 RECOMMENDATIONS
[Recommendations based on the combined analysis of all documents]

Documents to analyze:
{chr(10).join(doc_contents)}

Please provide a comprehensive analysis that synthesizes information from all {len(docs)} documents."""
        else:
            # This is a specific comparison request
            prompt = f"""Please compare the following documents based on the user's query: "{user_query}"

Documents:
{chr(10).join(doc_contents)}

Please provide a detailed comparison highlighting similarities, differences, and key insights."""

        try:
            print("🚀 Starting Groq API comparison...")
            comparison_result = groq_generate(prompt, max_tokens=1500, temperature=0.3, timeout=180)
            
            if not comparison_result:
                comparison_result = f"""API rate limit reached. Please wait a moment and try again.

Documents available for comparison:
"""
                for i, filename in enumerate(filenames, 1):
                    comparison_result += f"- Document {i}: {filename}\n"
                comparison_result += f"""
Total Documents: {len(docs)}
Status: Rate limited - please retry in 1-2 minutes

Recommendations: Wait for the API rate limit to reset and try the comparison again."""
                
        except Exception as e:
            print(f"❌ Groq API comparison error: {str(e)}")
            comparison_result = f"""API error occurred during comparison.

Documents available for comparison:
"""
            for i, filename in enumerate(filenames, 1):
                comparison_result += f"- Document {i}: {filename}\n"
            comparison_result += f"""
Total Documents: {len(docs)}
Status: API error - please try again

Recommendations: Please try the comparison again in a few moments."""

        return { "answer": comparison_result }
        
    except Exception as e:
        print(f"Comparison error: {str(e)}")
        return { "answer": f"Error performing comparison: {str(e)}" }

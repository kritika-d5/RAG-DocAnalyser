from utils.rag_pipeline import handle_rag_query
from utils.summarizer import summarize_documents
from utils.comparison import compare_documents
from utils.groq_api import groq_fast_generate

# Intent Routing Prompt
def route_query_prompt(user_query):
    return f"""
You are an intelligent document assistant. Based on the user's query below, decide which of the following four tasks is most appropriate. Respond ONLY with the task number.

1. RAG-Based Query:
   - The user is asking a specific question and wants an answer based on the uploaded document(s).
   - Examples: "What is X?", "How does Y work?", "Explain Z"

2. Summarization:
   - The user is asking for a summary, overview, or gist of the document(s).
   - Examples: "Summarize", "Main points", "Key points", "Overview", "Summary"

3. Comparison:
   - The user wants a comparison or analysis between two or more documents.
   - Examples: "Compare", "Difference", "Versus", "Contrast"

4. RAG + Source Trace:
   - The user is asking a question and wants not just the answer, but also where in the document the answer came from (line, chunk, or filename).

User Query:
\"\"\"{user_query}\"\"\"

Which task (1, 2, 3, or 4) should be activated? Respond ONLY with a single number (1, 2, 3, or 4).
"""

# Intent Detection using Groq API
def detect_intent(user_query):
    try:
        prompt = route_query_prompt(user_query)
        
        # Try Groq API first
        response_text = groq_fast_generate(prompt, max_tokens=10, temperature=0.0, timeout=30)
        
        if response_text:
            print(f"🤖 Groq API intent response: '{response_text}'")
            
            # Try to extract just the number from the response
            import re
            number_match = re.search(r'\b([1-4])\b', response_text)
            if number_match:
                intent_number = int(number_match.group(1))
                print(f"✅ Extracted intent number: {intent_number}")
                return intent_number
            else:
                print(f"❌ No valid intent number found in response")
                return detect_intent_keywords(user_query)
        else:
            print("❌ Groq API intent detection failed, using keyword fallback...")
            return detect_intent_keywords(user_query)
            
    except Exception as e:
        print(f"Groq API intent detection failed: {str(e)}")
        return detect_intent_keywords(user_query)

def detect_intent_keywords(user_query):
    """Simple keyword-based intent detection fallback"""
    query_lower = user_query.lower()
    
    # Check for comparison keywords FIRST (higher priority)
    comparison_keywords = ['compare', 'comparison', 'difference', 'versus', 'vs', 'contrast', 'comparing']
    if any(keyword in query_lower for keyword in comparison_keywords):
        print(f"🎯 Keyword detection: Found comparison keyword in '{query_lower}'")
        return 3
    
    # Check for summarization keywords
    summary_keywords = ['summarize', 'summary', 'overview', 'gist', 'main points', 'key points', 'summarise', 'summaries']
    if any(keyword in query_lower for keyword in summary_keywords):
        print(f"🎯 Keyword detection: Found summary keyword in '{query_lower}'")
        return 2
    
    # Default to RAG
    print(f"🎯 Keyword detection: No specific keywords found, defaulting to RAG")
    return 1

# Master Intent Router Function
def handle_query(user_query, document_ids):
    try:
        print(f"🎯 Processing query: '{user_query}'")

        intent = detect_intent(user_query)
        print(f"📊 Detected intent: {intent}")

        if intent == 1:
            print("🔍 Using RAG-based query...")
            result = handle_rag_query(user_query, document_ids)

        elif intent == 2:
            print("📝 Using summarization...")
            result = summarize_documents(user_query, document_ids)

        elif intent == 3:
            print("⚖️ Using comparison...")
            result = compare_documents(user_query, document_ids)

        elif intent == 4:
            print("🔍 Using RAG with source trace...")
            result = handle_rag_query(user_query, document_ids, with_trace=True)

        else:
            print(f"❌ Unknown intent: {intent}")
            result = {"answer": "[Error] Couldn't determine the intent of your query."}

        return result

    except Exception as e:
        print(f"❌ Intent router error: {str(e)}")
        import traceback
        traceback.print_exc()
        return {"answer": f"I encountered an error while processing your request: {str(e)}. Please try again."}
from utils.rag_pipeline import handle_rag_query
from utils.summarizer import summarize_documents
from utils.comparison import compare_documents
from utils.groq_api import groq_fast_generate, test_groq_connection
from utils.translator import translate_query, detect_language
import requests

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

# Master Intent Router Function with Translation Support
def handle_query(user_query, document_ids):
    try:
        print(f"🎯 Processing query: '{user_query}'")
        
        # Detect query language and translate if needed
        original_query = user_query
        query_lang = detect_language(user_query)
        
        # Translate query to English for better processing
        if query_lang != 'en' and query_lang != 'unknown':
            print(f"🌍 Query is in {query_lang}, translating to English...")
            translated_query, detected_lang = translate_query(user_query, 'en')
            processing_query = translated_query
            print(f"🌍 Query translated: '{original_query}' → '{processing_query}'")
        else:
            processing_query = user_query
            print(f"✅ Query is in English, no translation needed")
        
        # Detect intent using the translated query
        print(f"🎯 Detecting intent for query: '{processing_query}'")
        intent = detect_intent(processing_query)
        print(f"📊 Detected intent: {intent}")

        # Process based on intent
        if intent == 1:
            print("🔍 Using RAG-based query...")
            result = handle_rag_query(processing_query, document_ids)
            
        elif intent == 2:
            print("📝 Using summarization...")
            result = summarize_documents(processing_query, document_ids)
            
        elif intent == 3:
            print("⚖️ Using comparison...")
            result = compare_documents(processing_query, document_ids)
            
        elif intent == 4:
            print("🔍 Using RAG with source trace...")
            result = handle_rag_query(processing_query, document_ids, with_trace=True)
            
        else:
            print(f"❌ Unknown intent: {intent}")
            result = {"answer": "[Error] Couldn't determine the intent of your query."}
        
        # Add translation info to response if query was translated
        if query_lang != 'en' and query_lang != 'unknown':
            if isinstance(result, dict) and 'answer' in result:
                result['translation_info'] = {
                    'original_query': original_query,
                    'translated_query': processing_query,
                    'query_language': query_lang,
                    'was_translated': True
                }
                # Add note about translation
                result['answer'] = f"[Query translated from {query_lang} to English]\n\n{result['answer']}"
        
        return result
        
    except Exception as e:
        print(f"❌ Intent router error: {str(e)}")
        import traceback
        traceback.print_exc()
        return {"answer": f"I encountered an error while processing your request: {str(e)}. Please try again."}
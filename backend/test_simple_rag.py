from utils.simple_rag import handle_simple_rag_query

def test_simple_rag():
    """Test the simple RAG implementation"""
    try:
        # Test with a sample document ID (you'll need to replace this with a real one)
        test_doc_id = "d3ba049c-3175-4b7f-a3e1-3019d5fb0265"  # From the MongoDB test
        
        test_queries = [
            "What is iron oxide?",
            "Summarize this document",
            "How does the process work?",
            "What are the main points?"
        ]
        
        for query in test_queries:
            print(f"\n🔍 Testing query: '{query}'")
            result = handle_simple_rag_query(query, [test_doc_id])
            print(f"✅ Response: {result['answer'][:200]}...")
            
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")

if __name__ == "__main__":
    test_simple_rag() 
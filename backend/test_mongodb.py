from pymongo import MongoClient
from dotenv import load_dotenv
import os

load_dotenv()

# MongoDB setup using env vars
MONGO_URI = os.getenv("MONGO_URI")
DATABASE_NAME = os.getenv("DATABASE_NAME")
COLLECTION_NAME = os.getenv("COLLECTION_NAME")

print(f"Connecting to MongoDB: {MONGO_URI}")
print(f"Database: {DATABASE_NAME}")
print(f"Collection: {COLLECTION_NAME}")

client = MongoClient(MONGO_URI)
db = client[DATABASE_NAME]
collection = db[COLLECTION_NAME]

def test_mongodb_connection():
    """Test MongoDB connection and document structure"""
    try:
        # Test connection
        client.admin.command('ping')
        print("✅ MongoDB connection successful")
        
        # Count documents
        doc_count = collection.count_documents({})
        print(f"📄 Total documents in collection: {doc_count}")
        
        if doc_count > 0:
            # Get first document to examine structure
            first_doc = collection.find_one()
            print(f"\n📋 Document structure:")
            print(f"  - Keys: {list(first_doc.keys())}")
            
            if 'document_id' in first_doc:
                print(f"  - Document ID: {first_doc['document_id']}")
            
            if 'filename' in first_doc:
                print(f"  - Filename: {first_doc['filename']}")
            
            if 'chunks' in first_doc:
                chunks = first_doc['chunks']
                print(f"  - Number of chunks: {len(chunks)}")
                
                if chunks:
                    first_chunk = chunks[0]
                    print(f"  - First chunk keys: {list(first_chunk.keys())}")
                    
                    if 'text' in first_chunk:
                        print(f"  - First chunk text preview: {first_chunk['text'][:100]}...")
                    
                    if 'embedding' in first_chunk:
                        embedding = first_chunk['embedding']
                        print(f"  - First chunk embedding length: {len(embedding) if embedding else 0}")
                        if embedding:
                            print(f"  - First chunk embedding preview: {embedding[:5]}...")
            
            # List all document IDs
            doc_ids = list(collection.distinct("document_id"))
            print(f"\n📝 Available document IDs: {doc_ids}")
            
        else:
            print("❌ No documents found in collection")
            
    except Exception as e:
        print(f"❌ MongoDB test failed: {str(e)}")

def test_rag_query():
    """Test the RAG query functionality"""
    try:
        from utils.rag_pipeline import get_similar_chunks
        
        # Get first document ID
        first_doc = collection.find_one()
        if not first_doc or 'document_id' not in first_doc:
            print("❌ No documents with document_id found")
            return
            
        doc_id = first_doc['document_id']
        print(f"\n🔍 Testing RAG query with document ID: {doc_id}")
        
        # Test query
        test_query = "What is this document about?"
        results = get_similar_chunks(test_query, [doc_id], top_k=3)
        
        print(f"✅ RAG query successful, found {len(results)} results")
        
        for i, result in enumerate(results):
            print(f"  Result {i+1}:")
            print(f"    - Filename: {result.get('filename', 'Unknown')}")
            print(f"    - Similarity: {result.get('similarity', 0):.4f}")
            print(f"    - Text preview: {result.get('chunk', '')[:100]}...")
            
    except Exception as e:
        print(f"❌ RAG query test failed: {str(e)}")

if __name__ == "__main__":
    print("Testing MongoDB connection and document structure...")
    test_mongodb_connection()
    print("\nTesting RAG query functionality...")
    test_rag_query() 
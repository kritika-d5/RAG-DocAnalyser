from utils.fast_ollama import fast_generate, ultra_fast_generate, get_best_model
import time

def test_fast_generation():
    """Test the fast generation functions"""
    print("🚀 Testing Fast Ollama Generation")
    print("=" * 40)
    
    # Test ultra-fast generation
    print("\n1. Testing Ultra-Fast Generation:")
    start_time = time.time()
    result = ultra_fast_generate("What is 2+2?", timeout=15)
    end_time = time.time()
    
    if result:
        print(f"✅ Success ({end_time - start_time:.1f}s): {result}")
    else:
        print(f"❌ Failed ({end_time - start_time:.1f}s)")
    
    # Test fast generation
    print("\n2. Testing Fast Generation:")
    start_time = time.time()
    result = fast_generate("Explain what is machine learning in one sentence.", max_tokens=50, timeout=30)
    end_time = time.time()
    
    if result:
        print(f"✅ Success ({end_time - start_time:.1f}s): {result}")
    else:
        print(f"❌ Failed ({end_time - start_time:.1f}s)")
    
    # Test best model detection
    print("\n3. Best Available Model:")
    best_model = get_best_model()
    print(f"📦 Recommended model: {best_model}")

if __name__ == "__main__":
    test_fast_generation() 
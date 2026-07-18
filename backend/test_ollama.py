import requests
import json

def test_ollama_connection():
    """Test if Ollama is running and accessible"""
    try:
        # Test basic connection
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        if response.status_code == 200:
            print("✅ Ollama is running and accessible")
            
            # Check if tinyllama model is available
            models = response.json().get('models', [])
            tinyllama_available = any('tinyllama' in model.get('name', '').lower() for model in models)
            
            if tinyllama_available:
                print("✅ TinyLLaMA model is available")
            else:
                print("❌ TinyLLaMA model not found. Available models:")
                for model in models:
                    print(f"  - {model.get('name', 'Unknown')}")
                print("\nTo install TinyLLaMA model, run: ollama pull tinyllama")
        else:
            print(f"❌ Ollama responded with status code: {response.status_code}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to Ollama. Make sure it's running on localhost:11434")
        print("To start Ollama, run: ollama serve")
    except requests.exceptions.Timeout:
        print("❌ Ollama connection timed out")
    except Exception as e:
        print(f"❌ Error testing Ollama: {str(e)}")

def test_ollama_generation():
    """Test if Ollama can generate responses"""
    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={"model": "tinyllama", "prompt": "Hello, this is a test.", "stream": False},
            timeout=120  # Increased timeout to 120 seconds
        )
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Ollama generation test successful")
            print(f"Response: {result.get('response', 'No response')[:100]}...")
        else:
            print(f"❌ Ollama generation failed with status code: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Ollama generation test failed: {str(e)}")

if __name__ == "__main__":
    print("Testing Ollama connection...")
    test_ollama_connection()
    print("\nTesting Ollama generation...")
    test_ollama_generation() 
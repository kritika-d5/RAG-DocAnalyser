import requests
import json
import time
import psutil
import os

def check_system_resources():
    """Check system resources"""
    print("🖥️ System Resources:")
    print(f"  - CPU Cores: {psutil.cpu_count()}")
    print(f"  - RAM Total: {psutil.virtual_memory().total / (1024**3):.1f} GB")
    print(f"  - RAM Available: {psutil.virtual_memory().available / (1024**3):.1f} GB")
    print(f"  - RAM Usage: {psutil.virtual_memory().percent}%")
    
    # Check if we have enough RAM (need at least 4GB free)
    available_gb = psutil.virtual_memory().available / (1024**3)
    if available_gb < 4:
        print(f"⚠️  Warning: Only {available_gb:.1f} GB RAM available. Ollama needs at least 4GB.")

def check_ollama_status():
    """Check if Ollama is running and accessible"""
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        if response.status_code == 200:
            print("✅ Ollama is running and accessible")
            return True
        else:
            print(f"❌ Ollama responded with status: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Cannot connect to Ollama: {str(e)}")
        return False

def check_models():
    """Check available models"""
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=10)
        if response.status_code == 200:
            models = response.json().get('models', [])
            print(f"📚 Available models: {len(models)}")
            
            for model in models:
                name = model.get('name', 'Unknown')
                size = model.get('size', 0)
                size_gb = size / (1024**3) if size > 0 else 0
                print(f"  - {name}: {size_gb:.1f} GB")
                
                # Check if tinyllama is available
                if 'tinyllama' in name.lower():
                    print(f"    ✅ TinyLLaMA model found")
                    return True
            
            print("❌ TinyLLaMA model not found")
            return False
        else:
            print(f"❌ Failed to get models: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error checking models: {str(e)}")
        return False

def test_simple_generation():
    """Test simple text generation"""
    print("\n🧪 Testing simple generation...")
    
    test_prompts = [
        "Hello, how are you?",
        "What is 2+2?",
        "Say 'test' if you can hear me."
    ]
    
    for i, prompt in enumerate(test_prompts, 1):
        print(f"  Test {i}: '{prompt}'")
        try:
            start_time = time.time()
            response = requests.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": "tinyllama",
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "num_predict": 50,  # Limit response length
                        "temperature": 0.1   # Low temperature for faster response
                    }
                },
                timeout=30
            )
            end_time = time.time()
            
            if response.status_code == 200:
                result = response.json()
                response_text = result.get('response', 'No response')
                print(f"    ✅ Success ({end_time - start_time:.1f}s): {response_text[:50]}...")
            else:
                print(f"    ❌ Failed with status {response.status_code}")
                
        except requests.exceptions.Timeout:
            print(f"    ⏰ Timeout after 30s")
        except Exception as e:
            print(f"    ❌ Error: {str(e)}")

def test_model_parameters():
    """Test different model parameters"""
    print("\n⚙️ Testing model parameters...")
    
    # Test with minimal parameters
    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
                            json={
                    "model": "tinyllama",
                    "prompt": "Hi",
                    "stream": False,
                    "options": {
                        "num_predict": 10,
                        "temperature": 0.0,
                        "top_p": 0.1,
                        "top_k": 1
                    }
                },
            timeout=60
        )
        
        if response.status_code == 200:
            print("✅ Minimal parameters work")
        else:
            print(f"❌ Minimal parameters failed: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Parameter test failed: {str(e)}")

def suggest_optimizations():
    """Suggest optimizations"""
    print("\n💡 Optimization Suggestions:")
    
    # Check available RAM
    available_gb = psutil.virtual_memory().available / (1024**3)
    
    if available_gb < 8:
        print("1. 🧠 Increase RAM or close other applications")
        print("2. 📦 Try a smaller model like 'phi3:mini' or 'llama2:7b'")
    
    print("3. ⚡ Use faster model parameters:")
    print("   - Lower temperature (0.0-0.3)")
    print("   - Limit response length (num_predict: 100-200)")
    print("   - Use top_p and top_k for faster sampling")
    
    print("4. 🔧 Ollama configuration:")
    print("   - Restart Ollama: ollama serve")
    print("   - Pull optimized model: ollama pull tinyllama:latest")
    print("   - Check GPU support: ollama list")

def main():
    print("🔍 Ollama Diagnostic Tool")
    print("=" * 50)
    
    check_system_resources()
    print()
    
    if not check_ollama_status():
        print("\n❌ Ollama is not running. Start it with: ollama serve")
        return
    
    print()
    if not check_models():
        print("\n❌ TinyLLaMA model not found. Install it with: ollama pull tinyllama")
        return
    
    print()
    test_simple_generation()
    test_model_parameters()
    suggest_optimizations()

if __name__ == "__main__":
    main() 
import requests
import time

def fast_generate(prompt, model="tinyllama", max_tokens=100, timeout=30):
    """Fast text generation with optimized parameters"""
    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "num_predict": max_tokens,
                    "temperature": 0.1,    # Very low for speed
                    "top_p": 0.5,          # Fast sampling
                    "top_k": 20,           # Fast sampling
                    "repeat_penalty": 1.0,  # No repetition penalty for speed
                    "num_ctx": 512         # Smaller context for speed
                }
            },
            timeout=timeout
        )
        
        if response.status_code == 200:
            return response.json().get('response', '')
        else:
            return None
            
    except Exception as e:
        print(f"Fast generation failed: {str(e)}")
        return None

def ultra_fast_generate(prompt, timeout=15):
    """Ultra-fast generation with minimal parameters"""
    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "tinyllama",
                "prompt": prompt,
                "stream": False,
                "options": {
                    "num_predict": 50,
                    "temperature": 0.0,
                    "top_p": 0.1,
                    "top_k": 1,
                    "num_ctx": 256
                }
            },
            timeout=timeout
        )
        
        if response.status_code == 200:
            return response.json().get('response', '')
        else:
            return None
            
    except Exception as e:
        print(f"Ultra-fast generation failed: {str(e)}")
        return None

def check_available_models():
    """Check what models are available"""
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        if response.status_code == 200:
            models = response.json().get('models', [])
            return [model.get('name', '') for model in models]
        return []
    except:
        return []

def get_best_model():
    """Get the best available model for the current system"""
    models = check_available_models()
    
    # Prefer smaller models for better performance
    preferred_models = [
        "tinyllama",
        "phi3:mini",
        "llama2:7b",
        "phi3",
        "llama2:13b"
    ]
    
    for model in preferred_models:
        if model in models:
            return model
    
    # Return first available model
    return models[0] if models else "tinyllama" 
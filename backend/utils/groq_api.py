import os
import requests
import time
import random
from dotenv import load_dotenv
import re  # Moved import to top level

load_dotenv()

# Groq API configuration
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
# Updated to use faster, lighter model as per your existing code
MODEL_NAME = "llama-3.1-8b-instant"

# --- MODIFIED FUNCTION ---
def groq_generate(prompt, max_tokens=600, temperature=0.3, timeout=90, max_retries=5, base_delay=2):
    """
    Generate text using Groq API with built-in exponential backoff for rate limits.
    """
    if not GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY not found in environment variables")
    
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": MODEL_NAME,
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ],
        "max_tokens": max_tokens,
        "temperature": temperature,
        "top_p": 0.9,
        "stream": False
    }
    
    print(f"🚀 Calling Groq API with model: {MODEL_NAME}")

    # --- RETRY LOGIC STARTS HERE ---
    for attempt in range(max_retries):
        try:
            # Make the actual API request
            response = requests.post(
                GROQ_API_URL,
                headers=headers,
                json=data,
                timeout=timeout
            )
            
            # ✅ SUCCESS: If status is 200 OK, return the result immediately
            if response.status_code == 200:
                result = response.json()
                generated_text = result['choices'][0]['message']['content']
                print(f"✅ Groq API call successful")
                return generated_text

            # ⚠️ RATE LIMIT: If status is 429, wait and try again
            elif response.status_code == 429:
                error_data = response.json()
                print(f"⏰ Groq API rate limit exceeded (Attempt {attempt + 1}/{max_retries}): {error_data}")
                
                # Try to extract retry time from error message (your existing logic)
                retry_match = re.search(r'try again in (\d+\.?\d*)s', error_data.get('error', {}).get('message', ''))
                if retry_match:
                    retry_seconds = float(retry_match.group(1))
                    print(f"⏰ Suggested retry time from API: {retry_seconds} seconds")
                
                # Calculate exponential backoff delay: base * 2^attempt + random jitter
                delay = (base_delay * (2 ** attempt)) + random.uniform(0, 1)
                print(f"⏳ Retrying in {delay:.2f} seconds...")
                time.sleep(delay)
                continue # Go back to the start of the loop to retry
            
            # ❌ OTHER ERRORS: For any other bad status, print error and give up
            else:
                print(f"❌ Groq API error: {response.status_code} - {response.text}")
                return None
                
        except requests.exceptions.Timeout:
            print(f"⏰ Groq API timeout after {timeout} seconds")
            # Optional: You could decide to retry on timeouts too
            return None
        except requests.exceptions.ConnectionError:
            print("🔌 Groq API connection error")
             # Optional: You could decide to retry on connection errors too
            return None
        except Exception as e:
            print(f"❌ Groq API error: {str(e)}")
            return None

    # --- RETRY LOGIC ENDS HERE ---
    
    # If the loop finishes without returning, it means all retries failed
    print(f"❌ Groq API request failed after {max_retries} attempts due to rate limiting.")
    return None
# ---------------------------


def groq_fast_generate(prompt, max_tokens=200, temperature=0.1, timeout=30):
    """
    Fast generation for intent detection and simple queries
    """
    # You can optionally pass max_retries and base_delay here too if needed
    return groq_generate(prompt, max_tokens, temperature, timeout)

def groq_summarize_generate(prompt, max_tokens=800, temperature=0.3, timeout=120):
    """
    Generation optimized for summarization tasks
    """
    # Summarization is more likely to hit rate limits, so you could increase retries here
    # return groq_generate(prompt, max_tokens, temperature, timeout, max_retries=7, base_delay=3)
    return groq_generate(prompt, max_tokens, temperature, timeout)

def test_groq_connection():
    """
    Test if Groq API is working
    """
    try:
        test_prompt = "Hello, this is a test. Please respond with 'Test successful'."
        response = groq_generate(test_prompt, max_tokens=50, timeout=30)
        if response and "Test successful" in response:
            print("✅ Groq API connection test successful")
            return True
        else:
            print("❌ Groq API connection test failed")
            return False
    except Exception as e:
        print(f"❌ Groq API connection test error: {str(e)}")
        return False
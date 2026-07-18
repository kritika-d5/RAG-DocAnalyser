import subprocess
import sys
import time

def run_command(command, description):
    """Run a command and show progress"""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ {description} completed successfully")
            return True
        else:
            print(f"❌ {description} failed:")
            print(f"Error: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ {description} failed with exception: {str(e)}")
        return False

def check_ollama_installed():
    """Check if Ollama is installed"""
    try:
        result = subprocess.run(["ollama", "--version"], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ Ollama is installed: {result.stdout.strip()}")
            return True
        else:
            print("❌ Ollama is not installed or not in PATH")
            return False
    except FileNotFoundError:
        print("❌ Ollama is not installed. Please install it first from https://ollama.ai")
        return False

def install_tinyllama():
    """Install TinyLLaMA model"""
    print("🚀 Installing TinyLLaMA Model")
    print("=" * 40)
    
    # Check if Ollama is installed
    if not check_ollama_installed():
        print("\n📥 Please install Ollama first:")
        print("1. Go to https://ollama.ai")
        print("2. Download and install Ollama for your system")
        print("3. Run this script again")
        return False
    
    # Start Ollama if not running
    print("\n🔄 Starting Ollama...")
    try:
        # Try to start Ollama in background
        subprocess.Popen(["ollama", "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print("✅ Ollama started")
        time.sleep(3)  # Wait for Ollama to start
    except Exception as e:
        print(f"⚠️ Could not start Ollama automatically: {str(e)}")
        print("Please start Ollama manually with: ollama serve")
    
    # Pull TinyLLaMA model
    print("\n📦 Pulling TinyLLaMA model...")
    print("This may take several minutes depending on your internet connection...")
    
    if run_command("ollama pull tinyllama", "Pulling TinyLLaMA model"):
        print("\n🎉 TinyLLaMA installation completed successfully!")
        print("\n📋 Next steps:")
        print("1. Restart your backend server")
        print("2. Test the model with: python test_ollama.py")
        print("3. Try uploading a document and asking questions")
        return True
    else:
        print("\n❌ TinyLLaMA installation failed")
        print("Please try manually: ollama pull tinyllama")
        return False

if __name__ == "__main__":
    install_tinyllama() 
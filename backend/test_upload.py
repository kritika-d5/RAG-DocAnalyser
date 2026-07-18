#!/usr/bin/env python3
"""
Test script for upload endpoint
"""

import requests
import os

def test_upload():
    print("🧪 Testing Upload Endpoint")
    print("=" * 50)
    
    # Create a test file
    test_content = "This is a test document for upload testing."
    test_filename = "test_document.txt"
    
    with open(test_filename, 'w') as f:
        f.write(test_content)
    
    try:
        # Test single file upload
        print("📤 Testing single file upload...")
        with open(test_filename, 'rb') as f:
            files = {'file0': (test_filename, f, 'text/plain')}
            response = requests.post('http://localhost:5000/api/upload', files=files)
        
        print(f"📥 Response status: {response.status_code}")
        print(f"📥 Response data: {response.json()}")
        
        if response.status_code == 200:
            print("✅ Single file upload successful!")
        else:
            print("❌ Single file upload failed!")
            return False
            
    except Exception as e:
        print(f"❌ Upload test failed: {str(e)}")
        return False
    finally:
        # Clean up test file
        if os.path.exists(test_filename):
            os.remove(test_filename)
    
    print("\n🎉 Upload test completed successfully!")
    return True

if __name__ == "__main__":
    success = test_upload()
    if not success:
        print("\n❌ Upload test failed. Please check if the backend is running.")
        exit(1) 
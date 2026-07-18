#!/usr/bin/env python3
"""
Test script for Groq API integration
"""

import os
from dotenv import load_dotenv
from utils.groq_api import test_groq_connection, groq_generate

load_dotenv()

def main():
    print("🧪 Testing Groq API Integration")
    print("=" * 50)
    
    # Check if API key is set
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        print("❌ GROQ_API_KEY not found in environment variables")
        print("Please add your Groq API key to the .env file:")
        print("GROQ_API_KEY=your_api_key_here")
        return False
    
    print(f"✅ GROQ_API_KEY found: {api_key[:10]}...")
    
    # Test connection
    print("\n🔗 Testing Groq API connection...")
    if test_groq_connection():
        print("✅ Groq API connection successful!")
    else:
        print("❌ Groq API connection failed!")
        return False
    
    # Test basic generation
    print("\n🤖 Testing basic text generation...")
    test_prompt = "Write a short paragraph about artificial intelligence."
    response = groq_generate(test_prompt, max_tokens=100, temperature=0.3, timeout=30)
    
    if response:
        print("✅ Basic generation successful!")
        print(f"Response: {response[:200]}...")
    else:
        print("❌ Basic generation failed!")
        return False
    
    # Test intent detection prompt
    print("\n🎯 Testing intent detection prompt...")
    intent_prompt = """You are an intelligent document assistant. Based on the user's query below, decide which of the following four tasks is most appropriate. Respond ONLY with the task number.

1. RAG-Based Query
2. Summarization
3. Comparison
4. RAG + Source Trace

User Query: "Summarize this document"

Which task (1, 2, 3, or 4) should be activated? Respond ONLY with a single number (1, 2, 3, or 4)."""
    
    intent_response = groq_generate(intent_prompt, max_tokens=10, temperature=0.0, timeout=30)
    
    if intent_response:
        print("✅ Intent detection prompt successful!")
        print(f"Response: '{intent_response.strip()}'")
    else:
        print("❌ Intent detection prompt failed!")
        return False
    
    # Test summarization prompt
    print("\n📝 Testing summarization prompt...")
    summary_prompt = """You are an expert document summarizer. Create a comprehensive, well-formatted summary with the following structure:

# 📋 DOCUMENT SUMMARY

## 📊 OVERALL SUMMARY
[Write a concise 5-10 sentence summary of the main content and purpose of the document]

## 📝 SECTION-WISE BREAKDOWN
[For each major section, provide:
- **Section Title**: [Section name]
- **Key Points**: [2-3 bullet points with key information]
- **Important Details**: [Highlight any critical data, findings, or conclusions]]

## 🔍 KEY FINDINGS & HIGHLIGHTS
[Extract and highlight 5-7 most important findings, including:
- **Research Findings**: [Any research results or discoveries]
- **Methodologies**: [Key methods or approaches mentioned]
- **Conclusions**: [Main conclusions or recommendations]
- **Critical Data**: [Important statistics, numbers, or metrics]]

## 🎯 MAIN TOPICS & THEMES
[List the primary topics, themes, and subject areas covered in the document]

## 💡 RECOMMENDATIONS & INSIGHTS
[Any recommendations, suggestions, or insights provided in the document]

Document content:
This is a sample document about machine learning and artificial intelligence. The document discusses various algorithms, applications, and future trends in the field of AI.

Please format the response with clear headings, bullet points, and highlight key elements using **bold** text for emphasis."""
    
    summary_response = groq_generate(summary_prompt, max_tokens=400, temperature=0.3, timeout=60)
    
    if summary_response:
        print("✅ Summarization prompt successful!")
        print(f"Response preview: {summary_response[:200]}...")
    else:
        print("❌ Summarization prompt failed!")
        return False
    
    print("\n🎉 All Groq API tests passed successfully!")
    print("✅ Your Groq API integration is working correctly!")
    print(f"✅ Using model: llama3-70b-8192")
    return True

if __name__ == "__main__":
    success = main()
    if not success:
        print("\n❌ Some tests failed. Please check your API key and internet connection.")
        exit(1) 
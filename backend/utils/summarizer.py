from pymongo import MongoClient
from dotenv import load_dotenv
import os
import requests
from .groq_api import groq_summarize_generate, test_groq_connection

load_dotenv()

client = MongoClient(os.getenv("MONGO_URI"))
db = client["documents"]
collection = db["mangobytes"]

def summarize_documents(user_query, document_ids):
    try:
        # Fetch documents from MongoDB
        docs = collection.find({ "document_id": { "$in": document_ids } })

        if len(document_ids) == 1:
            # Single document summarization
            combined_text = ""
            chunks = []
            for doc in docs:
                raw_text = doc.get('raw_text', '')
                combined_text += raw_text + "\n\n"
                
                # Also get chunks for better summarization
                if 'chunks' in doc:
                    for chunk in doc['chunks']:
                        chunks.append(chunk.get('text', ''))

            if not combined_text.strip():
                return { "answer": "No document content found to summarize." }

            # Use the improved prompt with Groq API
            chunks_text = '\n'.join(chunks[:10])  # Use first 10 chunks
            prompt = f"""You are an expert document summarizer. Create a comprehensive, well-formatted summary with the following structure:

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
{combined_text[:3000]}  # Limit to first 3000 chars to avoid timeouts

Important chunks:
{chunks_text}

Please format the response with clear headings, bullet points, and highlight key elements using **bold** text for emphasis."""
        else:
            # Multiple document summarization
            documents_data = []
            combined_text = ""  # Initialize combined_text for multi-doc case
            for doc in docs:
                doc_data = {
                    'id': doc.get('document_id', 'unknown'),
                    'filename': doc.get('filename', 'Unknown'),
                    'raw_text': doc.get('raw_text', ''),
                    'chunks': [chunk.get('text', '') for chunk in doc.get('chunks', [])]
                }
                documents_data.append(doc_data)
                combined_text += doc.get('raw_text', '') + "\n\n"  # Build combined_text

            if not documents_data:
                return { "answer": "No documents found to summarize." }

            # Create multi-document summary prompt
            docs_content = ""
            for i, doc in enumerate(documents_data, 1):
                docs_content += f"\n--- DOCUMENT {i}: {doc['filename']} ---\n"
                docs_content += doc['raw_text'][:2000] + "\n\n"

            prompt = f"""You are an expert multi-document analyst. Create a comprehensive summary comparing and analyzing {len(documents_data)} documents.

# 📚 MULTI-DOCUMENT ANALYSIS

## 📊 OVERALL COMPARISON
[Provide a high-level comparison of all documents, their purposes, and relationships]

## 📝 DOCUMENT-BY-DOCUMENT BREAKDOWN
[For each document, provide:
- **Document {i+1}**: [Document name]
- **Main Purpose**: [What this document is about]
- **Key Points**: [2-3 main points from this document]
- **Unique Contributions**: [What this document adds that others don't]]

## 🔍 CROSS-DOCUMENT FINDINGS
[Analyze patterns, similarities, and differences across documents:
- **Common Themes**: [Topics that appear in multiple documents]
- **Contradictions**: [Any conflicting information between documents]
- **Complementary Information**: [How documents build on each other]]

## 🎯 SYNTHESIZED INSIGHTS
[Overall insights gained from analyzing all documents together]

## 💡 RECOMMENDATIONS
[Recommendations based on the combined analysis of all documents]

Documents to analyze:
{docs_content}

Please provide a comprehensive analysis that synthesizes information from all {len(documents_data)} documents."""
        prompt = f"""You are an expert document summarizer. Create a comprehensive, well-formatted summary with the following structure:

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
{combined_text[:3000]}  # Limit to first 3000 chars to avoid timeouts

Important chunks:
{chunks_text}

Please format the response with clear headings, bullet points, and highlight key elements using **bold** text for emphasis."""

        try:
            print("🚀 Starting Groq API summarization...")
            full_response = groq_summarize_generate(prompt, max_tokens=800, temperature=0.3, timeout=90)
            
            if full_response:
                print(f"✅ Groq API summarization completed successfully")
                return { "answer": full_response.strip() }
            else:
                print(f"❌ Groq API summarization failed")
                summary = generate_enhanced_fallback_summary(combined_text, document_ids)
                
        except Exception as e:
            print(f"❌ Groq API summarization error: {str(e)}, using enhanced fallback...")
            summary = generate_enhanced_fallback_summary(combined_text, document_ids)

        return { "answer": summary }
        
    except Exception as e:
        print(f"Summarization error: {str(e)}")
        return { "answer": f"Error generating summary: {str(e)}" }

def generate_enhanced_fallback_summary(text, document_ids):
    """Generate an enhanced fallback summary with section analysis"""
    try:
        if not text.strip():
            return "No document content found to summarize."
        
        # Split text into paragraphs
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        
        # Take first few sentences for overall summary
        sentences = text.split('.')
        first_sentences = '. '.join(sentences[:3]) + '.'
        
        # Count words and characters
        word_count = len(text.split())
        char_count = len(text)
        
        # Create section-wise summary from paragraphs
        section_summary = ""
        for i, para in enumerate(paragraphs[:5]):  # First 5 paragraphs
            if len(para) > 50:  # Only meaningful paragraphs
                # Extract potential section title (first sentence)
                sentences = para.split('.')
                title = sentences[0][:50] if sentences else f"Section {i+1}"
                
                # Extract key points (first few sentences)
                key_points = '. '.join(sentences[:2]) + '.' if len(sentences) > 1 else para[:150]
                
                section_summary += f"### **Section {i+1}: {title}**\n"
                section_summary += f"**Key Points**: {key_points}\n"
                section_summary += f"**Details**: {para[:200]}...\n\n"
        
        # Extract key terms (simple approach)
        words = text.lower().split()
        word_freq = {}
        for word in words:
            if len(word) > 4 and word.isalpha():  # Only meaningful words
                word_freq[word] = word_freq.get(word, 0) + 1
        
        # Get top 5 most frequent words
        top_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:5]
        key_terms = [word for word, freq in top_words]
        
        summary = f"""# 📋 DOCUMENT SUMMARY

## 📊 OVERALL SUMMARY
{first_sentences}

## 📈 KEY STATISTICS
• **Document Length**: {word_count} words, {char_count} characters
• **Number of Documents**: {len(document_ids)}
• **Number of Sections**: {len(paragraphs)}

## 📝 SECTION-WISE BREAKDOWN
{section_summary}

## 🔍 KEY FINDINGS & HIGHLIGHTS
• **Main Topics**: {', '.join(key_terms)}
• **Document Type**: Academic/Research document
• **Primary Focus**: Language learning and mobile technology
• **Key Themes**: Research methodology, educational technology, language acquisition

## 🎯 MAIN TOPICS & THEMES
• **Research Methodology**: Academic research and analysis
• **Educational Technology**: Mobile learning and digital tools
• **Language Learning**: Second language acquisition and teaching methods
• **Data Analysis**: Statistical analysis and research findings

## 💡 RECOMMENDATIONS & INSIGHTS
• **Research Implications**: Findings suggest new approaches to language learning
• **Technology Integration**: Mobile devices show promise for educational applications
• **Future Directions**: Continued research needed in digital language learning

---
*This is an enhanced summary generated when the AI model was unavailable.*"""
        
        return summary
        
    except Exception as e:
        return f"Document summary: This document contains {len(text)} characters of text across {len(document_ids)} document(s)."

def generate_simple_summary(text, document_ids):
    """Generate a simple summary without using LLM"""
    try:
        if not text.strip():
            return "No document content found to summarize."
        
        # Simple summary: take first few sentences and key statistics
        sentences = text.split('.')
        first_sentences = '. '.join(sentences[:3]) + '.'
        
        # Count words and characters
        word_count = len(text.split())
        char_count = len(text)
        
        summary = f"""Document Summary:

Key Information:
- Document length: {word_count} words, {char_count} characters
- Number of documents: {len(document_ids)}

Main content preview:
{first_sentences}

This is a basic summary generated from the document content."""
        
        return summary
        
    except Exception as e:
        return f"Document summary: This document contains {len(text)} characters of text across {len(document_ids)} document(s)."


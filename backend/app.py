from flask import Flask, request, jsonify
from utils.intent_router import handle_query
from utils.extract_text import extract_text_from_file
from utils.text_utils import process_document
from utils.translator import translate_document_content, detect_language, translate_query
from utils.language_config import get_language_name, is_well_supported, SUPPORTED_LANGUAGES
from pymongo import MongoClient
import os
import logging
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

@app.after_request
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization,Accept'
    response.headers['Access-Control-Allow-Methods'] = 'GET,POST,OPTIONS'
    response.headers['Access-Control-Max-Age'] = '86400'
    return response

@app.route('/api/<path:path>', methods=['OPTIONS'])
def handle_options(path):
    return jsonify({}), 200

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('multilingual_app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# MongoDB setup using env vars
MONGO_URI = os.getenv("MONGO_URI")
DATABASE_NAME = os.getenv("DATABASE_NAME")
COLLECTION_NAME = os.getenv("COLLECTION_NAME")

client = MongoClient(MONGO_URI)
db = client[DATABASE_NAME]
collection = db[COLLECTION_NAME]

def process_multilingual_document(file_bytes, filename, file_ext, file_content_type):
    """
    Enhanced document processing with automatic language detection and translation
    """
    try:
        logger.info(f"🌍 Processing multilingual document: {filename} (size: {len(file_bytes)} bytes, ext: {file_ext})")
        
        # Extract text from file
        try:
            raw_text = extract_text_from_file(file_bytes, file_ext)
            logger.info(f"📝 Extracted {len(raw_text)} characters from {filename}")
            
            if not raw_text or not raw_text.strip():
                logger.warning(f"⚠️ Extracted text is empty for {filename}")
                return None, "Could not extract text from the document. The document may be empty or not contain extractable text.", None
                
        except Exception as e:
            logger.error(f"❌ Error extracting text from {filename}: {str(e)}", exc_info=True)
            return None, f"Error extracting text from document: {str(e)}", None
        
        logger.info(f"📄 Extracted {len(raw_text)} characters of text from {filename}")
        
        # Detect and translate if necessary
        translated_text, original_lang, was_translated = translate_document_content(raw_text, filename)
        
        # Process document with the translated (English) text for better embeddings
        processing_text = translated_text if was_translated else raw_text
        
        # Process document 
        document = process_document(filename, file_content_type, processing_text)
        
        # Add additional multilingual metadata that might not be in process_document
        if 'original_language' not in document:
            document['original_language'] = original_lang
        if 'was_translated' not in document:
            document['was_translated'] = was_translated
        if 'original_text' not in document and was_translated:
            document['original_text'] = raw_text
        
        # Ensure translation_info exists
        if 'translation_info' not in document:
            document['translation_info'] = {
                'original_language': original_lang,
                'translated_to': "en" if was_translated else original_lang,
                'translation_method': "groq_api" if was_translated else "none",
                'processed_at': datetime.utcnow().isoformat()
            }
        
        # Log the processing result
        lang_name = get_language_name(original_lang)
        if was_translated:
            logger.info(f"✅ Document processed and translated: {filename} ({lang_name} → English)")
            success_message = f"Document '{filename}' uploaded and translated from {lang_name} to English."
        else:
            logger.info(f"✅ Document processed: {filename} ({lang_name}, no translation needed)")
            success_message = f"Document '{filename}' uploaded successfully ({lang_name})."
        
        language_info = {
            'original_language': original_lang,
            'language_name': lang_name,
            'was_translated': was_translated,
            'is_well_supported': is_well_supported(original_lang)
        }
        
        return document, success_message, language_info
        
    except Exception as e:
        logger.error(f"❌ Error processing multilingual document {filename}: {str(e)}")
        return None, f"Error processing document: {str(e)}", None

def get_document_language_summary(document_ids):
    """
    Get a summary of languages in the uploaded documents
    """
    try:
        docs = list(collection.find({"document_id": {"$in": document_ids}}))
        
        language_summary = {
            'total_documents': len(docs),
            'translated_documents': 0,
            'original_english': 0,
            'languages': {},
            'well_supported_count': 0
        }
        
        for doc in docs:
            original_lang = doc.get('original_language', 'unknown')
            was_translated = doc.get('was_translated', False)
            
            if was_translated:
                language_summary['translated_documents'] += 1
            elif original_lang == 'en':
                language_summary['original_english'] += 1
                
            if is_well_supported(original_lang):
                language_summary['well_supported_count'] += 1
            
            lang_name = get_language_name(original_lang)
            if lang_name not in language_summary['languages']:
                language_summary['languages'][lang_name] = {
                    'count': 0,
                    'documents': [],
                    'language_code': original_lang,
                    'is_well_supported': is_well_supported(original_lang)
                }
            
            language_summary['languages'][lang_name]['count'] += 1
            language_summary['languages'][lang_name]['documents'].append({
                'filename': doc.get('filename', 'Unknown'),
                'was_translated': was_translated,
                'document_id': doc.get('document_id', 'unknown')
            })
        
        return language_summary
        
    except Exception as e:
        logger.error(f"Error getting language summary: {str(e)}")
        return None

@app.route('/api/upload', methods=['POST', 'OPTIONS'])
def upload_document():
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    try:
        logger.info("📤 Upload request received")
        logger.info(f"📋 Request files: {list(request.files.keys())}")
        logger.info(f"📋 Request form: {list(request.form.keys())}")
        
        # Log request headers for debugging
        logger.info(f"📋 Request headers: {dict(request.headers)}")
        logger.info(f"📋 Request content type: {request.content_type}")
        logger.info(f"📋 Request content length: {request.content_length}")
        logger.info(f"📋 Request method: {request.method}")
        
        # Handle multiple files
        uploaded_files = []
        
        # Check for multiple files (file0, file1, etc.)
        file_index = 0
        while f'file{file_index}' in request.files:
            file = request.files[f'file{file_index}']
            if file.filename != '':
                uploaded_files.append(file)
                logger.info(f"📄 Found file{file_index}: {file.filename} (size: {len(file.read())} bytes)")
                file.seek(0)  # Reset file pointer after reading
            file_index += 1
        
        # Also check for single file with key 'file'
        if 'file' in request.files:
            file = request.files['file']
            if file.filename != '':
                uploaded_files.append(file)
                logger.info(f"📄 Found single file: {file.filename} (size: {len(file.read())} bytes)")
                file.seek(0)  # Reset file pointer after reading
        
        if not uploaded_files:
            logger.warning("❌ No valid files found")
            return jsonify({'error': 'No files uploaded', 'details': 'No files were found in the request or all files were empty'}), 400
        
        logger.info(f"📁 Processing {len(uploaded_files)} file(s) with multilingual support")
        
        # Process all uploaded files with multilingual support
        uploaded_documents = []
        language_summary = {
            'total_processed': 0,
            'translated_count': 0,
            'languages_detected': set(),
            'processing_errors': []
        }
        
        for file in uploaded_files:
            try:
                # Get file information
                filename = file.filename
                if not filename:
                    raise ValueError("File has no name")
                    
                file_ext = os.path.splitext(filename)[1].lower()
                if not file_ext:
                    raise ValueError("File has no extension")
                    
                file_content_type = file.content_type or 'application/octet-stream'
                logger.info(f"📄 Processing file: {filename} (type: {file_content_type}, ext: {file_ext})")

                # Read file bytes for processing
                file_bytes = file.read()
                if not file_bytes:
                    raise ValueError("File is empty")

                # Process with multilingual support
                try:
                    logger.info(f"🔍 Starting to process file: {filename} (size: {len(file_bytes)} bytes)")
                    document_json, message, language_info = process_multilingual_document(
                        file_bytes, filename, file_ext, file_content_type
                    )
                    logger.info(f"✅ Successfully processed file: {filename}")
                except Exception as e:
                    logger.error(f"❌ Error processing file {filename}: {str(e)}", exc_info=True)
                    # Try to get more detailed error information
                    import traceback
                    error_details = traceback.format_exc()
                    logger.error(f"📜 Error details: {error_details}")
                    return jsonify({
                        'error': f'Failed to process file {filename}',
                        'details': str(e),
                        'traceback': error_details
                    }), 400
                
                if document_json is None:
                    language_summary['processing_errors'].append({
                        'filename': filename,
                        'error': message
                    })
                    continue
                
                logger.info(f"📄 Processing document: {document_json['filename']}")
                logger.info(f"🆔 Generated document ID: {document_json['document_id']}")

                # Store in MongoDB
                result = collection.insert_one(document_json)
                logger.info(f"💾 Document stored in MongoDB with ID: {result.inserted_id}")
                
                # Update language summary
                language_summary['total_processed'] += 1
                if language_info and language_info['was_translated']:
                    language_summary['translated_count'] += 1
                if language_info:
                    language_summary['languages_detected'].add(language_info['language_name'])
                
                uploaded_documents.append({
                    'documentId': document_json['document_id'],
                    'filename': document_json['filename'],
                    'language_info': language_info,
                    'message': message
                })
                
            except Exception as e:
                error_msg = f"Error processing {filename}: {str(e)}"
                logger.error(f"❌ {error_msg}")
                language_summary['processing_errors'].append({
                    'filename': filename,
                    'error': error_msg
                })

        if not uploaded_documents:
            return jsonify({
                'error': 'Failed to process any documents',
                'details': language_summary['processing_errors']
            }), 400

        # Prepare response with language information
        language_summary['languages_detected'] = list(language_summary['languages_detected'])
        
        if len(uploaded_documents) == 1:
            doc = uploaded_documents[0]
            response_data = {
                'message': doc['message'],
                'documentId': doc['documentId'],
                'filename': doc['filename'],
                'language_info': doc['language_info'],
                'multilingual_summary': language_summary
            }
        else:
            response_data = {
                'message': f'{len(uploaded_documents)} documents uploaded and processed successfully',
                'documentIds': [doc['documentId'] for doc in uploaded_documents],
                'filenames': [doc['filename'] for doc in uploaded_documents],
                'language_details': [doc['language_info'] for doc in uploaded_documents],
                'multilingual_summary': language_summary,
                # Keep for backward compatibility
                'documentId': uploaded_documents[0]['documentId'],
                'filename': uploaded_documents[0]['filename']
            }
        
        logger.info(f"📤 Sending response with {len(uploaded_documents)} processed documents")
        return jsonify(response_data), 200
        
    except Exception as e:
        logger.error(f"❌ Error in upload_document: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Upload failed: {str(e)}'}), 500

@app.route('/api/query', methods=['POST'])
def query_documents():
    try:
        data = request.json
        if not data:
            logger.warning("❌ No JSON data provided")
            return jsonify({'error': 'No JSON data provided'}), 400
            
        user_query = data.get('message') or data.get('query')  # Handle both 'message' and 'query' keys
        if not user_query:
            logger.warning("❌ No query or message provided")
            return jsonify({'error': 'No query or message provided'}), 400
            
        document_ids = data.get('document_ids', [])
        
        # Detect query language for logging
        query_lang = detect_language(user_query)
        query_lang_name = get_language_name(query_lang)
        
        logger.info(f"🔍 Processing query in {query_lang_name}: '{user_query}' for documents: {document_ids}")

        if not document_ids:
            logger.warning("❌ No documents uploaded yet")
            return jsonify({'error': 'No documents uploaded yet.'}), 400

        logger.info("🚀 Calling handle_query with multilingual support...")
        
        # The handle_query function now automatically handles translation
        response = handle_query(user_query, document_ids)
        
        # Add language context to response
        language_summary = get_document_language_summary(document_ids)
        if language_summary:
            response['document_languages'] = language_summary
        
        # Add query language info
        response['query_language'] = {
            'detected_language': query_lang,
            'language_name': query_lang_name,
            'is_english': query_lang == 'en'
        }
        
        logger.info(f"✅ Query completed successfully")
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"❌ Error in query_documents: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/documents/languages', methods=['POST'])
def get_document_languages():
    """
    Get detailed language information for uploaded documents
    """
    try:
        data = request.json
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
            
        document_ids = data.get('document_ids', [])
        
        if not document_ids:
            return jsonify({'error': 'document_ids are required'}), 400
        
        language_summary = get_document_language_summary(document_ids)
        
        if language_summary is None:
            return jsonify({'error': 'Could not retrieve language information'}), 500
        
        return jsonify(language_summary), 200
        
    except Exception as e:
        logger.error(f"❌ Language info retrieval failed: {str(e)}")
        return jsonify({'error': f'Language info retrieval failed: {str(e)}'}), 500

@app.route('/api/languages/supported', methods=['GET'])
def get_supported_languages():
    """
    Get list of all supported languages
    """
    try:
        supported_langs = []
        for code, name in SUPPORTED_LANGUAGES.items():
            supported_langs.append({
                'code': code,
                'name': name,
                'is_well_supported': is_well_supported(code)
            })
        
        # Sort by name
        supported_langs.sort(key=lambda x: x['name'])
        
        return jsonify({
            'total_languages': len(supported_langs),
            'well_supported_count': len([l for l in supported_langs if l['is_well_supported']]),
            'languages': supported_langs
        }), 200
        
    except Exception as e:
        logger.error(f"❌ Error getting supported languages: {str(e)}")
        return jsonify({'error': f'Failed to get supported languages: {str(e)}'}), 500

@app.route('/api/translate/test', methods=['POST'])
def test_translation():
    """
    Test endpoint for translation functionality
    """
    try:
        data = request.json
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        text = data.get('text', '')
        source_lang = data.get('source_lang', 'auto')
        target_lang = data.get('target_lang', 'en')
        
        if not text:
            return jsonify({'error': 'Text is required'}), 400
        
        # Detect language if source is auto
        if source_lang == 'auto':
            detected_lang = detect_language(text)
            source_lang = detected_lang
        
        # Translate
        from utils.translator import translate_with_groq
        translated_text = translate_with_groq(text, source_lang, target_lang)
        
        return jsonify({
            'original_text': text,
            'translated_text': translated_text,
            'source_language': source_lang,
            'source_language_name': get_language_name(source_lang),
            'target_language': target_lang,
            'target_language_name': get_language_name(target_lang),
            'translation_successful': translated_text is not None
        }), 200
        
    except Exception as e:
        logger.error(f"❌ Translation test failed: {str(e)}")
        return jsonify({'error': f'Translation test failed: {str(e)}'}), 500

@app.route('/api/health/multilingual', methods=['GET'])
def health_check_multilingual():
    """
    Health check endpoint for multilingual features
    """
    try:
        # Test language detection
        test_text = "Hello world"
        detected_lang = detect_language(test_text)
        
        # Test Groq API connection
        from utils.groq_api import test_groq_connection
        groq_status = test_groq_connection()
        
        # Get database stats
        total_docs = collection.count_documents({})
        translated_docs = collection.count_documents({"was_translated": True})
        
        # Get language distribution
        pipeline = [
            {"$group": {"_id": "$original_language", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
            {"$limit": 10}
        ]
        
        top_languages = list(collection.aggregate(pipeline))
        
        return jsonify({
            'status': 'healthy',
            'language_detection': {
                'working': detected_lang is not None,
                'test_result': detected_lang
            },
            'translation_api': {
                'groq_status': groq_status
            },
            'database_stats': {
                'total_documents': total_docs,
                'translated_documents': translated_docs,
                'top_languages': top_languages
            },
            'supported_languages_count': len(SUPPORTED_LANGUAGES),
            'timestamp': datetime.utcnow().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"❌ Health check failed: {str(e)}")
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500

if __name__ == '__main__':
    logger.info("🚀 Starting Flask app with multilingual support")
    logger.info(f"🌍 Supporting {len(SUPPORTED_LANGUAGES)} languages")

    port = int(os.environ.get('PORT', 5000))

    # Use Waitress when PORT is set (Render/production) or FLASK_ENV=production
    if os.environ.get('PORT') or os.environ.get('FLASK_ENV') == 'production':
        from waitress import serve
        logger.info(f"🚀 Starting production server with Waitress on port {port}")
        serve(app, host='0.0.0.0', port=port, threads=4)
    else:
        from werkzeug.serving import WSGIRequestHandler

        class HTTP1RequestHandler(WSGIRequestHandler):
            protocol_version = "HTTP/1.1"

        logger.info(f"🚀 Starting development server on port {port}")
        app.run(
            debug=True,
            host='0.0.0.0',
            port=port,
            threaded=True,
            request_handler=HTTP1RequestHandler,
        )
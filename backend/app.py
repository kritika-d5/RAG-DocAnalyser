import sys

# Force UTF-8 on stdout/stderr so emoji in print()/log statements don't crash
# on consoles using a legacy codec (e.g. cp1252 on Windows).
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

from flask import Flask, request, jsonify
from utils.intent_router import handle_query
from utils.extract_text import extract_text_from_file
from utils.text_utils import process_document
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
        logging.FileHandler('app.log'),
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

def process_uploaded_document(file_bytes, filename, file_ext, file_content_type):
    """
    Extract text from an uploaded file, chunk + embed it, and build the record.
    Returns (document, message). document is None on failure.
    """
    try:
        logger.info(f"📄 Processing document: {filename} (size: {len(file_bytes)} bytes, ext: {file_ext})")

        raw_text = extract_text_from_file(file_bytes, file_ext)
        logger.info(f"📝 Extracted {len(raw_text)} characters from {filename}")

        if not raw_text or not raw_text.strip():
            logger.warning(f"⚠️ Extracted text is empty for {filename}")
            return None, "Could not extract text from the document. It may be empty or image-only."

        document = process_document(filename, file_content_type, raw_text)
        logger.info(f"✅ Document processed: {filename}")
        return document, f"Document '{filename}' uploaded successfully."

    except Exception as e:
        logger.error(f"❌ Error processing document {filename}: {str(e)}", exc_info=True)
        return None, f"Error processing document: {str(e)}"

@app.route('/api/upload', methods=['POST', 'OPTIONS'])
def upload_document():
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    try:
        logger.info("📤 Upload request received")

        # Collect uploaded files (file0, file1, ... and/or a single 'file')
        uploaded_files = []
        file_index = 0
        while f'file{file_index}' in request.files:
            file = request.files[f'file{file_index}']
            if file.filename != '':
                uploaded_files.append(file)
            file_index += 1

        if 'file' in request.files and request.files['file'].filename != '':
            uploaded_files.append(request.files['file'])

        if not uploaded_files:
            logger.warning("❌ No valid files found")
            return jsonify({'error': 'No files uploaded'}), 400

        logger.info(f"📁 Processing {len(uploaded_files)} file(s)")

        uploaded_documents = []
        processing_errors = []

        for file in uploaded_files:
            filename = file.filename
            try:
                file_ext = os.path.splitext(filename)[1].lower()
                if not file_ext:
                    raise ValueError("File has no extension")

                file_content_type = file.content_type or 'application/octet-stream'
                file_bytes = file.read()
                if not file_bytes:
                    raise ValueError("File is empty")

                document_json, message = process_uploaded_document(
                    file_bytes, filename, file_ext, file_content_type
                )

                if document_json is None:
                    processing_errors.append({'filename': filename, 'error': message})
                    continue

                collection.insert_one(document_json)
                logger.info(f"💾 Stored document {document_json['document_id']} ({filename})")

                uploaded_documents.append({
                    'documentId': document_json['document_id'],
                    'filename': document_json['filename'],
                    'message': message
                })

            except Exception as e:
                error_msg = f"Error processing {filename}: {str(e)}"
                logger.error(f"❌ {error_msg}")
                processing_errors.append({'filename': filename, 'error': error_msg})

        if not uploaded_documents:
            return jsonify({
                'error': 'Failed to process any documents',
                'details': processing_errors
            }), 400

        if len(uploaded_documents) == 1:
            doc = uploaded_documents[0]
            response_data = {
                'message': doc['message'],
                'documentId': doc['documentId'],
                'filename': doc['filename']
            }
        else:
            response_data = {
                'message': f'{len(uploaded_documents)} documents uploaded successfully',
                'documentIds': [d['documentId'] for d in uploaded_documents],
                'filenames': [d['filename'] for d in uploaded_documents],
                # Keep single-doc keys for backward compatibility
                'documentId': uploaded_documents[0]['documentId'],
                'filename': uploaded_documents[0]['filename']
            }

        if processing_errors:
            response_data['processing_errors'] = processing_errors

        logger.info(f"📤 Uploaded {len(uploaded_documents)} document(s)")
        return jsonify(response_data), 200

    except Exception as e:
        logger.error(f"❌ Error in upload_document: {str(e)}", exc_info=True)
        return jsonify({'error': f'Upload failed: {str(e)}'}), 500

@app.route('/api/query', methods=['POST'])
def query_documents():
    try:
        data = request.json
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400

        # Accept both 'message' and 'query' keys
        user_query = data.get('message') or data.get('query')
        if not user_query:
            return jsonify({'error': 'No query or message provided'}), 400

        document_ids = data.get('document_ids', [])
        if not document_ids:
            return jsonify({'error': 'No documents uploaded yet.'}), 400

        logger.info(f"🔍 Processing query: '{user_query}' for documents: {document_ids}")
        response = handle_query(user_query, document_ids)
        logger.info("✅ Query completed successfully")
        return jsonify(response)

    except Exception as e:
        logger.error(f"❌ Error in query_documents: {str(e)}", exc_info=True)
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """Basic health check: DB reachability and document count."""
    try:
        collection.database.client.admin.command('ping')
        total_docs = collection.count_documents({})
        return jsonify({
            'status': 'healthy',
            'total_documents': total_docs,
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
    logger.info("🚀 Starting Flask app")

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

#!/usr/bin/env python3
"""
PDF OCR → MD Flask App
Complete frontend + backend bundled application
"""

import os
import sys
import webbrowser
import threading
import time
from pathlib import Path
from flask import Flask, render_template, request, jsonify, send_file
from werkzeug.utils import secure_filename
import tempfile

# Load environment variables
from dotenv import load_dotenv
load_dotenv('.env')
load_dotenv('../.env')  # Fallback

# Import our OCR processors
from chunked_ocr_processor import ChunkedOCRProcessor
from two_column_ocr_processor import TwoColumnOCRProcessor

app = Flask(__name__)
app.secret_key = 'pdf-ocr-md-secret-key'

# Configure upload settings
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['UPLOAD_FOLDER'] = tempfile.gettempdir()

@app.route('/')
def index():
    """Serve the main web interface."""
    return render_template('index.html')

@app.route('/process', methods=['POST'])
def process_pdf():
    """Process uploaded PDF with OCR."""
    print(f"📥 Received request - Method: {request.method}")
    print(f"📋 Content-Type: {request.content_type}")
    print(f"📊 Content-Length: {request.content_length}")
    print(f"📁 Files in request: {list(request.files.keys())}")
    print(f"📝 Form data: {list(request.form.keys())}")
    
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'No file uploaded'})
        
        file = request.files['file']
        mode = request.form.get('mode', 'chunked')
        model = request.form.get('model', 'gpt5mini')
        preserve_footnotes = request.form.get('preserve_footnotes', 'false').lower() == 'true'
        
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'})
        
        if not file.filename.lower().endswith('.pdf'):
            return jsonify({'success': False, 'error': 'Please upload a PDF file'})
        
        # Save uploaded file temporarily
        filename = secure_filename(file.filename)
        temp_path = tempfile.mktemp(suffix='.pdf')
        file.save(temp_path)
        
        # Process with appropriate OCR processor
        try:
            if mode == 'two_column':
                processor = TwoColumnOCRProcessor()
                result_path = processor.process_pdf(temp_path, start_page=1, end_page=10)  # Max 10 pages
            else:  # chunked (default)
                processor = ChunkedOCRProcessor(chunk_size=1)  # One page at a time
                
                # Enhance prompt for footnote preservation if enabled
                if preserve_footnotes:
                    processor.ocr_prompt += " CRITICAL: Do NOT create any footnote markers ([^1], [^2], etc.) unless you can clearly see actual footnote numbers or symbols in the original image that need to be preserved. Most documents have NO footnotes - only add footnote markers if you see obvious footnote references like tiny superscript numbers in the text or numbered footnote lists at the bottom. When in doubt, do NOT add footnotes."
                
                result_path = processor.process_pdf(temp_path, start_page=0, max_pages=10)
            
            # Clean up temp PDF
            os.unlink(temp_path)
            
            # Store result path for download
            result_filename = f"result_{int(time.time())}.md"
            app.config[f'result_{result_filename}'] = result_path
            
            return jsonify({
                'success': True, 
                'filename': result_filename,
                'message': 'Processing complete! Your PDF has been converted to Markdown.'
            })
            
        except Exception as e:
            # Clean up temp file on error
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            return jsonify({'success': False, 'error': f'OCR processing failed: {str(e)}'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': f'Upload error: {str(e)}'})

@app.route('/download/<filename>')
def download_file(filename):
    """Download processed Markdown file."""
    try:
        file_path = app.config.get(f'result_{filename}')
        if file_path and os.path.exists(file_path):
            return send_file(file_path, as_attachment=True, download_name=filename)
        else:
            return "File not found or expired", 404
    except Exception as e:
        return f"Download error: {str(e)}", 500

@app.route('/health')
def health_check():
    """Health check endpoint for deployment."""
    api_keys_loaded = bool(os.getenv("OPENAI_API_KEY"))
    return jsonify({
        'status': 'healthy',
        'api_keys': 'loaded' if api_keys_loaded else 'missing',
        'version': '1.0.0'
    })

def open_browser():
    """Open browser after server starts."""
    time.sleep(1.5)
    webbrowser.open('http://127.0.0.1:5000')

if __name__ == '__main__':
    print("🚀 Starting PDF OCR → MD Server")
    print("=" * 50)
    print("✅ API Keys:", "Loaded" if os.getenv("OPENAI_API_KEY") else "❌ Missing")
    print("🌐 Server starting at: http://127.0.0.1:5000")
    print("🔄 Browser will open automatically...")
    print("⚠️  Press Ctrl+C to stop")
    print("=" * 50)
    
    # Start browser in background thread
    threading.Thread(target=open_browser, daemon=True).start()
    
    # Start Flask app
    app.run(host='127.0.0.1', port=5000, debug=False)
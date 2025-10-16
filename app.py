"""PDF OCR → MD Flask App
Complete frontend + backend bundled application"""

import os
import sys
import webbrowser
import threading
import time
from pathlib import Path
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_file, g
from werkzeug.utils import secure_filename
import tempfile

# Load environment variables
from dotenv import load_dotenv
load_dotenv('.env')
load_dotenv('../.env')  # Fallback

# Import our OCR processor
from chunked_ocr_processor import ChunkedOCRProcessor

# Import authentication module
from auth import (
    require_auth,
    check_usage_limit,
    track_usage,
    get_user_subscription,
    get_monthly_usage,
    supabase
)

app = Flask(__name__)
app.secret_key = 'pdf-ocr-md-secret-key'

# Configure upload settings
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['UPLOAD_FOLDER'] = tempfile.gettempdir()

# Status tracking for processing jobs
processing_status = {}

# Workbench storage - tracks documents and their batch processing status
workbench_documents = {}

@app.route('/')
def index():
    """Serve the main web interface."""
    return render_template('index.html')

@app.route('/auth')
def auth_page():
    """Serve the authentication page."""
    return render_template('auth.html')

@app.route('/workbench')
def workbench():
    """Serve the workbench interface."""
    return render_template('workbench.html')


# ===== AUTHENTICATION ENDPOINTS =====

@app.route('/auth/signup', methods=['POST'])
def signup():
    """Register a new user."""
    if not supabase:
        return jsonify({'success': False, 'error': 'Authentication not configured'}), 503

    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        full_name = data.get('full_name')

        if not email or not password:
            return jsonify({'success': False, 'error': 'Email and password required'}), 400

        # Sign up user with Supabase
        response = supabase.auth.sign_up({
            'email': email,
            'password': password,
            'options': {
                'data': {
                    'full_name': full_name
                }
            }
        })

        if response.user:
            # Manually create user profile and subscription using admin client
            from auth import supabase_admin
            try:
                # Create user profile
                supabase_admin.table('user_profiles').insert({
                    'id': response.user.id,
                    'email': email,
                    'full_name': full_name
                }).execute()

                # Create free tier subscription
                supabase_admin.table('subscriptions').insert({
                    'user_id': response.user.id,
                    'tier': 'free',
                    'status': 'active'
                }).execute()
            except Exception as profile_error:
                print(f"Profile creation error: {profile_error}")
                # Continue anyway - profile might already exist

            return jsonify({
                'success': True,
                'message': 'Account created successfully! You can now login.',
                'user': {
                    'id': response.user.id,
                    'email': response.user.email
                }
            })
        else:
            return jsonify({'success': False, 'error': 'Signup failed'}), 400

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400


@app.route('/auth/login', methods=['POST'])
def login():
    """Login existing user."""
    if not supabase:
        return jsonify({'success': False, 'error': 'Authentication not configured'}), 503

    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')

        if not email or not password:
            return jsonify({'success': False, 'error': 'Email and password required'}), 400

        # Sign in with Supabase
        response = supabase.auth.sign_in_with_password({
            'email': email,
            'password': password
        })

        if response.session:
            return jsonify({
                'success': True,
                'session': {
                    'access_token': response.session.access_token,
                    'refresh_token': response.session.refresh_token,
                    'expires_at': response.session.expires_at
                },
                'user': {
                    'id': response.user.id,
                    'email': response.user.email
                }
            })
        else:
            return jsonify({'success': False, 'error': 'Login failed'}), 401

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 401


@app.route('/auth/logout', methods=['POST'])
@require_auth
def logout():
    """Logout current user."""
    if not supabase:
        return jsonify({'success': False, 'error': 'Authentication not configured'}), 503

    try:
        supabase.auth.sign_out()
        return jsonify({'success': True, 'message': 'Logged out successfully'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400


@app.route('/auth/user', methods=['GET'])
@require_auth
def get_current_user():
    """Get current user profile."""
    try:
        user = g.user
        subscription = get_user_subscription(user['id'])

        # Get current month usage
        now = datetime.now()
        usage = get_monthly_usage(user['id'], now.year, now.month)

        return jsonify({
            'success': True,
            'user': user,
            'subscription': subscription,
            'usage': usage
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/process', methods=['POST'])
# @require_auth  # Disabled for now - no authentication required
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
        ai_model = request.form.get('model', 'gpt-5-mini')  # Get model from form
        preserve_footnotes = request.form.get('preserve_footnotes', 'false').lower() == 'true'

        # Determine provider based on model
        if 'claude' in ai_model.lower() or 'haiku' in ai_model.lower():
            provider = 'anthropic'
        else:
            provider = 'openai'

        if file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'})

        if not file.filename.lower().endswith('.pdf'):
            return jsonify({'success': False, 'error': 'Please upload a PDF file'})

        # Save uploaded file temporarily
        filename = secure_filename(file.filename)
        temp_path = tempfile.mktemp(suffix='.pdf')
        file.save(temp_path)

        # Generate job ID
        job_id = f"job_{int(time.time())}_{os.urandom(4).hex()}"

        # Get total pages
        import fitz
        doc = fitz.open(temp_path)
        total_pages = min(len(doc), 10)  # Max 10 pages
        doc.close()

        # Check usage limits (if authenticated)
        # user_id = g.user['id']
        # allowed, error_msg = check_usage_limit(user_id, total_pages)
        # if not allowed:
        #     os.unlink(temp_path)
        #     return jsonify({'success': False, 'error': error_msg}), 403

        # Initialize status
        processing_status[job_id] = {
            'status': 'processing',
            'current_page': 0,
            'total_pages': total_pages,
            'message': 'Starting processing...'
        }

        # Start processing in background thread
        def process_in_background():
            try:
                # Status update callback
                def update_status(page_num, total, message):
                    processing_status[job_id] = {
                        'status': 'processing',
                        'current_page': page_num,
                        'total_pages': total,
                        'message': message
                    }

                processor = ChunkedOCRProcessor(chunk_size=1, provider=provider, model=ai_model)
                processor.status_callback = update_status
                result_path = processor.process_pdf(temp_path, start_page=0, max_pages=total_pages)

                # Clean up temp PDF
                os.unlink(temp_path)

                # Track usage for this user
                # track_usage(user_id, total_pages, job_id, filename, mode)  # Disabled - no auth

                # Store result
                result_filename = f"result_{int(time.time())}.md"
                app.config[f'result_{result_filename}'] = result_path

                # Update status to complete
                processing_status[job_id] = {
                    'status': 'complete',
                    'current_page': total_pages,
                    'total_pages': total_pages,
                    'message': 'Processing complete!',
                    'filename': result_filename
                }

            except Exception as e:
                # Clean up temp file on error
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
                processing_status[job_id] = {
                    'status': 'error',
                    'message': f'OCR processing failed: {str(e)}'
                }

        threading.Thread(target=process_in_background, daemon=True).start()

        return jsonify({
            'success': True,
            'job_id': job_id,
            'total_pages': total_pages,
            'message': 'Processing started'
        })

    except Exception as e:
        return jsonify({'success': False, 'error': f'Upload error: {str(e)}'})

@app.route('/status/<job_id>')
def get_status(job_id):
    """Get processing status for a job."""
    if job_id in processing_status:
        return jsonify(processing_status[job_id])
    else:
        return jsonify({'status': 'not_found', 'message': 'Job not found'}), 404

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

@app.route('/workbench/upload', methods=['POST'])
def workbench_upload():
    """Upload a PDF to the workbench for batch processing."""
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'No file uploaded'})

        file = request.files['file']
        batch_size = int(request.form.get('batch_size', 5))

        if file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'})

        if not file.filename.lower().endswith('.pdf'):
            return jsonify({'success': False, 'error': 'Please upload a PDF file'})

        # Save uploaded file
        filename = secure_filename(file.filename)
        temp_path = tempfile.mktemp(suffix='.pdf')
        file.save(temp_path)

        # Get total pages
        import fitz
        doc = fitz.open(temp_path)
        total_pages = len(doc)
        doc.close()

        # Create document ID
        doc_id = f"doc_{int(time.time())}_{os.urandom(4).hex()}"

        # Create batches
        batches = []
        for start_page in range(1, total_pages + 1, batch_size):
            end_page = min(start_page + batch_size - 1, total_pages)
            batches.append({
                'start': start_page,
                'end': end_page,
                'status': 'pending',
                'result_file': None
            })

        # Store in workbench
        workbench_documents[doc_id] = {
            'filename': filename,
            'pdf_path': temp_path,
            'total_pages': total_pages,
            'batch_size': batch_size,
            'batches': batches,
            'created_at': time.time()
        }

        return jsonify({
            'success': True,
            'doc_id': doc_id,
            'filename': filename,
            'total_pages': total_pages,
            'batches': batches
        })

    except Exception as e:
        return jsonify({'success': False, 'error': f'Upload error: {str(e)}'})

@app.route('/workbench/documents')
def workbench_list():
    """List all documents in the workbench."""
    docs = []
    for doc_id, doc_data in workbench_documents.items():
        docs.append({
            'doc_id': doc_id,
            'filename': doc_data['filename'],
            'total_pages': doc_data['total_pages'],
            'batch_size': doc_data['batch_size'],
            'batches': doc_data['batches'],
            'created_at': doc_data['created_at']
        })
    return jsonify({'documents': docs})

@app.route('/workbench/process-batch/<doc_id>/<int:batch_index>', methods=['POST'])
def workbench_process_batch(doc_id, batch_index):
    """Process a specific batch of a document."""
    try:
        if doc_id not in workbench_documents:
            return jsonify({'success': False, 'error': 'Document not found'})

        doc = workbench_documents[doc_id]
        if batch_index >= len(doc['batches']):
            return jsonify({'success': False, 'error': 'Batch index out of range'})

        batch = doc['batches'][batch_index]

        # Generate job ID
        job_id = f"job_{doc_id}_{batch_index}_{int(time.time())}"

        # Initialize status
        processing_status[job_id] = {
            'status': 'processing',
            'current_page': batch['start'],
            'total_pages': batch['end'],
            'message': 'Starting batch processing...'
        }

        # Update batch status
        batch['status'] = 'processing'

        # Capture request data before background thread (can't access request in thread)
        processing_mode = request.form.get('mode', 'chunked')

        # Start processing in background
        def process_batch_in_background():
            import traceback
            try:
                print(f"🔄 Starting background processing for batch {batch_index} of {doc_id}")

                def update_status(page_num, total, message):
                    processing_status[job_id] = {
                        'status': 'processing',
                        'current_page': page_num,
                        'total_pages': total,
                        'message': message
                    }
                    print(f"📊 Status update: {message}")

                print(f"📝 Mode: {processing_mode}, Pages: {batch['start']}-{batch['end']}")

                # Create output file path
                output_file = tempfile.mktemp(suffix='.md')
                print(f"💾 Output file: {output_file}")

                processor = ChunkedOCRProcessor(chunk_size=1)
                processor.status_callback = update_status
                # Convert to 0-indexed
                result_path = processor.process_pdf(
                    doc['pdf_path'],
                    start_page=batch['start'] - 1,
                    max_pages=batch['end'] - batch['start'] + 1,
                    output_file_override=output_file
                )

                print(f"✅ Processing complete, result at: {result_path}")

                # Store result
                result_filename = f"batch_{doc_id}_{batch_index}.md"
                app.config[f'result_{result_filename}'] = result_path

                # Update batch and status
                batch['status'] = 'completed'
                batch['result_file'] = result_filename

                processing_status[job_id] = {
                    'status': 'complete',
                    'current_page': batch['end'],
                    'total_pages': batch['end'],
                    'message': 'Batch processing complete!',
                    'filename': result_filename
                }

                print(f"✅ Batch {batch_index} marked as completed")

            except Exception as e:
                error_msg = f'Batch processing failed: {str(e)}'
                print(f"❌ ERROR: {error_msg}")
                traceback.print_exc()
                batch['status'] = 'error'
                processing_status[job_id] = {
                    'status': 'error',
                    'message': error_msg
                }

        threading.Thread(target=process_batch_in_background, daemon=True).start()

        return jsonify({
            'success': True,
            'job_id': job_id,
            'batch': batch
        })

    except Exception as e:
        return jsonify({'success': False, 'error': f'Processing error: {str(e)}'})

@app.route('/workbench/download-all/<doc_id>')
def workbench_download_all(doc_id):
    """Download all completed batches as a single markdown file."""
    try:
        if doc_id not in workbench_documents:
            return "Document not found", 404

        doc = workbench_documents[doc_id]
        combined_content = []

        for i, batch in enumerate(doc['batches']):
            if batch['status'] == 'completed' and batch['result_file']:
                file_path = app.config.get(f"result_{batch['result_file']}")
                if file_path and os.path.exists(file_path):
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        combined_content.append(f"# Pages {batch['start']}-{batch['end']}\n\n{content}")

        if not combined_content:
            return "No completed batches to download", 404

        # Create combined file
        combined_text = "\n\n---\n\n".join(combined_content)
        combined_file = tempfile.mktemp(suffix='.md')
        with open(combined_file, 'w', encoding='utf-8') as f:
            f.write(combined_text)

        return send_file(
            combined_file,
            as_attachment=True,
            download_name=f"{doc['filename'].replace('.pdf', '')}_complete.md"
        )

    except Exception as e:
        return f"Download error: {str(e)}", 500


# ===== BILLING ENDPOINTS =====

@app.route('/billing/create-checkout', methods=['POST'])
@require_auth
def create_checkout():
    """Create a Stripe checkout session for subscription upgrade."""
    from billing import create_checkout_session

    try:
        data = request.get_json()
        tier = data.get('tier')

        if tier not in ['starter', 'professional', 'enterprise']:
            return jsonify({'success': False, 'error': 'Invalid tier'}), 400

        user = g.user
        success_url = data.get('success_url', request.host_url + 'billing/success')
        cancel_url = data.get('cancel_url', request.host_url + 'billing/canceled')

        checkout_url = create_checkout_session(
            user['id'],
            user['email'],
            tier,
            success_url,
            cancel_url
        )

        if checkout_url:
            return jsonify({'success': True, 'checkout_url': checkout_url})
        else:
            return jsonify({'success': False, 'error': 'Failed to create checkout session'}), 500

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400


@app.route('/billing/portal', methods=['POST'])
@require_auth
def customer_portal():
    """Create a Stripe customer portal session for subscription management."""
    from billing import create_customer_portal_session

    try:
        user = g.user
        subscription = get_user_subscription(user['id'])

        if not subscription or not subscription.get('stripe_customer_id'):
            return jsonify({'success': False, 'error': 'No active subscription'}), 400

        return_url = request.get_json().get('return_url', request.host_url)

        portal_url = create_customer_portal_session(
            subscription['stripe_customer_id'],
            return_url
        )

        if portal_url:
            return jsonify({'success': True, 'portal_url': portal_url})
        else:
            return jsonify({'success': False, 'error': 'Failed to create portal session'}), 500

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400


@app.route('/billing/webhook', methods=['POST'])
def stripe_webhook():
    """Handle Stripe webhooks."""
    from billing import (
        verify_webhook_signature,
        handle_checkout_completed,
        handle_subscription_updated,
        handle_subscription_deleted
    )

    payload = request.data
    signature = request.headers.get('Stripe-Signature')

    event = verify_webhook_signature(payload, signature)

    if not event:
        return jsonify({'error': 'Invalid signature'}), 400

    # Handle the event
    event_type = event['type']

    if event_type == 'checkout.session.completed':
        handle_checkout_completed(event['data']['object'])
    elif event_type == 'customer.subscription.updated':
        handle_subscription_updated(event['data']['object'])
    elif event_type == 'customer.subscription.deleted':
        handle_subscription_deleted(event['data']['object'])

    return jsonify({'success': True})


@app.route('/billing/cancel', methods=['POST'])
@require_auth
def cancel_subscription_endpoint():
    """Cancel user's subscription."""
    from billing import cancel_subscription

    try:
        user = g.user
        subscription = get_user_subscription(user['id'])

        if not subscription or not subscription.get('stripe_subscription_id'):
            return jsonify({'success': False, 'error': 'No active subscription'}), 400

        data = request.get_json() or {}
        at_period_end = data.get('at_period_end', True)

        success = cancel_subscription(subscription['stripe_subscription_id'], at_period_end)

        if success:
            return jsonify({'success': True, 'message': 'Subscription canceled'})
        else:
            return jsonify({'success': False, 'error': 'Failed to cancel subscription'}), 500

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400


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

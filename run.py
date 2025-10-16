#!/usr/bin/env python3
"""
PDF OCR → MD Server Launcher
Production-ready startup script
"""

import os
from app import app

if __name__ == '__main__':
    # Get port from environment (for deployment platforms)
    port = int(os.environ.get('PORT', 5000))
    host = os.environ.get('HOST', '0.0.0.0')
    
    print("🚀 PDF OCR → MD Server Starting...")
    print(f"🌐 Running on {host}:{port}")
    print("✅ Full OCR processing enabled")
    
    # Run the Flask app
    app.run(host=host, port=port, debug=False)
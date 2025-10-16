"""
Authentication and authorization module using Supabase.
Handles user authentication, session management, and usage tracking.
"""
import os
import functools
from flask import request, jsonify, g
from supabase import create_client, Client
from typing import Optional, Dict, Any
import jwt

# Initialize Supabase client
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not all([SUPABASE_URL, SUPABASE_ANON_KEY, SUPABASE_SERVICE_KEY]):
    print("⚠️  WARNING: Supabase credentials not configured")
    supabase: Optional[Client] = None
    supabase_admin: Optional[Client] = None
else:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
    supabase_admin: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

# Usage tier limits (pages per month)
TIER_LIMITS = {
    'free': int(os.getenv('FREE_TIER_LIMIT', 50)),
    'starter': int(os.getenv('STARTER_TIER_LIMIT', 500)),
    'professional': int(os.getenv('PROFESSIONAL_TIER_LIMIT', 5000)),
    'enterprise': int(os.getenv('ENTERPRISE_TIER_LIMIT', 50000))
}


def get_user_from_token(token: str) -> Optional[Dict[str, Any]]:
    """Verify JWT token and return user data."""
    if not supabase:
        return None

    try:
        # Verify token with Supabase
        response = supabase.auth.get_user(token)
        if response and response.user:
            return {
                'id': response.user.id,
                'email': response.user.email,
                'metadata': response.user.user_metadata
            }
    except Exception as e:
        print(f"Token verification failed: {e}")
        return None

    return None


def require_auth(f):
    """Decorator to require authentication for a route."""
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        # Check for Authorization header
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'success': False, 'error': 'Authentication required'}), 401

        token = auth_header.split(' ')[1]
        user = get_user_from_token(token)

        if not user:
            return jsonify({'success': False, 'error': 'Invalid or expired token'}), 401

        # Store user in request context
        g.user = user

        return f(*args, **kwargs)

    return decorated_function


def get_user_subscription(user_id: str) -> Optional[Dict[str, Any]]:
    """Get user's current subscription details."""
    if not supabase_admin:
        return None

    try:
        response = supabase_admin.table('subscriptions').select('*').eq('user_id', user_id).single().execute()
        return response.data
    except Exception as e:
        print(f"Error fetching subscription: {e}")
        return None


def get_monthly_usage(user_id: str, year: int, month: int) -> Dict[str, int]:
    """Get user's usage for a specific month."""
    if not supabase_admin:
        return {'total_pages': 0, 'total_jobs': 0}

    try:
        response = supabase_admin.table('monthly_usage').select('*').eq('user_id', user_id).eq('year', year).eq('month', month).single().execute()
        if response.data:
            return {
                'total_pages': response.data['total_pages'],
                'total_jobs': response.data['total_jobs']
            }
    except Exception:
        pass

    return {'total_pages': 0, 'total_jobs': 0}


def check_usage_limit(user_id: str, pages_to_process: int) -> tuple[bool, Optional[str]]:
    """
    Check if user has enough quota to process pages.
    Returns (allowed: bool, error_message: Optional[str])
    """
    if not supabase_admin:
        # If Supabase not configured, allow unlimited access
        return True, None

    # Get subscription
    subscription = get_user_subscription(user_id)
    if not subscription:
        return False, "Subscription not found"

    tier = subscription['tier']
    limit = TIER_LIMITS.get(tier, TIER_LIMITS['free'])

    # Get current month usage
    from datetime import datetime
    now = datetime.now()
    usage = get_monthly_usage(user_id, now.year, now.month)

    current_usage = usage['total_pages']

    if current_usage + pages_to_process > limit:
        return False, f"Usage limit exceeded. Your {tier} plan allows {limit} pages/month. You've used {current_usage} pages."

    return True, None


def track_usage(user_id: str, pages_processed: int, job_id: str, pdf_filename: str, processing_mode: str) -> bool:
    """Record usage for a user."""
    if not supabase_admin:
        return False

    try:
        supabase_admin.table('usage_records').insert({
            'user_id': user_id,
            'pages_processed': pages_processed,
            'job_id': job_id,
            'pdf_filename': pdf_filename,
            'processing_mode': processing_mode
        }).execute()
        return True
    except Exception as e:
        print(f"Error tracking usage: {e}")
        return False


def create_user_profile(user_id: str, email: str, full_name: Optional[str] = None) -> bool:
    """Create a user profile (called after signup)."""
    if not supabase_admin:
        return False

    try:
        # Create profile
        supabase_admin.table('user_profiles').insert({
            'id': user_id,
            'email': email,
            'full_name': full_name
        }).execute()

        # Create free subscription
        supabase_admin.table('subscriptions').insert({
            'user_id': user_id,
            'tier': 'free',
            'status': 'active'
        }).execute()

        return True
    except Exception as e:
        print(f"Error creating user profile: {e}")
        return False

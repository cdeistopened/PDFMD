"""
Stripe billing integration for subscription management.
Handles payment processing, subscription creation, and webhooks.
"""
import os
import stripe
from typing import Dict, Any, Optional
from auth import supabase_admin

# Initialize Stripe
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")

# Price IDs for each tier (set these in your Stripe dashboard)
STRIPE_PRICE_IDS = {
    'starter': os.getenv('STRIPE_STARTER_PRICE_ID'),
    'professional': os.getenv('STRIPE_PROFESSIONAL_PRICE_ID'),
    'enterprise': os.getenv('STRIPE_ENTERPRISE_PRICE_ID')
}


def create_checkout_session(user_id: str, user_email: str, tier: str, success_url: str, cancel_url: str) -> Optional[str]:
    """
    Create a Stripe checkout session for subscription.
    Returns the checkout session URL.
    """
    if tier not in STRIPE_PRICE_IDS or not STRIPE_PRICE_IDS[tier]:
        raise ValueError(f"Invalid tier or price ID not configured: {tier}")

    try:
        # Create or retrieve Stripe customer
        customer = stripe.Customer.create(
            email=user_email,
            metadata={'user_id': user_id}
        )

        # Create checkout session
        session = stripe.checkout.Session.create(
            customer=customer.id,
            payment_method_types=['card'],
            line_items=[{
                'price': STRIPE_PRICE_IDS[tier],
                'quantity': 1,
            }],
            mode='subscription',
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={
                'user_id': user_id,
                'tier': tier
            }
        )

        return session.url
    except Exception as e:
        print(f"Error creating checkout session: {e}")
        return None


def create_customer_portal_session(stripe_customer_id: str, return_url: str) -> Optional[str]:
    """
    Create a Stripe customer portal session for managing subscription.
    Returns the portal session URL.
    """
    try:
        session = stripe.billing_portal.Session.create(
            customer=stripe_customer_id,
            return_url=return_url,
        )
        return session.url
    except Exception as e:
        print(f"Error creating portal session: {e}")
        return None


def handle_checkout_completed(session: Dict[str, Any]) -> bool:
    """Handle successful checkout completion."""
    try:
        user_id = session['metadata']['user_id']
        tier = session['metadata']['tier']
        customer_id = session['customer']
        subscription_id = session['subscription']

        # Retrieve subscription details
        subscription = stripe.Subscription.retrieve(subscription_id)

        # Update user subscription in database
        if supabase_admin:
            supabase_admin.table('subscriptions').update({
                'tier': tier,
                'status': 'active',
                'stripe_customer_id': customer_id,
                'stripe_subscription_id': subscription_id,
                'current_period_start': subscription.current_period_start,
                'current_period_end': subscription.current_period_end,
            }).eq('user_id', user_id).execute()

        return True
    except Exception as e:
        print(f"Error handling checkout completed: {e}")
        return False


def handle_subscription_updated(subscription: Dict[str, Any]) -> bool:
    """Handle subscription updates (renewals, changes, etc.)."""
    try:
        customer_id = subscription['customer']
        subscription_id = subscription['id']
        status = subscription['status']

        # Map Stripe status to our status
        status_map = {
            'active': 'active',
            'past_due': 'past_due',
            'canceled': 'canceled',
            'trialing': 'trialing'
        }

        db_status = status_map.get(status, 'active')

        # Update subscription in database
        if supabase_admin:
            supabase_admin.table('subscriptions').update({
                'status': db_status,
                'current_period_start': subscription['current_period_start'],
                'current_period_end': subscription['current_period_end'],
                'cancel_at_period_end': subscription.get('cancel_at_period_end', False)
            }).eq('stripe_subscription_id', subscription_id).execute()

        return True
    except Exception as e:
        print(f"Error handling subscription updated: {e}")
        return False


def handle_subscription_deleted(subscription: Dict[str, Any]) -> bool:
    """Handle subscription cancellation."""
    try:
        subscription_id = subscription['id']

        # Update subscription to canceled and downgrade to free tier
        if supabase_admin:
            supabase_admin.table('subscriptions').update({
                'tier': 'free',
                'status': 'canceled',
                'stripe_subscription_id': None,
                'current_period_start': None,
                'current_period_end': None
            }).eq('stripe_subscription_id', subscription_id).execute()

        return True
    except Exception as e:
        print(f"Error handling subscription deleted: {e}")
        return False


def verify_webhook_signature(payload: bytes, signature: str) -> Optional[Dict[str, Any]]:
    """
    Verify Stripe webhook signature and return the event.
    Returns None if verification fails.
    """
    if not STRIPE_WEBHOOK_SECRET:
        print("Warning: Stripe webhook secret not configured")
        return None

    try:
        event = stripe.Webhook.construct_event(
            payload, signature, STRIPE_WEBHOOK_SECRET
        )
        return event
    except ValueError:
        print("Invalid webhook payload")
        return None
    except stripe.error.SignatureVerificationError:
        print("Invalid webhook signature")
        return None


def cancel_subscription(stripe_subscription_id: str, at_period_end: bool = True) -> bool:
    """
    Cancel a subscription.
    If at_period_end is True, subscription remains active until period ends.
    """
    try:
        if at_period_end:
            stripe.Subscription.modify(
                stripe_subscription_id,
                cancel_at_period_end=True
            )
        else:
            stripe.Subscription.delete(stripe_subscription_id)

        return True
    except Exception as e:
        print(f"Error canceling subscription: {e}")
        return False

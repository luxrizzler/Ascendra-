"""Fail-closed Stripe billing helpers for Ascendra's proposed migration.

Staging only: this module is not imported by production routes.
No network requests, prices, subscriptions, or entitlements are changed.
"""
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from urllib.parse import urlsplit


class BillingSafetyError(Exception):
    """A generic, customer-safe validation or verification failure."""


@dataclass(frozen=True)
class CheckoutPlan:
    tier: str
    interval: str
    amount_cents: int
    origin: str


def validate_checkout(tier, interval, origin_url, tiers, allowed_origins):
    """Validate paid checkout against approved prices and exact HTTPS origins.

    Trial purchases are intentionally excluded until conflicting trial
    terms in existing routes are reconciled and approved.
    """
    if tier not in tiers or interval not in ("monthly", "annual"):
        raise BillingSafetyError("Unsupported checkout selection.")
    if not isinstance(origin_url, str):
        raise BillingSafetyError("Invalid return destination.")
    origin = origin_url.rstrip("/")
    parsed = urlsplit(origin)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise BillingSafetyError("Invalid return destination.")
    if parsed.path or parsed.query or parsed.fragment:
        raise BillingSafetyError("Invalid return destination.")
    if origin not in allowed_origins:
        raise BillingSafetyError("Return destination not approved.")
    try:
        amount = Decimal(str(tiers[tier]["price_" + interval]))
        cents = amount * 100
        if not cents.is_finite() or cents != cents.to_integral_value() or cents <= 0:
            raise BillingSafetyError("Invalid approved price.")
    except (KeyError, TypeError, ValueError, InvalidOperation) as exc:
        raise BillingSafetyError("Invalid approved price.") from exc
    return CheckoutPlan(tier, interval, int(cents), origin)


def verify_native_webhook(payload, signature, secret, stripe_sdk):
    """Require native signature verification; never fall back on failure."""
    if not payload or not signature or not secret:
        raise BillingSafetyError("Invalid webhook.")
    try:
        event = stripe_sdk.Webhook.construct_event(
            payload=payload, sig_header=signature, secret=secret
        )
    except Exception as exc:
        raise BillingSafetyError("Invalid webhook.") from exc
    if not event or not event.get("id") or not event.get("type"):
        raise BillingSafetyError("Invalid webhook.")
    return event


def subscription_id_from_event(event):
    """Never mistake an invoice identifier for a subscription identifier."""
    obj = event.get("data", {}).get("object", {})
    typ = event.get("type", "")
    if typ in ("checkout.session.completed", "invoice.paid", "invoice.payment_succeeded"):
        sub_id = obj.get("subscription")
    elif typ in ("customer.subscription.updated", "customer.subscription.deleted"):
        sub_id = obj.get("id")
    else:
        return None
    return sub_id if isinstance(sub_id, str) and sub_id.startswith("sub_") else None


def requires_entitlement_review(event):
    """Access changes need validated payment state and event deduplication."""
    return event.get("type") in {
        "checkout.session.completed", "invoice.paid", "invoice.payment_succeeded",
        "customer.subscription.updated", "customer.subscription.deleted",
    }

from types import SimpleNamespace
from pathlib import Path
import sys

# Staging-only tests; no live Stripe requests or customer mutations.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
import pytest
from billing_safety import (BillingSafetyError, validate_checkout,
                            verify_native_webhook, subscription_id_from_event,
                            requires_entitlement_review)

TIERS = {"sage": {"price_monthly": 29.99, "price_annual": 299}}
ORIGINS = {"https://ascendraacademy.com", "https://www.ascendraacademy.com"}


def test_price_and_origin():
    p = validate_checkout("sage", "annual", "https://ascendraacademy.com/", TIERS, ORIGINS)
    assert p.amount_cents == 29900 and p.origin == "https://ascendraacademy.com"


@pytest.mark.parametrize("origin", [
    "https://attacker.example", "http://ascendraacademy.com",
    "https://ascendraacademy.com.evil.example",
    "https://ascendraacademy.com/evil",
    "https://ascendraacademy.com?redirect=evil",
    "https://user:password@ascendraacademy.com", "javascript:alert(1)",
])
def test_reject_unapproved_origin(origin):
    with pytest.raises(BillingSafetyError):
        validate_checkout("sage", "monthly", origin, TIERS, ORIGINS)


@pytest.mark.parametrize("interval", ["trial", "lifetime", "", None])
def test_trial_and_unknown_terms_blocked(interval):
    with pytest.raises(BillingSafetyError):
        validate_checkout("sage", interval, "https://ascendraacademy.com", TIERS, ORIGINS)


def test_signature_required_and_fail_closed():
    sdk = SimpleNamespace(Webhook=SimpleNamespace(
        construct_event=lambda **kw: (_ for _ in ()).throw(ValueError("bad signature"))))
    with pytest.raises(BillingSafetyError, match="Invalid webhook"):
        verify_native_webhook(b"{}", "bad", "whsec_test", sdk)
    with pytest.raises(BillingSafetyError):
        verify_native_webhook(b"{}", "", "whsec_test", sdk)


def test_signed_event_parses_without_network():
    event = {"id": "evt_test", "type": "invoice.paid",
             "data": {"object": {"id": "in_test", "subscription": "sub_test"}}}
    sdk = SimpleNamespace(Webhook=SimpleNamespace(construct_event=lambda **kw: event))
    assert verify_native_webhook(b"payload", "sig", "whsec_test", sdk) == event
    assert subscription_id_from_event(event) == "sub_test"


def test_invoice_id_never_treated_as_subscription():
    event = {"type": "invoice.paid",
             "data": {"object": {"id": "in_123", "customer": "cus_123"}}}
    assert subscription_id_from_event(event) is None


def test_unknown_events_do_not_change_entitlements():
    event = {"type": "payment_intent.created", "data": {"object": {"id": "pi_123"}}}
    assert subscription_id_from_event(event) is None
    assert not requires_entitlement_review(event)


@pytest.mark.parametrize("price", [0, -1, "NaN", "Infinity", 19.995, "not-a-price"])
def test_invalid_price_rejected(price):
    tiers = {"sage": {"price_monthly": price}}
    with pytest.raises(BillingSafetyError):
        validate_checkout("sage", "monthly", "https://ascendraacademy.com", tiers, ORIGINS)


def test_unknown_tier_rejected():
    with pytest.raises(BillingSafetyError):
        validate_checkout("unknown", "monthly", "https://ascendraacademy.com", TIERS, ORIGINS)


def test_signed_but_malformed_event_rejected():
    sdk = SimpleNamespace(Webhook=SimpleNamespace(
        construct_event=lambda **kw: {"type": "invoice.paid"}))
    with pytest.raises(BillingSafetyError):
        verify_native_webhook(b"payload", "sig", "whsec_test", sdk)


def test_subscription_lifecycle_event_uses_subscription_id():
    event = {"type": "customer.subscription.deleted",
             "data": {"object": {"id": "sub_test"}}}
    assert subscription_id_from_event(event) == "sub_test"
    assert requires_entitlement_review(event)

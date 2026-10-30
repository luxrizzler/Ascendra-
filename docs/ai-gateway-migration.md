# Ascendra AI gateway migration checklist

Status: implementation branch only; production unchanged.

1. Introduce a provider-neutral interface for the AI Tutor.
2. Implement an opt-in adapter for an approved provider; credentials remain in deployment secrets.
3. Bound the conversation window (12 recent turns, with per-message length caps) instead of resending 200 turns.
4. Add per-user quotas and deployment-wide budget ceilings before enabling requests. Free tiers can have rate limits and changing terms.
5. Migrate tutor routes behind tests, preserving chat history and entitlements.
6. Replace payment wrapper with existing native Stripe SDK and verified webhooks; do not change live prices or subscriptions.
7. Remove obsolete middleware dependencies only after regression tests pass.
8. Validate checkout, renewal, refunds, webhook signatures, rate limits, and existing customer access in a non-production environment.
9. Do not merge or deploy until an approved credential is securely provisioned and rollback is documented.

No paid services, secret values, or production changes are authorized by this document.

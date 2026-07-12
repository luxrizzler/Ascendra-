# Changelog

All notable, project-level (non-code-runtime) changes to this repository will be documented here.
Runtime feature history lives in `/app/plan.md`.

## [Unreleased]

### Added
- **Fourth subscription tier: Business** ($149/mo standard, $99/mo founding for first 25 businesses)
  - `backend/server.py`: new `"business"` entry in `TIERS` dict; new `FOUNDING_BUSINESS_SEATS=25` constant; new async `_business_founding_status()` helper counts current Business subscribers from `users_col`; `/api/pricing` endpoint now annotates the Business tier with `founding_seats_used`, `founding_seats_remaining`, `founding_active`, `effective_price_monthly`, `effective_price_annual`; `"business"` added to every `Literal[...]` type union and every `["ascender","pathfinder","sage"]` list.
  - `backend/stripe_config.json`: new `"business"` entry with empty `product_id` + empty `prices.monthly/annual` and an operator note describing the manual Stripe setup steps. Empty price IDs cause the existing `/billing/checkout` to gracefully return HTTP 503 with a clear "not configured" message — no crash.
  - `frontend/src/pages/Pricing.js`: grid updated from `lg:grid-cols-3` to `md:grid-cols-2 lg:grid-cols-4 gap-4`; SEO description updated; new "FOUNDING · N/25 SEATS LEFT" badge on the Business card; strikethrough standard price + promotional price rendering when founding is active; editable marketing note explaining post-founding rate; Business CTA styled in the tier's blue palette.
  - `frontend/src/pages/Landing.js`: `FALLBACK_TIERS` array extended with the Business entry; homepage teaser grid updated from `lg:grid-cols-3` to `lg:grid-cols-4`.
  - `frontend/src/components/TierBadge.js`: added `business: "#3B82F6"` to color map.
  - `frontend/src/components/SubscriptionCard.js`: added `business: "Business"` to tier-name map.
  - `frontend/src/pages/Admin.js`, `frontend/src/pages/AdminCurriculumEdit.js`, `frontend/src/pages/AdminStudio.js`, `frontend/src/pages/AdminPathsReview.js`, `frontend/src/pages/AdminWhatsNew.js`: added `"business"` to admin tier selectors, dropdowns, and color mapping.

### Manual operator setup required (Business tier)
- Create a Business Product in Stripe Dashboard (LIVE mode).
- Create a monthly Price ($99 during founding period; $149 after 25 seats).
- Create an annual Price ($990 during founding; $1490 after 25 seats).
- Paste the two Stripe Price IDs into `backend/stripe_config.json` `tiers.business.prices`.
- Restart backend (`supervisorctl restart backend`).
- When founding seats fill, rotate the Stripe Price IDs in `stripe_config.json`.

### Organizational documentation folder `project/`
- Introduced with README, STATUS, ROADMAP, TASKS, DECISIONS, CHANGELOG, SETUP (documentation-only, no application behavior changed).

### Not changed
- Existing Ascender, Pathfinder, Sage tier definitions, prices, features, Stripe products, or subscribers.
- No Stripe products or prices were created by the build agent.
- No secrets modified, no dependencies added, no deployment triggered.
- No changes to social integrations (X, TikTok, Meta), auth, database schema, or unrelated code.

---

Future entries follow the shape:

```
## [YYYY-MM-DD]
### Added / Changed / Deprecated / Removed / Fixed / Security
- Short description with file references where relevant.
```

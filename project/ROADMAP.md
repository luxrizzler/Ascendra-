# Roadmap

Derived from `/app/plan.md` pending items and gaps evident in the codebase. Priorities reflect what unblocks user or business value fastest.

## P0 — Now

1. **Rotate secrets that transited through the setup chat.**
   - Meta App Secret (if/when Meta is re-enabled)
   - TikTok Client Secret
   - X Access Token + Access Token Secret
   *Non-code task: user regenerates in each developer portal, paste new value directly into `/app/backend/.env`, restart backend.*

2. **X posting: live smoke test.**
   - `/admin/social/x/status` reports connected.
   - Post one real thread (or dry-run) and confirm the tweet appears + budget counter decrements.

3. **TikTok connect + sandbox post.**
   - Confirm redirect URI + scopes in TikTok developer portal.
   - Complete OAuth flow via “Connect TikTok” in Settings.
   - Post a `SELF_ONLY` test video and verify status via `/admin/social/tiktok/publish/{id}/status`.

## P1 — Next

4. **Backend refactor: split `server.py` with `APIRouter`.**
   Target sub-routers: `auth`, `stripe`, `curriculum`, `practice`, `social`, `admin`, `seo`, `email`. Non-functional but reduces the ~4,900-line surface.

5. **LinkedIn auto-posting.**
   Fastest platform to gain approval. Requires: LinkedIn app + `w_member_social` scope, personal + Company Page targets, new `linkedin_publisher.py` module mirroring `meta_publisher.py` shape.

6. **Meta re-enablement decision.**
   Either commit to App Review (submit Ascendra for `pages_manage_posts` + `instagram_content_publish`) and re-surface the UI, or formally deprecate the code path.

7. **TikTok App Audit submission.**
   Required before public-visibility posts. Sandbox is fine for internal iteration.

## P2 — Later

8. **Content quality dashboard.**
   Aggregate `content_scanner.py` findings over time, surface trending outdated references, expose fix ROI.

9. **Analytics dashboard exclusions.**
   Ensure internal QA/admin accounts remain excluded from all business dashboards (already done for key ones per `plan.md`).

10. **Trophy Case social sharing.**
    Add OG images + shareable public URLs for each medal/achievement.

11. **AI training bot policy in `robots.txt`.**
    Product decision pending: unblock GPTBot / Google-Extended / ClaudeBot to appear in AI answer engines, or keep blocked to preserve content moat.

## Out of Scope (explicitly)

- Promo/discount codes (per prior product decision — no discounts offered).
- Refunds (documented in `/no-refunds`).
- Adult / restricted content categories.

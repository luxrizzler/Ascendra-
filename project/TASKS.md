# Actionable Tasks

Checklist form. Each item names the file(s) or portal-side action needed. Check off as completed.

## Environment hardening

- [ ] Rotate Meta App Secret (Meta developer portal → App Settings → Basic → Reset)
- [ ] Rotate TikTok Client Secret (TikTok developer portal → App Info → Reset Secret)
- [ ] Rotate X Access Token + Access Token Secret (Keys and tokens → Regenerate)
- [ ] Confirm `PUBLIC_BASE_URL=https://ascendraacademy.com` set in backend `.env` (used for signed URLs)
- [ ] Confirm `PUBLIC_FRONTEND_URL=https://ascendraacademy.com` set (used for OAuth return redirects)
- [ ] Confirm `SOCIAL_MEDIA_SIGNING_SECRET` set to a strong 32+ char random value

## X (Twitter) go-live

- [ ] Run `GET /api/admin/social/x/status` and confirm `ok: true` + expected `screen_name`
- [ ] Dry-run: `POST /api/admin/social/x/test-post` with `dry_run: true`
- [ ] Real post: pick a generated post at `/admin/social` and click **Post Thread Live**
- [ ] Verify budget counter decrements at `/admin/social/settings`

## TikTok go-live (sandbox)

- [ ] In TikTok developer portal, confirm redirect URI `https://ascendraacademy.com/api/social/tiktok/callback` is whitelisted
- [ ] Confirm scopes `user.info.basic`, `video.upload`, `video.publish` are enabled
- [ ] Add own TikTok account as sandbox test user
- [ ] From `/admin/social/settings`, click **Connect TikTok**
- [ ] Complete OAuth flow; verify green **Connected** badge appears
- [ ] Post one video (privacy `SELF_ONLY`) and confirm it appears in TikTok drafts/profile
- [ ] Submit for App Audit when ready to post publicly

## LinkedIn (P1 build)

- [ ] Create LinkedIn app at linkedin.com/developers
- [ ] Request scopes: `w_member_social`, `r_liteprofile`, `w_organization_social`
- [ ] Add redirect URI `https://ascendraacademy.com/api/social/linkedin/callback`
- [ ] Add `linkedin_publisher.py` following the `meta_publisher.py` shape
- [ ] Add `/api/admin/social/linkedin/*` OAuth + post endpoints in `server.py`
- [ ] Add LinkedIn `<PlatformSection>` in `AdminSocialSettings.js` and `<PlatformCard>` in `AdminSocial.js`
- [ ] Add `linkedin` fields to the platform-strip and settings response

## Backend refactor (P1)

- [ ] Extract auth routes to `backend/routers/auth.py`
- [ ] Extract stripe routes to `backend/routers/stripe.py`
- [ ] Extract curriculum routes to `backend/routers/curriculum.py`
- [ ] Extract practice routes to `backend/routers/practice.py`
- [ ] Extract social routes to `backend/routers/social.py`
- [ ] Extract admin routes to `backend/routers/admin.py`
- [ ] Mount each router in `server.py` via `include_router(...)`
- [ ] Re-run existing test suites to confirm no regressions

## Housekeeping

- [ ] Decide on GPTBot / Google-Extended / ClaudeBot policy in `frontend/public/robots.txt`
- [ ] Clean up commented dead code at `backend/server.py` lines around 4370–4390 (orphaned `snooze_drill` fragment referencing undefined `lesson_id`; ruff F821)
- [ ] Consider hiding or removing the dead X `X_CLIENT_ID` / `X_CLIENT_SECRET` env vars if they ever appear (currently kept OAuth 1.0a only)

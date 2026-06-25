"""
Resend transactional email service for Ascendra.

- Beautifully branded HTML templates (gold + dark celestial)
- Plain-text fallback
- Sandbox sender (onboarding@resend.dev) when domain not yet verified
- Verified sender (noreply@ascendraacademy.com) once DNS is wired up
- Safe in dev: logs instead of raising if RESEND_API_KEY is missing
"""
from __future__ import annotations
import os
import logging
from typing import Optional

log = logging.getLogger("ascendra.email")


def _from_address() -> str:
    """Return verified sender if configured AND likely-verified, otherwise sandbox."""
    # The verified one only works once the domain is actually verified in Resend
    # console (3 DNS records). Until then, all sends must use the sandbox
    # `onboarding@resend.dev` to avoid 403s. We toggle via an env switch.
    if os.getenv("EMAIL_FROM_VERIFIED_ENABLED", "false").lower() == "true":
        return os.getenv("EMAIL_FROM_VERIFIED") or os.getenv("EMAIL_FROM") or "Ascendra <onboarding@resend.dev>"
    return os.getenv("EMAIL_FROM") or "Ascendra <onboarding@resend.dev>"


def _resend_client():
    api_key = os.getenv("RESEND_API_KEY", "").strip()
    if not api_key:
        return None
    try:
        import resend
        resend.api_key = api_key
        return resend
    except Exception as e:
        log.warning(f"resend SDK init failed: {e}")
        return None


def _send(to: str, subject: str, html: str, text: str) -> dict:
    """Internal send. Returns {ok, id?, error?}. Never raises."""
    client = _resend_client()
    payload = {
        "from": _from_address(),
        "to": [to],
        "subject": subject,
        "html": html,
        "text": text,
    }
    if client is None:
        log.warning(f"[EMAIL DRY-RUN] No RESEND_API_KEY set. Would send to={to} subj={subject!r}")
        return {"ok": True, "dry_run": True}
    try:
        r = client.Emails.send(payload)
        log.info(f"resend ok: to={to} subj={subject!r} id={r.get('id')}")
        return {"ok": True, "id": r.get("id")}
    except Exception as e:
        log.error(f"resend failed to={to} err={e}")
        return {"ok": False, "error": str(e)}


# ──────────────────────────────────────────────────────────────────────
# Branded template (shared)
# ──────────────────────────────────────────────────────────────────────
def _shell(title: str, preheader: str, body_html: str) -> str:
    """Wrap inner body in Ascendra-branded email shell."""
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="x-apple-disable-message-reformatting">
  <title>{title}</title>
</head>
<body style="margin:0;padding:0;background:#0a0a0a;color:#EDEDED;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;">
  <!-- preheader -->
  <div style="display:none;font-size:0;line-height:0;color:transparent;opacity:0;overflow:hidden;mso-hide:all;">{preheader}</div>

  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background:#0a0a0a;padding:32px 16px;">
    <tr>
      <td align="center">
        <table role="presentation" width="540" cellpadding="0" cellspacing="0" border="0" style="max-width:540px;background:#13131A;border:1px solid #26262E;border-radius:18px;overflow:hidden;">
          <!-- header -->
          <tr>
            <td style="padding:36px 36px 8px 36px;text-align:left;">
              <div style="color:#FFB000;font-weight:900;letter-spacing:6px;font-size:14px;">ASCENDRA</div>
              <div style="width:48px;height:2px;background:#FFB000;margin-top:8px;border-radius:1px;"></div>
            </td>
          </tr>
          <!-- body -->
          <tr>
            <td style="padding:18px 36px 36px 36px;">
              {body_html}
            </td>
          </tr>
          <!-- footer -->
          <tr>
            <td style="padding:20px 36px 32px 36px;border-top:1px solid #26262E;color:#7a7a85;font-size:11px;line-height:18px;">
              You're receiving this because someone (hopefully you) requested it on
              <span style="color:#FFB000;">ascendraacademy.com</span>.<br>
              If this wasn't you, just ignore this email — no action is needed.
            </td>
          </tr>
        </table>
        <div style="color:#5a5a64;font-size:11px;margin-top:18px;">© Ascendra Academy · The path is yours to climb.</div>
      </td>
    </tr>
  </table>
</body>
</html>"""


# ──────────────────────────────────────────────────────────────────────
# Public sending functions
# ──────────────────────────────────────────────────────────────────────
def send_password_reset(to: str, name: Optional[str], reset_url: str, expires_minutes: int = 60) -> dict:
    """Magic link to reset password."""
    display = name or to.split("@")[0]
    subject = "Reset your Ascendra password"
    preheader = f"Reset your password — link expires in {expires_minutes} minutes."

    body_html = f"""
      <h1 style="margin:0 0 6px 0;color:#FFFFFF;font-size:28px;line-height:34px;letter-spacing:-0.5px;font-weight:900;">
        Reset your password
      </h1>
      <p style="margin:0 0 20px 0;color:#B8B8C2;font-size:15px;line-height:22px;">
        Hey {display}, we got a request to reset your Ascendra password.
        Tap the button below to choose a new one. The link expires in
        <strong style="color:#EDEDED;">{expires_minutes} minutes</strong> and can only be used once.
      </p>
      <table role="presentation" cellpadding="0" cellspacing="0" border="0" style="margin:18px 0 22px 0;">
        <tr>
          <td bgcolor="#FFB000" style="border-radius:12px;">
            <a href="{reset_url}"
               style="display:inline-block;padding:14px 26px;color:#000000;font-weight:800;font-size:15px;text-decoration:none;border-radius:12px;">
              Reset password →
            </a>
          </td>
        </tr>
      </table>
      <p style="margin:8px 0 0 0;color:#7a7a85;font-size:12px;line-height:18px;">
        Or copy &amp; paste this URL into your browser:<br>
        <a href="{reset_url}" style="color:#FFB000;text-decoration:none;word-break:break-all;">{reset_url}</a>
      </p>
      <p style="margin:24px 0 0 0;color:#7a7a85;font-size:12px;line-height:18px;">
        Didn't ask for this? You can safely ignore this email — your password won't change.
      </p>
    """

    text = (
        f"Hey {display}, reset your Ascendra password by visiting:\n\n"
        f"{reset_url}\n\n"
        f"This link expires in {expires_minutes} minutes and can only be used once.\n"
        f"If you didn't request this, ignore this email — nothing will change."
    )
    return _send(to, subject, _shell(subject, preheader, body_html), text)


def send_checkout_success(to: str, name: Optional[str], tier: str, interval: str,
                            amount_usd: float, dashboard_url: str) -> dict:
    """Welcome email triggered when a checkout payment is confirmed."""
    display = name or to.split("@")[0]
    tier_upper = (tier or "ascender").upper()
    blurbs = {
        "ASCENDER": "You've unlocked Ascender — the path begins.",
        "PATHFINDER": "Welcome to Pathfinder. Seven paths are now yours.",
        "SAGE": "Welcome, Sage. Every path. Every founder playbook. Yours.",
    }
    headline = blurbs.get(tier_upper, f"Welcome to {tier_upper}.")
    period_label = {"monthly": "monthly", "annual": "annual (12 months)", "trial": "7-day trial"}.get(interval, interval)
    subject = f"You're in. Welcome to Ascendra {tier_upper}."
    preheader = f"Your {tier_upper} access is active. Time to rise."

    body_html = f"""
      <h1 style="margin:0 0 6px 0;color:#FFFFFF;font-size:28px;line-height:34px;letter-spacing:-0.5px;font-weight:900;">
        {headline}
      </h1>
      <p style="margin:0 0 18px 0;color:#B8B8C2;font-size:15px;line-height:22px;">
        Hey {display} — your payment came through, and your full Ascendra
        <strong style="color:#FFB000;">{tier_upper}</strong> access is now live.
        Open the dashboard to pick up where you left off — or start your first path.
      </p>

      <div style="margin:18px 0;padding:18px;background:#0d0d12;border:1px solid #26262E;border-radius:12px;">
        <div style="color:#7a7a85;font-size:11px;letter-spacing:1.5px;font-weight:700;">RECEIPT</div>
        <div style="margin-top:10px;color:#EDEDED;font-size:14px;">
          <span style="color:#7a7a85;">Plan:</span> <strong>Ascendra {tier_upper}</strong>
        </div>
        <div style="margin-top:6px;color:#EDEDED;font-size:14px;">
          <span style="color:#7a7a85;">Billing:</span> {period_label}
        </div>
        <div style="margin-top:6px;color:#EDEDED;font-size:14px;">
          <span style="color:#7a7a85;">Amount:</span>
          <strong style="color:#FFB000;">${amount_usd:.2f} USD</strong>
        </div>
      </div>

      <table role="presentation" cellpadding="0" cellspacing="0" border="0" style="margin:14px 0 22px 0;">
        <tr>
          <td bgcolor="#FFB000" style="border-radius:12px;">
            <a href="{dashboard_url}"
               style="display:inline-block;padding:14px 26px;color:#000000;font-weight:800;font-size:15px;text-decoration:none;border-radius:12px;">
              Open my dashboard →
            </a>
          </td>
        </tr>
      </table>

      <p style="margin:18px 0 0 0;color:#B8B8C2;font-size:14px;line-height:21px;">
        Quick wins for day one:
      </p>
      <ul style="margin:8px 0 14px 0;padding-left:18px;color:#B8B8C2;font-size:14px;line-height:22px;">
        <li>Open one lesson — even 5 minutes builds the streak.</li>
        <li>Ask the AI Tutor anything (it remembers across sessions).</li>
        <li>Pick the path that maps to your goal — the rest can wait.</li>
      </ul>

      <p style="margin:18px 0 0 0;color:#7a7a85;font-size:12px;line-height:18px;">
        Need help or have a question? Just reply to this email.
      </p>
    """
    text = (
        f"Hey {display}, your Ascendra {tier_upper} access is now live.\n\n"
        f"Plan:    Ascendra {tier_upper}\n"
        f"Billing: {period_label}\n"
        f"Amount:  ${amount_usd:.2f} USD\n\n"
        f"Open dashboard: {dashboard_url}\n\n"
        f"Quick wins for day one:\n"
        f"- Open one lesson (even 5 min builds the streak)\n"
        f"- Ask the AI Tutor anything\n"
        f"- Pick the path that maps to your goal\n\n"
        f"Reply to this email if you need anything."
    )
    return _send(to, subject, _shell(subject, preheader, body_html), text)



def send_digest(to: str, published: list, drafted: list, failed: list) -> dict:
    """Daily auto-pilot digest for admins."""
    total = len(published) + len(drafted) + len(failed)
    subject = f"Ascendra auto-pilot · {len(published)} live, {len(drafted)} drafts, {len(failed)} failed"
    preheader = f"Last 24h: {total} runs · {len(published)} published"

    def _rows(items: list, color: str) -> str:
        if not items:
            return f'<div style="color:#7a7a85;font-size:12px;margin:6px 0;">None.</div>'
        out = []
        for it in items[:20]:
            s = it.get("summary", {})
            topic = s.get("topic", "(no topic)")
            grades = s.get("grades", {})
            grade_str = ""
            if grades:
                grade_str = (f' &nbsp; <span style="color:#7a7a85;font-size:11px;">'
                             f'acc {grades.get("accuracy","?")} · cl {grades.get("clarity","?")} · '
                             f'br {grades.get("brand_fit","?")} · dp {grades.get("depth","?")}</span>')
            out.append(
                f'<div style="padding:8px 10px;background:#0d0d12;border:1px solid #26262E;border-radius:8px;margin:6px 0;color:#EDEDED;font-size:13px;">'
                f'<span style="color:{color};font-weight:800;">•</span> {topic}{grade_str}'
                f'</div>'
            )
        return "".join(out)

    body_html = f"""
      <h1 style="margin:0 0 6px 0;color:#FFFFFF;font-size:28px;line-height:34px;letter-spacing:-0.5px;font-weight:900;">Auto-pilot digest</h1>
      <p style="margin:0 0 18px 0;color:#B8B8C2;font-size:14px;">Last 24 hours of automated content generation.</p>

      <div style="margin:16px 0;color:#34D399;font-size:12px;font-weight:800;letter-spacing:1.5px;">PUBLISHED ({len(published)})</div>
      {_rows(published, "#34D399")}

      <div style="margin:18px 0 6px 0;color:#FFB000;font-size:12px;font-weight:800;letter-spacing:1.5px;">FLAGGED FOR REVIEW ({len(drafted)})</div>
      {_rows(drafted, "#FFB000")}

      <div style="margin:18px 0 6px 0;color:#FB7185;font-size:12px;font-weight:800;letter-spacing:1.5px;">FAILED ({len(failed)})</div>
      {_rows(failed, "#FB7185")}

      <p style="margin:22px 0 0 0;color:#7a7a85;font-size:12px;">Review flagged items in <a href="https://repo-to-site-2.preview.emergentagent.com/admin/auto-content" style="color:#FFB000;">/admin/auto-content</a>.</p>
    """
    text = (
        f"Auto-pilot digest — last 24 hours\n"
        f"Published: {len(published)}\nFlagged for review: {len(drafted)}\nFailed: {len(failed)}\n"
        f"Review: https://repo-to-site-2.preview.emergentagent.com/admin/auto-content\n"
    )
    return _send(to, subject, _shell(subject, preheader, body_html), text)


def send_renewal_reminder(
    to: str,
    name: Optional[str],
    tier: str,
    interval: str,           # "monthly" | "annual"
    renewal_date_str: str,   # e.g. "January 8, 2026"
    amount_usd: float,
    portal_url: str,
    days_until: int = 7,
) -> dict:
    """Renewal reminder, sent ~7 days before next Stripe invoice charges."""
    display = name or to.split("@")[0]
    tier_upper = (tier or "ascender").upper()
    cycle = "yearly" if interval == "annual" else "monthly"
    subject = f"Heads up — your Ascendra {tier_upper} renews in {days_until} days"
    preheader = f"Renewal in {days_until} days · ${amount_usd:.2f} {cycle}"

    body_html = f"""
      <h1 style="margin:0 0 6px 0;color:#FFFFFF;font-size:28px;line-height:34px;letter-spacing:-0.5px;font-weight:900;">
        Your plan renews in {days_until} days
      </h1>
      <p style="margin:0 0 18px 0;color:#B8B8C2;font-size:15px;line-height:22px;">
        Hey {display} — quick heads up that your Ascendra
        <strong style="color:#FFB000;">{tier_upper}</strong> plan will automatically
        renew on <strong style="color:#EDEDED;">{renewal_date_str}</strong>. No action
        needed if you'd like to keep climbing.
      </p>

      <div style="margin:18px 0;padding:18px;background:#0d0d12;border:1px solid #26262E;border-radius:12px;">
        <div style="color:#7a7a85;font-size:11px;letter-spacing:1.5px;font-weight:700;">UPCOMING CHARGE</div>
        <div style="margin-top:10px;color:#EDEDED;font-size:14px;">
          <span style="color:#7a7a85;">Plan:</span> <strong>Ascendra {tier_upper}</strong>
        </div>
        <div style="margin-top:6px;color:#EDEDED;font-size:14px;">
          <span style="color:#7a7a85;">Billing:</span> {cycle}
        </div>
        <div style="margin-top:6px;color:#EDEDED;font-size:14px;">
          <span style="color:#7a7a85;">Amount:</span>
          <strong style="color:#FFB000;">${amount_usd:.2f} USD</strong>
        </div>
        <div style="margin-top:6px;color:#EDEDED;font-size:14px;">
          <span style="color:#7a7a85;">Charges on:</span> {renewal_date_str}
        </div>
      </div>

      <p style="margin:0 0 12px 0;color:#B8B8C2;font-size:14px;line-height:21px;">
        Want to update your card, change plan, or cancel? You can do all of that
        in one click from the billing portal:
      </p>

      <table role="presentation" cellpadding="0" cellspacing="0" border="0" style="margin:14px 0 22px 0;">
        <tr>
          <td bgcolor="#FFB000" style="border-radius:12px;">
            <a href="{portal_url}"
               style="display:inline-block;padding:14px 26px;color:#000000;font-weight:800;font-size:15px;text-decoration:none;border-radius:12px;">
              Manage billing →
            </a>
          </td>
        </tr>
      </table>

      <p style="margin:18px 0 0 0;color:#7a7a85;font-size:12px;line-height:18px;">
        If you cancel before {renewal_date_str}, you keep your {tier_upper} access until
        that date — and you won't be charged again. Reply to this email if you need a hand.
      </p>
    """
    text = (
        f"Hey {display},\n\n"
        f"Heads up — your Ascendra {tier_upper} plan will automatically renew on {renewal_date_str}.\n\n"
        f"Plan:        Ascendra {tier_upper}\n"
        f"Billing:     {cycle}\n"
        f"Amount:      ${amount_usd:.2f} USD\n"
        f"Charges on:  {renewal_date_str}\n\n"
        f"Want to update your card, change plan, or cancel? Manage billing here:\n{portal_url}\n\n"
        f"If you cancel before {renewal_date_str}, you keep {tier_upper} access until that date "
        f"and you won't be charged again."
    )
    return _send(to, subject, _shell(subject, preheader, body_html), text)


def send_invite(to: str, name: Optional[str], temp_password: str, login_url: str,
                  invited_by: Optional[str] = None, tier: str = "sage") -> dict:
    """Welcome / invite email with one-time temp password."""
    display = name or to.split("@")[0]
    subject = "Your Ascendra Academy invite"
    preheader = f"Your {tier.upper()} access is ready — first-time password inside."
    by_line = f" by {invited_by}" if invited_by else ""

    body_html = f"""
      <h1 style="margin:0 0 6px 0;color:#FFFFFF;font-size:28px;line-height:34px;letter-spacing:-0.5px;font-weight:900;">
        You're in. Welcome.
      </h1>
      <p style="margin:0 0 18px 0;color:#B8B8C2;font-size:15px;line-height:22px;">
        Hey {display} — you've been invited{by_line} to <strong style="color:#FFB000;">Ascendra Academy</strong>
        with full <strong>{tier.upper()}</strong> access. Hands-on AI mastery, from fundamentals
        to building a real business with AI.
      </p>
      <div style="margin:18px 0;padding:18px;background:#0d0d12;border:1px solid #26262E;border-radius:12px;">
        <div style="color:#7a7a85;font-size:11px;letter-spacing:1.5px;font-weight:700;">YOUR LOGIN</div>
        <div style="margin-top:10px;color:#EDEDED;font-size:14px;">
          <span style="color:#7a7a85;">Email:</span> <strong>{to}</strong>
        </div>
        <div style="margin-top:6px;color:#EDEDED;font-size:14px;">
          <span style="color:#7a7a85;">Temp password:</span>
          <code style="background:#26262E;padding:3px 8px;border-radius:6px;color:#FFB000;font-family:ui-monospace,Menlo,monospace;">{temp_password}</code>
        </div>
        <div style="margin-top:10px;color:#7a7a85;font-size:11px;line-height:16px;">
          You'll be prompted to change this on your first sign-in.
        </div>
      </div>
      <table role="presentation" cellpadding="0" cellspacing="0" border="0" style="margin:14px 0 22px 0;">
        <tr>
          <td bgcolor="#FFB000" style="border-radius:12px;">
            <a href="{login_url}"
               style="display:inline-block;padding:14px 26px;color:#000000;font-weight:800;font-size:15px;text-decoration:none;border-radius:12px;">
              Sign in to Ascendra →
            </a>
          </td>
        </tr>
      </table>
      <p style="margin:18px 0 0 0;color:#7a7a85;font-size:12px;line-height:18px;">
        Or paste this into your browser:<br>
        <a href="{login_url}" style="color:#FFB000;text-decoration:none;word-break:break-all;">{login_url}</a>
      </p>
    """
    text = (
        f"Welcome to Ascendra Academy, {display}!\n\n"
        f"You've been invited{by_line} with {tier.upper()} access.\n\n"
        f"Email:         {to}\n"
        f"Temp password: {temp_password}\n\n"
        f"Sign in: {login_url}\n\n"
        f"You'll be asked to choose a new password on first login."
    )
    return _send(to, subject, _shell(subject, preheader, body_html), text)

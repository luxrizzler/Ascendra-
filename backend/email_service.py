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
